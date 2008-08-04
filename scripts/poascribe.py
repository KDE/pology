#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import fallback_import_paths

import os
import sys
import re
import codecs
import time
import datetime
from optparse import OptionParser
from ConfigParser import SafeConfigParser

from pology.misc.report import error, warning, warning_on_msg
from pology.misc.fsops import collect_catalogs, mkdirpath
from pology.misc.vcs import make_vcs
from pology.file.catalog import Catalog
from pology.file.message import Message
from pology.misc.monitored import Monlist, Monset
from pology.misc.wrap import wrap_field_ontag_unwrap
from pology.misc.tabulate import tabulate
from pology.misc.diff import diff_texts

WRAPF = wrap_field_ontag_unwrap
UFUZZ = "fuzzy"


def main ():

    # Setup options and parse the command line.
    usage = (
        u"%prog [OPTIONS] [PATHS...]")
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
        "-m", "--modified", metavar="USER",
        action="store", dest="modified", default=None,
        help="ascribe all modified entries to this user")
    opars.add_option(
        "-r", "--reviewed", metavar="USER",
        action="store", dest="reviewed", default=None,
        help="ascribe selected or all entries as reviewed to this user")
    opars.add_option(
        "-f", "--fuzzied",
        action="store_true", dest="fuzzied", default=False,
        help="ascribe all fuzzied entries to fuzzy-user (if enabled)")
    opars.add_option(
        "-t", "--tag", metavar="TAG",
        action="store", dest="tag", default=None,
        help="tag to add or consider in ascription records (in some modes)")
    opars.add_option(
        "-a", "--all",
        action="store_true", dest="all", default=False,
        help="ascribe all entries instead of selected (in some modes)")
    opars.add_option(
        "-s", "--select", metavar="TYPE[:ARGS]",
        action="append", dest="selects", default=[],
        help="mark entries in original catalogs that match given condition")
    opars.add_option(
        "-d", "--diff", metavar="TYPE[:ARGS]",
        action="store", dest="diff", default=None,
        help="diff entries in original catalogs against an earlier version "
             "(if --select in effect, only those matched)")
    opars.add_option(
        "-F", "--prediff-filter", metavar="NAME",
        action="store", dest="prediff_filter", default=None,
        help="pass texts to be diffed through a filter beforehand")
    opars.add_option(
        "-n", "--no-state",
        action="store_false", dest="state", default=True,
        help="do not examine the ascription state of catalogs")
    opars.add_option(
        "-v", "--verbose",
        action="store_true", dest="verbose", default=False,
        help="output more detailed progress info")
    (options, free_args) = opars.parse_args()

    options.paths = [os.path.normpath(x) for x in free_args]
    if not options.paths:
        options.paths = ["."]

    # Could use some speedup.
    if options.use_psyco:
        try:
            import psyco
            psyco.full()
        except ImportError:
            pass

    # For each path:
    # - determine its associated ascription config,
    # - collect all catalogs.
    configs_loaded = {}
    configs_catpaths = []
    for path in options.paths:
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

            # Assert fuzzy-user enabled if fuzzy-ascription requested.
            if options.fuzzied and not config.asc_fuzz:
                error("fuzzy-ascription requested, but not enabled in "
                      "configuration at: %s" % cfgpath)

        # Collect PO files.
        if os.path.isdir(path):
            catpaths = collect_catalogs(path)
        else:
            catpaths = [path]

        # Collect the config and corresponding catalogs.
        configs_catpaths.append((config, catpaths))

    if options.modified:
        ascribe_modified(options, configs_catpaths, options.modified)
    if options.reviewed:
        ascribe_reviewed(options, configs_catpaths, options.reviewed)
    if options.fuzzied:
        ascribe_fuzzied(options, configs_catpaths)
    # Selection and diffing after all ascription.
    if options.selects or options.diff:
        select_matching(options, configs_catpaths,
                        options.selects, options.diff)
    # State after everything else.
    if options.state:
        examine_state(options, configs_catpaths)


