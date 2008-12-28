#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import fallback_import_paths

import os
import sys
import re
import codecs
import time
import datetime
import locale
from optparse import OptionParser
from ConfigParser import SafeConfigParser

from pology.misc.report import report, warning, error
from pology.misc.msgreport import warning_on_msg
from pology.misc.fsops import collect_catalogs, mkdirpath, join_ncwd
from pology.misc.vcs import make_vcs
from pology.file.catalog import Catalog
from pology.file.message import Message
from pology.misc.monitored import Monlist, Monset
from pology.misc.wrap import wrap_field_ontag_unwrap
from pology.misc.tabulate import tabulate
from pology.misc.langdep import get_hook_lreq

WRAPF = wrap_field_ontag_unwrap
UFUZZ = "fuzzy"


def main ():

    locale.setlocale(locale.LC_ALL, "")

    # Setup options and parse the command line.
    usage = (
        u"%prog [OPTIONS] [MODE] [MODEARGS] [PATHS...]")
    description = (
        u"Keep track of who, when, and how, has translated, modified, "
        u"or reviewed messages in a collection of PO files.")
    version = (
        u"%prog (Pology) experimental\n"
        u"Copyright © 2008 Chusslove Illich (Часлав Илић) "
        u"<caslav.ilic@gmx.net>\n")

    opars = OptionParser(usage=usage, description=description, version=version)
    opars.add_option(
        "--no-psyco",
        action="store_false", dest="use_psyco", default=True,
        help="do not try to use Psyco specializing compiler")
    opars.add_option(
        "-s", "--select", metavar="SELECTOR[:ARGS]",
        action="append", dest="selectors", default=[],
        help="consider only messages matched by this selector. "
             "Can be repeated, AND-semantics.")
    opars.add_option(
        "-a", "--select-ascription", metavar="SELECTOR[:ARGS]",
        action="append", dest="aselectors", default=[],
        help="select message from ascription history by this selector "
             "(relevant in some modes). "
             "Can be repeated, AND-semantics.")
    opars.add_option(
        "-f", "--filter", metavar="NAME",
        action="store", dest="text_filter", default=None,
        help="pass relevent message text fields through a filter before "
             "matching or comparing them "
             "(relevant in some modes)")
    opars.add_option(
        "-t", "--tag", metavar="TAG",
        action="store", dest="tag", default=None,
        help="tag to add or consider in ascription records "
             "(relevant in some modes)")
    opars.add_option(
        "-v", "--verbose",
        action="store_true", dest="verbose", default=False,
        help="output more detailed progress info")
    (options, free_args) = opars.parse_args()

    # Could use some speedup.
    if options.use_psyco:
        try:
            import psyco
            psyco.full()
        except ImportError:
            pass

    # Fetch filter if requested, store it in options.
    options.tfilter = None
    if options.text_filter:
        options.tfilter = get_hook_lreq(options.text_filter, abort=True)

    # Create selectors if any explicitly given.
    selector = None
    if options.selectors:
        selector = build_selector(options, options.selectors)
    aselector = None
    if options.aselectors:
        aselector = build_selector(options, options.aselectors, hist=True)

    # Parse operation mode and its arguments.
    if len(free_args) < 1:
        error("operation mode not given")
    class Mode: pass
    mode = Mode()
    mode.name = free_args.pop(0)
    if 0: pass
    elif mode.name in ("status", "st"):
        execute_operation = examine_state
        mode.selector = selector or build_selector(options, ["any"])
    elif mode.name in ("modified", "mo"):
        if len(free_args) < 1:
            error("no user to whom to ascribe modifications given")
        mode.user = free_args.pop(0)
        mode.selector = selector or build_selector(options, ["any"])
        execute_operation = ascribe_modified
    elif mode.name in ("reviewed", "re"):
        if len(free_args) < 1:
            error("no user to whom to ascribe reviews given")
        mode.user = free_args.pop(0)
        execute_operation = ascribe_reviewed
        # Default selector for review ascription must match
        # default selector for review selection.
        mode.selector = selector or build_selector(options, ["nwasc"])
    elif mode.name in ("post-merge", "pm"):
        execute_operation = ascribe_postmerge
        mode.selector = selector or build_selector(options, ["any"])
    elif mode.name in ("diff", "di"):
        execute_operation = diff_select
        # Default selector for review selection must match
        # default selector for review ascription.
        mode.selector = selector or build_selector(options, ["nwasc"])
        # Build default ascription selector only if neither selector
        # is explicitly given, since explicit basic selector may be used for
        # ascription selection in a suitable sense (see diff_select_cat()).
        if not selector and not aselector:
            mode.aselector = build_selector(options, ["asc"], hist=True)
        else:
            mode.aselector = aselector
    elif mode.name in ("clear-review", "cr"):
        execute_operation = clear_review
        mode.selector = selector or build_selector(options, ["any"])
    else:
        error("unknown operation mode '%s'" % mode.name)

    # For each path:
    # - determine its associated ascription config,
    # - collect all catalogs.
    paths = [join_ncwd(x) for x in free_args]
    if not paths:
        paths = ["."]
    configs_loaded = {}
    configs_catpaths = []
    for path in paths:
        # Look for the first config file up the directory tree.
        parent = os.path.abspath(path)
        if os.path.isfile(parent):
            parent = os.path.dirname(parent)
        while True:
            cfgpath = os.path.join(parent, "ascribe")
            if os.path.isfile(cfgpath):
                break
            else:
                cfgpath = ""
            pparent = parent
            parent = os.path.dirname(parent)
            if parent == pparent:
                break
        if not cfgpath:
            error("cannot find ascription configuration for path: %s" % path)
        cfgpath = rel_path(os.getcwd(), cfgpath) # for nicer message output
        config = configs_loaded.get(cfgpath, None)
        if not config:
            # New config, load.
            config = Config(cfgpath)
            configs_loaded[cfgpath] = config

        # Collect PO files.
        if os.path.isdir(path):
            catpaths = collect_catalogs(path)
        else:
            catpaths = [path]

        # Collect the config and corresponding catalogs.
        configs_catpaths.append((config, catpaths))

    # Execute operation.
    execute_operation(options, configs_catpaths, mode)


