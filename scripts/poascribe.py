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
import imp
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
        "-d", "--depth", metavar="LEVEL",
        action="store", dest="depth", default=None,
        help="consider ascription history up to this level into the past "
             "(relevant in some modes)")
    opars.add_option(
        "-x", "--externals", metavar="PYFILE",
        action="append", dest="externals", default=[],
        help="collect optional functionality from an external Python file "
             "(selectors, etc.)")
    opars.add_option(
        "-l", "--live-diff",
        action="store_true", dest="live_diff", default=False,
        help="use \"live\" differencing, i.e. embedding into current fields "
             "(relevant in some modes)")
    opars.add_option(
        "-c", "--commit",
        action="store_true", dest="commit", default=False,
        help="automatically commit original and ascription catalogs, "
             "in proper order")
    opars.add_option(
        "-m", "--message", metavar="TEXT",
        action="store", dest="message", default=None,
        help="commit message for original catalogs, when %(option)s "
             "is in effect" % dict(option="-c"))
    opars.add_option(
        "-M", "--ascript-message", metavar="TEXT",
        action="store", dest="ascript_message", default=None,
        help="commit message for ascription catalogs, when %(option)s "
             "is in effect" % dict(option="-c"))
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

    # Collect any external functionality.
    for xmod_path in options.externals:
        collect_externals(xmod_path)

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
    modenames = free_args.pop(0).split(",")
    needuser = False
    class _Mode: pass
    modes = []
    for modename in modenames:
        mode = _Mode()
        mode.name = modename
        if 0: pass
        elif mode.name in ("status", "st"):
            mode.execute = examine_state
            mode.selector = selector or build_selector(options, ["any"])
        elif mode.name in ("modified", "mo"):
            mode.execute = ascribe_modified
            mode.selector = selector or build_selector(options, ["any"])
            needuser = True
        elif mode.name in ("reviewed", "re"):
            mode.execute = ascribe_reviewed
            # Default selector for review ascription must match
            # default selector for review selection.
            mode.selector = selector or build_selector(options, ["nwasc"])
            needuser = True
        elif mode.name in ("diff", "di"):
            mode.execute = diff_select
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
            mode.execute = clear_review
            mode.selector = selector or build_selector(options, ["any"])
        elif mode.name in ("history", "hi"):
            mode.execute = show_history
            mode.selector = selector or build_selector(options, ["nwasc"])
        else:
            error("unknown operation mode '%s'" % mode.name)
        modes.append(mode)

    if needuser:
        if len(free_args) < 1:
            error("issued operations require a user to be specified")
        user = free_args.pop(0).strip()
        for mode in modes:
            mode.user = user

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
        cfgpath = join_ncwd(cfgpath) # for nicer message output
        config = configs_loaded.get(cfgpath, None)
        if not config:
            # New config, load.
            config = Config(cfgpath)
            configs_loaded[cfgpath] = config

        # Collect PO files.
        if os.path.isdir(path):
            catpaths_raw = collect_catalogs(path)
        else:
            catpaths_raw = [path]
        # Determine paths of ascription catalogs.
        # Pack as (catpath, acatpath) tuples.
        catpaths = []
        absrootpath = os.path.abspath(config.catroot)
        lenarpath = len(absrootpath)
        lenarpathws = lenarpath + len(os.path.sep)
        for catpath_raw in catpaths_raw:
            abscatpath = os.path.abspath(catpath_raw)
            p = abscatpath.find(absrootpath)
            if p != 0 or abscatpath[lenarpath:lenarpathws] != os.path.sep:
                error("catalog not in the root given by configuration: %s"
                      % catpath_raw)
            acatpath = join_ncwd(config.ascroot, abscatpath[lenarpathws:])
            catpaths.append((join_ncwd(catpath_raw), acatpath))

        # Collect the config and corresponding catalogs.
        configs_catpaths.append((config, catpaths))

    # Commit modifications to original catalogs if requested.
    if options.commit:
        commit_catalogs(configs_catpaths, False, options.message)

    # Execute operations.
    for mode in modes:
        mode.execute(options, configs_catpaths, mode)

    # Commit modifications to ascription catalogs if requested.
    if options.commit:
        commit_catalogs(configs_catpaths, True, options.ascript_message)


def commit_catalogs (configs_catpaths, ascriptions=True, message=None):

    # Attach paths to each distinct config, to commit them all at once.
    configs = []
    catpaths_byconf = {}
    for config, catpaths in configs_catpaths:
        if config not in catpaths_byconf:
            catpaths_byconf[config] = []
            configs.append(config)
        for catpath, acatpath in catpaths:
            if ascriptions:
                catpath = acatpath
            catpaths_byconf[config].append(catpath)

    # Commit by config.
    for config in configs:
        cmsg = message
        if message is None:
            if ascriptions:
                cmsg = config.ascript_commit_message
            else:
                cmsg = config.commit_message
        if not config.vcs.commit(catpaths_byconf[config], cmsg):
            error("VCS reports that catalogs cannot be committed")


