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

from pology.misc.fsops import str_to_unicode, unicode_to_str
from pology.misc.report import report, warning, error
from pology.misc.msgreport import warning_on_msg, report_msg_content
from pology.misc.fsops import collect_catalogs, mkdirpath, join_ncwd
from pology.misc.vcs import make_vcs
from pology.file.catalog import Catalog
from pology.file.message import Message, MessageUnsafe
from pology.misc.monitored import Monlist, Monset
from pology.misc.wrap import wrap_field_fine_unwrap
from pology.misc.tabulate import tabulate
from pology.misc.langdep import get_hook_lreq
from pology.sieve.find_messages import build_msg_fmatcher
from pology.misc.colors import colors_for_file
from pology.misc.diff import msg_diff, msg_ediff, msg_ediff_to_new
import pology.misc.config as pology_config
from pology.misc.tabulate import tabulate
import pology.misc.colors as C

WRAPF = wrap_field_fine_unwrap
UFUZZ = "fuzzy"


def main ():

    locale.setlocale(locale.LC_ALL, "")

    # Setup options and parse the command line.
    usage = (
        u"%prog [OPTIONS] [MODE] [PATHS...]")
    description = (
        u"Keep track of who, when, and how, has translated, modified, "
        u"or reviewed messages in a collection of PO files.")
    version = (
        u"%prog (Pology) experimental\n"
        u"Copyright © 2008 Chusslove Illich (Часлав Илић) "
        u"<caslav.ilic@gmx.net>\n")

    cfgsec = pology_config.section("poascribe")
    def_commit = cfgsec.boolean("commit", False)

    opars = OptionParser(usage=usage, description=description, version=version)
    opars.add_option(
        "--no-psyco",
        action="store_false", dest="use_psyco", default=True,
        help="do not try to use Psyco specializing compiler")
    opars.add_option(
        "-u", "--user", metavar="USER",
        action="store", dest="user", default=None,
        help="user in the focus of the operation "
             "(relevant in some modes)")
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
        "-c", "--commit",
        action="store_true", dest="commit", default=def_commit,
        help="automatically commit original and ascription catalogs, "
             "in proper order (relevant in some modes)")
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
    modename = free_args.pop(0)
    needuser = False
    canselect = False
    canaselect = False
    class _Mode: pass
    mode = _Mode()
    mode.name = modename
    if 0: pass
    elif mode.name in ("status", "st"):
        mode.execute = examine_state
        mode.selector = selector or build_selector(options, ["any"])
        canselect = True
    elif mode.name in ("modified", "mo"):
        mode.execute = ascribe_modified
        mode.selector = selector or build_selector(options, ["any"])
        canselect = True
        needuser = True
    elif mode.name in ("reviewed", "re"):
        mode.execute = ascribe_reviewed
        # Default selector for review ascription must match
        # default selector for review selection.
        mode.selector = selector or build_selector(options, ["nwasc"])
        canselect = True
        needuser = True
    elif mode.name in ("modreviewed", "mr"):
        mode.execute = ascribe_modreviewed
        mode.selector = selector
        canselect = True
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
        canselect = True
        canaselect = True
    elif mode.name in ("clear-review", "cr"):
        mode.execute = clear_review
        mode.selector = selector or build_selector(options, ["any"])
        canselect = True
    elif mode.name in ("history", "hi"):
        mode.execute = show_history
        mode.selector = selector or build_selector(options, ["nwasc"])
        canselect = True
    else:
        error("unknown operation mode '%s'" % mode.name)

    mode.user = None
    if needuser and not options.user and not cfgsec.string("user"):
        error("operation mode requires a user to be specified "
              "(either in command line or in Pology configuration)")
    mode.user = options.user or cfgsec.string("user")
    if not canselect and selector:
        error("operation mode does not accept selectors")
    if not canaselect and aselector:
        error("operation mode does not accept history selectors")

    # Collect the config which covers each path, and all catalogs inside it.
    configs_catpaths = collect_configs_catpaths(free_args or ["."])

    # Execute operation.
    mode.execute(options, configs_catpaths, mode)


# For each path:
# - determine its associated ascription config
# - collect all catalogs
# FIXME: Imported by others, factor out.
def collect_configs_catpaths (paths):

    paths = map(join_ncwd, paths)
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

    return configs_catpaths


def commit_catalogs (configs_catpaths, user, message=None, ascriptions=True):

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
            if config.vcs.is_versioned(catpath):
                catpaths_byconf[config].append(catpath)

    # Commit by config.
    for config in configs:
        cmsg = message
        cmsgfile = None
        if not cmsg:
            if ascriptions:
                cmsg = config.ascript_commit_message
            else:
                cmsg = config.commit_message
        if not cmsg:
            cmsgfile, cmsgfile_orig = get_commit_message_file_path(user)
        else:
            cmsg += " " + fmt_commit_user(user)
        if not config.vcs.commit(catpaths_byconf[config],
                                 message=cmsg, msgfile=cmsgfile):
            if not cmsgfile:
                error("VCS reports that catalogs cannot be committed")
            else:
                os.unlink(cmsgfile)
                error("VCS reports that catalogs cannot be committed "
                      "(commit message preserved in %s)" % cmsgfile_orig)
        if cmsgfile:
            os.unlink(cmsgfile)
            os.unlink(cmsgfile_orig)