def rel_path (ref_path, rel_path):

    if os.path.isabs(rel_path):
        path = rel_path
    else:
        ref_dir = os.path.dirname(ref_path)
        path = join_ncwd(ref_dir, rel_path)
    return path


class Config:

    def __init__ (self, cpath):

        config = SafeConfigParser()
        ifl = codecs.open(cpath, "r", "UTF-8")
        config.readfp(ifl)
        ifl.close()

        self.path = cpath

        gsect = dict(config.items("global"))
        self.catroot = rel_path(cpath, gsect.get("catalog-root", ""))
        self.ascroot = rel_path(cpath, gsect.get("ascript-root", ""))
        if self.catroot == self.ascroot:
            error("%s: catalog root and ascription root "
                  "resolve to same path: %s" % (cpath, self.catroot))

        self.lang_team = gsect.get("language-team")
        self.team_email = gsect.get("team-email")
        self.plural_header = gsect.get("plural-header")

        self.vcs = make_vcs(gsect.get("version-control", "noop"))

        class UserData: pass
        self.udata = {}
        self.users = []
        userst = "user-"
        for section in config.sections():
            if section.startswith(userst):
                user = section[len(userst):]
                usect = dict(config.items(section))
                if user in self.users:
                    error("%s: repeated user: %s" % (cpath, user))
                udat = UserData()
                self.udata[user] = udat
                self.users.append(user)
                udat.ascroot = os.path.join(self.ascroot, user)
                if "name" not in usect:
                    error("%s: user '%s' misses the name" % (cpath, user))
                udat.name = usect.get("name")
                if udat.name == UFUZZ:
                    error("%s: user name '%s' is reserved" % (cpath, UFUZZ))
                udat.oname = usect.get("original-name")
                udat.email = usect.get("email")
        self.users.sort()

        # Create fuzzy-user.
        udat = UserData()
        self.udata[UFUZZ] = udat
        self.users.append(UFUZZ)
        udat.ascroot = os.path.join(self.ascroot, UFUZZ)
        udat.name = "Fuzzy"
        udat.oname = None
        udat.email = None


def examine_state (options, configs_catpaths, mode):

    stest = mode.selector

    # Count unascribed messages through catalogs.
    unasc_trans_by_cat = {}
    unasc_fuzzy_by_cat = {}
    for config, catpaths in configs_catpaths:
        for catpath in catpaths:
            # Open current and all ascription catalogs.
            cat = Catalog(catpath, monitored=False)
            acats = collect_asc_cats(config, cat.name)
            # Count non-ascribed.
            for msg in cat:
                if msg.translated:
                    unasc_by_cat = unasc_trans_by_cat
                elif msg.fuzzy:
                    unasc_by_cat = unasc_fuzzy_by_cat
                else:
                    continue
                if is_ascribed(msg, acats):
                    continue
                history = asc_collect_history(msg, acats, config)
                if stest(msg, cat, history, config, options) is None:
                    continue
                if catpath not in unasc_by_cat:
                    unasc_by_cat[catpath] = 0
                unasc_by_cat[catpath] += 1

    # Present findings.
    for unasc_cnts, chead in (
        (unasc_trans_by_cat, "Unascribed translated"),
        (unasc_fuzzy_by_cat, "Unascribed fuzzy"),
    ):
        if not unasc_cnts:
            continue
        nunasc = reduce(lambda s, x: s + x, unasc_cnts.itervalues())
        ncats = len(unasc_cnts)
        report("===? %s: %d entries in %d catalogs" % (chead, nunasc, ncats))
        catnames = unasc_cnts.keys()
        catnames.sort()
        rown = catnames
        data = [[unasc_cnts[x] for x in catnames]]
        report(tabulate(data=data, rown=rown, indent="  "))


