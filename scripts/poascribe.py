#!/usr/bin/env python
# -*- coding: UTF-8 -*-

try:
    import fallback_import_paths
except:
    pass

import datetime
import locale
import os
import re
import sys
from tempfile import NamedTemporaryFile
import time

from pology import PologyError, version, _, n_, t_
from pology.ascript import collect_ascription_associations
from pology.ascript import collect_ascription_history
from pology.ascript import collect_ascription_history_segment
from pology.ascript import ascription_equal, merge_modified
from pology.ascript import ascribe_modification, ascribe_review
from pology.ascript import first_non_fuzzy, has_tracked_parts
from pology.ascript import make_ascription_selector
from pology.ascript import AscPoint
from pology.catalog import Catalog
from pology.header import Header, TZInfo, format_datetime
from pology.message import Message, MessageUnsafe
from pology.gtxtools import msgfmt
from pology.colors import ColorOptionParser, cjoin
import pology.config as pology_config
from pology.diff import msg_ediff, msg_ediff_to_new
from pology.diff import editprob
from pology.fsops import str_to_unicode, unicode_to_str
from pology.fsops import collect_paths_cmdline, collect_catalogs
from pology.fsops import mkdirpath, join_ncwd
from pology.fsops import exit_on_exception
from pology.getfunc import get_hook_ireq
from pology.merge import merge_pofile
from pology.monitored import Monlist
from pology.msgreport import warning_on_msg, report_msg_content
from pology.msgreport import report_msg_to_lokalize
from pology.report import report, error, format_item_list
from pology.report import init_file_progress
from pology.stdcmdopt import add_cmdopt_incexc, add_cmdopt_filesfrom
from pology.tabulate import tabulate


# Wrapping in ascription catalogs.
_ascwrapping = ["fine"]

# Flag used to mark diffed messages.
# NOTE: All diff flags should start with 'ediff', as some other scripts
# only need to check if any of them is present.
_diffflag = u"ediff"
_diffflag_tot = u"ediff-total"
_diffflag_ign = u"ediff-ignored"

# Flags used to explicitly mark messages as reviewed or unreviewed.
_revdflags = (u"reviewed", u"revd", u"rev") # synonyms
_urevdflags = (u"unreviewed", u"nrevd", u"nrev") # synonyms

# Comment used to show ascription chain in messages marked for review.
_achncmnt = "~ascto:"

# String used to separate tags to review flags.
_flagtagsep = "/"

_diffflags = (_diffflag, _diffflag_tot, _diffflag_ign)
_all_flags = _diffflags + _revdflags + _urevdflags
_all_flags = sorted(_all_flags, key=lambda x: (-len(x), x))
# ...this order is necessary for proper |-linking in regexes.
_all_cmnts = (_achncmnt,)

# Datetime at the moment the script is started.
_dt_start = datetime.datetime(*(time.localtime()[:6] + (0, TZInfo())))