def fmt_commit_user (user):

    return "[>%s]" % user


def get_commit_message_file_path (user):

    while True:
        tfmt = time.strftime("%Y-%m-%d-%H-%M-%S")
        prefix = "poascribe-commit-message"
        ext = "txt"
        fpath = "%s-%s.%s" % (prefix, tfmt, ext)
        fpath_asc = "%s-%s-asc.%s" % (prefix, tfmt, ext)
        if not os.path.isfile(fpath) and not os.path.isfile(fpath_asc):
            break

    edcmd = None
    if not edcmd:
        edcmd = os.getenv("ASC_EDITOR")
    if not edcmd:
        edcmd = pology_config.section("poascribe").string("editor")
    if not edcmd:
        edcmd = os.getenv("EDITOR")
    if not edcmd:
        edcmd = "/usr/bin/vi"

    cmd = "%s %s" % (edcmd, fpath)
    if os.system(cmd):
        error("error from editor command for commit message: %s" % cmd)
    if not os.path.isfile(fpath):
        error("editor command did not produce a file: %s" % cmd)

    cmsg = open(fpath, "r").read()
    if not cmsg.endswith("\n"):
        cmsg += "\n"
    fmt_user = unicode_to_str(fmt_commit_user(user))
    if cmsg.count("\n") == 1:
        cmsg = cmsg[:-1] + " " + fmt_user + "\n"
    else:
        cmsg += fmt_user + "\n"
    fh = open(fpath_asc, "w")
    fh.write(cmsg)
    fh.close()

    return fpath_asc, fpath


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

        cval = gsect.get("review-tags", None)
        if cval is not None:
            self.review_tags = set(cval.split())
        else:
            self.review_tags = set()

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


def assert_mode_user (configs_catpaths, mode, nousers=[]):

    if mode.user in nousers:
        error("user '%s' not allowed in mode '%s'" % (mode.user, mode.name))
    for config, catpaths in configs_catpaths:
        if mode.user not in config.users:
            error("user '%s' not defined in '%s'" % (mode.user, config.path))


def assert_review_tag (configs_catpaths, tag):

    if tag is not None:
        for config, catpaths in configs_catpaths:
            if tag not in config.review_tags:
                error("review tag '%s' not defined in '%s'"
                      % (tag, config.path))


def examine_state (options, configs_catpaths, mode):

    # Count ascribed and unascribed messages through catalogs.
    counts_a = dict([(x, {}) for x in _all_states])
    counts_na = dict([(x, {}) for x in _all_states])

    for config, catpaths in configs_catpaths:
        for catpath, acatpath in catpaths:
            # Open current and ascription catalog.
            cat = Catalog(catpath, monitored=False)
            acat = Catalog(acatpath, create=True, monitored=False)
            # Count non-ascribed by original catalog.
            for msg in cat:
                history = asc_collect_history(msg, acat, config)
                if history[0].user is None and msg.untranslated:
                    continue # pristine
                if mode.selector(msg, cat, history, config, options) is None:
                    continue # not selected
                counts = history[0].user is None and counts_na or counts_a
                st = msg.state()
                if catpath not in counts[st]:
                    counts[st][catpath] = 0
                counts[st][catpath] += 1
            # Count non-ascribed by ascription catalog.
            for amsg in acat:
                if amsg not in cat:
                    ast = amsg.state()
                    st = None
                    if ast == _st_tran:
                        st = _st_otran
                    elif ast == _st_fuzzy:
                        st = _st_ofuzzy
                    elif ast == _st_untran:
                        st = _st_ountran
                    if st:
                        if catpath not in counts_na[st]:
                            counts_na[st][catpath] = 0
                        counts_na[st][catpath] += 1

    # Some general data for tabulation of output.
    coln = ["msg/t", "msg/f", "msg/u", "msg/ot", "msg/of", "msg/ou"]
    can_color = sys.stdout.isatty()
    none="-"

    # Present totals of ascribed and unascribed messages.
    totals_a, totals_na = {}, {}
    for totals, counts in ((totals_a, counts_a), (totals_na, counts_na)):
        for st, cnt_per_cat in counts.items():
            totals[st] = sum(cnt_per_cat.values())
    rown = ["ascribed", "unascribed"]
    data = [[totals_a[x] or None, totals_na[x] or None] for x in _all_states]
    report(tabulate(data=data, coln=coln, rown=rown,
                    none=none, colorized=can_color))

    # Present totals of unascribed messages per catalog.
    totals_na_pc = {}
    for st, cnt_per_cat in counts_na.items():
        for catpath, nunasc in cnt_per_cat.items():
            if catpath not in totals_na_pc:
                totals_na_pc[catpath] = dict([(x, None) for x in _all_states])
            totals_na_pc[catpath][st] = nunasc
    if totals_na_pc:
        report(none)
        catpaths = totals_na_pc.keys()
        catpaths.sort()
        coln.insert(0, "unascribed-by-catalog")
        data = [[totals_na_pc[x][y] for x in catpaths] for y in _all_states]
        data.insert(0, catpaths)
        dfmt = ["%%-%ds" % max([len(x) for x in catpaths])]
        report(tabulate(data=data, coln=coln, dfmt=dfmt,
                        none=none, colorized=can_color))