def ascribe_modified (options, configs_catpaths, mode):

    user = mode.user

    if user == UFUZZ:
        error("cannot ascribe modifications to reserved user '%s'" % UFUZZ)

    nasc = 0
    for config, catpaths in configs_catpaths:
        if user not in config.users:
            error("unknown user '%s' in config '%s'" % (user, config.path))

        mkdirpath(config.udata[user].ascroot)

        for catpath in catpaths:
            nasc += ascribe_modified_cat(options, config, user, catpath,
                                         mode.selector)

    if nasc > 0:
        report("===! Ascribed as modified: %d entries" % nasc)


def ascribe_reviewed (options, configs_catpaths, mode):

    user = mode.user
    stest = mode.selector

    if user == UFUZZ:
        error("cannot ascribe reviews to reserved user '%s'" % UFUZZ)

    nasc = 0
    for config, catpaths in configs_catpaths:
        if user not in config.users:
            error("unknown user '%s' in config '%s'" % (user, config.path))

        mkdirpath(config.udata[user].ascroot)

        for catpath in catpaths:
            nasc += ascribe_reviewed_cat(options, config, user, catpath, stest)

    if nasc > 0:
        report("===! Ascribed as reviewed: %d entries" % nasc)


def ascribe_postmerge (options, configs_catpaths, mode):

    stest = mode.selector

    nasc = 0
    for config, catpaths in configs_catpaths:

        mkdirpath(config.udata[UFUZZ].ascroot)

        for catpath in catpaths:
            nasc += ascribe_modified_cat(options, config, UFUZZ, catpath, stest)

    if nasc > 0:
        report("===! Ascribed as modified (fuzzy): %d entries" % nasc)


def diff_select (options, configs_catpaths, mode):

    stest = mode.selector
    aselect = mode.aselector
    pfilter = options.tfilter

    ndiffed = 0
    for config, catpaths in configs_catpaths:
        for catpath in catpaths:
            ndiffed += diff_select_cat(options, config, catpath,
                                       stest, aselect, pfilter)

    if ndiffed > 0:
        report("===! Diffed from history: %d" % ndiffed)


def clear_review (options, configs_catpaths, mode):

    stest = mode.selector

    ncleared = 0
    for config, catpaths in configs_catpaths:
        for catpath in catpaths:
            ncleared += clear_review_cat(options, config, catpath, stest)

    if ncleared > 0:
        report("===! Cleared review states: %d" % ncleared)


def ascribe_modified_cat (options, config, user, catpath, stest):

    # Open current catalog and all ascription catalogs.
    cat = Catalog(catpath, monitored=False, wrapf=WRAPF)
    acats = collect_asc_cats(config, cat.name, user)

    # Collect all translated (or fuzzy) and unascribed messages.
    unasc_msgs = []
    for msg in cat:
        if is_ascribed(msg, acats):
            continue
        history = asc_collect_history(msg, acats, config)
        if stest(msg, cat, history, config, options) is None:
            continue
        if (   (user != UFUZZ and not msg.translated)
            or (user == UFUZZ and not msg.fuzzy)
        ):
            continue
        unasc_msgs.append(msg)

    if not unasc_msgs:
        # No messages to ascribe.
        return 0

    if not config.vcs.is_clear(cat.filename):
        warning("%s: VCS state not clear, cannot ascribe modifications"
                % cat.filename)
        return 0

    # Create ascription catalog for this user if not existing already.
    acat = acats.get(user)
    if not acat:
        acat = init_asc_cat(cat.name, user, config)
    else:
        update_asc_hdr(acat, user, config)

    # Current VCS revision of the catalog.
    catrev = config.vcs.revision(cat.filename)

    # Ascribe messages: add or modify if existing.
    for msg in unasc_msgs:
        if msg not in acat:
            # Copy ID elements of the original message.
            amsg = Message()
            amsg.msgctxt = msg.msgctxt
            amsg.msgid = msg.msgid
            # Append to the end of catalog.
            pos = acat.add(amsg, -1)
        else:
            # Retrieve existing ascribed message.
            amsg = acat[msg]

        # Copy desired non-ID elements.
        amsg.msgid_plural = msg.msgid_plural
        if msg.fuzzy:
            amsg.fuzzy = True
            amsg.msgctxt_previous = msg.msgctxt_previous
            amsg.msgid_previous = msg.msgid_previous
            amsg.msgid_plural_previous = msg.msgid_plural_previous
        amsg.msgstr = Monlist(msg.msgstr)

        # Ascribe modification of the message.
        ascribe_msg_mod(amsg, user, config, catrev)

    if sync_and_rep(acat):
        config.vcs.add(acat.filename)

    return len(unasc_msgs)