def main ():

    locale.setlocale(locale.LC_ALL, "")

    mode_spec = (
        ("status", ("st",)),
        ("commit", ("co", "ci", "mo")),
        ("diff", ("di",)),
        ("purge", ("pu",)),
        ("history", ("hi",)),
    )
    mode_allnames = set()
    mode_tolong = {}
    for name, syns in mode_spec:
        mode_allnames.add(name)
        mode_allnames.update(syns)
        mode_tolong[name] = name
        mode_tolong.update((s, name) for s in syns)

    known_editors = {
        "lokalize": report_msg_to_lokalize,
    }

    # Setup options and parse the command line.
    usage = _("@info command usage",
        "%(cmd)s MODE [OPTIONS] [PATHS...]",
        cmd="%prog")
    desc = _("@info command description",
        "Keep track of who, when, and how, has translated, modified, "
        "or reviewed messages in a collection of PO files.")
    ver = _("@info command version",
        u"%(cmd)s (Pology) %(version)s\n"
        u"Copyright © 2008, 2009, 2010 "
        u"Chusslove Illich (Часлав Илић) &lt;%(email)s&gt;",
        cmd="%prog", version=version(), email="caslav.ilic@gmx.net")

    opars = ColorOptionParser(usage=usage, description=desc, version=ver)
    opars.add_option(
        "-a", "--select-ascription",
        metavar=_("@info command line value placeholder", "SELECTOR[:ARGS]"),
        action="append", dest="aselectors", default=None,
        help=_("@info command line option description",
               "Select a message from ascription history by this selector. "
               "Can be repeated, in which case the message is selected "
               "if all selectors match it."))
    opars.add_option(
        "-A", "--min-adjsim-diff",
        metavar=_("@info command line value placeholder", "RATIO"),
        action="store", dest="min_adjsim_diff", default=None,
        help=_("@info command line option description",
               "Minimum adjusted similarity between two versions of a message "
               "needed to show the embedded difference. "
               "Range 0.0-1.0, where 0 means always to show the difference, "
               "and 1 never to show it; a convenient range is 0.6-0.8. "
               "When the difference is not shown, the '%(flag)s' flag is "
               "added to the message.",
               flag=_diffflag_ign))
    opars.add_option(
        "-b", "--show-by-file",
        action="store_true", dest="show_by_file", default=False,
        help=_("@info command line option description",
               "Next to global summary, also present results by file."))
    opars.add_option(
        "-C", "--no-vcs-commit",
        action="store_false", dest="vcs_commit", default=None,
        help=_("@info command line option description",
               "Do not commit catalogs to version control "
               "(when version control is used)."))
    opars.add_option(
        "-d", "--depth",
        metavar=_("@info command line value placeholder", "LEVEL"),
        action="store", dest="depth", default=None,
        help=_("@info command line option description",
               "Consider ascription history up to this level into the past."))
    opars.add_option(
        "-D", "--diff-reduce-history",
        metavar=_("@info command line value placeholder", "SPEC"),
        action="store", dest="diff_reduce_history", default=None,
        help=_("@info command line option description",
               "Reduce each message in history to a part of the difference "
               "from the first earlier modification: to added, removed, or "
               "equal segments. "
               "The value begins with one of the characters 'a', 'r', or 'e', "
               "followed by substring that will be used to separate "
               "selected difference segments in resulting messages "
               "(if this substring is empty, space is used)."))
    opars.add_option(
        "-F", "--filter",
        metavar=_("@info command line value placeholder", "NAME"),
        action="append", dest="filters", default=None,
        help=_("@info command line option description",
               "Pass relevant message text fields through a filter before "
               "matching or comparing them (relevant in some modes). "
               "Can be repeated to add several filters."))
    opars.add_option(
        "-G", "--show-filtered",
        action="store_true", dest="show_filtered", default=False,
        help=_("@info command line option description",
               "When operating under a filter, also show filtered versions "
               "of whatever is shown in original (e.g. in diffs)."))
    opars.add_option(
        "-k", "--keep-flags",
        action="store_true", dest="keep_flags", default=False,
        help=_("@info command line option description",
               "Do not remove review-significant flags from messages "
               "(possibly convert them as appropriate)."))
    opars.add_option(
        "-m", "--message",
        metavar=_("@info command line value placeholder", "TEXT"),
        action="store", dest="message", default=None,
        help=_("@info command line option description",
               "Version control commit message for original catalogs, "
               "when %(opt)s is in effect.",
               opt="-c"))
    opars.add_option(
        "-o", "--open-in-editor",
        metavar=("|".join(sorted(known_editors))),
        action="store", dest="po_editor", default=None,
        help=_("@info command line option description",
               "Open selected messages in one of the supported PO editors."))
    opars.add_option(
        "-L", "--max-fraction-select",
        metavar=_("@info command line value placeholder", "FRACTION"),
        action="store", dest="max_fraction_select", default=None,
        help=_("@info command line option description",
               "Select messages in a catalog only if the total number "
               "of selected messages in that catalog would be at most "
               "the given fraction (0.0-1.0) of total number of messages."))
    opars.add_option(
        "-s", "--selector",
        metavar=_("@info command line value placeholder", "SELECTOR[:ARGS]"),
        action="append", dest="selectors", default=None,
        help=_("@info command line option description",
               "Consider only messages matched by this selector. "
               "Can be repeated, in which case the message is selected "
               "if all selectors match it."))
    opars.add_option(
        "-t", "--tag",
        metavar=_("@info command line value placeholder", "TAG"),
        action="store", dest="tags", default=None,
        help=_("@info command line option description",
               "Tag to add or consider in ascription records. "
               "Several tags may be given separated by commas."))
    opars.add_option(
        "-u", "--user",
        metavar=_("@info command line value placeholder", "USER"),
        action="store", dest="user", default=None,
        help=_("@info command line option description",
               "User in whose name the operation is performed."))
    opars.add_option(
        "-U", "--update-headers",
        action="store_true", dest="update_headers", default=None,
        help=_("@info command line option description",
               "Update headers in catalogs which contain modifications "
               "before committing them, with user's translator information."))
    opars.add_option(
        "-v", "--verbose",
        action="store_true", dest="verbose", default=False,
        help=_("@info command line option description",
               "Output more detailed progress info."))
    opars.add_option(
        "-w", "--write-modified",
        metavar=_("@info command line value placeholder", "FILE"),
        action="store", dest="write_modified", default=None,
        help=_("@info command line option description",
               "Write paths of all original catalogs modified by "
               "ascription operations into the given file."))
    opars.add_option(
        "-x", "--externals",
        metavar=_("@info command line value placeholder", "PYFILE"),
        action="append", dest="externals", default=[],
        help=_("@info command line option description",
               "Collect optional functionality from an external Python file "
               "(selectors, etc)."))
    opars.add_option(
        "--all-reviewed",
        action="store_true", dest="all_reviewed", default=False,
        help=_("@info command line option description",
               "Ascribe all messages as reviewed on commit, "
               "overriding any existing review elements. "
               "Tags given by %(opt)s apply. "
               "This should not be done in day-to-day practice; "
               "the primary use is initial review ascription.",
               opt="--tag"))
    add_cmdopt_filesfrom(opars)
    add_cmdopt_incexc(opars)

    (options, free_args) = opars.parse_args(str_to_unicode(sys.argv[1:]))

    # Parse operation mode and its arguments.
    if len(free_args) < 1:
        error(_("@info", "Operation mode not given."))
    rawmodename = free_args.pop(0)
    modename = mode_tolong.get(rawmodename)
    if modename is None:
        flatmodes = ["/".join((x[0],) + x[1]) for x in mode_spec]
        error(_("@info",
                "Unknown operation mode '%(mode)s' "
                "(known modes: %(modelist)s).",
                mode=rawmodename,
                modelist=format_item_list(flatmodes)))

    # For options not issued, read values from user configuration.
    # Configuration values can also be issued by mode using
    # C{afield/amode = value} syntax, which takes precedence over
    # general fields (e.g. C{filters/review} vs. C{filters}).
    cfgsec = pology_config.section("poascribe")
    for optname, getvalf, defval in (
        ("aselectors", cfgsec.strdlist, []),
        ("vcs-commit", cfgsec.boolean, True),
        ("po-editor", cfgsec.string, None),
        ("filters", cfgsec.strslist, []),
        ("min-adjsim-diff", cfgsec.real, 0.0),
        ("selectors", cfgsec.strdlist, []),
        ("tags", cfgsec.string, ""),
        ("user", cfgsec.string, None),
        ("update-headers", cfgsec.boolean, False),
        ("diff-reduce-history", cfgsec.string, None),
        ("max-fraction-select", cfgsec.real, 1.01),
    ):
        uoptname = optname.replace("-", "_")
        if getattr(options, uoptname) is None:
            for fldname in ("%s/%s" % (optname, modename), optname):
                fldval = getvalf(fldname, None)
                if fldval is not None:
                    break
            if fldval is None:
                fldval = defval
            setattr(options, uoptname, fldval)

    # Convert options to non-string types.
    def valconv_editor (edkey):
        msgrepf = known_editors.get(edkey)
        if msgrepf is None:
            error(_("@info",
                    "PO editor '%(ed)s' is not among "
                    "the supported editors: %(edlist)s.",
                    ed=edkey, edlist=format_item_list(sorted(known_editors))))
        return msgrepf
    def valconv_tags (cstr):
        return set(x.strip() for x in cstr.split(","))
    for optname, valconv in (
        ("max-fraction-select", float),
        ("min-adjsim-diff", float),
        ("po-editor", valconv_editor),
        ("tags", valconv_tags),
    ):
        uoptname = optname.replace("-", "_")
        valraw = getattr(options, uoptname, None)
        if valraw is not None:
            try:
                value = valconv(valraw)
            except TypeError:
                error(_("@info",
                        "Value '%(val)s' to option '%(opt)s' is of wrong type.",
                        val=valraw, opt=("--" + optname)))
            setattr(options, uoptname, value)

    # Collect any external functionality.
    for xmod_path in options.externals:
        collect_externals(xmod_path)

    # Create history filter if requested, store it in options.
    options.hfilter = None
    options.sfilter = None
    if options.filters:
        hfilters = []
        for hspec in options.filters:
            hfilters.append(get_hook_ireq(hspec, abort=True))
        def hfilter_composition (text):
            for hfilter in hfilters:
                text = hfilter(text)
            return text
        options.hfilter = hfilter_composition
        if options.show_filtered:
            options.sfilter = options.hfilter

    # Create specification for reducing historical messages to diffs.
    options.addrem = None
    if options.diff_reduce_history:
        options.addrem = options.diff_reduce_history
        if options.addrem[:1] not in ("a", "e", "r"):
            error(_("@info",
                    "Value '%(val)s' to option '%(opt)s' must start "
                    "with '%(char1)s', '%(char2)s', or '%(char3)s'.",
                    val=options.addrem, opt="--diff-reduce-history",
                    char1="a", char2="e", char3="r"))

    # Create selectors if any explicitly given.
    selector = None
    if options.selectors:
        selector = make_ascription_selector(options.selectors)
    aselector = None
    if options.aselectors:
        aselector = make_ascription_selector(options.aselectors, hist=True)

    # Assemble operation mode.
    needuser = False
    canselect = False
    canaselect = False
    class _Mode: pass
    mode = _Mode()
    mode.name = modename
    if 0: pass
    elif mode.name == "status":
        mode.execute = status
        mode.selector = selector or make_ascription_selector(["any"])
        canselect = True
    elif mode.name == "commit":
        mode.execute = commit
        mode.selector = selector or make_ascription_selector(["any"])
        needuser = True
        canselect = True
    elif mode.name == "diff":
        mode.execute = diff
        mode.selector = selector or make_ascription_selector(["modar"])
        mode.aselector = aselector
        canselect = True
        canaselect = True
    elif mode.name == "purge":
        mode.execute = purge
        mode.selector = selector or make_ascription_selector(["any"])
        canselect = True
    elif mode.name == "history":
        mode.execute = history
        mode.selector = selector or make_ascription_selector(["any"])
        canselect = True
    else:
        error(_("@info",
                "Unhandled operation mode '%(mode)s'.",
                mode=mode.name))

    mode.user = None
    if needuser:
        if not options.user:
            error(_("@info",
                    "Operation mode '%(mode)s' requires a user "
                    "to be specified.",
                    mode=mode.name))
        mode.user = options.user
    if not canselect and selector:
        error(_("@info",
                "Operation mode '%(mode)s' does not accept selectors.",
                mode=mode.name))
    if not canaselect and aselector:
        error(_("@info",
                "Operation mode '%(mode)s' does not accept history selectors.",
                mode=mode.name))

    # Collect list of catalogs supplied through command line.
    # If none supplied, assume current working directory.
    catpaths = collect_paths_cmdline(rawpaths=free_args,
                                     incnames=options.include_names,
                                     incpaths=options.include_paths,
                                     excnames=options.exclude_names,
                                     excpaths=options.exclude_paths,
                                     filesfrom=options.files_from,
                                     elsecwd=True,
                                     respathf=collect_catalogs,
                                     abort=True)

    # Split catalogs into lists by ascription config,
    # and link them to their ascription catalogs.
    aconfs_catpaths = collect_ascription_associations(catpaths)
    assert_review_tags(aconfs_catpaths, options.tags)

    # Execute operation.
    mode.execute(options, aconfs_catpaths, mode)

    # Write out list of modified original catalogs if requested.
    if options.write_modified and _modified_cats:
        lfpath = options.write_modified
        f = open(lfpath, "w")
        f.write(("\n".join(sorted(_modified_cats)) + "\n").encode("utf-8"))
        f.close()
        report(_("@info",
                 "Paths of modified catalogs written to '%(file)s'.",
                 file=lfpath))