def ascribe_modified (options, configs_catpaths, mode):

    assert_mode_user(configs_catpaths, mode)

    if options.commit:
        commit_catalogs(configs_catpaths, mode.user,
                        options.message, False)

    ascribe_modified_w(options, configs_catpaths, mode)

    if options.commit:
        commit_catalogs(configs_catpaths, mode.user,
                        options.ascript_message, True)


def ascribe_modified_w (options, configs_catpaths, mode):

    counts = dict([(x, 0) for x in _all_states])
    for config, catpaths in configs_catpaths:
        for catpath, acatpath in catpaths:
            ccounts = ascribe_modified_cat(options, config, mode.user,
                                           catpath, acatpath, mode.selector)
            for st, val in ccounts.items():
                counts[st] += val

    if counts[_st_tran] > 0:
        report("===! Translated: %d" % counts[_st_tran])
    if counts[_st_fuzzy] > 0:
        report("===! Fuzzy: %d" % counts[_st_fuzzy])
    if counts[_st_untran] > 0:
        report("===! Untranslated: %d" % counts[_st_untran])
    if counts[_st_otran] > 0:
        report("===! Obsolete translated: %d" % counts[_st_otran])
    if counts[_st_ofuzzy] > 0:
        report("===! Obsolete fuzzy: %d" % counts[_st_ofuzzy])
    if counts[_st_ountran] > 0:
        report("===! Obsolete untranslated: %d" % counts[_st_ountran])


def ascribe_reviewed (options, configs_catpaths, mode):

    assert_mode_user(configs_catpaths, mode, nousers=[UFUZZ])
    assert_review_tag(configs_catpaths, options.tag)

    ascribe_reviewed_w(options, configs_catpaths, mode)

    if options.commit:
        commit_catalogs(configs_catpaths, mode.user,
                        options.ascript_message, True)


def ascribe_reviewed_w (options, configs_catpaths, mode):

    nasc = 0
    for config, catpaths in configs_catpaths:
        for catpath, acatpath in catpaths:
            nasc += ascribe_reviewed_cat(options, config, mode.user,
                                         catpath, acatpath, mode.selector)

    if nasc > 0:
        report("===! Reviewed: %d" % nasc)


def ascribe_modreviewed (options, configs_catpaths, mode):

    assert_mode_user(configs_catpaths, mode, nousers=[UFUZZ])
    assert_review_tag(configs_catpaths, options.tag)

    # Remove any review diffs.
    # If any were actually removed, ascribe reviews only on them,
    # providing they also pass the selector.
    # If there were no diffs removed, ascribe reviews for all messages
    # that pass the selector.
    # In both cases, ascribe modifications to all modified messages.

    stest_orig = mode.selector
    stest_any = build_selector(options, ["any"])

    mode.selector = stest_any
    cleared_by_cat = clear_review_w(options, configs_catpaths, mode)
    ncleared = sum(map(len, cleared_by_cat.values()))

    if options.commit:
        commit_catalogs(configs_catpaths, mode.user,
                        options.message, False)

    mode.selector = stest_any
    ascribe_modified_w(options, configs_catpaths, mode)

    if ncleared > 0:
        def stest (msg, cat, hist, conf, opts):
            if msg.refentry not in cleared_by_cat[cat.filename]:
                return None
            if stest_orig and stest_orig(msg, cat, hist, conf, opts) is None:
                return None
            return True
        mode.selector = stest
    else:
        mode.selector = stest_orig or stest_any
    ascribe_reviewed_w(options, configs_catpaths, mode)

    if options.commit:
        commit_catalogs(configs_catpaths, mode.user,
                        options.ascript_message, True)


def diff_select (options, configs_catpaths, mode):

    ndiffed = 0
    for config, catpaths in configs_catpaths:
        for catpath, acatpath in catpaths:
            pfilter = options.tfilter or config.tfilter
            ndiffed += diff_select_cat(options, config, catpath, acatpath,
                                       mode.selector, mode.aselector, pfilter)

    if ndiffed > 0:
        report("===! Diffed from history: %d" % ndiffed)


def clear_review (options, configs_catpaths, mode):

    clear_review_w(options, configs_catpaths, mode)