_revdflags = ("revd", "reviewed")
_revdflag_rx = re.compile(r"^(?:%s) *[/:]?(.*)" % "|".join(_revdflags), re.I)

def ascribe_reviewed_cat (options, config, user, catpath, stest):

    # Open current catalog and all ascription catalogs.
    # Monitored, for removal of reviewed-* flags.
    cat = Catalog(catpath, monitored=True, wrapf=WRAPF)
    acats = collect_asc_cats(config, cat.name, user)

    rev_msgs_tags = []
    non_mod_asc_msgs = []
    for msg in cat:
        if not msg.translated:
            continue
        history = asc_collect_history(msg, acats, config)
        if stest(msg, cat, history, config, options) is None:
            continue

        # Message cannot be ascribed as reviewed if it has not been
        # already ascribed as modified.
        if not is_ascribed(msg, acats):
            # Collect to report later.
            # NOTE: Intentionally not removing any misplaced review flags.
            non_mod_asc_msgs.append(msg)
            continue

        # Collect any tags in explicit reviewed-flags.
        tags = []
        for flag in msg.flag:
            m = _revdflag_rx.search(flag)
            if m:
                tags.append(m.group(1).strip() or None)
                # Do not break, several review flags possible.
        if not tags:
            tags.append(options.tag)

        # Clear review state.
        clear_review_msg(msg)

        rev_msgs_tags.append((msg, tags))

    if non_mod_asc_msgs:
        fmtrefs = ", ".join(["%s(#%s)" % (x.refline, x.refentry)
                             for x in non_mod_asc_msgs])
        warning("%s: some messages cannot be ascribed as reviewed "
                "because they were not ascribed as modified: %s"
                % (cat.filename, fmtrefs))

    if not rev_msgs_tags:
        # No messages to ascribe.
        return 0

    # Create ascription catalog for this user if not existing already.
    acat = acats.get(user)
    if not acat:
        acat = init_asc_cat(cat.name, user, config)
    else:
        update_asc_hdr(acat, user, config)

    # Current VCS revision of the catalog.
    catrev = config.vcs.revision(cat.filename)

    # Ascribe messages as reviewed.
    for msg, tags in rev_msgs_tags:
        if msg not in acat:
            # Copy ID elements of the original message.
            amsg = Message()
            amsg.msgctxt = msg.msgctxt
            amsg.msgid = msg.msgid
            # Append to the end of catalog.
            pos = acat.add(amsg, -1)
        else:
            # Retrieve existing ascribed message.
            amsg = acat[msg]

        # Copy desired non-ID elements.
        amsg.msgid_plural = msg.msgid_plural
        amsg.msgstr = Monlist(msg.msgstr)

        # Ascribe review of the message.
        ascribe_msg_rev(amsg, tags, user, config, catrev)

    sync_and_rep(cat)
    if sync_and_rep(acat):
        config.vcs.add(acat.filename)

    return len(rev_msgs_tags)


# Flag used to mark messages selected for review.
_revflag = u"review"


def diff_select_cat (options, config, catpath, stest, aselect, pfilter):

    cat = Catalog(catpath, monitored=True, wrapf=WRAPF)
    acats = collect_asc_cats(config, cat.name)

    nflagged = 0
    for msg in cat:
        if not msg.translated:
            continue
        history = asc_collect_history(msg, acats, config)
        sres = stest(msg, cat, history, config, options)
        if sres is None:
            continue

        # Try to select ascription to differentiate from.
        i_asc = None
        if aselect:
            i_asc = aselect(msg, cat, history, config, options)
        elif isinstance(sres, int) and sres + 1 < len(history):
            # If there is no ascription selector, but basic selector returned
            # an ascription index, use one ascription before for diffing.
            i_asc = sres + 1

        # Differentiate and flag.
        if i_asc is not None:
            anydiff = msg.embed_diff(history[i_asc].msg, pfilter=pfilter)
            # NOTE: Do NOT think of avoiding to flag the message if there is
            # no difference to history, must be symmetric to review ascription.
        msg.flag.add(_revflag)
        nflagged += 1

    sync_and_rep(cat)

    return nflagged