def vcs_commit_catalogs (aconfs_catpaths, user, message=None, onabortf=None):

    report(_("@info:progress VCS is acronym for \"version control system\"",
             ">>>>> VCS is committing catalogs:"))

    # Attach paths to each distinct config, to commit them all at once.
    aconfs = []
    catpaths_byconf = {}
    for aconf, catpaths in aconfs_catpaths:
        if aconf not in catpaths_byconf:
            catpaths_byconf[aconf] = []
            aconfs.append(aconf)
        for catpath, acatpath in catpaths:
            catpaths_byconf[aconf].append(catpath)
            if os.path.isfile(acatpath):
                catpaths_byconf[aconf].append(acatpath)

    # Commit by config.
    for aconf in aconfs:
        cmsg = message
        cmsgfile = None
        if not cmsg:
            cmsg = aconf.commitmsg
        if not cmsg:
            cmsgfile, cmsgfile_orig = get_commit_message_file_path(user)
        else:
            cmsg += " " + fmt_commit_user(user)
        added, apaths = aconf.vcs.add(catpaths_byconf[aconf], repadd=True)
        if not added:
            if onabortf:
                onabortf()
            error(_("@info",
                    "VCS reports that some catalogs cannot be added."))
        cpaths = sorted(set(map(join_ncwd, catpaths_byconf[aconf] + apaths)))
        if not aconf.vcs.commit(cpaths, message=cmsg, msgfile=cmsgfile,
                                incparents=False):
            if onabortf:
                onabortf()
            if not cmsgfile:
                error(_("@info",
                        "VCS reports that some catalogs cannot be committed."))
            else:
                os.remove(cmsgfile)
                error(_("@info",
                        "VCS reports that some catalogs cannot be committed "
                        "(commit message preserved in '%(file)s').",
                        file=cmsgfile_orig))
        if cmsgfile:
            os.remove(cmsgfile)
            os.remove(cmsgfile_orig)


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
        error(_("@info",
                "Еrror from editor command '%(cmd)s' for commit message.",
                cmd=cmd))
    if not os.path.isfile(fpath):
        error(_("@info",
                "Editor command '%(cmd)s' did not produce a file.",
                cmd=cmd))

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


def assert_mode_user (aconfs_catpaths, mode):

    for aconf, catpaths in aconfs_catpaths:
        if mode.user not in aconf.users:
            error(_("@info",
                    "User '%(user)s' not defined in '%(file)s'.",
                    user=mode.user, file=aconf.path))