class Config:

    def __init__ (self, cpath):

        config = SafeConfigParser()
        ifl = codecs.open(cpath, "r", "UTF-8")
        config.readfp(ifl)
        ifl.close()

        self.path = cpath

        gsect = dict(config.items("global"))
        cpathdir = os.path.dirname(cpath)
        self.catroot = join_ncwd(cpathdir, gsect.get("catalog-root", ""))
        self.ascroot = join_ncwd(cpathdir, gsect.get("ascript-root", ""))
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

        self.commit_message = gsect.get("commit-message", None)
        self.ascript_commit_message = gsect.get("ascript-commit-message", None)

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
        udat.name = "UFUZZ"
        udat.oname = None
        udat.email = None


def examine_state (options, configs_catpaths, mode):

    stest = mode.selector

    # Count unascribed messages through catalogs.
    counts = dict([(x, {}) for x in _all_states])
    def accu(countdict, catpath):
        if catpath not in countdict:
            countdict[catpath] = 0
        countdict[catpath] += 1
        return countdict[catpath]

    for config, catpaths in configs_catpaths:
        for catpath, acatpath in catpaths:
            # Open current and ascription catalog.
            cat = Catalog(catpath, monitored=False)
            acat = Catalog(acatpath, create=True, monitored=False)
            # Count non-ascribed by original catalog.
            for msg in cat:
                history = asc_collect_history(msg, acat, config)
                if not history and is_any_untran(msg):
                    continue # pristine
                if stest(msg, cat, history, config, options) is None:
                    continue # not selected
                if not history or not asc_eq(msg, history[0].msg):
                    st = state(msg)
                    if catpath not in counts[st]:
                        counts[st][catpath] = 0
                    counts[st][catpath] += 1
            # Count non-ascribed by ascription catalog.
            for amsg in acat:
                if amsg not in cat:
                    ast = state(amsg)
                    st = None
                    if ast == _st_tran:
                        st = _st_otran
                    elif ast == _st_fuzzy:
                        st = _st_ofuzzy
                    elif ast == _st_untran:
                        st = _st_ountran
                    if st:
                        if catpath not in counts[st]:
                            counts[st][catpath] = 0
                        counts[st][catpath] += 1

    # Present findings.
    for st, chead in (
        (_st_tran, "Unascribed translated"),
        (_st_fuzzy, "Unascribed fuzzy"),
        (_st_untran, "Unascribed untranslated"),
        (_st_otran, "Unascribed obsolete translated"),
        (_st_ofuzzy, "Unascribed obsolete fuzzy"),
        (_st_ountran, "Unascribed obsolete untranslated"),
    ):
        unasc_cnts = counts[st]
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

    counts = dict([(x, 0) for x in _all_states])
    for config, catpaths in configs_catpaths:
        if user not in config.users:
            error("unknown user '%s' in config '%s'" % (user, config.path))

        for catpath, acatpath in catpaths:
            ccounts = ascribe_modified_cat(options, config, user,
                                           catpath, acatpath, mode.selector)
            for st, val in ccounts.items():
                counts[st] += val

    if counts[_st_tran] > 0:
        report("===! Translated: %d entries" % counts[_st_tran])
    if counts[_st_fuzzy] > 0:
        report("===! Fuzzy: %d entries" % counts[_st_fuzzy])
    if counts[_st_untran] > 0:
        report("===! Untranslated: %d entries" % counts[_st_untran])
    if counts[_st_otran] > 0:
        report("===! Obsolete translated: %d entries" % counts[_st_otran])
    if counts[_st_ofuzzy] > 0:
        report("===! Obsolete fuzzy: %d entries" % counts[_st_ofuzzy])
    if counts[_st_ountran] > 0:
        report("===! Obsolete untranslated: %d entries" % counts[_st_ountran])


def ascribe_reviewed (options, configs_catpaths, mode):

    user = mode.user
    stest = mode.selector

    if user == UFUZZ:
        error("cannot ascribe reviews to reserved user '%s'" % UFUZZ)

    nasc = 0
    for config, catpaths in configs_catpaths:
        if user not in config.users:
            error("unknown user '%s' in config '%s'" % (user, config.path))

        for catpath, acatpath in catpaths:
            nasc += ascribe_reviewed_cat(options, config, user,
                                         catpath, acatpath, stest)

    if nasc > 0:
        report("===! Reviewed: %d entries" % nasc)


def diff_select (options, configs_catpaths, mode):

    stest = mode.selector
    aselect = mode.aselector

    ndiffed = 0
    for config, catpaths in configs_catpaths:
        for catpath, acatpath in catpaths:
            pfilter = options.tfilter or config.tfilter
            ndiffed += diff_select_cat(options, config, catpath, acatpath,
                                       stest, aselect, pfilter)

    if ndiffed > 0:
        report("===! Diffed from history: %d" % ndiffed)