def rel_path (ref_path, rel_path):

    if os.path.isabs(rel_path):
        path = rel_path
    else:
        ref_dir = os.path.dirname(ref_path)
        path = os.path.abspath(os.path.join(ref_dir, rel_path))
    cwd = os.getcwd() + os.path.sep
    if path.startswith(cwd):
        path = path[len(cwd):]
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

        # Urgh.
        self.asc_fuzz = True
        if gsect.get("ascribe-fuzzies"):
            self.asc_fuzz = config.getboolean("global", "ascribe-fuzzies")

        if self.asc_fuzz:
            # Create fuzzy-user.
            udat = UserData()
            self.udata[UFUZZ] = udat
            self.users.append(UFUZZ)
            udat.ascroot = os.path.join(self.ascroot, UFUZZ)
            udat.name = "Fuzzy"
            udat.oname = None
            udat.email = None


def examine_state (options, configs_catpaths):

    # Count unascribed messages through catalogs.
    unasc_by_cat = {}
    unasc_fuzz_by_cat = {}
    for config, catpaths in configs_catpaths:
        for catpath in catpaths:
            # Open current and all ascription catalogs.
            cat = Catalog(catpath, monitored=False)
            acats, acats_fuzzy = collect_asc_cats(config, cat.name)
            # Count non-ascribed.
            for msg in cat:
                if msg.translated:
                    if not is_ascribed(msg, acats):
                        if catpath not in unasc_by_cat:
                            unasc_by_cat[catpath] = 0
                        unasc_by_cat[catpath] += 1
                elif msg.fuzzy and config.asc_fuzz:
                    if not is_ascribed(msg, acats_fuzzy):
                        if catpath not in unasc_fuzz_by_cat:
                            unasc_fuzz_by_cat[catpath] = 0
                        unasc_fuzz_by_cat[catpath] += 1

    # Present findings.
    for unasc_cnts, chead in (
        (unasc_by_cat, "Unascribed"),
        (unasc_fuzz_by_cat, "Unascribed fuzzies"),
    ):
        if not unasc_cnts:
            continue
        nunasc = reduce(lambda s, x: s + x, unasc_cnts.itervalues())
        ncats = len(unasc_cnts)
        print "===? %s: %d entries in %d catalogs" % (chead, nunasc, ncats)
        catnames = unasc_cnts.keys()
        catnames.sort()
        rown = catnames
        data = [[unasc_cnts[x] for x in catnames]]
        print tabulate(data=data, rown=rown, indent="  ")


def ascribe_modified (options, configs_catpaths, user):

    if user == UFUZZ:
        error("cannot ascribe modifications to reserved user '%s'" % UFUZZ)

    nasc = 0
    for config, catpaths in configs_catpaths:
        if user not in config.users:
            error("unknown user '%s' in config '%s'" % (user, config.path))

        mkdirpath(config.udata[user].ascroot)

        for catpath in catpaths:
            nasc += ascribe_modified_cat(options, config, user, catpath)

    if nasc > 0:
        print "===! Ascribed as modified: %d entries" % nasc


def ascribe_reviewed (options, configs_catpaths, user):

    if user == UFUZZ:
        error("cannot ascribe reviews to reserved user '%s'" % UFUZZ)

    nasc = 0
    for config, catpaths in configs_catpaths:
        if user not in config.users:
            error("unknown user '%s' in config '%s'" % (user, config.path))

        mkdirpath(config.udata[user].ascroot)

        for catpath in catpaths:
            nasc += ascribe_reviewed_cat(options, config, user, catpath)

    if nasc > 0:
        print "===! Ascribed as reviewed: %d entries" % nasc


def ascribe_fuzzied (options, configs_catpaths):

    nasc = 0
    for config, catpaths in configs_catpaths:

        mkdirpath(config.udata[UFUZZ].ascroot)

        for catpath in catpaths:
            nasc += ascribe_modified_cat(options, config, UFUZZ, catpath)

    if nasc > 0:
        print "===! Ascribed as modified (fuzzy): %d entries" % nasc