def assert_review_tags (aconfs_catpaths, tags):

    for aconf, catpaths in aconfs_catpaths:
        for tag in tags:
            if tag not in aconf.revtags:
                error(_("@info",
                        "Review tag '%(tag)s' not defined in '%(file)s'.",
                        tag=tag, file=aconf.path))


def assert_syntax (aconfs_catpaths, onabortf=None):

    checkf = msgfmt(options=["--check"])
    numerr = 0
    for aconf, catpaths in aconfs_catpaths:
        for catpath, acatpath in catpaths:
            numerr += checkf(catpath)
    if numerr:
        if onabortf:
            onabortf()
        error(_("@info",
                "Invalid syntax in some files, see the reports above. "
                "Ascription aborted."))
    return numerr


def setup_progress (aconfs_catpaths, addfmt):

    acps = [y[0] for x in aconfs_catpaths for y in x[1]]
    return init_file_progress(acps, addfmt=addfmt)


# Exclusive states of a message, as reported by Message.state().
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


def status (options, aconfs_catpaths, mode):

    # Count ascribed and unascribed messages through catalogs.
    counts_a = dict([(x, {}) for x in _all_states])
    counts_na = dict([(x, {}) for x in _all_states])

    upprog = setup_progress(aconfs_catpaths,
                            t_("@info:progress",
                               "Examining state: %(file)s"))
    for aconf, catpaths in aconfs_catpaths:
        for catpath, acatpath in catpaths:
            upprog(catpath)
            # Open current and ascription catalog.
            cat = Catalog(catpath, monitored=False)
            acat = Catalog(acatpath, create=True, monitored=False)
            # Count ascribed and non-ascribed by original catalog.
            nselected = 0
            for msg in cat:
                purge_msg(msg)
                ahist = collect_ascription_history(
                    msg, acat, aconf,
                    hfilter=options.hfilter, addrem=options.addrem, nomrg=True)
                if ahist[0].user is None and not has_tracked_parts(msg):
                    continue # pristine
                if not mode.selector(msg, cat, ahist, aconf):
                    continue # not selected
                counts = ahist[0].user is None and counts_na or counts_a
                st = msg.state()
                if catpath not in counts[st]:
                    counts[st][catpath] = 0
                counts[st][catpath] += 1
                nselected += 1
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
            # Cancel counts if maximum selection fraction exceeded.
            if float(nselected) / len(cat) > options.max_fraction_select:
                for counts in (counts_a, counts_na):
                    for st in _all_states:
                        if catpath in counts[st]:
                            counts[st].pop(catpath)
    upprog()

    # Some general data for tabulation of output.
    coln = [_("@title:column translated messages", "msg/t"),
            _("@title:column fuzzy messages", "msg/f"),
            _("@title:column untranslated messages", "msg/u"),
            _("@title:column obsolete translated messages", "msg/ot"),
            _("@title:column obsolete fuzzy messages", "msg/of"),
            _("@title:column obsolete untranslated messages", "msg/ou")]
    none="-"

    # NOTE: When reporting, do not show anything if there are
    # neither ascribed nor non-ascribed messages selected.
    # If there are some ascribed and none non-ascribed,
    # show only the row for ascribed.
    # However, if there are some non-ascribed but none ascribed,
    # still show the row for ascribed, to not accidentally confuse
    # non-ascribed for ascribed.

    # Report totals.
    totals_a, totals_na = {}, {}
    for totals, counts in ((totals_a, counts_a), (totals_na, counts_na)):
        for st, cnt_per_cat in counts.items():
            totals[st] = sum(cnt_per_cat.values())
    # See previous NOTE.
    if sum(totals_a.values()) > 0 or sum(totals_na.values()) > 0:
        rown = [_("@title:row number of ascribed messages",
                  "ascribed")]
        data = [[totals_a[x] or None] for x in _all_states]
        if sum(totals_na.values()) > 0:
            rown.append(_("@title:row number of unascribed messages",
                          "unascribed"))
            for i in range(len(_all_states)):
                data[i].append(totals_na[_all_states[i]] or None)
        report(tabulate(data=data, coln=coln, rown=rown,
                        none=none, colorize=True))

    # Report counts per catalog if requested.
    if options.show_by_file:
        catpaths = set()
        for counts in (counts_a, counts_na):
            catpaths.update(sum([x.keys() for x in counts.values()], []))
        catpaths = sorted(catpaths)
        if catpaths:
            coln.insert(0, _("@title:column", "catalog"))
            coln.insert(1, _("@title:column state (asc/nasc)", "st"))
            data = [[] for x in _all_states]
            for catpath in catpaths:
                cc_a = [counts_a[x].get(catpath, 0) for x in _all_states]
                cc_na = [counts_na[x].get(catpath, 0) for x in _all_states]
                # See previous NOTE.
                if sum(cc_a) > 0 or sum(cc_na) > 0:
                    data[0].append(catpath)
                    data[1].append(
                        _("@item:intable number of ascribed messages",
                          "asc"))
                    for datac, cc in zip(data[2:], cc_a):
                        datac.append(cc or None)
                    if sum(cc_na) > 0:
                        data[0].append("^^^")
                        data[1].append(
                            _("@item:intable number of unascribed messages",
                              "nasc"))
                        for datac, cc in zip(data[2:], cc_na):
                            datac.append(cc or None)
            if any(data):
                dfmt = ["%%-%ds" % max([len(x) for x in catpaths])]
                report("-")
                report(tabulate(data=data, coln=coln, dfmt=dfmt,
                                none=none, colorize=True))


# FIXME: Factor out into message module.
_fields_current = (
    "msgctxt", "msgid", "msgid_plural",
)
_fields_previous = (
    "msgctxt_previous", "msgid_previous", "msgid_plural_previous",
)

def msg_to_previous (msg, copy=True):

    if msg.fuzzy and msg.msgid_previous is not None:
        pmsg = MessageUnsafe(msg) if copy else msg
        for fcurr, fprev in zip(_fields_current, _fields_previous):
            setattr(pmsg, fcurr, pmsg.get(fprev))
        pmsg.unfuzzy()
        return pmsg