def clear_review (options, configs_catpaths, mode):

    stest = mode.selector

    ncleared = 0
    for config, catpaths in configs_catpaths:
        for catpath, acatpath in catpaths:
            ncleared += clear_review_cat(options, config, catpath, acatpath,
                                         stest)

    if ncleared > 0:
        report("===! Cleared review states: %d" % ncleared)


def show_history (options, configs_catpaths, mode):

    stest = mode.selector

    nshown = 0
    for config, catpaths in configs_catpaths:
        for catpath, acatpath in catpaths:
            nshown += show_history_cat(options, config, catpath, acatpath,
                                       stest)

    if nshown > 0:
        report("===> Computed histories: %d" % nshown)


def ascribe_modified_cat (options, config, user, catpath, acatpath, stest):

    # Open current catalog and ascription catalog.
    cat = Catalog(catpath, monitored=False)
    acat = prep_write_asc_cat(acatpath, config)

    # Collect unascribed messages, but ignoring pristine ones
    # (those which are both untranslated and without history).
    toasc_msgs = []
    counts = dict([(x, 0) for x in _all_states])
    counts0 = counts.copy()
    for msg in cat:
        history = asc_collect_history(msg, acat, config)
        if not history and is_any_untran(msg):
            continue # pristine
        if stest(msg, cat, history, config, options) is None:
            continue # not selected
        if not (history and asc_eq(msg, history[0].msg)):
            toasc_msgs.append(msg)
            counts[state(msg)] += 1

    # Collect non-obsolete ascribed messages that no longer have
    # original counterpart, to ascribe as obsolete.
    for amsg in acat:
        if amsg not in cat:
            ast = state(amsg)
            st = None
            if ast == _st_tran:
                st = _st_otran
            elif ast == _st_fuzzy:
                st = _st_ofuzzy
            elif ast == _st_untran:
                st = _st_ountran
            if st:
                msg = asc_collect_history_single(amsg, acat, config)[0].msg
                msg.obsolete = True
                toasc_msgs.append(msg)
                counts[st] += 1

    if not toasc_msgs:
        # No messages to ascribe.
        return counts0

    if not config.vcs.is_clear(cat.filename):
        warning("%s: VCS state not clear, cannot ascribe modifications"
                % cat.filename)
        return counts0

    # Current VCS revision of the catalog.
    catrev = config.vcs.revision(cat.filename)

    # Ascribe messages as modified.
    for msg in toasc_msgs:
        ascribe_msg_mod(msg, acat, catrev, user, config)

    if asc_sync_and_rep(acat):
        config.vcs.add(acat.filename)

    return counts


_revdflags = ("revd", "reviewed")
_revdflag_rx = re.compile(r"^(?:%s) *[/:]?(.*)" % "|".join(_revdflags), re.I)

def ascribe_reviewed_cat (options, config, user, catpath, acatpath, stest):

    live = options.live_diff

    # Open current catalog and ascription catalog.
    # Monitored, for removal of reviewed-* flags.
    cat = Catalog(catpath, monitored=True, wrapf=WRAPF)
    acat = prep_write_asc_cat(acatpath, config)

    rev_msgs_tags = []
    non_mod_asc_msgs = []
    for msg in cat:
        history = asc_collect_history(msg, acat, config)
        # Makes no sense to ascribe review to pristine messages.
        if not history and is_any_untran(msg):
            continue
        if stest(msg, cat, history, config, options) is None:
            continue
        # Message cannot be ascribed as reviewed if it has not been
        # already ascribed as modified.
        # Message equality must be tested without review scaffolding.
        cmsg = MessageUnsafe(msg)
        clear_review_msg(cmsg, live)
        if not history or not asc_eq(cmsg, history[0].msg):
            # Collect to report later.
            non_mod_asc_msgs.append(msg)
            # Clear only flags to-review, and not explicit review-done.
            clear_review_msg(msg, live, clrevd=False)
            continue

        # Collect any tags in explicit reviewed-flags.
        tags = []
        for flag in msg.flag:
            m = _revdflag_rx.search(flag)
            if m:
                tags.append(m.group(1).strip() or None)
                # Do not break, several review flags possible.
        if not tags and options.tag:
            tags.append(options.tag)

        # Clear review state.
        clear_review_msg(msg, live)

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

    # Current VCS revision of the catalog.
    catrev = config.vcs.revision(cat.filename)

    # Ascribe messages as reviewed.
    for msg, tags in rev_msgs_tags:
        ascribe_msg_rev(msg, acat, tags, catrev, user, config)

    sync_and_rep(cat)
    if asc_sync_and_rep(acat):
        config.vcs.add(acat.filename)

    return len(rev_msgs_tags)


# Flag used to mark messages selected for review.
_revflag = u"review"