def clear_review_cat (options, config, catpath, stest):

    cat = Catalog(catpath, monitored=True, wrapf=WRAPF)
    acats = collect_asc_cats(config, cat.name)

    nontrans_with_revflags = []
    ncleared = 0
    for msg in cat:
        history = asc_collect_history(msg, acats, config)
        if stest(msg, cat, history, config, options) is None:
            continue

        if clear_review_msg(msg, nontrans_with_revflags):
            ncleared += 1

    if nontrans_with_revflags:
        fmtrefs = ", ".join(["%s(#%s)" % (x.refline, x.refentry)
                             for x in nontrans_with_revflags])
        warning("%s: some non-translated messages have review flags, "
                "which should never be the case: %s"
                % (cat.filename, fmtrefs))

    sync_and_rep(cat)

    return ncleared


def clear_review_msg (msg, rep_ntrans=None):

    cleared = False
    for flag in msg.flag.items():
        if flag == _revflag or _revdflag_rx.search(flag):
            if msg.translated:
                msg.flag.remove(flag)
                if not cleared:
                    # Clear possible embedded diffs.
                    msg.msgctxt_previous = None
                    msg.msgid_previous = u""
                    msg.msgid_plural_previous = u""
                cleared = True
                # Do not break, other review flags possible.
            else:
                # Non-translated messages should not have review flags,
                # collect to report if requested.
                if rep_ntrans is not None:
                    rep_ntrans.append(msg)
                break

    return cleared


def is_ascribed (msg, acats):

    ascribed = False
    for ouser, acat in acats.iteritems():
        if msg in acat and asc_eq(msg, acat[msg]):
            ascribed = True
            break
    return ascribed


def collect_asc_cats (config, catname, muser=None):

    acats = {}
    for ouser in config.users:
        amon = False
        if muser and ouser == muser:
            amon = True
        acatpath = os.path.join(config.udata[ouser].ascroot, catname + ".po")
        if os.path.isfile(acatpath):
            acats[ouser] = Catalog(acatpath, monitored=amon, wrapf=WRAPF)

    return acats


def init_asc_cat (catname, user, config):

    udat = config.udata[user]
    acatpath = os.path.join(udat.ascroot, catname + ".po")
    acat = Catalog(acatpath, create=True, wrapf=WRAPF)
    ahdr = acat.header

    ahdr.title = Monlist([u"Ascription shadow for %s.po" % catname])

    if udat.oname and udat.email:
        author = u"%s (%s) <%s>" % (udat.name, udat.oname, udat.email)
    elif udat.oname:
        author = u"%s (%s)" % (udat.name, udat.oname)
    elif udat.email:
        author = u"%s <%s>" % (udat.name, udat.email)
    else:
        author = u"%s" % udat.name
    ahdr.author = Monlist([author])

    ahdr.copyright = u"Copyright same as for the original catalog."
    ahdr.license = u"License same as for the original catalog."
    ahdr.comment = Monlist([u"===== DO NOT EDIT MANUALLY ====="])

    rfv = ahdr.replace_field_value # shortcut

    rfv("Project-Id-Version", unicode(catname))
    rfv("Report-Msgid-Bugs-To", unicode(udat.email or ""))
    rfv("PO-Revision-Date", unicode(date_now()))
    rfv("Content-Type", u"text/plain; charset=UTF-8")
    rfv("Content-Transfer-Encoding", u"8bit")

    if udat.email:
        ltr = "%s <%s>" % (udat.name, udat.email)
    else:
        ltr = udat.name
    rfv("Last-Translator", unicode(ltr))

    if config.lang_team:
        if config.team_email:
            tline = u"%s <%s>" % (config.lang_team, config.team_email)
        else:
            tline = config.lang_team
        rfv("Language-Team", unicode(tline))
    else:
        ahdr.remove_field("Language-Team")

    if config.plural_header:
        rfv("Plural-Forms", unicode(config.plural_header))
    else:
        ahdr.remove_field("Plural-Forms")

    return acat


def update_asc_hdr (acat, user, config):

    acat.header.replace_field_value("PO-Revision-Date", unicode(date_now()))


_atype_mod = "modified"

def ascribe_msg_mod (amsg, user, config, catrev):

    modstr = date_now()
    if catrev:
        modstr += " | " + catrev
    asc_append_field(amsg, _atype_mod, modstr)


_atype_rev = "reviewed"
_atype_rev_tagsep = "/"