def restore_reviews (aconfs_catpaths, revspecs_by_catmsg):

    upprog = setup_progress(aconfs_catpaths,
                            t_("@info:progress",
                               "Restoring reviews: %(file)s"))
    nrestored = 0
    for aconf, catpaths in aconfs_catpaths:
        for catpath, acatpath in catpaths:
            upprog(catpath)
            revels_by_msg = revspecs_by_catmsg.get(catpath)
            if revels_by_msg:
                cat = Catalog(catpath, monitored=True)
                for msgref, revels in sorted(revels_by_msg.items()):
                    msg = cat[msgref - 1]
                    revtags, unrevd, revok = revels
                    restore_review_flags(msg, revtags, unrevd)
                    nrestored += 1
                sync_and_rep(cat, shownmod=False)
                if aconf.vcs.is_versioned(acatpath):
                    aconf.vcs.revert(acatpath)
                # ...no else: because revert may cause the file
                # not to be versioned any more.
                if not aconf.vcs.is_versioned(acatpath):
                    os.remove(acatpath)

    if nrestored > 0:
        report(n_("@info:progress",
                  "===== Review elements restored to %(num)d message.",
                  "===== Review elements restored to %(num)d messages.",
                  num=nrestored))


def restore_review_flags (msg, revtags, unrevd):

    for tag in revtags:
        flag = _revdflags[0]
        if tag:
            flag += _flagtagsep + tag
        msg.flag.add(flag)
    if unrevd:
        msg.flag.add(_urevdflags[0])

    return msg


def commit (options, aconfs_catpaths, mode):

    assert_mode_user(aconfs_catpaths, mode)

    # Ascribe modifications and reviews.
    upprog = setup_progress(aconfs_catpaths,
                            t_("@info:progress",
                               "Ascribing: %(file)s"))
    revels = {}
    counts = dict([(x, [0, 0]) for x in _all_states])
    aconfs_catpaths_ascmod = []
    aconf_by_catpath = {}
    for aconf, catpaths in aconfs_catpaths:
        aconfs_catpaths_ascmod.append((aconf, []))
        for catpath, acatpath in catpaths:
            upprog(catpath)
            res = commit_cat(options, aconf, mode.user, catpath, acatpath,
                             mode.selector)
            ccounts, crevels, catmod = res
            for st, (nmod, nrev) in ccounts.items():
                counts[st][0] += nmod
                counts[st][1] += nrev
            revels[catpath] = crevels
            if catmod:
                aconfs_catpaths_ascmod[-1][1].append((catpath, acatpath))
            aconf_by_catpath[catpath] = aconf
    upprog()

    onabortf = lambda: restore_reviews(aconfs_catpaths_ascmod, revels)

    # Assert that all reviews were good.
    unknown_revtags = []
    for catpath, revels1 in sorted(revels.items()):
        aconf = aconf_by_catpath[catpath]
        for msgref, (revtags, unrevd, revok) in sorted(revels1.items()):
            if not revok:
                onabortf()
                error("Ascription aborted due to earlier warnings.")

    assert_syntax(aconfs_catpaths_ascmod, onabortf=onabortf)
    # ...must be done after committing, to have all review elements purged

    coln = [_("@title:column number of modified messages",
              "modified")]
    rown = []
    data = [[]]
    for st, stlabel in (
        (_st_tran,
         _("@title:row number of translated messages",
           "translated")),
        (_st_fuzzy,
         _("@title:row number of fuzzy messages",
           "fuzzy")),
        (_st_untran,
         _("@title:row number of untranslated messages",
           "untranslated")),
        (_st_otran,
         _("@title:row number of obsolete translated messages",
           "obsolete/t")),
        (_st_ofuzzy,
         _("@title:row number of obsolete fuzzy messages",
           "obsolete/f")),
        (_st_ountran,
         _("@title:row number of obsolete untranslated messages",
           "obsolete/u")),
    ):
        if counts[st][1] > 0 and len(coln) < 2:
            coln.append(_("@title:column number of reviewed messages",
                          "reviewed"))
            data.append([])
        if counts[st][0] > 0 or counts[st][1] > 0:
            rown.append(stlabel)
            data[0].append(counts[st][0] or None)
            if len(coln) >= 2:
                data[1].append(counts[st][1] or None)
    if rown:
        report(_("@info:progress", "===== Ascription summary:"))
        report(tabulate(data, coln=coln, rown=rown, none="-",
                        colorize=True))

    if options.vcs_commit:
        vcs_commit_catalogs(aconfs_catpaths, mode.user,
                            message=options.message, onabortf=onabortf)
        # ...not configs_catpaths_ascmod, as non-ascription relevant
        # modifications may exist (e.g. new pristine catalog added).


def diff (options, aconfs_catpaths, mode):

    upprog = setup_progress(aconfs_catpaths,
                            t_("@info:progress",
                               "Diffing for review: %(file)s"))
    ndiffed = 0
    for aconf, catpaths in aconfs_catpaths:
        for catpath, acatpath in catpaths:
            upprog(catpath)
            ndiffed += diff_cat(options, aconf, catpath, acatpath,
                                mode.selector, mode.aselector)
    upprog()
    if ndiffed > 0:
        report(n_("@info:progress",
                  "===== %(num)d message diffed for review.",
                  "===== %(num)d messages diffed for review.",
                  num=ndiffed))


def purge (options, aconfs_catpaths, mode):

    upprog = setup_progress(aconfs_catpaths,
                            t_("@info:progress",
                               "Purging review elements: %(file)s"))
    npurged = 0
    for aconf, catpaths in aconfs_catpaths:
        for catpath, acatpath in catpaths:
            upprog(catpath)
            npurged += purge_cat(options, aconf, catpath, acatpath,
                                 mode.selector)
    upprog()

    if npurged > 0:
        if not options.keep_flags:
            report(n_("@info:progress",
                      "===== Review elements purged from %(num)d message.",
                      "===== Review elements purged from %(num)d messages.",
                      num=npurged))
        else:
            report(n_("@info:progress",
                      "===== Review elements purged from %(num)d message "
                      "(flags kept).",
                      "===== Review elements purged from %(num)d messages "
                      "(flags kept).",
                      num=npurged))

    return npurged


def history (options, aconfs_catpaths, mode):

    upprog = setup_progress(aconfs_catpaths,
                            t_("@info:progress",
                               "Computing histories: %(file)s"))
    nshown = 0
    for aconf, catpaths in aconfs_catpaths:
        for catpath, acatpath in catpaths:
            upprog(catpath)
            nshown += history_cat(options, aconf, catpath, acatpath,
                                  mode.selector)
    upprog()
    if nshown > 0:
        report(n_("@info:progress",
                  "===== Histories computed for %(num)d message.",
                  "===== Histories computed for %(num)d messages.",
                  num=nshown))