def diff_select_cat (options, config, catpath, acatpath,
                     stest, aselect, pfilter):

    live = options.live_diff

    cat = Catalog(catpath, monitored=True, wrapf=WRAPF)
    acat = Catalog(acatpath, create=True, monitored=False)

    nflagged = 0
    for msg in cat:
        history = asc_collect_history(msg, acat, config)
        # Makes no sense to review pristine messages.
        if not history and is_any_untran(msg):
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
            amsg = history[i_asc].msg
            anydiff = msg.embed_diff(amsg, live=live, pfilter=pfilter)
            # NOTE: Do NOT think of avoiding to flag the message if there is
            # no difference to history, must be symmetric to review ascription.
        msg.flag.add(_revflag)
        nflagged += 1

    sync_and_rep(cat)

    return nflagged


def clear_review_cat (options, config, catpath, acatpath, stest):

    live = options.live_diff

    cat = Catalog(catpath, monitored=True, wrapf=WRAPF)
    acat = Catalog(acatpath, create=True, monitored=False)

    ncleared = 0
    for msg in cat:
        history = asc_collect_history(msg, acat, config)
        if stest(msg, cat, history, config, options) is None:
            continue
        if clear_review_msg(msg, live):
            ncleared += 1

    sync_and_rep(cat)

    return ncleared


def show_history_cat (options, config, catpath, acatpath, stest):

    C = colors_for_file(sys.stdout)

    cat = Catalog(catpath, monitored=False, wrapf=WRAPF)
    acat = Catalog(acatpath, create=True, monitored=False)

    pfilter = options.tfilter or config.tfilter

    nselected = 0
    for msg in cat:
        history = asc_collect_history(msg, acat, config)
        if stest(msg, cat, history, config, options) is None:
            continue
        nselected += 1

        hlevels = len(history)
        if options.depth is not None:
            hlevels = int(options.depth)
            if hlevels > len(history):
                hlevels = len(history)

        hinfo = []
        if hlevels > 0:
            hinfo += [C.GREEN + ">>> history follows:" + C.RESET]
            hfmt = "%%%dd" % len(str(hlevels))
        for i in range(hlevels):
            a = history[i]
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
            if not a.type == _atype_mod or is_any_fuzzy(a.msg):
                # Nothing more to show if this ascription is not modification,
                # or a fuzzy message is associated to it.
                continue
            # Find first earlier non-fuzzy for diffing.
            i_next = first_nfuzzy(history, i + 1)
            if i_next is None:
                # Nothing more to show without next non-fuzzy.
                continue
            dmsg = MessageUnsafe(a.msg)
            nmsg = history[i_next].msg
            anydiff = dmsg.embed_diff(nmsg, live=True,
                                      pfilter=pfilter, hlto=sys.stdout)
            if anydiff:
                dmsgfmt = dmsg.to_string(force=True, wrapf=WRAPF).rstrip("\n")
                hindent = " " * (len(hfmt % 0) + 2)
                hinfo += [hindent + x for x in dmsgfmt.split("\n")]
        hinfo = "\n".join(hinfo)

        i_nfasc = first_nfuzzy(history)
        if i_nfasc is not None:
            msg = Message(msg)
            nmsg = history[i_nfasc].msg
            anydiff = msg.embed_diff(nmsg, live=True,
                                     pfilter=pfilter, hlto=sys.stdout)
        report_msg_content(msg, cat, wrapf=WRAPF,
                           note=(hinfo or None), delim=("-" * 20))

    return nselected


def clear_review_msg (msg, live, rep_ntrans=None, clrevd=True):

    cleared = False
    for flag in list(msg.flag): # modified inside
        if flag == _revflag or (clrevd and _revdflag_rx.search(flag)):
            msg.flag.remove(flag)
            if not cleared:
                # Clear possible embedded diffs.
                msg.unembed_diff(live=live)
                cleared = True
            # Do not break, other review flags possible.

    return cleared


# Exclusive states of a message.
# FIXME: This functionality better exported to pology.file.message
_st_tran = "T"
_st_fuzzy = "F"
_st_untran = "U"
_st_otran = "OT"
_st_ofuzzy = "OF"
_st_ountran = "OU"
_all_states = (
    _st_tran, _st_fuzzy, _st_untran,
    _st_otran, _st_ofuzzy, _st_ountran,
)
def state (msg):
    if not msg.obsolete:
        if msg.translated:
            return _st_tran
        elif msg.fuzzy:
            return _st_fuzzy
        else:
            return _st_untran
    else:
        if "fuzzy" in msg.flag:
            return _st_ofuzzy
        for msgstr in msg.msgstr:
            if msgstr:
                return _st_otran
        return _st_ountran


def is_tran (msg):
    return state(msg) == _st_tran

def is_fuzzy (msg):
    return state(msg) == _st_fuzzy

def is_untran (msg):
    return state(msg) == _st_untran

def is_otran (msg):
    return state(msg) == _st_otran