def select_matching (options, configs_catpaths, sels, diff):

    # Split selectors into arguments.
    psels = [x.split(":") for x in sels]
    pdiff = []
    if diff:
        pdiff = diff.split(":")

    # Fetch prediff filter if requested.
    pfilter = None
    if options.prediff_filter:
        fspec = options.prediff_filter
        lst = fspec.split(":")
        if len(lst) != 2:
            error("pre-diff filter must be specified as <lang>:<filter>, "
                  "given '%s' instead" % fspec)
        lang, modname = lst
        modname = modname.replace("-", "_")
        try:
            m = __import__("pology.l10n.%s.filter.%s" % (lang, modname),
                           globals(), locals(), [""])
            pfilter = m.process
        except ImportError:
            error("cannot load requested pre-diff filter '%s'" % fspec)

    nsel = 0
    for config, catpaths in configs_catpaths:
        for catpath in catpaths:
            nsel += select_matching_cat(options, config,
                                        psels, pdiff, pfilter, catpath)

    if nsel > 0:
        print "===! Selected matching: %d entries" % nsel


def ascribe_modified_cat (options, config, user, catpath):

    # Open current catalog and all ascription catalogs.
    cat = Catalog(catpath, monitored=False, wrapf=WRAPF)
    acats, acats_fuzzy = collect_asc_cats(config, cat.name, user)

    # Collect all translated (or fuzzy) and unascribed messages.
    asc_fuzz = (user == UFUZZ)
    unasc_msgs = []
    for msg in cat:
        if not msg.fuzzy:
            if not msg.translated:
                continue
            if not is_ascribed(msg, acats):
                unasc_msgs.append(msg)
        else:
            if not asc_fuzz:
                continue
            if not is_ascribed(msg, acats_fuzzy):
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


def ascribe_reviewed_cat (options, config, user, catpath):

    # Open current catalog and all ascription catalogs.
    # Monitored, for removal of reviewed-* flags.
    cat = Catalog(catpath, monitored=True, wrapf=WRAPF)
    acats, acats_fuzzy = collect_asc_cats(config, cat.name, user)

    # Collect all or flagged messages (must be translated), with tags.
    fl_rx = re.compile(r"^(?:revd|reviewed) *[/:]?(.*)", re.I)
    rev_msgs_tags = []
    for msg in cat:
        if not msg.translated and not msg.fuzzy:
            continue

        # Check if the message has been flagged as reviewed.
        # Must not skip checking if --all is in effect, in order
        # to collect any tagged reviews and clear any review flags.
        flagged = False
        flags = msg.flag.items()
        tags = []
        for flag in flags:
            m = fl_rx.search(flag)
            if m:
                tags.append(m.group(1).strip() or None)
                flagged = True
                msg.flag.remove(flag)
        if not flagged and not options.all:
            continue

        # Fuzzy messages may be explicitly flagged,
        # e.g. after review with embedded diffs.
        # Otherwise skip the fuzzy.
        if msg.fuzzy:
            if not flagged:
                continue
            msg.fuzzy = False

        if not is_ascribed(msg, acats):
            warning("%s: not all reviewed messages ascribed as modified, "
                    "cannot ascribe reviews" % cat.filename)
            return 0

        if not tags:
            tags.append(options.tag)

        rev_msgs_tags.append((msg, tags))

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


def select_matching_cat (options, config, sels, diff, pfilter, catpath):

    # Open current catalog and all ascription catalogs.
    # Monitored, for adding selection flags.
    cat = Catalog(catpath, monitored=True, wrapf=WRAPF)
    acats = collect_asc_cats(config, cat.name, wfuzzy=True)

    nflagged = 0
    for msg in cat:
        if not msg.translated:
            continue

        # Ascription history for current message.
        history = asc_collect_history(msg, acats, config)

        # Apply selectors.
        selected = apply_selectors(sels, msg, history, config)
        if not selected:
            continue

        # Apply differ.
        if diff:
            anydiff = apply_differ(diff, msg, history, config, pfilter)
            if not anydiff:
                continue

        # Flag.
        msg.flag.add(u"review")

        nflagged += 1

    sync_and_rep(cat)

    return nflagged