def ascribe_msg_rev (amsg, tags, user, config, catrev):

    modstr = date_now()
    if catrev:
        modstr += " | " + catrev
    for tag in tags:
        field = _atype_rev
        if tag:
             field += _atype_rev_tagsep + tag
        asc_append_field(amsg, field, modstr)


def asc_eq (msg1, msg2):
    """
    Whether two messages are equal from the ascription viewpoint.
    """

    return (    True
            and msg1.fuzzy == msg2.fuzzy
            and msg1.msgctxt == msg2.msgctxt
            and msg1.msgid == msg2.msgid
            and msg1.msgid_plural == msg2.msgid_plural
            and msg1.msgstr == msg2.msgstr
    )


fld_sep = ":"


def asc_get_fields (msg, field, defvals=[]):

    values = []
    for text in msg.manual_comment:
        text = text.strip()
        lst = [x.strip() for x in text.split(fld_sep, 1)]
        if lst and lst[0] == field:
            if len(lst) == 2:
                values.append(lst[1])
            else:
                values.append("")
    if not values:
        values = defvals
    return values


def asc_set_field (msg, field, value):

    stext = u"".join([field, fld_sep, " ", str(value)])

    # Try to find the field and replace its value.
    replaced = False
    for i in range(len(msg.manual_comment)):
        text = msg.manual_comment[i].strip()
        lst = [x.strip() for x in text.split(fld_sep, 1)]
        if lst and lst[0] == field:
            msg.manual_comment[i] = stext
            replaced = True
            break

    # Field not found, append.
    if not replaced:
        msg.manual_comment.append(stext)


def asc_append_field (msg, field, value):

    stext = u"".join([field, fld_sep, " ", str(value)])
    msg.manual_comment.append(stext)


class _Ascription (object):

    def __setattr__ (self, attr, val):

        if attr not in ("msg", "user", "type", "tag", "date", "rev"):
            raise KeyError, \
                  "trying to set invalid ascription field '%s'" % attr
        self.__dict__[attr] = val


def asc_collect_history (msg, acats, config):

    return asc_collect_history_w(msg, acats, config, {})


def asc_collect_history_w (msg, acats, config, seenmsg):
    """
    Create ascription history of the message.

    The history is assembled as list of tuples
    C{(asc-message, user, asc-type, asc-tag, date, revision)},
    sorted chronologically by date/revision (newest first).
    Date gets to be a real C{datetime} object.
    """

    history = []
    if not seenmsg:
        seenmsg = {}

    # Avoid circular paths.
    if msg.key in seenmsg:
        return history
    seenmsg[msg.key] = True

    # Collect history from all ascription catalogs.
    for user, acat in acats.iteritems():
        if user == UFUZZ:
            continue
        if msg in acat:
            amsg = acat[msg]
            for asc in asc_parse_ascriptions(amsg, acat):
                a = _Ascription()
                a.msg, a.user = amsg, user
                a.type, a.tag, a.date, a.rev = asc
                history.append(a)

    # Continue into the past by pivoting around fuzzy messages.
    acat = acats.get(UFUZZ)
    if acat and msg in acat:
        amsg = acat[msg]
        if amsg.msgctxt_previous or amsg.msgid_previous:
            pmsg = Message()
            pmsg.msgctxt = amsg.msgctxt_previous
            pmsg.msgid = amsg.msgid_previous
            ct_history = asc_collect_history_w(pmsg, acats, config, seenmsg)
            history.extend(ct_history)

    history.sort(lambda x, y: asc_age_cmp(y, x, config))

    return history


def asc_parse_ascriptions (amsg, acat):
    """
    Get ascriptions from given ascription message as list of tuples
    C{(asc-type, asc-tag, date, revision)}, with date being a real
    C{datetime} object.
    """

    ascripts = []
    for cmnt in amsg.manual_comment:
        p = cmnt.find(":")
        if p < 0:
            warning_on_msg("malformed ascription comment '%s' "
                           "(no ascription type)" % cmnt, amsg, acat)
            continue
        asctype = cmnt[:p].strip()
        asctag = None
        lst = asctype.split(_atype_rev_tagsep, 1)
        if len(lst) == 2:
            asctype = lst[0].strip()
            asctag = lst[1].strip()
        lst = cmnt[p+1:].split("|")
        if len(lst) == 1:
            datestr = lst[0].strip()
            revision = None
        elif len(lst) == 2:
            datestr = lst[0].strip()
            revision = lst[1].strip()
        else:
            warning_on_msg("malformed ascription comment '%s' "
                           "(wrong number of descriptors)" % cmnt, amsg, acat)
            continue
        try:
            date = parse_datetime(datestr)
        except:
            warning_on_msg("malformed ascription comment '%s' "
                           "(malformed date string)" % cmnt, amsg, acat)
            continue
        ascripts.append((asctype, asctag, date, revision))

    return ascripts