def is_ofuzzy (msg):
    return state(msg) == _st_ofuzzy

def is_ountran (msg):
    return state(msg) == _st_ountran

def is_any_untran (msg):
    return state(msg) in (_st_untran, _st_ountran)

def is_any_fuzzy (msg):
    return state(msg) in (_st_fuzzy, _st_ofuzzy)

def is_any_obsolete (msg):
    return state(msg) in (_st_otran, _st_ofuzzy, _st_ountran)


def first_nfuzzy (history, start=0):

    for i in range(start, len(history)):
        hmsg = history[i].msg
        if hmsg and not is_any_fuzzy(hmsg):
            return i

    return None


def prep_write_asc_cat (acatpath, config):

    if not os.path.isfile(acatpath):
        return init_asc_cat(acatpath, config)
    else:
        return Catalog(acatpath, monitored=True, wrapf=WRAPF)


def init_asc_cat (acatpath, config):

    acat = Catalog(acatpath, create=True, monitored=True, wrapf=WRAPF)
    ahdr = acat.header

    ahdr.title = Monlist([u"Ascription shadow for %s.po" % acat.name])

    translator = u"Ascriber"

    if config.team_email:
        author = u"%s <%s>" % (translator, config.team_email)
    else:
        author = u"%s" % translator
    ahdr.author = Monlist([author])

    ahdr.copyright = u"Copyright same as for the original catalog."
    ahdr.license = u"License same as for the original catalog."
    ahdr.comment = Monlist([u"===== DO NOT EDIT MANUALLY ====="])

    rfv = ahdr.replace_field_value # shortcut

    rfv("Project-Id-Version", unicode(acat.name))
    rfv("Report-Msgid-Bugs-To", unicode(config.team_email or ""))
    rfv("PO-Revision-Date", unicode(format_datetime()))
    rfv("Content-Type", u"text/plain; charset=UTF-8")
    rfv("Content-Transfer-Encoding", u"8bit")

    if config.team_email:
        ltr = "%s <%s>" % (translator, config.team_email)
    else:
        ltr = translator
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


def update_asc_hdr (acat):

    acat.header.replace_field_value("PO-Revision-Date",
                                    unicode(format_datetime()))


_id_fields = (
    "msgctxt", "msgid",
)
_nonid_fields = (
    "msgid_plural", "msgstr",
)
_fields_previous = (
    "msgctxt_previous", "msgid_previous", "msgid_plural_previous",
)
_fields_comment = (
    "manual_comment", "auto_comment",
)
_nonid_fields_tracked = (()
    + _nonid_fields
    + _fields_previous
    + ("manual_comment",)
)
_multiple_fields = (()
    + ("msgstr",)
    + _fields_comment
)
_nonid_fields_eq_nonfuzzy = (()
    + _nonid_fields
    + ("manual_comment",)
)
_nonid_fields_eq_fuzzy = (()
    + _nonid_fields_eq_nonfuzzy
    + _fields_previous
)

_trsep_head = u"|"
_trsep_head_ext = u"~"
_trsep_mod_none = u"x"
_trsep_mod_eq = u"e"

def field_separator_head (length):

    return _trsep_head + _trsep_head_ext * length


def needed_separator_length (msg):

    goodsep = False
    seplen = 0
    while not goodsep:
        seplen += 1
        sephead = field_separator_head(seplen)
        goodsep = True
        for field in _nonid_fields_tracked:
            values = msg.get(field)
            if values is None:
                continue
            if isinstance(values, basestring):
                values = [values]
            for value in values:
                if sephead in value:
                    goodsep = False
                    break
            if not goodsep:
                break

    return seplen


def has_nonid_diff (pmsg, msg):

    for field in _nonid_fields_tracked:
        msg_value = msg.get(field)
        if not is_any_fuzzy(msg) and field in _fields_previous:
            # Ignore previous values in messages with no fuzzy flag.
            msg_value = None
        pmsg_value = pmsg.get(field)
        if msg_value != pmsg_value:
            return True

    return False


def get_as_sequence (msg, field, asc=True):

    if not asc and not is_any_fuzzy(msg) and field in _fields_previous:
        # Ignore previous fields on non-ascription messages without fuzzy flag.
        return []

    msg_seq = msg.get(field)
    if msg_seq is None:
        msg_seq = []
    elif field not in _multiple_fields:
        msg_seq = [msg_seq]
    elif field in _fields_comment:
        # Report comments as a single newline-delimited entry.
        if msg_seq:
            msg_seq = [u"\n".join(msg_seq)]

    return msg_seq


def set_from_sequence (msg_seq, msg, field):

    if field not in _multiple_fields:
        # Single entry; set to given, or to None if no elements.
        msg_val = None
        if msg_seq:
            msg_val = msg_seq[0]
        multiple = False
    elif field in _fields_comment:
        # Comments treated as single newline-delimited entries; split.
        msg_val = []
        if msg_seq:
            msg_val = msg_seq[0].split("\n")
        multiple = True
    else:
        # Straight sequence.
        msg_val = msg_seq
        multiple = True

    if multiple and isinstance(msg, Message):
        msg_val = Monlist(msg_val)

    setattr(msg, field, msg_val)