def commit_cat (options, aconf, user, catpath, acatpath, stest):

    # Open current catalog and ascription catalog.
    # Monitored, for removal of review elements.
    cat = Catalog(catpath, monitored=True)
    acat = prep_write_asc_cat(acatpath, aconf)

    revtags_ovr = None
    if options.all_reviewed:
        revtags_ovr = options.tags

    # Collect unascribed messages, but ignoring pristine ones
    # (those which are both untranslated and without history).
    # Collect and purge any review elements.
    # Check if any modification cannot be due to merging
    # (if header update is requested).
    mod_msgs = []
    rev_msgs = []
    revels_by_msg = {}
    counts = dict([(x, [0, 0]) for x in _all_states])
    counts0 = counts.copy()
    any_nonmerges = False
    prev_msgs = []
    check_mid_msgs = []
    for msg in cat:
        mod, revtags, unrevd = purge_msg(msg)
        if mod:
            revels_by_msg[msg.refentry] = [revtags, unrevd, True]
        ahist = collect_ascription_history(msg, acat, aconf) # after purging
        # Do not ascribe anything if the message is new and untranslated.
        if (    ahist[0].user is None and len(ahist) == 1
            and not has_tracked_parts(msg)
        ):
            continue
        # Possibly ascribe review only if the message passes the selector.
        if stest(msg, cat, ahist, aconf) and (mod or revtags_ovr):
            if revtags_ovr:
                revtags = revtags_ovr
                unrevd = False
            if revtags and not unrevd: # unreviewed flag overrides
                rev_msgs.append((msg, revtags))
                counts[msg.state()][1] += 1
                # Check and record if review tags are not valid.
                unknown_revtags = revtags.difference(aconf.revtags)
                if unknown_revtags:
                    revels_by_msg[msg.refentry][-1] = False
                    tagfmt = format_item_list(sorted(unknown_revtags))
                    warning_on_msg(_("@info",
                                     "Unknown review tags: %(taglist)s.",
                                     taglist=tagfmt), msg, cat)
        # Ascribe modification regardless of the selector.
        if ahist[0].user is None:
            mod_msgs.append(msg)
            counts[msg.state()][0] += 1
            if options.update_headers and not any_nonmerges:
                if len(ahist) == 1 or not merge_modified(ahist[1].msg, msg):
                    any_nonmerges = True
            # Record that reconstruction of the post-merge message
            # should be tried if this message has no prior history
            # but it is not pristine (it may be that the translator
            # has merged the catalog and updated fuzzy messages in one step,
            # without committing the catalog right after merging).
            if len(ahist) == 1:
                check_mid_msgs.append(msg)
        # Collect latest historical version of the message,
        # in case reconstruction of post-merge messages is needed.
        if ahist[0].user is not None or len(ahist) > 1:
            pmsg = ahist[1 if ahist[0].user is None else 0].msg
            prev_msgs.append(pmsg)

    # Collect non-obsolete ascribed messages that no longer have
    # original counterpart, to ascribe as obsolete.
    # If reconstruction of post-merge messages is needed,
    # also collect latest historical versions.
    cat.sync_map() # in case key fields were purged
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
            if st or check_mid_msgs:
                msg = collect_ascription_history_segment(amsg, acat, aconf)[0].msg
                if check_mid_msgs:
                    prev_msgs.append(msg)
                if st:
                    msg.obsolete = True
                    mod_msgs.append(msg)
                    counts[st][0] += 1

    # Shortcut if nothing to do, because sync_and_rep later are expensive.
    if not mod_msgs and not revels_by_msg:
        # No messages to commit.
        return counts0, revels_by_msg, False

    # Construct post-merge messages.
    mod_mid_msgs = []
    if check_mid_msgs and not acat.created():
        mid_cat = create_post_merge_cat(cat, prev_msgs)
        for msg in check_mid_msgs:
            mid_msg = mid_cat.get(msg)
            if (    mid_msg is not None
                and mid_msg.fuzzy
                and not ascription_equal(mid_msg, msg)
            ):
                mod_mid_msgs.append(mid_msg)

    # Ascribe modifications.
    for mid_msg in mod_mid_msgs: # ascribe post-merge before actual
        ascribe_modification(mid_msg, user, _dt_start, acat, aconf)
    for msg in mod_msgs:
        ascribe_modification(msg, user, _dt_start, acat, aconf)

    # Ascribe reviews.
    for msg, revtags in rev_msgs:
        ascribe_review(msg, user, _dt_start, revtags, acat, aconf)

    # Update header if requested and translator's modifications detected.
    if options.update_headers and any_nonmerges:
        cat.update_header(project=cat.name,
                          title=aconf.title,
                          name=aconf.users[user].name,
                          email=aconf.users[user].email,
                          teamemail=aconf.teamemail,
                          langname=aconf.langteam,
                          langcode=aconf.langcode,
                          plforms=aconf.plforms)

    nmod = [len(mod_msgs)]
    if len(rev_msgs) > 0:
        nmod.append(len(rev_msgs))
    catmod = False
    if sync_and_rep(cat, nmod=nmod):
        catmod = True
    if asc_sync_and_rep(acat, shownmod=False, nmod=[0]):
        catmod = True

    return counts, revels_by_msg, catmod