_known_selectors = {}

def apply_selectors (sels, msg, history, config):

    selected = True

    for sargs in sels:
        sname, args = sargs[0].strip(), sargs[1:]
        invert = False
        sname_orig = sname
        if sname.startswith("n"):
            invert = True
            sname = sname[1:]

        selector = _known_selectors.get(sname)
        if not selector:
            error("unknown selector type '%s'" % sname_orig)
        matched = selector(args, msg, history, config)
        if invert:
            matched = not matched
        selected = selected and matched
        if not selected:
            break

    return selected


_known_diffsels = {}

def apply_differ (diff, msg, history, config, pfilter=None):

    dname, args = diff[0].strip(), diff[1:]
    diffsel = _known_diffsels.get(dname)
    if not diffsel:
        error("unknown diff-selector type '%s'" % dname)
    amsg = diffsel(args, msg, history, config)
    if not amsg:
        return False

    # Make a diff only if selector reports non-empty message.
    # Empty message (instead of C{None}) means that there is
    # no purpose showing the diff, although the message is different.
    if amsg.msgid:
        anydiff = embed_diff(amsg, msg, pfilter)
    else:
        anydiff = True

    return anydiff


def embed_diff (msg1, msg2, pfilter=None):
    """
    Make diffs of all text fields from C{msg1} to C{msg2}, and embed them
    into C{*_previous} fields of C{msg2} (making it fuzzy).
    Every text field is passed through C{pfilter} before diffing.
    Returns C{True} if there was any difference.
    """

    # Equalize number of msgstr fields.
    msgstrs1 = []
    msgstrs2 = []
    lenm1 = len(msg1.msgstr)
    lenm2 = len(msg2.msgstr)
    for i in range(max(lenm1, lenm2)):
        if i < lenm1:
            msgstrs1.append(msg1.msgstr[i])
        else:
            msgstrs1.append(u"")
        if i < lenm2:
            msgstrs2.append(msg2.msgstr[i])
        else:
            msgstrs2.append(u"")

    # Create diffs.
    anydiff = False
    field_diffs = []
    for text1, text2 in [
        (msg1.msgctxt, msg2.msgctxt),
        (msg1.msgid, msg2.msgid),
        (msg1.msgid_plural, msg2.msgid_plural),
    ] + zip(msgstrs1, msgstrs2):
        if pfilter:
            text1 = pfilter(text1)
            text2 = pfilter(text2)
        diff = u""
        if text1 != text2:
            anydiff = True
        diff, dr = diff_texts(text1, text2, markup=True, format=msg2.format)
        field_diffs.append(diff)

    if not anydiff:
        return False

    # Embed diffs.
    msgctxt_previous = field_diffs[0]
    msgid_previous = field_diffs[1]
    msgid_plural_previous = field_diffs[2]
    msgstr_previous_sections = []
    add_indices = len(field_diffs) > 4
    for i in range(3, len(field_diffs)):
        if field_diffs[i]:
            if add_indices:
                msgstr_previous_sections.append("========== [%d]" % i)
            else:
                msgstr_previous_sections.append("==========")
            msgstr_previous_sections.append(field_diffs[i])
    msgstr_previous = "\n".join(msgstr_previous_sections)
    if msgstr_previous:
        if not msg2.msgid_plural:
            msgid_previous += "\n" + msgstr_previous
        else:
            msgid_plural_previous += "\n" + msgstr_previous

    msg2.msgctxt_previous = msgctxt_previous
    msg2.msgid_previous = msgid_previous
    msg2.msgid_plural_previous = msgid_plural_previous
    msg2.fuzzy = True # or else *_previous fields will be removed on sync

    return True


def is_ascribed (msg, acats):

    ascribed = False
    for ouser, acat in acats.iteritems():
        if msg in acat and asc_eq(msg, acat[msg]):
            ascribed = True
            break
    return ascribed