def add_nonid (amsg, msg, slen, rhistory):

    shead = field_separator_head(slen)
    nones = [field_separator_head(x.slen) + _trsep_mod_none
             for x in rhistory if x.slen]
    padnone = u"\n".join(nones)

    for field in _nonid_fields_tracked:

        msg_seq = get_as_sequence(msg, field, asc=False)
        amsg_seq = get_as_sequence(amsg, field)

        # Expand items to length in new message.
        for i in range(len(amsg_seq), len(msg_seq)):
            amsg_seq.append(padnone)

        # Add to items.
        for i in range(len(amsg_seq)):
            if i < len(msg_seq):
                nmod = 0
                i_eq = None
                for a in rhistory:
                    if not a.slen: # no modification in this ascription
                        continue
                    if i_eq is None:
                        msg_seq_p = get_as_sequence(a.msg, field)
                        if i < len(msg_seq_p) and msg_seq[i] == msg_seq_p[i]:
                            i_eq = nmod
                            # ...no break, need number of modifications.
                    nmod += 1
                if i_eq is None:
                    add = msg_seq[i] + shead
                else:
                    add = shead + _trsep_mod_eq + str(i_eq)
            else:
                add = shead + _trsep_mod_none
            if amsg_seq[i]:
                amsg_seq[i] += u"\n"
            amsg_seq[i] += add

        set_from_sequence(amsg_seq, amsg, field)


_atag_sep = u"/"
_mark_fuzz = u"f"
_mark_obs = u"o"

def ascribe_msg_any (msg, acat, atype, atags, arev, user, config,
                     dt=None):

    # Create or retrieve ascription message.
    if msg not in acat:
        # Copy ID elements of the original message.
        amsg = Message()
        for field in _id_fields:
            setattr(amsg, field, getattr(msg, field))
        # Append to the end of catalog.
        pos = acat.add(amsg, -1)
    else:
        # Retrieve existing ascription message.
        amsg = acat[msg]

    # Reconstruct historical messages, from first to last.
    rhistory = asc_collect_history_single(amsg, acat, config)
    rhistory.reverse()

    # Do any of non-ID elements differ to last historical message?
    if rhistory:
        hasdiff_state = state(rhistory[-1].msg) != state(msg)
        hasdiff_nonid = has_nonid_diff(rhistory[-1].msg, msg)
    else:
        hasdiff_nonid = True
        hasdiff_state = True
    hasdiff = hasdiff_nonid or hasdiff_state

    # Add ascription comment.
    modstr = user + " | " + format_datetime(dt)
    if arev or hasdiff:
        modstr += " | " + (arev or "")
    modstr_wsep = modstr
    if hasdiff:
        wsep = ""
        if hasdiff_nonid:
            seplen = needed_separator_length(msg)
            wsep += str(seplen)
        if is_any_obsolete(msg):
            wsep += _mark_obs
        if is_any_fuzzy(msg):
            wsep += _mark_fuzz
        if wsep:
            modstr_wsep += " | " + wsep
    first = True
    for atag in atags or [None]:
        field = atype
        if atag:
            field += _atag_sep + atag
        if first:
            asc_append_field(amsg, field, modstr_wsep)
            first = False
        else:
            asc_append_field(amsg, field, modstr)

    # Add non-ID fields.
    if hasdiff_nonid:
        add_nonid(amsg, msg, seplen, rhistory)

    # Update state.
    if is_any_fuzzy(msg):
        amsg.flag.add(u"fuzzy")
    else:
        amsg.flag.remove(u"fuzzy")
    if is_any_obsolete(msg):
        amsg.obsolete = True
    else:
        amsg.obsolete = False


_atype_mod = "modified"

def ascribe_msg_mod (msg, acat, catrev, user, config):

    ascribe_msg_any(msg, acat, _atype_mod, [], catrev, user, config)


_atype_rev = "reviewed"

def ascribe_msg_rev (msg, acat, tags, catrev, user, config):

    ascribe_msg_any(msg, acat, _atype_rev, tags, catrev, user, config)


def asc_eq (msg1, msg2):
    """
    Whether two messages are equal from the ascription viewpoint.
    """

    if state(msg1) != state(msg2):
        return False
    if is_any_fuzzy(msg1):
        check_fields = _nonid_fields_eq_fuzzy
    else:
        check_fields = _nonid_fields_eq_nonfuzzy
    for field in check_fields:
        if msg1.get(field) != msg2.get(field):
            return False
    return True


fld_sep = ":"

def asc_append_field (msg, field, value):

    stext = u"".join([field, fld_sep, " ", str(value)])
    msg.auto_comment.append(stext)