def clear_review_w (options, configs_catpaths, mode):

    cleared_by_cat = {}
    for config, catpaths in configs_catpaths:
        for catpath, acatpath in catpaths:
            cleared = clear_review_cat(options, config, catpath, acatpath,
                                       mode.selector)
            cleared_by_cat[catpath] = cleared

    ncleared = sum(map(len, cleared_by_cat.values()))
    if ncleared > 0:
        report("===! Cleared review states: %d" % ncleared)

    return cleared_by_cat


def show_history (options, configs_catpaths, mode):

    nshown = 0
    for config, catpaths in configs_catpaths:
        for catpath, acatpath in catpaths:
            nshown += show_history_cat(options, config, catpath, acatpath,
                                       mode.selector)

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
        if history[0].user is None and msg.untranslated:
            continue # pristine
        if stest(msg, cat, history, config, options) is None:
            continue # not selected
        if history[0].user is None:
            toasc_msgs.append(msg)
            counts[msg.state()] += 1

    # Collect non-obsolete ascribed messages that no longer have
    # original counterpart, to ascribe as obsolete.
    for amsg in acat:
        if amsg not in cat:
            ast = amsg.state()
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


def ascribe_reviewed_cat (options, config, user, catpath, acatpath, stest):

    # Open current catalog and ascription catalog.
    # Monitored, for removal of reviewed-* flags.
    cat = Catalog(catpath, monitored=True, wrapf=WRAPF)
    acat = prep_write_asc_cat(acatpath, config)

    rev_msgs_tags = []
    non_mod_asc_msgs = []
    for msg in cat:
        # Remove any review scaffolding, collecting any review-done tags.
        tags = clear_review_msg(msg)
        if not tags and options.tag:
            tags.append(options.tag)

        history = asc_collect_history(msg, acat, config)
        # Makes no sense to ascribe review to pristine messages.
        if history[0].user is None and msg.untranslated:
            continue
        if stest(msg, cat, history, config, options) is None:
            continue
        # Message cannot be ascribed as reviewed if it has not been
        # already ascribed as modified.
        if history[0].user is None:
            # Collect to report later.
            non_mod_asc_msgs.append(msg)
            continue

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


# Flag used to mark diffed messages.
_diffflag = u"ediff"
_diffflag_tot = u"ediff-total"
_diffflags = (_diffflag, _diffflag_tot)

def diff_select_cat (options, config, catpath, acatpath,
                     stest, aselect, pfilter):

    cat = Catalog(catpath, monitored=True, wrapf=WRAPF)
    acat = Catalog(acatpath, create=True, monitored=False)

    nflagged = 0
    for msg in cat:
        history = asc_collect_history(msg, acat, config)
        # Makes no sense to review pristine messages.
        if history[0].user is None and msg.untranslated:
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
        amsg = i_asc is not None and history[i_asc].msg or None
        if amsg is not None:
            msg_ediff(amsg, msg, emsg=msg, pfilter=pfilter)
            # NOTE: Do NOT think of avoiding to flag the message if there is
            # no difference to history, must be symmetric to review ascription.
            msg.flag.add(_diffflag)
        else:
            # If no previous ascription selected, add special flag
            # to denote that the whole message is to be reviewed.
            msg.flag.add(_diffflag_tot)
        nflagged += 1

    sync_and_rep(cat)

    return nflagged


def clear_review_cat (options, config, catpath, acatpath, stest):

    cat = Catalog(catpath, monitored=True, wrapf=WRAPF)
    acat = Catalog(acatpath, create=True, monitored=False)

    cleared = []
    for msg in cat:
        history = asc_collect_history(msg, acat, config)
        if stest(msg, cat, history, config, options) is None:
            continue
        clear_review_msg(msg)
        if msg.modcount > 0:
            cleared.append(msg.refentry)

    sync_and_rep(cat)

    return cleared


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
            if history[0].user is None:
                hlevels += 1
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
            elif a.user:
                anote = "%(mod)s by %(usr)s on %(dat)s" % anote_d
            else:
                anote = "not ascribed yet"
            hinfo += [ihead + anote]
            if not a.type == ATYPE_MOD or a.msg.fuzzy:
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
            if dmsg != nmsg:
                msg_ediff(nmsg, dmsg, emsg=dmsg,
                          pfilter=pfilter, hlto=sys.stdout)
                dmsgfmt = dmsg.to_string(force=True, wrapf=WRAPF).rstrip("\n")
                hindent = " " * (len(hfmt % 0) + 2)
                hinfo += [hindent + x for x in dmsgfmt.split("\n")]
        hinfo = "\n".join(hinfo)

        i_nfasc = first_nfuzzy(history)
        if i_nfasc is not None:
            msg = Message(msg)
            nmsg = history[i_nfasc].msg
            msg_ediff(nmsg, msg, emsg=msg,
                      pfilter=pfilter, hlto=sys.stdout)
        report_msg_content(msg, cat, wrapf=WRAPF,
                           note=(hinfo or None), delim=("-" * 20))

    return nselected


