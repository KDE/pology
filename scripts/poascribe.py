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

from pology.misc.fsops import str_to_unicode
from pology.misc.report import report, warning, error
from pology.misc.msgreport import warning_on_msg, report_msg_content
from pology.misc.fsops import collect_catalogs, mkdirpath, join_ncwd
from pology.misc.vcs import make_vcs
from pology.file.catalog import Catalog
from pology.file.message import Message, MessageUnsafe
from pology.misc.monitored import Monlist, Monset
from pology.misc.wrap import wrap_field_ontag_unwrap
from pology.misc.tabulate import tabulate
from pology.misc.langdep import get_hook_lreq
from pology.sieve.find_messages import build_msg_fmatcher
from pology.misc.colors import colors_for_file

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
        "-c", "--config", metavar="PATH",
        action="store", dest="config", default=None,
        help="explicit path to ascription configuration "
             "(instead of automatic lookup up the directory tree)")
    opars.add_option(
        "-v", "--verbose",
        action="store_true", dest="verbose", default=False,
        help="output more detailed progress info")

    (options, free_args) = opars.parse_args(str_to_unicode(sys.argv[1:]))

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
    elif mode.name in ("history", "hi"):
        execute_operation = show_history
        mode.selector = selector or build_selector(options, ["nwasc"])
    elif mode.name in ("derive-obsolete", "do"):
        execute_operation = ascribe_derivobs
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
        if not options.config:
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
        else:
            # Use config file supplied through the command line.
            cfgpath = options.config
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

        self.tfilter = gsect.get("text-filter", None)
        if self.tfilter:
            self.tfilter = get_hook_lreq(self.tfilter, abort=True)

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

        # Create merging user.
        udat = UserData()
        self.udata[UFUZZ] = udat
        self.users.append(UFUZZ)
        udat.ascroot = os.path.join(self.ascroot, UFUZZ)
        udat.name = "UFUZZ"
        udat.oname = None
        udat.email = None