def diff_cat (options, aconf, catpath, acatpath, stest, aselect):

    cat = Catalog(catpath, monitored=True)
    acat = Catalog(acatpath, create=True, monitored=False)

    # Select messages for diffing.
    msgs_to_diff = []
    for msg in cat:
        purge_msg(msg)
        ahist = collect_ascription_history(
            msg, acat, aconf,
            hfilter=options.hfilter, addrem=options.addrem, nomrg=True)
        # Makes no sense to review pristine messages.
        if ahist[0].user is None and not has_tracked_parts(msg):
            continue
        sres = stest(msg, cat, ahist, aconf)
        if not sres:
            continue
        msgs_to_diff.append((msg, ahist, sres))

    # Cancel selection if maximum fraction exceeded.
    if float(len(msgs_to_diff)) / len(cat) > options.max_fraction_select:
        msgs_to_diff = []

    if not msgs_to_diff:
        return 0

    # Diff selected messages.
    diffed_msgs = []
    tagfmt = _flagtagsep.join(options.tags)
    for msg, ahist, sres in msgs_to_diff:

        # Try to select ascription to differentiate from.
        # (Note that ascription indices returned by selectors are 1-based.)
        i_asc = None
        if aselect:
            asres = aselect(msg, cat, ahist, aconf)
            i_asc = (asres - 1) if asres else None
        elif not isinstance(sres, bool):
            # If there is no ascription selector, but basic selector returned
            # an ascription index, use first earlier non-fuzzy for diffing.
            i_asc = sres - 1
            i_asc = first_non_fuzzy(ahist, i_asc + 1)

        # Differentiate and flag.
        amsg = i_asc is not None and ahist[i_asc].msg or None
        if amsg is not None:
            if editprob(amsg.msgid, msg.msgid) > options.min_adjsim_diff:
                msg_ediff(amsg, msg, emsg=msg, pfilter=options.sfilter)
                flag = _diffflag
            else:
                # If to great difference, add special flag and do not diff.
                flag = _diffflag_ign
        else:
            # If no previous ascription selected, add special flag.
            flag = _diffflag_tot
        if tagfmt:
            flag += _flagtagsep + tagfmt
        msg.flag.add(flag)

        # Add ascription chain comment.
        ascfmts = []
        i_from = (i_asc - 1) if i_asc is not None else len(ahist) - 1
        for i in range(i_from, -1, -1):
            a = ahist[i]
            shtype = {AscPoint.ATYPE_MOD: "m",
                      AscPoint.ATYPE_REV: "r"}[a.type]
            if a.tag:
                ascfmt = "%s:%s(%s)" % (a.user, shtype, a.tag)
            else:
                ascfmt = "%s:%s" % (a.user, shtype)
            ascfmts.append(ascfmt)
        achnfmt = u"%s %s" % (_achncmnt, " ".join(ascfmts))
        msg.auto_comment.append(achnfmt)

        diffed_msgs.append(msg)

    sync_and_rep(cat)

    # Open in the PO editor if requested.
    if options.po_editor:
        for msg in diffed_msgs:
            options.po_editor(msg, cat,
                              report=_("@info note on selected message",
                                       "Selected for review."))

    return len(diffed_msgs)


_subreflags = "|".join(_all_flags)
_subrecmnts = "|".join(_all_cmnts)
_any_to_purge_rx = re.compile(r"^\s*(#,.*\b(%s)|#\.\s*(%s))"
                              % (_subreflags, _subrecmnts),
                              re.M|re.U)

# Quickly check if it may be that some messages in the PO file
# have review elements (diffs, flags).
def may_have_revels (catpath):

    return bool(_any_to_purge_rx.search(open(catpath).read()))


def purge_cat (options, aconf, catpath, acatpath, stest):

    if not may_have_revels(catpath):
        return 0

    cat = Catalog(catpath, monitored=True)
    acat = Catalog(acatpath, create=True, monitored=False)

    # Select messages to purge.
    msgs_to_purge = []
    for msg in cat:
        cmsg = MessageUnsafe(msg)
        purge_msg(cmsg)
        ahist = collect_ascription_history(
            cmsg, acat, aconf,
            hfilter=options.hfilter, addrem=options.addrem, nomrg=True)
        if not stest(cmsg, cat, ahist, aconf):
            continue
        msgs_to_purge.append(msg)

    # Does observing options.max_fraction_select makes sense for purging?
    ## Cancel selection if maximum fraction exceeded.
    #if float(len(msgs_to_purge)) / len(cat) > options.max_fraction_select:
        #msgs_to_purge = []

    # Purge selected messages.
    npurged = 0
    for msg in msgs_to_purge:
        res = purge_msg(msg, keepflags=options.keep_flags)
        mod, revtags, unrevd = res
        if mod:
            npurged += 1

    sync_and_rep(cat)

    return npurged


def history_cat (options, aconf, catpath, acatpath, stest):

    cat = Catalog(catpath, monitored=False)
    acat = Catalog(acatpath, create=True, monitored=False)

    # Select messages for which to compute histories.
    msgs_to_hist = []
    for msg in cat:
        purge_msg(msg)
        ahist = collect_ascription_history(
            msg, acat, aconf,
            hfilter=options.hfilter, addrem=options.addrem, nomrg=True)
        if not stest(msg, cat, ahist, aconf):
            continue
        msgs_to_hist.append((msg, ahist))

    # Cancel selection if maximum fraction exceeded.
    if float(len(msgs_to_hist)) / len(cat) > options.max_fraction_select:
        msgs_to_hist = []

    # Compute histories for selected messages.
    for msg, ahist in msgs_to_hist:

        unasc = ahist[0].user is None
        if unasc:
            ahist.pop(0)

        hlevels = len(ahist)
        if options.depth is not None:
            hlevels = int(options.depth)
            if ahist[0].user is None:
                hlevels += 1
            if hlevels > len(ahist):
                hlevels = len(ahist)

        hinfo = []
        if hlevels > 0:
            hinfo += [_("@info:progress",
                        "<green>>>> History follows:</green>")]
            hfmt = "%%%dd" % len(str(hlevels))
        for i in range(hlevels):
            a = ahist[i]
            if a.type == AscPoint.ATYPE_MOD:
                anote = _("@item:intable",
                          "<bold>#%(pos)d</bold> "
                          "modified by %(user)s on %(date)s",
                          pos=a.pos, user=a.user, date=a.date)
            elif a.type == AscPoint.ATYPE_REV:
                if not a.tag:
                    anote = _("@item:intable",
                              "<bold>#%(pos)d</bold> "
                              "reviewed by %(user)s on %(date)s",
                              pos=a.pos, user=a.user, date=a.date)
                else:
                    anote = _("@item:intable",
                              "<bold>#%(pos)d</bold> "
                              "reviewed (%(tag)s) by %(user)s on %(date)s",
                               pos=a.pos, user=a.user, tag=a.tag, date=a.date)
            else:
                warning_on_msg(
                    _("@info",
                      "Unknown ascription type '%(type)s' found in history.",
                      type=a.type), msg, cat)
                continue
            hinfo += [anote]
            if not a.type == AscPoint.ATYPE_MOD:
                # Nothing more to show if this ascription is not modification.
                continue
            i_next = i + 1
            if i_next == len(ahist):
                # Nothing more to show at end of history.
                continue
            dmsg = MessageUnsafe(a.msg)
            nmsg = ahist[i_next].msg
            if dmsg != nmsg:
                msg_ediff(nmsg, dmsg, emsg=dmsg,
                          pfilter=options.sfilter, colorize=True)
                dmsgfmt = dmsg.to_string(force=True,
                                         wrapf=cat.wrapf()).rstrip("\n")
                hindent = " " * (len(hfmt % 0) + 2)
                hinfo += [hindent + x for x in dmsgfmt.split("\n")]
        hinfo = cjoin(hinfo, "\n")

        if unasc or msg.fuzzy:
            pmsg = None
            i_nfasc = first_non_fuzzy(ahist)
            if i_nfasc is not None:
                pmsg = ahist[i_nfasc].msg
            elif msg.fuzzy and msg.msgid_previous is not None:
                pmsg = msg_to_previous(msg)
            if pmsg is not None:
                for fprev in _fields_previous:
                    setattr(msg, fprev, None)
                msg_ediff(pmsg, msg, emsg=msg,
                          pfilter=options.sfilter, colorize=True)
        report_msg_content(msg, cat,
                           note=(hinfo or None), delim=("-" * 20))

    return len(msgs_to_hist)