class _Ascription (object):

    def __setattr__ (self, attr, val):

        if attr not in ("rmsg", "msg", "user", "type", "tag", "date", "rev",
                        "slen", "fuzz", "obs"):
            raise KeyError, \
                  "trying to set invalid ascription field '%s'" % attr
        self.__dict__[attr] = val


def asc_collect_history (msg, acat, config):

    return asc_collect_history_w(msg, acat, config, None, {})


def asc_collect_history_w (msg, acat, config, before, seenmsg):

    history = []
    if not seenmsg:
        seenmsg = {}

    # Avoid circular paths.
    if msg.key in seenmsg:
        return history
    seenmsg[msg.key] = True

    # Collect history from all ascription catalogs.
    if msg in acat:
        amsg = acat[msg]
        for a in asc_collect_history_single(amsg, acat, config):
            if not before or asc_age_cmp(a, before, config) < 0:
                history.append(a)

    # Continue into the past by pivoting around first message if fuzzy.
    amsg = history and history[-1].msg or msg
    if is_any_fuzzy(amsg) and amsg.msgid_previous:
        pmsg = MessageUnsafe()
        for field in _id_fields:
            setattr(pmsg, field, amsg.get(field + "_previous"))
        # All ascriptions beyond the pivot must be older than the oldest so far.
        after = history and history[-1] or before
        ct_history = asc_collect_history_w(pmsg, acat, config, after, seenmsg)
        history.extend(ct_history)

    return history


def amsg_step_value (aval, shead, stail, spos, pvals, i):

    if i >= len(spos):
        spos.extend([0] * (i - len(spos) + 1))
    if i >= len(pvals):
        pvals.extend([[] for x in range(i - len(pvals) + 1)])
    p0 = spos[i]
    p1 = aval.find(shead, p0)
    p2 = aval.find(stail, p1 + 1)
    if p2 < 0:
        p2 = len(aval)
    spos[i] = p2 + len(stail)
    mods = aval[p1 + len(shead):p2]
    if _trsep_mod_eq in mods:
        q1 = mods.find(_trsep_mod_eq) + len(_trsep_mod_eq)
        q2 = q1
        while q2 < len(mods) and mods[q2].isdigit():
            q2 += 1
        nrev = int(mods[q1:q2])
        pval = pvals[i][nrev]
    else:
        if _trsep_mod_none in mods:
            pval = None
        else:
            pval = aval[p0:p1]
    pvals[i].append(pval)
    return pval


def asc_collect_history_single (amsg, acat, config):

    history = []
    spos = dict([(field, [0]) for field in _nonid_fields_tracked])
    pvals = dict([(field, [[]]) for field in _nonid_fields_tracked])
    for asc in asc_parse_ascriptions(amsg, acat, config):
        a = _Ascription()
        a.user, a.type, a.tag, a.date, a.rev, a.slen, a.fuzz, a.obs = asc
        if a.slen: # separator existing, reconstruct the fields
            shead = field_separator_head(a.slen)
            pmsg = MessageUnsafe()
            for field in _id_fields:
                setattr(pmsg, field, amsg.get(field))
            for field in _nonid_fields_tracked:
                amsg_seq = get_as_sequence(amsg, field)
                pmsg_seq = []
                for i in range(len(amsg_seq)):
                    aval = amsg_seq[i]
                    pval = amsg_step_value(aval, shead, u"\n",
                                           spos[field], pvals[field], i)
                    # ...do not break if None, has to roll all spos items
                    if pval is not None:
                        while i >= len(pmsg_seq):
                            pmsg_seq.append(u"")
                        pmsg_seq[i] = pval
                set_from_sequence(pmsg_seq, pmsg, field)
        else:
            pmsg = MessageUnsafe(history[-1].msg) # must exist
        if a.fuzz:
            pmsg.flag.add(u"fuzzy")
        elif u"fuzzy" in pmsg.flag:
            pmsg.flag.remove(u"fuzzy")
        pmsg.obsolete = a.obs
        a.rmsg, a.msg = amsg, pmsg
        history.append(a)

    #history.sort(lambda x, y: asc_age_cmp(y, x, config))
    # ...sorting not good, in case several operations were done at once,
    # e.g. ascribing modification and review at the same time.
    history.reverse()

    return history