def examine_state (options, configs_catpaths, mode):

    stest = mode.selector

    # Count unascribed messages through catalogs.
    unasc_trans_by_cat = {}
    unasc_fuzzy_by_cat = {}
    unasc_utran_by_cat = {}
    for config, catpaths in configs_catpaths:
        for catpath in catpaths:
            # Open current and all ascription catalogs.
            cat = Catalog(catpath, monitored=False)
            acats = collect_asc_cats(config, cat.name)
            # Count non-ascribed.
            for msg in cat:
                history = asc_collect_history(msg, acats, config)
                if not history and not is_translated(msg) and not is_fuzzy(msg):
                    continue # pristine
                if history and asc_eq(msg, history[0].msg):
                    continue # ascribed
                if stest(msg, cat, history, config, options) is None:
                    continue # not selected
                if is_translated(msg):
                    unasc_by_cat = unasc_trans_by_cat
                elif is_fuzzy(msg):
                    unasc_by_cat = unasc_fuzzy_by_cat
                else:
                    unasc_by_cat = unasc_utran_by_cat
                if catpath not in unasc_by_cat:
                    unasc_by_cat[catpath] = 0
                unasc_by_cat[catpath] += 1

    # Present findings.
    for unasc_cnts, chead in (
        (unasc_trans_by_cat, "Unascribed translated"),
        (unasc_fuzzy_by_cat, "Unascribed fuzzy"),
        (unasc_utran_by_cat, "Unascribed untranslated"),
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

    nmod = 0
    nfuz = 0
    nutr = 0
    nobs = 0
    nrvv = 0
    for config, catpaths in configs_catpaths:
        if user not in config.users:
            error("unknown user '%s' in config '%s'" % (user, config.path))

        mkdirpath(config.udata[user].ascroot)

        for catpath in catpaths:
            cnmod, cnfuz, cnutr, cnobs, cnrvv \
                = ascribe_modified_cat(options, config, user, catpath,
                                       mode.selector)
            nmod += cnmod
            nfuz += cnfuz
            nutr += cnutr
            nobs += cnobs
            nrvv += cnrvv

    if nmod > 0:
        report("===! Modified (translated): %d entries" % nmod)
    if nfuz > 0:
        report("===! Modified (fuzzy): %d entries" % nfuz)
    if nutr > 0:
        report("===! Modified (untranslated): %d entries" % nutr)
    if nobs > 0:
        report("===! Obsoleted: %d entries" % nobs)
    if nrvv > 0:
        report("===! Revived: %d entries" % nrvv)


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
        report("===! Reviewed: %d entries" % nasc)


def ascribe_derivobs (options, configs_catpaths, mode):

    nobs = 0
    for config, catpaths in configs_catpaths:

        for catpath in catpaths:
            nobs += ascribe_derivobs_cat(options, config, catpath)

    if nobs > 0:
        report("===! Obsoleted by derivation: %d entries" % nobs)


def diff_select (options, configs_catpaths, mode):

    stest = mode.selector
    aselect = mode.aselector

    ndiffed = 0
    for config, catpaths in configs_catpaths:
        for catpath in catpaths:
            pfilter = options.tfilter or config.tfilter
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


def show_history (options, configs_catpaths, mode):

    stest = mode.selector

    nshown = 0
    for config, catpaths in configs_catpaths:
        for catpath in catpaths:
            nshown += show_history_cat(options, config, catpath, stest)

    if nshown > 0:
        report("===> Computed histories: %d" % nshown)


def ascribe_modified_cat (options, config, user, catpath, stest):

    # Open current catalog and all ascription catalogs.
    cat = Catalog(catpath, monitored=False, wrapf=WRAPF)
    acats = collect_asc_cats(config, cat.name, user)

    # Collect unascribed messages, but ignoring pristine ones
    # (those which are both untranslated and without history).
    # Treat obsolete messages also as either translated or fuzzy.
    toasc_msgs = []
    ntrnmodif = 0
    nfuzmodif = 0
    nutrmodif = 0
    nobsoleted = 0
    nrevived = 0
    for msg in cat:
        history = asc_collect_history(msg, acats, config)
        if not history and not is_translated(msg) and not is_fuzzy(msg):
            continue # pristine
        if stest(msg, cat, history, config, options) is None:
            continue # not selected

        # Note message for modification.
        if not (history and asc_eq(msg, history[0].msg)):
            toasc_msgs.append((msg, ascribe_msg_mod))
            if is_translated(msg):
                ntrnmodif += 1
            elif is_fuzzy(msg):
                nfuzmodif += 1
            else:
                nutrmodif += 1

        # Note for obsolescence/revival (must follow modification,
        # in case of a previously unascribed obsolete message).
        if msg.obsolete:
            # Note for obsolescence if history not showing it already.
            if not history or not is_obsoleted(history):
                toasc_msgs.append((msg, ascribe_msg_obs))
                nobsoleted += 1
        else:
            # Note for revival if history is showing obsolescence.
            if history and is_obsoleted(history):
                toasc_msgs.append((msg, ascribe_msg_rvv))
                nrevived += 1

    if not toasc_msgs:
        # No messages to ascribe.
        return 0, 0, 0, 0, 0

    if not config.vcs.is_clear(cat.filename):
        warning("%s: VCS state not clear, cannot ascribe modifications"
                % cat.filename)
        return 0, 0, 0, 0, 0

    # Create ascription catalog for this user if not existing already.
    acat = acats.get(user)
    if not acat:
        acat = init_asc_cat(cat.name, user, config)
    else:
        update_asc_hdr(acat, user, config)

    # Current VCS revision of the catalog.
    catrev = config.vcs.revision(cat.filename)

    # Ascribe messages: add or modify if existing.
    for msg, ascribe_msg in toasc_msgs:
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
        if is_fuzzy(msg):
            amsg.fuzzy = True
            amsg.msgctxt_previous = msg.msgctxt_previous
            amsg.msgid_previous = msg.msgid_previous
            amsg.msgid_plural_previous = msg.msgid_plural_previous
        else:
            amsg.fuzzy = False # to also remove previous fields
        amsg.msgid_plural = msg.msgid_plural
        amsg.msgstr = Monlist(msg.msgstr)

        # Ascribe modification of the message.
        ascribe_msg(amsg, user, config, catrev)

    if sync_and_rep(acat):
        config.vcs.add(acat.filename)

    return ntrnmodif, nfuzmodif, nutrmodif, nobsoleted, nrevived


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
        history = asc_collect_history(msg, acats, config)
        # Makes no sense to ascribe review to pristine messages.
        if not history and not is_translated(msg) and not is_fuzzy(msg):
            continue
        if stest(msg, cat, history, config, options) is None:
            continue
        # Message cannot be ascribed as reviewed if it has not been
        # already ascribed as modified.
        if not history or not asc_eq(msg, history[0].msg):
            # Collect to report later.
            non_mod_asc_msgs.append(msg)
            # Clear only flags to-review, and not explicit review-done.
            clear_review_msg(msg, clrevd=False)
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
        if non_mod_asc_msgs:
            # May have had some review states cleared.
            sync_and_rep(cat)
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
        history = asc_collect_history(msg, acats, config)
        # Makes no sense to review pristine messages.
        if not history and not is_translated(msg) and not is_fuzzy(msg):
            continue
        sres = stest(msg, cat, history, config, options)
        if sres is None:
            continue

        # Try to select ascription to differentiate from.
        i_asc = None
        if aselect:
            i_asc = aselect(msg, cat, history, config, options)
        elif isinstance(sres, int):
            # If there is no ascription selector, but basic selector returned
            # an ascription index, use first earlier non-fuzzy ascription
            # for diffing.
            i_asc = first_nfuzzy(history, sres + 1)

        # Differentiate and flag.
        if i_asc is not None:
            anydiff = msg.embed_diff(history[i_asc].msg, keeponfuzz=True,
                                     pfilter=pfilter)
            # NOTE: Do NOT think of avoiding to flag the message if there is
            # no difference to history, must be symmetric to review ascription.
        msg.flag.add(_revflag)
        nflagged += 1

    sync_and_rep(cat)

    return nflagged


def clear_review_cat (options, config, catpath, stest):

    cat = Catalog(catpath, monitored=True, wrapf=WRAPF)
    acats = collect_asc_cats(config, cat.name)

    ncleared = 0
    for msg in cat:
        history = asc_collect_history(msg, acats, config)
        if stest(msg, cat, history, config, options) is None:
            continue
        if clear_review_msg(msg):
            ncleared += 1

    sync_and_rep(cat)

    return ncleared


def show_history_cat (options, config, catpath, stest):

    C = colors_for_file(sys.stdout)

    cat = Catalog(catpath, monitored=False, wrapf=WRAPF)
    acats = collect_asc_cats(config, cat.name)

    pfilter = options.tfilter or config.tfilter

    nselected = 0
    for msg in cat:
        history = asc_collect_history(msg, acats, config)
        if stest(msg, cat, history, config, options) is None:
            continue
        nselected += 1

        # In order to index ascriptions properly, collect all.
        history = asc_collect_history(msg, acats, config, all=True)

        hinfo = [C.GREEN + ">>> history follows:" + C.RESET]
        hfmt = "%%%dd" % len(str(len(history)))
        for i in range(len(history)):
            a = history[i]
            wtrans = a.msg and not is_fuzzy(a.msg)
            typewtag = a.type
            if a.tag:
                typewtag += "/" + a.tag
            ihead = C.BOLD + "#%d" % (i + 1) + C.RESET + " "
            anote_d = dict(usr=a.user, mod=typewtag, dat=a.date, rev=a.rev)
            if a.rev:
                anote = "%(mod)s by %(usr)s on %(dat)s (rev %(rev)s)" % anote_d
            else:
                anote = "%(mod)s by %(usr)s on %(dat)s" % anote_d
            hinfo += [ihead + anote]
            if not a.type == _atype_mod or not wtrans:
                # Nothing more to show if this ascription was not modification,
                # or there is no translated message associated to it.
                continue
            # Find first earlier non-fuzzy for diffing.
            i_next = first_nfuzzy(history, i + 1)
            if i_next is None:
                # Nothing more to show without next non-fuzzy.
                continue
            dmsg = Message(a.msg)
            anydiff = dmsg.embed_diff(history[i_next].msg, tocurr=True,
                                      pfilter=pfilter, hlto=sys.stdout)
            if anydiff:
                dmsg.manual_comment = Monlist() # review tags were here
                dmsgstr = dmsg.to_string().rstrip("\n")
                hindent = " " * (len(hfmt % 0) + 2)
                hinfo += [hindent + x for x in dmsgstr.split("\n")]
        hinfo = "\n".join(hinfo)

        i_nfasc = first_nfuzzy(history)
        if i_nfasc is not None:
            msg = Message(msg)
            msg.embed_diff(history[i_nfasc].msg, tocurr=True,
                           pfilter=pfilter, hlto=sys.stdout)
        report_msg_content(msg, cat, wrapf=WRAPF,
                           note=hinfo, delim=("-" * 20))

    return nselected


def clear_review_msg (msg, rep_ntrans=None, clrevd=True):

    cleared = False
    for flag in msg.flag.items():
        if flag == _revflag or (clrevd and _revdflag_rx.search(flag)):
            msg.flag.remove(flag)
            if not cleared:
                # Clear possible embedded diffs.
                msg.unembed_diff(keeponfuzz=True)
                cleared = True
            # Do not break, other review flags possible.

    return cleared


def ascribe_derivobs_cat (options, config, catpath):

    cat = Catalog(catpath, monitored=False, wrapf=WRAPF)
    acats = collect_asc_cats(config, cat.name, monall=True)

    catrev = config.vcs.revision(cat.filename)

    reachable = set()
    for msg in cat:
        history = asc_collect_history(msg, acats, config)
        for a in history:
            reachable.add((a.user, a.msg))

    for user, acat in acats.iteritems():
        for amsg in acat:
            if (user, amsg) in reachable:
                continue
            oacats = acats.copy()
            oacats.pop(user)
            history = asc_collect_history(amsg, oacats, config)
            for a in history:
                reachable.add((a.user, a.msg))

    nobsoleted = 0
    for user, acat in acats.iteritems():
        for amsg in acat:
            if (user, amsg) not in reachable:
                # Ascribe obsolescence if history is not showing it already.
                history = asc_collect_history(amsg, acats, config)
                if not is_obsoleted(history):
                    nobsoleted += 1
                    ascribe_msg_obs(amsg, user, config, catrev)
        sync_and_rep(acat)

    return nobsoleted


def is_fuzzy (msg):

    return "fuzzy" in msg.flag


def is_translated (msg):

    if not msg.obsolete:
        return msg.translated
    else:
        if "fuzzy" not in msg.flag:
            for msgstr in msg.msgstr:
                if msgstr:
                    return True
        return False


def is_obsoleted (history):

    # History shows obsolescence if no revival after last obsolescence,
    # or if obsolescence was never ascribed.

    obsoleted = False
    for a in history:
        if a.type == _atype_obs:
            obsoleted = True
            break
        if a.type == _atype_rvv:
            break

    return obsoleted


def first_nfuzzy (history, start=0):

    for i in range(start, len(history)):
        if history[i].msg and not is_fuzzy(history[i].msg):
            return i

    return None


def collect_asc_cats (config, catname, muser=None, monall=False):

    acats = {}
    for ouser in config.users:
        amon = False
        if (muser and ouser == muser) or monall:
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


_atype_obs = "obsoleted"

def ascribe_msg_obs (amsg, user, config, catrev):

    modstr = date_now()
    if catrev:
        modstr += " | " + catrev
    asc_append_field(amsg, _atype_obs, modstr)


_atype_rvv = "revived"

def ascribe_msg_rvv (amsg, user, config, catrev):

    modstr = date_now()
    if catrev:
        modstr += " | " + catrev
    asc_append_field(amsg, _atype_rvv, modstr)


def asc_eq (msg1, msg2):
    """
    Whether two messages are equal from the ascription viewpoint.
    """

    return (    True
            and is_fuzzy(msg1) == is_fuzzy(msg2)
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


def asc_collect_history (msg, acats, config, all=False):
    """
    Create ascription history of the message.

    The history is assembled as list of tuples
    C{(asc-message, user, asc-type, asc-tag, date, revision)},
    sorted chronologically by date/revision (newest first).
    Date gets to be a real C{datetime} object.

    Normally only the last ascription of a given user/catalog/message
    combination is taken into history, as others do not have
    the associated message directly available. If C{all} is set to C{True},
    then all ascriptions are going to be taken. At the moment, messages
    attached to extra ascriptions will be C{None}, but in the future
    they may be obtained from VCS (pending fast CVS with local history).
    """

    return asc_collect_history_w(msg, acats, config, all, None, {})


def asc_collect_history_w (msg, acats, config, all, before, seenmsg):

    history = []
    if not seenmsg:
        seenmsg = {}

    # Avoid circular paths.
    if msg.key in seenmsg:
        return history
    seenmsg[msg.key] = True

    # Collect history from all ascription catalogs.
    fuzzy_amsgs = []
    for user, acat in acats.iteritems():
        if msg in acat:
            amsg = acat[msg]
            for a in asc_collect_history_single(amsg, acat, user, config, all):
                if not before or asc_age_cmp(a, before, config) < 0:
                    history.append(a)
            if is_fuzzy(amsg):
                fuzzy_amsgs.append(amsg)

    # Collect keys of fuzzy messages with unique and existing pivots.
    msg_pkey = (msg.msgctxt, msg.msgid)
    fuzzy_amsg_keys = set()
    for amsg in fuzzy_amsgs:
        if amsg.msgid_previous is not None:
            pkey = (amsg.msgctxt_previous, amsg.msgid_previous)
            if pkey != msg_pkey and pkey not in fuzzy_amsg_keys:
                fuzzy_amsg_keys.add(pkey)

    history.sort(lambda x, y: asc_age_cmp(y, x, config))

    # Continue into the past by pivoting around fuzzy messages.
    if fuzzy_amsg_keys:
        # FIXME:
        # What to do if there are several unique pivots?
        # Can it happen? In normal operation, or only in corner cases?
        # Multiple histories, diamond diagram and stuff...
        # For now, just draw one randomly, and warn about it.
        npaths = len(fuzzy_amsg_keys)
        if npaths > 1:
            warning("%s: multiple history paths (%d) for message at %s(#%s)"
                    % (cat.filename, npaths, msg.refline, msg.refentry))
        pmsg = MessageUnsafe()
        pmsg.msgctxt, pmsg.msgid = fuzzy_amsg_keys.pop()
        # All ascriptions beyond the pivot must be older than the oldest so far.
        after = history and history[-1] or before
        ct_history = asc_collect_history_w(pmsg, acats, config, all,
                                           after, seenmsg)
        history.extend(ct_history)

    return history


def asc_collect_history_single (amsg, acat, auser, config, all):

    history = []
    for asc in asc_parse_ascriptions(amsg, acat):
        a = _Ascription()
        a.msg, a.user = amsg, auser
        a.type, a.tag, a.date, a.rev = asc
        history.append(a)

    history.sort(lambda x, y: asc_age_cmp(y, x, config))
    if not all:
        history = [history[0]]
    else:
        # Kill messages of non-latest ascriptions,
        # until they can be fetched from VCS.
        for a in history[1:]:
            a.msg = None

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

    users = set()
    if userstr:
        for user in userstr.split(","):
            user = user.strip()
            if not user.startswith("~"):
                users.add(user)
            else:
                user = user[1:]
                for ouser in config.users:
                    if user != ouser:
                        users.add(ouser)
    for user in users:
        if user not in config.users:
            error("unknown user '%s' in config '%s'" % (user, config.path),
                  subsrc=cid)

    return users


# Build compound selector out of list of specifications.
# Selector specification is a string in format NAME:ARG1:ARG2:...
# (instead of colon, separator can be any non-alphanumeric excluding
# underscore and hyphen)
def build_selector (options, selspecs, hist=False):

    # Component selectors.
    selectors = []
    for selspec in selspecs:
        argsep = ":"
        for c in selspec:
            if not (c.isalpha() or c.isdigit() or c in ("_", "-")):
                argsep = c
                break
        lst = selspec.split(argsep)
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
# Caching for selectors.

class _Cache (object):

    def __init__ (self, dict={}):

        for key, val in dict.iteritems():
            self.__dict__[key] = val

    pass


def cached_matcher (cache, expr, config, options, cid):

    if (   getattr(cache, "options", None) is not options
        or getattr(cache, "config", None) is not config
    ):
        cache.options = options
        cache.config = config
        pfilter = options.tfilter or config.tfilter
        filters = []
        if pfilter:
            filters = [pfilter]
        mopts = _Cache(dict(case=False))
        cache.matcher = build_msg_fmatcher(expr, filters=filters, mopts=mopts)

    return cache.matcher


def cached_users (cache, user_spec, config, cid, utype=None):

    if (   getattr(cache, "config", None) is not config
        or utype not in getattr(cache, "users", {})
    ):
        cache.config = config
        if not hasattr(cache, "users"):
            cache.users = {}
        cache.users[utype] = []
        if user_spec:
            cache.users[utype] = parse_users(user_spec, config, cid)

    return cache.users[utype]


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

        pfilter = options.tfilter or config.tfilter

        if history:
            amsg = history[0].msg
            if asc_eq(msg, amsg):
                return True
            elif pfilter:
                # Also consider ascribed if no difference from last ascription
                # under the filter in effect.
                if not msg.diff_from(amsg, pfilter=pfilter):
                    return True
        elif not is_translated(msg) and not is_fuzzy(msg):
            # Also consider pristine messages ascribed.
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


def selector_fexpr (expr=None):
    cid = "selector:fexpr"

    if not (expr or "").strip():
        error("matching expression cannot be empty", subsrc=cid)

    cache = _Cache()

    def selector (msg, cat, history, config, options):

        matcher = cached_matcher(cache, expr, config, options, cid)
        if matcher(msg, cat):
            return True

        return None

    return selector


def selector_e (entry=None):
    cid = "selector:e"

    if not entry or not entry.isdigit():
        error("message reference by entry must be an integer", subsrc=cid)
    refentry = int(entry)

    def selector (msg, cat, history, config, options):

        if msg.refentry == refentry:
            return True

        return None

    return selector


def selector_hexpr (expr=None, user_spec=None, addrem=None):
    cid = "selector:hexpr"

    if not (expr or "").strip():
        error("matching expression cannot be empty", subsrc=cid)

    cache = _Cache()

    def selector (msg, cat, history, config, options):

        matcher = cached_matcher(cache, expr, config, options, cid)
        users = cached_users(cache, user_spec, config, cid)

        if not addrem:
            i = 0
        else:
            i = first_nfuzzy(history, 0)
            if i is None:
                return None

        while i < len(history):
            a = history[i]
            if users and a.user not in users:
                i += 1
                continue

            if not addrem:
                amsg = a.msg
                i_next = i + 1
            else:
                i_next = first_nfuzzy(history, i + 1)
                if i_next is None:
                    break
                amsg = MessageUnsafe(a.msg)
                pfilter = options.tfilter or config.tfilter
                amsg.embed_diff(history[i_next].msg, tocurr=True,
                                pfilter=pfilter, addrem=addrem)

            if matcher(amsg, cat):
                return i

            i = i_next

        return None

    return selector


# Select last ascription (any, or by users).
def selector_asc (user_spec=None):
    cid = "selector:asc"

    cache = _Cache()

    def selector (msg, cat, history, config, options):

        users = cached_users(cache, user_spec, config, cid)

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

    cache = _Cache()

    def selector (msg, cat, history, config, options):

        users = cached_users(cache, user_spec, config, cid)

        i_sel = None
        for i in range(len(history)):
            a = history[i]
            if a.type == _atype_mod and (not users or a.user in users):
                i_sel = i
                break

        return i_sel

    return selector


# Select first modification (any or by m-users, and not by r-users)
# after last review (any or by r-users, and not by m-users).
def selector_modar (muser_spec=None, ruser_spec=None, atag_req=None):
    cid = "selector:modar"

    cache = _Cache()

    def selector (msg, cat, history, config, options):

        rusers = cached_users(cache, ruser_spec, config, cid, utype="r")
        musers = cached_users(cache, muser_spec, config, cid, utype="m")

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
                    pf = options.tfilter or config.tfilter
                    if pf and not mm.diff_from(mr, pfilter=pf):
                        i_cand = None
                    else:
                        i_sel = i_cand
                        break
            if (    a.type == _atype_mod
                and (not musers or a.user in musers)
                and (not rusers or a.user not in rusers)
            ):
                # Modification found, make it candidate.
                i_cand = i

        if i_cand is not None:
            # There was no review after modification candidate, so use it,
            # unless filter is in effect and there is no difference between
            # candidate and the first earlier modification
            # (any, or not by m-users).
            pfilter = options.tfilter or config.tfilter
            if pfilter and i_cand + 1 < len(history):
                mm = history[i_cand].msg
                for a in history[i_cand + 1:]:
                    if (    a.type == _atype_mod
                        and (not musers or a.user not in musers)
                        and not a.msg.diff_from(mm, pfilter=options.tfilter)
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

    cache = _Cache()

    def selector (msg, cat, history, config, options):

        users = cached_users(cache, user_spec, config, cid)

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


# Select first review (any or by r-users, and not by m-users)
# before last modification (any or by m-users, and not by r-users).
def selector_revbm (ruser_spec=None, muser_spec=None, atag_req=None):
    cid = "selector:revbm"

    cache = _Cache()

    def selector (msg, cat, history, config, options):

        rusers = cached_users(cache, ruser_spec, config, cid, utype="r")
        musers = cached_users(cache, muser_spec, config, cid, utype="m")

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
                and (not musers or a.user not in musers)
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
    "fexpr": (selector_fexpr, False),
    "e": (selector_e, False),
    "hexpr": (selector_hexpr, True),
    "asc": (selector_asc, True),
    "mod": (selector_mod, True),
    "modar": (selector_modar, True),
    "rev": (selector_rev, True),
    "revbm": (selector_revbm, True),
}

# -----------------------------------------------------------------------------

if __name__ == "__main__":
    main()