_revflags_rx = re.compile(r"^(%s)(?: */(.*))?" % "|".join(_all_flags), re.I)

def purge_msg (msg, keepflags=False):

    modified = False

    # Remove review flags.
    diffed = False
    revtags = set()
    unrevd = False
    for flag in list(msg.flag): # modified inside
        m = _revflags_rx.search(flag)
        if m:
            sflag = m.group(1)
            tagstr = m.group(2) or ""
            tags = [x.strip() for x in tagstr.split(_flagtagsep)]
            if sflag not in _urevdflags:
                revtags.update(tags)
                if sflag in _diffflags:
                    diffed = True
            else:
                unrevd = True
            msg.flag.remove(flag)
            modified = True

    # Remove review comments.
    i = 0
    while i < len(msg.auto_comment):
        cmnt = msg.auto_comment[i].strip()
        if cmnt.startswith(_all_cmnts):
            msg.auto_comment.pop(i)
            modified = True
        else:
            i += 1

    # Remove any leftover previous fields.
    if msg.translated:
        for fprev in _fields_previous:
            if msg.get(fprev) is not None:
                setattr(msg, fprev, None)
                modified = True

    if diffed:
        msg_ediff_to_new(msg, rmsg=msg)
    if keepflags:
        restore_review_flags(msg, revtags, unrevd)

    return modified, revtags, unrevd


def prep_write_asc_cat (acatpath, aconf):

    if not os.path.isfile(acatpath):
        return init_asc_cat(acatpath, aconf)
    else:
        return Catalog(acatpath, monitored=True, wrapping=_ascwrapping)


def init_asc_cat (acatpath, aconf):

    acat = Catalog(acatpath, create=True, monitored=True, wrapping=_ascwrapping)
    ahdr = acat.header

    ahdr.title = Monlist([u"Ascription shadow for %s.po" % acat.name])

    translator = u"Ascriber"

    if aconf.teamemail:
        author = u"%s <%s>" % (translator, aconf.teamemail)
    else:
        author = u"%s" % translator
    ahdr.author = Monlist([author])

    ahdr.copyright = u"Copyright same as for the original catalog."
    ahdr.license = u"License same as for the original catalog."
    ahdr.comment = Monlist([u"===== DO NOT EDIT MANUALLY ====="])

    ahdr.set_field(u"Project-Id-Version", unicode(acat.name))
    ahdr.set_field(u"Report-Msgid-Bugs-To", unicode(aconf.teamemail or ""))
    ahdr.set_field(u"PO-Revision-Date", format_datetime(_dt_start))
    ahdr.set_field(u"Content-Type", u"text/plain; charset=UTF-8")
    ahdr.set_field(u"Content-Transfer-Encoding", u"8bit")

    if aconf.teamemail:
        ltr = "%s <%s>" % (translator, aconf.teamemail)
    else:
        ltr = translator
    ahdr.set_field(u"Last-Translator", unicode(ltr))

    if aconf.langteam:
        if aconf.teamemail:
            tline = u"%s <%s>" % (aconf.langteam, aconf.teamemail)
        else:
            tline = aconf.langteam
        ahdr.set_field(u"Language-Team", unicode(tline))
    else:
        ahdr.remove_field("Language-Team")

    if aconf.langcode:
        ahdr.set_field(u"Language", unicode(aconf.langcode))
    else:
        ahdr.remove_field("Language")

    if aconf.plforms:
        ahdr.set_field(u"Plural-Forms", unicode(aconf.plforms))
    else:
        ahdr.remove_field(u"Plural-Forms")

    return acat


def update_asc_hdr (acat):

    acat.header.set_field(u"PO-Revision-Date", format_datetime(_dt_start))


def create_post_merge_cat (cat, prev_msgs):

    # Prepare previous catalog based on ascription catalog.
    prev_cat = Catalog("", create=True, monitored=False)
    prev_cat.header = Header(cat.header)
    for prev_msg in prev_msgs:
        prev_cat.add_last(prev_msg)
    tmpf1 = NamedTemporaryFile(prefix="pology-merged-", suffix=".po")
    prev_cat.filename = tmpf1.name
    prev_cat.sync()

    # Prepare template based on current catalog.
    tmpl_cat = Catalog("", create=True, monitored=False)
    tmpl_cat.header = Header(cat.header)
    for msg in cat:
        if not msg.obsolete:
            tmpl_msg = MessageUnsafe(msg)
            tmpl_msg.clear()
            tmpl_cat.add_last(tmpl_msg)
    tmpf2 = NamedTemporaryFile(prefix="pology-template-", suffix=".pot")
    tmpl_cat.filename = tmpf2.name
    tmpl_cat.sync()

    # Merge previous catalog using current catalog as template.
    mid_cat = merge_pofile(prev_cat.filename, tmpl_cat.filename,
                           getcat=True, monitored=False, quiet=True)

    return mid_cat


_modified_cats = []

def sync_and_rep (cat, shownmod=True, nmod=None):

    if shownmod and nmod is None:
        nmod = [0]
        for msg in cat:
            if msg.modcount:
                nmod[0] += 1

    modified = cat.sync()
    if nmod and sum(nmod) > 0: # DO NOT check instead modified == True
        if shownmod:
            nmodfmt = "/".join("%d" % x for x in nmod)
            report("%s  (%s)" % (cat.filename, nmodfmt))
        else:
            report("%s" % cat.filename)
        _modified_cats.append(cat.filename)

    return modified


def asc_sync_and_rep (acat, shownmod=True, nmod=None):

    if acat.modcount:
        update_asc_hdr(acat)
        mkdirpath(os.path.dirname(acat.filename))

    return sync_and_rep(acat, shownmod=shownmod, nmod=nmod)


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    exit_on_exception(main)