_revdflags = ("revd", "reviewed")
_revdflag_rx = re.compile(r"^(?:%s) *[/:]?(.*)" % "|".join(_revdflags), re.I)

def clear_review_msg (msg):

    # Clear possible review flags, collect all remove-done tags.
    diffed = False
    tags = []
    for flag in list(msg.flag): # modified inside
        mantagged = _revdflag_rx.search(flag)
        if flag in _diffflags or mantagged:
            if flag in _diffflags:
                diffed = True
            if mantagged:
                tags.append(mantagged.group(1).strip() or None)
            msg.flag.remove(flag)
            # Do not break, other review flags possible.

    # Clear embedded diffs.
    if diffed:
        msg_ediff_to_new(msg, rmsg=msg)

    return tags


# Exclusive states of a message, as reported by Message.state().
# FIXME: These keywords better exported to pology.file.message
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


def first_nfuzzy (history, start=0):

    for i in range(start, len(history)):
        hmsg = history[i].msg
        if hmsg and not hmsg.fuzzy:
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
_fields_current = (
    "msgctxt", "msgid", "msgid_plural",
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
        if not msg.fuzzy and field in _fields_previous:
            # Ignore previous values in messages with no fuzzy flag.
            msg_value = None
        pmsg_value = pmsg.get(field)
        if msg_value != pmsg_value:
            return True

    return False


def get_as_sequence (msg, field, asc=True):

    if not asc and not msg.fuzzy and field in _fields_previous:
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
        acat.add_last(amsg)
    else:
        # Retrieve existing ascription message.
        amsg = acat[msg]

    # Reconstruct historical messages, from first to last.
    rhistory = asc_collect_history_single(amsg, acat, config)
    rhistory.reverse()

    # Do any of non-ID elements differ to last historical message?
    if rhistory:
        hasdiff_state = rhistory[-1].msg.state() != msg.state()
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
        if msg.obsolete:
            wsep += _mark_obs
        if msg.fuzzy:
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
    if msg.fuzzy:
        amsg.flag.add(u"fuzzy")
    else:
        amsg.flag.remove(u"fuzzy")
    if msg.obsolete:
        amsg.obsolete = True
    else:
        amsg.obsolete = False


# FIXME: Imported by others, factor out.
# NOTE: These string are written and read from ascription files.
ATYPE_MOD = "modified"
ATYPE_REV = "reviewed"


def ascribe_msg_mod (msg, acat, catrev, user, config):

    ascribe_msg_any(msg, acat, ATYPE_MOD, [], catrev, user, config)


def ascribe_msg_rev (msg, acat, tags, catrev, user, config):

    ascribe_msg_any(msg, acat, ATYPE_REV, tags, catrev, user, config)


# FIXME: Imported by others, factor out.
def asc_eq (msg1, msg2):
    """
    Whether two messages are equal from the ascription viewpoint.
    """

    if msg1.state() != msg2.state():
        return False
    if msg1.fuzzy:
        check_fields = _nonid_fields_eq_fuzzy
    else:
        check_fields = _nonid_fields_eq_nonfuzzy
    for field in check_fields:
        if msg1.get(field) != msg2.get(field):
            return False
    return True


def flt_eq (msg1, msg2, pfilter):
    """
    Whether two messages are equal under translation filter.
    """

    return msg_diff(msg1, msg2, pfilter=pfilter, diffr=True)[1] > 0.0


def merge_modified (msg1, msg2):
    """
    Whether second message may be considered derived from first by merging.
    """

    # Manual comments do not change on merge.
    if msg1.manual_comment != msg2.manual_comment:
        return False

    # Current and previous original fields may have changed on merge,
    # depending on whether both messages are fuzzy, or only one, and which.
    if msg1.fuzzy == msg2.fuzzy:
        fields = msg1.fuzzy and _fields_previous or _fields_current
        for field in fields:
            if msg1.get(field) != msg2.get(field):
                return False
    else:
        fields = (msg1.fuzzy and zip(_fields_previous, _fields_current)
                              or zip(_fields_current, _fields_previous))
        for field1, field2 in fields:
            if msg1.get(field1) != msg2.get(field2):
                return False

    # Translation does not change on merge,
    # except for multiplication/reduction when plurality differs.
    if (msg1.msgid_plural is None) == (msg2.msgid_plural is None):
        if msg1.msgstr != msg2.msgstr:
            return False
    else:
        if not msg1.fuzzy and not msg2.fuzzy:
            # Plurality cannot change between two non-fuzzy messages.
            return False
        if msg1.msgid_plural is not None:
            # Reduction to non-plural.
            if msg1.msgstr[0] != msg2.msgstr[0]:
                return False
        else:
            # Multiplication to plural.
            for msgstr in msg2.msgstr:
                if msgstr != msg1.msgstr[0]:
                    return False

    return True


fld_sep = ":"

def asc_append_field (msg, field, value):

    stext = u"".join([field, fld_sep, " ", str(value)])
    msg.auto_comment.append(stext)


_asc_attrs = (
    "rmsg", "msg",
    "user", "type", "tag", "date", "rev",
    "slen", "fuzz", "obs",
)

class _Ascription (object):

    def __init__ (self):

        for attr in _asc_attrs:
            self.__dict__[attr] = None

    def __setattr__ (self, attr, val):

        if attr not in self.__dict__:
            raise KeyError, "trying to set unknown ascription field '%s'" % attr
        self.__dict__[attr] = val


def asc_collect_history (msg, acat, config, nomrg=False):

    history = asc_collect_history_w(msg, acat, config, None, set())

    # If the message is not ascribed,
    # add it in front as modified by unknown user.
    if not history or not asc_eq(msg, history[0].msg):
        a = _Ascription()
        a.type = ATYPE_MOD
        a.user = None
        a.msg = msg
        history.insert(0, a)

    # Eliminate clean merges from history.
    if nomrg:
        history_r = []
        for i in range(len(history) - 1):
            a, ao = history[i], history[i + 1]
            if not a.user == UFUZZ or not merge_modified(ao.msg, a.msg):
                history_r.append(a)
        history_r.append(history[-1])
        history = history_r

    return history


def asc_collect_history_w (msg, acat, config, before, seenmsg):

    history = []

    # Avoid circular paths.
    if msg.key in seenmsg:
        return history
    seenmsg.add(msg.key)

    # Collect history from all ascription catalogs.
    if msg in acat:
        amsg = acat[msg]
        for a in asc_collect_history_single(amsg, acat, config):
            if not before or asc_age_cmp(a, before, config) < 0:
                history.append(a)

    # Continue into the past by pivoting around earliest message if fuzzy.
    amsg = history and history[-1].msg or msg
    if amsg.fuzzy and amsg.msgid_previous:
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
_dt_fmt_nosec = "%Y-%m-%d %H:%M%z"
_dt_str_now = time.strftime(_dt_fmt)
_dt_str_now_nosec = time.strftime(_dt_fmt_nosec)

def format_datetime (dt=None, wsec=True):

    if dt is not None:
        if wsec:
            dtstr = dt.strftime(_dt_fmt)
        else:
            dtstr = dt.strftime(_dt_fmt_nosec)
        # NOTE: If timezone offset is lost, the datetime object is UTC.
        tail = datestr[datestr.rfind(":"):]
        if "+" not in tail and "-" not in tail:
            dtstr += "+0000"
    else:
        if wsec:
            dtstr = _dt_str_now
        else:
            dtstr = _dt_str_now_nosec

    return unicode(dtstr)


_parse_date_rxs = [re.compile(x) for x in (
    r"^ *(\d+)-(\d+)-(\d+) *(\d+):(\d+):(\d+) *([+-]\d+) *$",
    r"^ *(\d+)-(\d+)-(\d+) *(\d+):(\d+)() *([+-]\d+) *$",
    # ...needs empty group to differentiate from the next case.
    r"^ *(\d+)-(\d+)-(\d+) *(\d+):(\d+):(\d+) *$",
    r"^ *(\d+)-(\d+)-(\d+) *(\d+):(\d+) *$",
    r"^ *(\d+)-(\d+)-(\d+) *$",
    r"^ *(\d+)-(\d+) *$",
    r"^ *(\d+) *$",
)]

# FIXME: Imported by posummit.py, move out of here.
def parse_datetime (dstr):
    # NOTE: Timezone offset is lost, the datetime object becomes UTC.
    # NOTE: Can we use dateutil module in here?

    for parse_date_rx in _parse_date_rxs:
        m = parse_date_rx.search(dstr)
        if m:
            break
    if not m:
        raise StandardError, "cannot parse date string '%s'" % dstr
    pgroups = list([int(x or 0) for x in m.groups()])
    pgroups.extend([1] * (3 - len(pgroups)))
    pgroups.extend([0] * (7 - len(pgroups)))
    year, month, day, hour, minute, second, off = pgroups
    dt0 = datetime.datetime(year=year, month=month, day=day,
                            hour=hour, minute=minute, second=second)
    offmin = (off // 100) * 60 + (abs(off) % 100)
    tzd = datetime.timedelta(minutes=offmin)
    dt = dt0 - tzd
    return dt


def parse_users (userstr, config, cid=None):
    """
    Parse users from comma-separated list, verifying that they exist.

    If the list starts with tilde (~), all users found in the config
    but for the listed will be selected (inverted selection).

    C{cid} is the string identifying the caller, for error report in
    case the a parsed user does not exist.
    """

    if not userstr:
        return set()

    userstr = userstr.replace(" ", "")
    inverted = False
    if userstr.startswith("~"):
        inverted = True
        userstr = userstr[1:]

    users = set(userstr.split(","))
    for user in users:
        if user not in config.users:
            error("user '%s' not defined in '%s'" % (user, config.path),
                  subsrc=cid)
    if inverted:
        users = set(config.users).difference(users)

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


def selector_active ():
    cid = "selector:active"

    def selector (msg, cat, history, config, options):

        return (msg.translated and not msg.obsolete) or None

    return selector


def selector_wasc ():
    cid = "selector:wasc"

    def selector (msg, cat, history, config, options):

        pfilter = options.tfilter or config.tfilter

        if history[0].user is not None:
            return True
        elif msg.untranslated:
            # Also consider pristine messages ascribed.
            return True
        elif pfilter and len(history) > 1:
            # Also consider ascribed if equal to last ascription
            # under the filter in effect.
            if flt_eq(msg, history[1].msg, pfilter):
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
        error("message reference by entry must be a positive integer",
              subsrc=cid)
    refentry = int(entry)

    def selector (msg, cat, history, config, options):

        if msg.refentry == refentry:
            return True

        return None

    return selector


def selector_l (line=None):
    cid = "selector:l"

    if not line or not line.isdigit():
        error("message reference by line must be a positive integer",
              subsrc=cid)
    refline = int(line)

    def selector (msg, cat, history, config, options):

        if abs(msg.refline - refline) <= 1:
            return True

        return None

    return selector


# Select messages between and including first and last reference by entry.
# If first entry is not given, all messages to the last entry are selected.
# If last entry is not given, all messages from the first entry are selected.
def selector_espan (first=None, last=None):
    cid = "selector:espan"

    if not first and not last:
        error("at least one of the first and last reference by entry "
              "must be given", subsrc=cid)
    if first and not first.isdigit():
        error("first message reference by entry must be a positive integer",
              subsrc=cid)
    if last and not last.isdigit():
        error("last message reference by entry must be a positive integer",
              subsrc=cid)
    first_entry = (first and [int(first)] or [None])[0]
    last_entry = (last and [int(last)] or [None])[0]

    def selector (msg, cat, history, config, options):

        if first_entry is not None and msg.refentry < first_entry:
            return None
        if last_entry is not None and msg.refentry > last_entry:
            return None
        return True

    return selector


# Select messages between and including first and last reference by line.
# If first line is not given, all messages to the last line are selected.
# If last line is not given, all messages from the first line are selected.
def selector_lspan (first=None, last=None):
    cid = "selector:lspan"

    if not first and not last:
        error("at least one of the first and last reference by line "
              "must be given", subsrc=cid)
    if first and not first.isdigit():
        error("first message reference by line must be a positive integer",
              subsrc=cid)
    if last and not last.isdigit():
        error("last message reference by line must be a positive integer",
              subsrc=cid)
    first_line = (first and [int(first)] or [None])[0]
    last_line = (last and [int(last)] or [None])[0]

    def selector (msg, cat, history, config, options):

        if first_line is not None and msg.refline < first_line:
            return None
        if last_line is not None and msg.refline > last_line:
            return None
        return True

    return selector


def selector_hexpr (expr=None, user_spec=None, addrem=None):
    cid = "selector:hexpr"

    if not (expr or "").strip():
        error("matching expression cannot be empty", subsrc=cid)

    cache = _Cache()

    def selector (msg, cat, history, config, options):

        if history[0].user is None:
            return None

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
                msg_ediff(amsg2, amsg, emsg=amsg,
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

        if history[0].user is None:
            return None

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

        if history[0].user is None:
            return None

        users = cached_users(cache, user_spec, config, cid)

        i_sel = None
        for i in range(len(history)):
            a = history[i]
            if not a.user:
                continue
            if a.type == ATYPE_MOD and (not users or a.user in users):
                i_sel = i
                break

        return i_sel

    return selector


# Select first modification (any or by m-users, and not by r-users)
# after last review (any or by r-users, and not by m-users).
def selector_modar (muser_spec=None, ruser_spec=None, atag_req=None):
    cid = "selector:modar"

    return w_selector_modax(cid, False, True,
                            muser_spec, ruser_spec, atag_req)


# Select first modification (any or by m-users, and not by mm-users)
# after last modification (any or by mm-users, and not by m-users).
def selector_modam (muser_spec=None, mmuser_spec=None):
    cid = "selector:modam"

    return w_selector_modax(cid, True, False,
                            muser_spec, mmuser_spec, None)


# Select first modification (any or by m-users, and not by rm-users)
# after last review or modification (any or by m-users, and not by rm-users).
def selector_modarm (muser_spec=None, rmuser_spec=None, atag_req=None):
    cid = "selector:modarm"

    return w_selector_modax(cid, True, True,
                            muser_spec, rmuser_spec, atag_req)


# Worker for builders of moda* selectors.
def w_selector_modax (cid, amod, arev,
                      muser_spec=None, rmuser_spec=None, atag_req=None):

    cache = _Cache()

    def selector (msg, cat, history, config, options):

        if history[0].user is None:
            return None

        musers = cached_users(cache, muser_spec, config, cid, utype="m")
        rmusers = cached_users(cache, rmuser_spec, config, cid, utype="rm")

        i_sel = None
        i_cand = None
        for i in range(len(history)):
            a = history[i]
            # Check if this message cancels candidate.
            if (    (   (amod and a.type == ATYPE_MOD)
                     or (arev and a.type == ATYPE_REV and a.tag == atag_req))
                and (not rmusers or a.user in rmusers)
                and (not musers or a.user not in musers)
            ):
                if i_cand is None:
                    # Cancelling message found before candidate,
                    # no match possible.
                    break
                else:
                    # Candidate is good unless:
                    # - either message is by fuzzy user and
                    #   only original texts have changed in between, or
                    # - filter is in effect and candidate is equal
                    #   to current message under the filter.
                    mm, mrm = history[i_cand].msg, a.msg
                    good = True
                    if history[i_cand].user == UFUZZ or a.user == UFUZZ:
                        if merge_modified(mrm, mm):
                            good = False
                    else:
                        pfilter = options.tfilter or config.tfilter
                        if pfilter and flt_eq(mrm, mm, pfilter):
                            good = False
                    # If not good, look for next candidate, else match found.
                    if not good:
                        i_cand = None
                    else:
                        i_sel = i_cand
                        break
            # Check if this message can be a candidate.
            if (    a.type == ATYPE_MOD
                and (not musers or a.user in musers)
                and (not rmusers or a.user not in rmusers)
            ):
                # Cannot be candidate if made by fuzzy user and
                # there are no differences to earlier message by
                # fields normally in translator's domain.
                good = True
                if a.user == UFUZZ and i + 1 < len(history):
                    if merge_modified(history[i + 1].msg, a.msg):
                        good = False
                # Compliant modification found, make it candidate.
                if good:
                    i_cand = i

        if i_cand is not None:
            # There was no cancelling message after candidate modification,
            # so use it, unless filter is in effect and candidate
            # is equal under it to the first earlier modification
            # (any, or not by m-users).
            pfilter = options.tfilter or config.tfilter
            if pfilter and i_cand + 1 < len(history):
                mm = history[i_cand].msg
                for a in history[i_cand + 1:]:
                    if (    a.type == ATYPE_MOD
                        and (not musers or a.user not in musers)
                        and flt_eq(mm, a.msg, pfilter)
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

        if history[0].user is None:
            return None

        users = cached_users(cache, user_spec, config, cid)

        i_sel = None
        for i in range(len(history)):
            a = history[i]
            if (    a.type == ATYPE_REV and a.tag == atag_req
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

        if history[0].user is None:
            return None

        rusers = cached_users(cache, ruser_spec, config, cid, utype="r")
        musers = cached_users(cache, muser_spec, config, cid, utype="m")

        # TODO: Make it filter-sensitive like :modar.

        i_sel = None
        can_select = False
        for i in range(len(history)):
            a = history[i]
            if (     a.type == ATYPE_MOD
                and (not musers or a.user in musers)
                and (not rusers or a.user not in rusers)
            ):
                # Modification found, enable selection of review.
                can_select = True
            if (    a.type == ATYPE_REV and a.tag == atag_req
                and (not rusers or a.user in rusers)
                and (not musers or a.user not in musers)
            ):
                # Review found, select it if enabled, and stop anyway.
                if can_select:
                    i_sel = i
                break

        return i_sel

    return selector


# Select first modification (any or by users) at or after given time/revision.
def selector_modafter (time_spec=None, user_spec=None):
    cid = "selector:modafter"

    cache = _Cache()

    if not time_spec:
        error("time/revision specification cannot be empty", subsrc=cid)

    if "-" in time_spec:
        date = parse_datetime(time_spec)
        rev = None
    else:
        date = None
        rev = time_spec.strip()

    def selector (msg, cat, history, config, options):

        if history[0].user is None:
            return None

        users = cached_users(cache, user_spec, config, cid)

        i_sel = None
        for i in range(len(history) - 1, -1, -1):
            a = history[i]
            if (    a.type == ATYPE_MOD and (not users or a.user in users)
                and (not date or a.date >= date)
                and (not rev or not config.vcs.is_older(a.rev, rev))
            ):
                i_sel = i
                break

        return i_sel

    return selector


xm_selector_factories = {
    # key: (function, can_be_used_as_history_selector)
    "any": (selector_any, False),
    "active": (selector_active, False),
    "wasc": (selector_wasc, False),
    "xrevd": (selector_xrevd, False),
    "fexpr": (selector_fexpr, False),
    "e": (selector_e, False),
    "l": (selector_l, False),
    "espan": (selector_espan, False),
    "lspan": (selector_lspan, False),
    "hexpr": (selector_hexpr, True),
    "asc": (selector_asc, True),
    "mod": (selector_mod, True),
    "modar": (selector_modar, True),
    "modam": (selector_modam, True),
    "modarm": (selector_modarm, True),
    "rev": (selector_rev, True),
    "revbm": (selector_revbm, True),
    "modafter": (selector_modafter, True),
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