def collect_asc_cats (config, catname, muser=None, wfuzzy=False):

    acats = {}
    for ouser in config.users:
        amon = False
        if muser and ouser == muser:
            amon = True
        acatpath = os.path.join(config.udata[ouser].ascroot, catname + ".po")
        if os.path.isfile(acatpath):
            acats[ouser] = Catalog(acatpath, monitored=amon, wrapf=WRAPF)

    if wfuzzy:
        return acats
    else:
        if UFUZZ in acats:
            return acats, {UFUZZ: acats.pop(UFUZZ)}
        else:
            return acats, {}


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

    return (    msg1.msgctxt == msg2.msgctxt
            and msg1.msgid == msg2.msgid
            and msg1.msgid_plural == msg2.msgid_plural
            and msg1.msgstr == msg2.msgstr)


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
            ascs = asc_parse_ascriptions(amsg, acat)
            for asc in ascs:
                history.append((amsg, user) + asc)

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


def asc_age_cmp (hist1, hist2, config):
    """
    Compare age of two ascriptions in history by their date/revision.

    See L{asc_collect_history} for the composition of C{hist*} arguments.
    Return value has the same semantics as with built-in C{cmp} function.
    """

    date1, rev1 = hist1[-2:]
    date2, rev2 = hist2[-2:]
    if rev1 and rev2:
        if rev1 == rev2:
            return 0
        elif config.vcs.is_older(rev1, rev2):
            return -1
        else:
            return 1
    else:
         return cmp(date1, date2)


def sync_and_rep (cat):

    modified = cat.sync()
    if modified:
        print "!    " + cat.filename

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


# -----------------------------------------------------------------------------
# Selectors.

#def selector_foo (args, msg, history, config):
    #cid = "selector:foo"

    #return True


_known_selectors = {
    #"foo": selector_foo,
}

# -----------------------------------------------------------------------------
# Diff-selectors.

def diffsel_asc (args, msg, history, config):
    cid = "diff-selector:asc"

    users = []
    if args:
        users = parse_users(args.pop(0), config, cid)
    if args:
        error("superflous arguments: %s" % " ".join(args), subsrc=cid)

    # Find the point of last ascription, any, or by requested users.
    i_asc = None
    for i in range(len(history)):
        amsg, user, atype, atag, date, revision = history[i]
        if not users or user in users:
            i_asc = i
            break

    if i_asc is not None:
        amsg_sel = history[i_asc][0]
    else:
        amsg_sel = Message()

    return amsg_sel


def diffsel_revb (args, msg, history, config):
    cid = "diff-selector:revb"

    users = []
    if args:
        users = parse_users(args.pop(0), config, cid)
    atag_req = None
    if args:
        atag_req = args.pop(0)
    if args:
        error("superflous arguments: %s" % " ".join(args), subsrc=cid)

    # Find review point.
    # Avoid reviews of users listed for modification.
    i_rev = None
    for i in range(len(history)):
        amsg, user, atype, atag, date, revision = history[i]
        if atype == _atype_rev and atag == atag_req:
            if not users or user not in users:
                i_rev = i
                break

    amsg_sel = None
    if i_rev is not None:
        # Review point found:
        # look for first later modification,
        # possibly by one of the requested users,
        # select one ascription earlier.
        i_mod = None
        for i in range(i_rev - 1, -1, -1):
            amsg, user, atype, atag, date, revision = history[i]
            if atype == _atype_mod and (not users or user in users):
                i_mod = i
                break
        if i_mod is not None:
            amsg_sel = history[i_mod + 1][0]
    else:
        # Review point not found:
        # If users specified, look for the first modification by one of them,
        # and report one modification earlier; if no such found,
        # report no message for diffing.
        # If users not specified, report empty message.
        if users:
            i_mod = None
            for i in range(len(history) - 1, -1, -1):
                amsg, user, atype, atag, date, revision = history[i]
                if atype == _atype_mod and user in users:
                    i_mod = i
                    break
            if i_mod is not None:
                amsg_sel = history[i_mod + 1][0]
        else:
            amsg_sel = Message()

    return amsg_sel


_known_diffsels = {
    "asc": diffsel_asc,
    "revb": diffsel_revb,
}

# -----------------------------------------------------------------------------

if __name__ == "__main__":
    main()