def asc_parse_ascriptions (amsg, acat, config):
    """
    Get ascriptions from given ascription message as list of tuples
    C{(user, type, tag, date, revision, seplen, isfuzzy, isobsolete)},
    with date being a real C{datetime} object.
    """

    ascripts = []
    for cmnt in amsg.auto_comment:
        p = cmnt.find(":")
        if p < 0:
            warning_on_msg("malformed ascription comment '%s' "
                           "(no ascription type)" % cmnt, amsg, acat)
            continue
        atype = cmnt[:p].strip()
        atag = None
        lst = atype.split(_atag_sep, 1)
        if len(lst) == 2:
            atype = lst[0].strip()
            atag = lst[1].strip()
        lst = cmnt[p+1:].split("|")
        if len(lst) < 2 or len(lst) > 4:
            warning_on_msg("malformed ascription comment '%s' "
                           "(wrong number of descriptors)" % cmnt, amsg, acat)
            continue

        auser = lst.pop(0).strip()
        if not auser:
            warning_on_msg("malformed ascription comment '%s' "
                           "(malformed user string)" % cmnt, amsg, acat)
            continue
        if auser not in config.users:
            warning_on_msg("malformed ascription comment '%s' "
                           "(unknown user)" % cmnt, amsg, acat)
            continue

        datestr = lst.pop(0).strip()
        try:
            date = parse_datetime(datestr)
        except:
            warning_on_msg("malformed ascription comment '%s' "
                           "(malformed date string)" % cmnt, amsg, acat)
            continue

        revision = None
        if lst:
            revision = lst.pop(0).strip() or None

        seplen = 0
        isfuzz = False
        isobs = False
        if lst:
            tmp = lst.pop(0).strip()
            if _mark_fuzz in tmp:
                isfuzz = True
                tmp = tmp.replace(_mark_fuzz, "", 1)
            if _mark_obs in tmp:
                isobs = True
                tmp = tmp.replace(_mark_obs, "", 1)
            if tmp:
                try:
                    seplen = int(tmp)
                except:
                    warning_on_msg("malformed ascription comment '%s' "
                                   "(malformed separator length)"
                                   % cmnt, amsg, acat)
                    continue

        ascripts.append((auser, atype, atag, date, revision, seplen,
                         isfuzz, isobs))

    return ascripts


def asc_age_cmp (a1, a2, config):
    """
    Compare age of two ascriptions in history by their date/revision.

    See L{asc_collect_history} for the composition of C{hist*} arguments.
    Return value has the same semantics as with built-in C{cmp} function.
    """

    if a1.rev and a2.rev and a1.rev != a2.rev:
        if config.vcs.is_older(a1.rev, a2.rev):
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


def asc_sync_and_rep (acat):

    if acat.modcount:
        update_asc_hdr(acat)
        mkdirpath(os.path.dirname(acat.filename))

    return sync_and_rep(acat)


_dt_fmt = "%Y-%m-%d %H:%M:%S%z"
_dt_str_now = time.strftime(_dt_fmt)

def format_datetime (dt=None):

    fmt = "%Y-%m-%d %H:%M:%S%z"
    if dt is not None:
        dtstr = dt.strftime(_dt_fmt)
        # NOTE: If timezone offset is lost, the datetime object is UTC.
        tail = datestr[datestr.rfind(":"):]
        if "+" not in tail and "-" not in tail:
            dtstr += "+0000"
    else:
        return _dt_str_now


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
        sfactory, can_hist = xm_selector_factories.get(sname, (None, False))
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
        cache.matcher = build_msg_fmatcher(expr, filters=filters, mopts=mopts,
                                           abort=True)

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
                if not msg.ediff_from(amsg, pfilter=pfilter):
                    return True
        elif not is_any_untran(msg):
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
                if i_next is not None:
                    amsg2 = history[i_next].msg
                else:
                    amsg2 = MessageUnsafe(a.msg)
                    for field in _nonid_fields_tracked:
                        amsg2_value = amsg2.get(field)
                        if amsg2_value is None:
                            pass
                        elif isinstance(amsg2_value, basestring):
                            setattr(amsg2, field, None)
                        else:
                            amsg2_value = [u""] * len(amsg2_value)
                    i_next = len(history)
                amsg = MessageUnsafe(a.msg)
                pfilter = options.tfilter or config.tfilter
                amsg.embed_diff(amsg2, live=True,
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
                    if pf and not mm.ediff_from(mr, pfilter=pf):
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
                        and not a.msg.ediff_from(mm, pfilter=options.tfilter)
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


xm_selector_factories = {
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

_external_mods = {}

def collect_externals (xmod_path):

    # Load external module.
    try:
        xmod_file = open(xmod_path)
    except IOError:
        error("cannot load external module: %s" % xmod_path)
    # Load file into new module.
    xmod_name = "xmod_" + str(len(_external_mods))
    xmod = imp.new_module(xmod_name)
    exec xmod_file in xmod.__dict__
    xmod_file.close()
    _external_mods[xmod_name] = xmod # to avoid garbage collection

    # Collect everything collectable from the module.

    xms = []

    xms.append("xm_selector_factories")
    selector_factories = getattr(xmod, xms[-1], None)
    if selector_factories is not None:
        xm_selector_factories.update(selector_factories)

    # Warn of unknown externals.
    known_xms = set(xms)
    for xm in filter(lambda x: x.startswith("xm_"), dir(xmod)):
        if xm not in known_xms:
            warning("unknown external resource '%s' in module '%s'"
                    % (xm, xmod_path))


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    main()