def asc_age_cmp (a1, a2, config):
    """
    Compare age of two ascriptions in history by their date/revision.

    See L{asc_collect_history} for the composition of C{hist*} arguments.
    Return value has the same semantics as with built-in C{cmp} function.
    """

    if a1.rev and a2.rev:
        if a1.rev == a2.rev:
            return 0
        elif config.vcs.is_older(a1.rev, a2.rev):
            return -1
        else:
            return 1
    else:
         return cmp(a1.date, a2.date)


def sync_and_rep (cat):

    modified = cat.sync()
    if modified:
        report("!    " + cat.filename)

    return modified


def date_now ():

    return time.strftime("%Y-%m-%d %H:%M:%S%z")


_parse_date_rx = re.compile(
    r"^ *(\d+)-(\d+)-(\d+) *(\d+):(\d+):(\d+) *([+-]\d+) *$")

def parse_datetime (dstr):
    # NOTE: Timezone offset is lost, the datetime object becomes UTC.
    # NOTE: Can we use dateutil module in here?

    m = _parse_date_rx.search(dstr)
    if not m:
        raise StandardError, "cannot parse date string '%s'" % dstr
    year, month, day, hour, minute, second, off = [int(x) for x in m.groups()]
    dt0 = datetime.datetime(year=year, month=month, day=day,
                            hour=hour, minute=minute, second=second)
    offmin = (off // 100) * 60 + (abs(off) % 100)
    tzd = datetime.timedelta(minutes=offmin)
    dt = dt0 - tzd
    return dt


def parse_users (userstr, config, cid=None):
    """
    Parse users from comma-separated list, verifying that they exist.

    C{cid} is the string identifying the caller, for error report in
    case the a parsed user does not exist.
    """

    users = []
    if userstr:
        users = userstr.split(",")
    for user in users:
        if user == UFUZZ:
            error("cannot explicitly select reserved user '%s'" % user,
                  subsrc=cid)
        if user not in config.users:
            error("unknown user '%s' in config '%s'" % (user, config.path),
                  subsrc=cid)

    return users


# Build compound selector out of list of specifications.
# Selector specification is a string in format NAME:ARG1:ARG2:...
def build_selector (options, selspecs, hist=False):

    # Component selectors.
    selectors = []
    for selspec in selspecs:
        lst = selspec.split(":")
        sname, sargs = lst[0], lst[1:]
        negated = False
        if sname.startswith("n"):
            sname = sname[1:]
            negated = True
        sfactory, can_hist = _selector_factories.get(sname, (None, False))
        if not sfactory:
            error("unknown selector '%s'" % sname)
        if hist:
            if not can_hist:
                error("selector '%s' cannot be used "
                      "as history selector" % sname)
            if negated:
                error("negated selectors (here '%s') cannot be used "
                      "as history selectors" % sname)
        selector = sfactory(*sargs)
        if negated:
            selector = negate_selector(selector)
        selectors.append(selector)

    # Compound selector.
    if hist:
        res0 = None
    else:
        res0 = False
    def cselector (*a):
        res = res0
        for selector in selectors:
            res = selector(*a)
            if res is None:
                return res
        return res

    return cselector


# Negative selector is built to return:
# - True if the positive selector returns None
# - None otherwise (the positive selector returns True or ascription index)
# NOTE: No False as return value because selectors should return
# one of None, True, or index.
def negate_selector (selector):

    def negative_selector (*args):
        res = selector(*args)
        if res is None:
            return True
        else:
            return None

    return negative_selector


# -----------------------------------------------------------------------------
# Selector factories.
# Use build_selector() to create selectors.

# NOTE: Selectors should return one of None, True, or
# a valid index into ascription history.
# They should never return False, so that non-selection can always be checked
# by ...is None, since index 0 and False would be same.

def selector_any ():
    cid = "selector:any"

    def selector (msg, cat, history, config, options):

        return True

    return selector


def selector_wasc ():
    cid = "selector:wasc"

    def selector (msg, cat, history, config, options):

        if history and asc_eq(msg, history[0].msg):
            return True

        return None

    return selector


def selector_xrevd ():
    cid = "selector:xrevd"

    revdflags_rx = re.compile(r"^(?:revd|reviewed) *[/:]?(.*)", re.I)

    def selector (msg, cat, history, config, options):

        for flag in msg.flags:
            if _revdflag_rx.search(flag):
                return True

        return None

    return selector


# Select last ascription (any, or by users).
def selector_asc (user_spec=None):
    cid = "selector:asc"

    def selector (msg, cat, history, config, options):

        users = []
        if user_spec:
            users = parse_users(user_spec, config, cid)

        i_sel = None
        for i in range(len(history)):
            a = history[i]
            if not users or a.user in users:
                i_sel = i
                break

        return i_sel

    return selector


# Select last modification (any or by users).
def selector_mod (user_spec=None):
    cid = "selector:mod"

    def selector (msg, cat, history, config, options):

        users = []
        if user_spec:
            users = parse_users(user_spec, config, cid)

        i_sel = None
        for i in range(len(history)):
            a = history[i]
            if a.type == _atype_mod and (not users or a.user in users):
                i_sel = i
                break

        return i_sel

    return selector


# Select first modification (any or by m-users) after last review
# (any or by r-users, and either way not by m-users).
def selector_modar (muser_spec=None, ruser_spec=None, atag_req=None):
    cid = "selector:modar"

    def selector (msg, cat, history, config, options):

        rusers = []
        if ruser_spec:
            rusers = parse_users(ruser_spec, config, cid)
        musers = []
        if muser_spec:
            musers = parse_users(muser_spec, config, cid)

        i_sel = None
        i_cand = None
        for i in range(len(history)):
            a = history[i]
            if (     a.type == _atype_rev and a.tag == atag_req
                and (not rusers or a.user in rusers)
                and (not musers or a.user not in musers)
            ):
                if i_cand is None:
                    # Review found before candidate modification.
                    break
                else:
                    # Candidate modification is good
                    # unless filter is in effect and there is no difference
                    # between the modification and current review.
                    mm, mr = history[i_cand].msg, a.msg
                    pf = options.tfilter
                    if pf and not mm.embed_diff(mr, pfilter=pf, dryrun=True):
                        i_cand = None
                    else:
                        i_sel = i_cand
                        break
            if a.type == _atype_mod and (not musers or a.user in musers):
                # Modification found, make it candidate.
                i_cand = i

        if i_cand is not None:
            # There was no review after modification candidate, so use it,
            # unless filter is in effect and there is no difference between
            # candidate and the first earlier modification
            # (any, or not by m-users).
            if options.tfilter and i_cand + 1 < len(history):
                mm = history[i_cand].msg
                pf = options.tfilter
                for a in history[i_cand + 1:]:
                    if (    a.type == _atype_mod
                        and (not musers or a.user not in musers)
                        and not a.msg.embed_diff(mm, pfilter=pf, dryrun=True)
                    ):
                        i_cand = None
                        break
            if i_cand is not None:
                i_sel = i_cand

        return i_sel

    return selector


# Select last review (any or by users).
def selector_rev (user_spec=None, atag_req=None):
    cid = "selector:rev"

    def selector (msg, cat, history, config, options):

        users = []
        if user_spec:
            users = parse_users(user_spec, config, cid)

        i_sel = None
        for i in range(len(history)):
            a = history[i]
            if (    a.type == _atype_rev and a.tag == atag_req
                and (not users or a.user in users)
            ):
                i_sel = i
                break

        return i_sel

    return selector


# Select first review (any or by r-users) before last modification
# (any or by m-users, and either way not by r-users).
def selector_revbm (ruser_spec=None, muser_spec=None, atag_req=None):
    cid = "selector:revbm"

    def selector (msg, cat, history, config, options):

        rusers = []
        if ruser_spec:
            rusers = parse_users(ruser_spec, config, cid)
        musers = []
        if muser_spec:
            musers = parse_users(muser_spec, config, cid)

        # TODO: Make it filter-sensitive like :modar.

        i_sel = None
        can_select = False
        for i in range(len(history)):
            a = history[i]
            if (     a.type == _atype_mod
                and (not musers or a.user in musers)
                and (not rusers or a.user not in rusers)
            ):
                # Modification found, enable selection of review.
                can_select = True
            if (    a.type == _atype_rev and a.tag == atag_req
                and (not rusers or a.user in rusers)
            ):
                # Review found, select it if enabled, and stop anyway.
                if can_select:
                    i_sel = i
                break

        return i_sel

    return selector


_selector_factories = {
    # key: (function, can_be_used_as_history_selector)
    "any": (selector_any, False),
    "wasc": (selector_wasc, False),
    "xrevd": (selector_xrevd, False),
    "asc": (selector_asc, True),
    "mod": (selector_mod, True),
    "modar": (selector_modar, True),
    "rev": (selector_rev, True),
    "revbm": (selector_revbm, True),
}

# -----------------------------------------------------------------------------

if __name__ == "__main__":
    main()

