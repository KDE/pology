#!/usr/bin/env python2
# -*- coding: UTF-8 -*-

"""
Create embedded diffs of PO files.

Documented in C{doc/user/diffpatch.docbook#sec-dppatch}.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import filecmp
import locale
import os
import shutil
import sys

try:
    import fallback_import_paths
except:
    pass

from pology import version, _, n_, t_
from pology.catalog import Catalog
from pology.message import MessageUnsafe
from pology.colors import ColorOptionParser, set_coloring_globals, cjoin
import pology.config as pology_config
from pology.fsops import str_to_unicode, collect_catalogs
from pology.fsops import exit_on_exception
from pology.diff import msg_ediff
from pology.report import error, warning, report, format_item_list
from pology.report import list_options
from pology.report import init_file_progress
from pology.stdcmdopt import add_cmdopt_colors
from pology.vcs import available_vcs, make_vcs

from pology.internal.poediffpatch import MPC, EDST
from pology.internal.poediffpatch import msg_eq_fields, msg_copy_fields
from pology.internal.poediffpatch import msg_clear_prev_fields
from pology.internal.poediffpatch import diff_cats, diff_hdrs
from pology.internal.poediffpatch import init_ediff_header
from pology.internal.poediffpatch import get_msgctxt_for_headers
from pology.internal.poediffpatch import cats_update_effort


def main ():

    locale.setlocale(locale.LC_ALL, "")

    # Get defaults for command line options from global config.
    cfgsec = pology_config.section("poediff")
    def_do_merge = cfgsec.boolean("merge", True)

    # Setup options and parse the command line.
    usage = _("@info command usage",
        "%(cmd)s [OPTIONS] FILE1 FILE2\n"
        "%(cmd)s [OPTIONS] DIR1 DIR2\n"
        "%(cmd)s -c VCS [OPTIONS] [PATHS...]",
        cmd="%prog")
    desc = _("@info command description",
        "Create embedded diffs of PO files.")
    ver = _("@info command version",
        u"%(cmd)s (Pology) %(version)s\n"
        u"Copyright © 2009, 2010 "
        u"Chusslove Illich (Часлав Илић) &lt;%(email)s&gt;",
        cmd="%prog", version=version(), email="caslav.ilic@gmx.net")

    showvcs = list(set(available_vcs()).difference(["none"]))
    showvcs.sort()

    opars = ColorOptionParser(usage=usage, description=desc, version=ver)
    opars.add_option(
        "-b", "--skip-obsolete",
        action="store_true", dest="skip_obsolete", default=False,
        help=_("@info command line option description",
               "Do not diff obsolete messages."))
    opars.add_option(
        "-c", "--vcs",
        metavar=_("@info command line value placeholder", "VCS"),
        dest="version_control",
        help=_("@info command line option description",
               "Paths are under version control by given VCS; "
               "can be one of: %(vcslist)s.",
               vcslist=format_item_list(showvcs)))
    opars.add_option(
        "--list-options",
        action="store_true", dest="list_options", default=False,
        help=_("@info command line option description",
               "List the names of available options."))
    opars.add_option(
        "--list-vcs",
        action="store_true", dest="list_vcs", default=False,
        help=_("@info command line option description",
               "List the keywords of known version control systems."))
    opars.add_option(
        "-n", "--no-merge",
        action="store_false", dest="do_merge", default=def_do_merge,
        help=_("@info command line option description",
               "Do not try to indirectly pair messages by merging catalogs."))
    opars.add_option(
        "-o", "--output",
        metavar=_("@info command line value placeholder", "POFILE"),
        dest="output",
        help=_("@info command line option description",
               "Output diff catalog to a file instead of stdout."))
    opars.add_option(
        "-p", "--paired-only",
        action="store_true", dest="paired_only", default=False,
        help=_("@info command line option description",
               "When two directories are diffed, ignore catalogs which "
               "are not present in both directories."))
    opars.add_option(
        "-q", "--quiet",
        action="store_true", dest="quiet", default=False,
        help=_("@info command line option description",
               "Do not display any progress info."))
    opars.add_option(
        "-Q", "--quick",
        action="store_true", dest="quick", default=False,
        help=_("@info command line option description",
               "Equivalent to %(opt)s.",
               opt="-bns"))
    opars.add_option(
        "-r", "--revision",
        metavar=_("@info command line value placeholder", "REV1[:REV2]"),
        dest="revision",
        help=_("@info command line option description",
               "Revision from which to diff to current working copy, "
               "or from first to second revision (if VCS is given)."))
    opars.add_option(
        "-s", "--strip-headers",
        action="store_true", dest="strip_headers", default=False,
        help=_("@info command line option description",
               "Do not diff headers and do not write out the top header "
               "(resulting output cannot be used as patch)."))
    opars.add_option(
        "-U", "--update-effort",
        action="store_true", dest="update_effort", default=False,
        help=_("@info command line option description",
               "Instead of outputting the diff, calculate and output "
               "an estimate of the effort that was needed to update "
               "the translation from old to new paths. "
               "Ignores %(opt1)s and %(opt1)s options.",
               opt1="-b", opt2="-n"))
    add_cmdopt_colors(opars)

    (op, free_args) = opars.parse_args(str_to_unicode(sys.argv[1:]))

    if op.list_options:
        report(list_options(opars))
        sys.exit(0)
    if op.list_vcs:
        report("\n".join(showvcs))
        sys.exit(0)

    # Could use some speedup.
    try:
        import psyco
        psyco.full()
    except ImportError:
        pass

    set_coloring_globals(ctype=op.coloring_type, outdep=(not op.raw_colors))

    if op.quick:
        op.do_merge = False
        op.skip_obsolete = True
        op.strip_headers = True

    # Create VCS.
    vcs = None
    if op.version_control:
        if op.version_control not in available_vcs(flat=True):
            error_wcl(_("@info",
                        "Unknown VCS '%(vcs)s' selected.",
                        vcs=op.version_control))
        vcs = make_vcs(op.version_control)

    # Sanity checks on paths.
    paths = free_args
    if not vcs:
        if len(paths) != 2:
            error_wcl(_("@info",
                        "Exactly two paths are needed for diffing."))
        for path in paths:
            if not os.path.exists(path):
                error_wcl("path does not exist: %s" % path)
        p1, p2 = paths
        if (not (   (os.path.isfile(p1) and (os.path.isfile(p2)))
                 or (os.path.isdir(p1) and (os.path.isdir(p2))))
        ):
            error_wcl(_("@info",
                        "Both paths must be either files or directories."))
    else:
        # Default to current working dir if no paths given.
        paths = paths or ["."]
        for path in paths:
            if not os.path.exists(path):
                error_wcl(_("@info",
                            "Path '%(path)s' does not exist.",
                            path=path))
            if not vcs.is_versioned(path):
                error_wcl(_("@info",
                            "Path '%(path)s' is not under version control.",
                            path=path))

    # Collect and pair PO files in given paths.
    # Each pair specification is in the form of
    # ((path1, path2), (vpath1, vpath2))
    # where path* are the real paths, and vpath* the visual paths to be
    # presented in diff output.
    if not vcs:
        fpairs = collect_file_pairs(paths[0], paths[1], op.paired_only)
        pspecs = [(x, x) for x in fpairs]
    else:
        lst = op.revision and op.revision.split(":", 1) or []
        if len(lst) > 2:
            error_wcl(_("@info",
                        "Too many revisions given: %(revlist)s.",
                        revspec=format_item_list(lst)))
        elif len(lst) == 2:
            revs = lst # diff between revisions
        elif len(lst) == 1:
            revs = [lst[0], None] # diff from revision to working copy
        else:
            revs = ["", None] # diff from head to working copy
            # Replace original paths with modified/added catalogs.
            paths_nc = []
            for path in paths:
                for path in vcs.to_commit(path):
                    if path.endswith(".po") or path.endswith(".pot"):
                        paths_nc.append(path)
            paths = paths_nc
            paths.sort()
        pspecs = collect_pspecs_from_vcs(vcs, paths, revs, op.paired_only)

    if not op.update_effort:
        ecat, ndiffed = diff_pairs(pspecs, op.do_merge,
                                   colorize=(not op.output),
                                   shdr=op.strip_headers,
                                   noobs=op.skip_obsolete,
                                   quiet=op.quiet)
        if ndiffed > 0:
            hmsgctxt = ecat.header.get_field_value(EDST.hmsgctxt_field)
            lines = []
            msgs = list(ecat)
            if not op.strip_headers:
                msgs.insert(0, ecat.header.to_msg())
            for msg in msgs:
                if op.strip_headers and msg.msgctxt == hmsgctxt:
                    sepl = []
                    sepl += [msg.manual_comment[0]]
                    sepl += msg.msgid.split("\n")[:2]
                    lines.extend(["# %s\n" % x for x in sepl])
                    lines.append("\n")
                else:
                    lines.extend(msg.to_lines(force=True, wrapf=ecat.wrapf()))
            diffstr = cjoin(lines)[:-1] # remove last newline
            if op.output:
                file = open(op.output, "w")
                file.write(diffstr.encode(ecat.encoding()))
                file.close()
            else:
                report(diffstr)
    else:
        updeff = pairs_update_effort(pspecs, quiet=op.quiet)
        ls = []
        for kw, desc, val, fmtval in updeff:
            ls.append(_("@info",
                        "%(quantity)s: %(value)s",
                        quantity=desc, value=fmtval))
        report("\n".join(ls))

    # Clean up.
    cleanup_tmppaths()


def diff_pairs (pspecs, merge,
                colorize=False, wrem=True, wadd=True, shdr=False, noobs=False,
                quiet=False):

    # Create diffs of messages.
    # Note: Headers will be collected and diffed after all messages,
    # to be able to check if any decoration to their message keys is needed.
    wrappings = {}
    ecat = Catalog("", create=True, monitored=False)
    hspecs = []
    ndiffed = 0
    update_progress = None
    if len(pspecs) > 1 and not quiet:
        update_progress = init_file_progress([vp[1] for fp, vp in pspecs],
                            addfmt=t_("@info:progress", "Diffing: %(file)s"))
    for fpaths, vpaths in pspecs:
        upprogf = None
        if update_progress:
            upprogf = lambda: update_progress(vpaths[1])
            upprogf()
        # Quick check if files are binary equal.
        if fpaths[0] and fpaths[1] and filecmp.cmp(*fpaths):
            continue
        cats = []
        for fpath in fpaths:
            try:
                cats.append(Catalog(fpath, create=True, monitored=False))
            except:
                error_wcl(_("@info",
                            "Cannot parse catalog '%(file)s'.",
                            file=fpath), norem=[fpath])
        tpos = len(ecat)
        cndiffed = diff_cats(cats[0], cats[1], ecat,
                             merge, colorize, wrem, wadd, noobs, upprogf)
        hspecs.append(([not x.created() and x.header or None
                        for x in cats], vpaths, tpos, cndiffed))
        ndiffed += cndiffed
        # Collect and count wrapping policy used for to-catalog.
        wrapping = cats[1].wrapping()
        if wrapping not in wrappings:
            wrappings[wrapping] = 0
        wrappings[wrapping] += 1
    if update_progress:
        update_progress()

    # Find appropriate length of context for header messages.
    hmsgctxt = get_msgctxt_for_headers(ecat)
    init_ediff_header(ecat.header, hmsgctxt=hmsgctxt)

    # Create diffs of headers.
    # If some of the messages were diffed,
    # header must be added even if there is no difference.
    incpos = 0
    for hdrs, vpaths, pos, cndiffed in hspecs:
        ehmsg, anydiff = diff_hdrs(hdrs[0], hdrs[1], vpaths[0], vpaths[1],
                                   hmsgctxt, ecat, colorize)
        if anydiff or cndiffed:
            ecat.add(ehmsg, pos + incpos)
            incpos += 1
    # Add diffed headers to total count only if header stripping not in effect.
    if not shdr:
        ndiffed += incpos

    # Set the most used wrapping policy for the ediff catalog.
    if wrappings:
        wrapping = sorted(wrappings.items(), key=lambda x: x[1])[-1][0]
        ecat.set_wrapping(wrapping)
        if wrapping is not None:
            ecat.header.set_field(u"X-Wrapping", u", ".join(wrapping))

    return ecat, ndiffed


# Collect and pair catalogs as list [(fpath1, fpath2)].
# Where a pair cannot be found, empty string is given for path
# (unless paired_only is True, when non-paired catalogs are ignored).
def collect_file_pairs (dpath1, dpath2, paired_only):

    if os.path.isfile(dpath1):
        return [(dpath1, dpath2)]

    bysub1, bysub2 = map(collect_and_split_fpaths, (dpath1, dpath2))

    # Try to pair files by subdirectories.
    # FIXME: Can and should anything smarter be done?
    fpairs = []
    subdirs = list(set(bysub1.keys() + bysub2.keys()))
    subdirs.sort()
    for subdir in subdirs:
        flinks1 = bysub1.get(subdir, {})
        flinks2 = bysub2.get(subdir, {})
        filenames = list(set(flinks1.keys() + flinks2.keys()))
        filenames.sort()
        for filename in filenames:
            fpath1 = flinks1.get(filename, "")
            fpath2 = flinks2.get(filename, "")
            if not paired_only or (fpath1 and fpath2):
                fpairs.append((fpath1, fpath2))

    return fpairs


# Collect all catalog paths in given root, and construct mapping
# {subdir: {filename: path}}, where subdir is relative to root.
def collect_and_split_fpaths (dpath):

    dpath = dpath.rstrip(os.path.sep) + os.path.sep
    fpaths = collect_catalogs(dpath)
    bysub = {}
    for fpath in fpaths:
        if not fpath.startswith(dpath):
            error_wcl(_("@info",
                        "Internal problem with path collection (200)."))
        subdir = os.path.dirname(fpath[len(dpath):])
        if subdir not in bysub:
            bysub[subdir] = {}
        bysub[subdir][os.path.basename(fpath)] = fpath

    return bysub


def collect_pspecs_from_vcs (vcs, paths, revs, paired_only):

    pspecs = []
    # FIXME: Use tempfile module.
    expref = "/tmp/poediff-export-"
    exind = 0
    for path in paths:
        expaths = {}
        for rev in revs:
            if rev is None:
                expaths[rev] = path
            else:
                expath = expref + "%d-%d-%s" % (os.getpid(), exind, rev)
                exind += 1
                if os.path.isfile(path):
                    expath += ".po"
                if not vcs.export(path, rev or None, expath):
                    error_wcl(_("@info",
                                "Cannot export path '%(path)s' "
                                "in revision '%(rev)s'.",
                                path=path, rev=rev))
                record_tmppath(expath)
                expaths[rev] = expath
        expaths = [os.path.normpath(expaths[x]) for x in revs]
        fpairs = collect_file_pairs(expaths[0], expaths[1], paired_only)
        for fpair in fpairs:
            fpaths = []
            vpaths = []
            for fpath, expath, rev in zip(fpair, expaths, revs):
                if rev is not None:
                    if not fpath:
                        fpath_m = ""
                    elif os.path.isdir(path):
                        fpath_m = fpath[len(expath) + len(os.path.sep):]
                        fpath_m = os.path.join(path, fpath_m)
                    else:
                        fpath_m = path
                    rev_m = rev or vcs.revision(path)
                    vpath = fpath_m + EDST.filerev_sep + rev_m
                else:
                    vpath = fpath
                fpaths.append(fpath)
                vpaths.append(vpath)
            pspecs.append((fpaths, vpaths))

    return pspecs


def pairs_update_effort (pspecs, quiet=False):

    update_progress = None
    if len(pspecs) > 1 and not quiet:
        update_progress = init_file_progress([vp[1] for fp, vp in pspecs],
                            addfmt=t_("@info:progress", "Diffing: %(file)s"))
    nntw_total = 0.0
    for fpaths, vpaths in pspecs:
        upprogf = None
        if update_progress:
            upprogf = lambda: update_progress(vpaths[1])
            upprogf()
        # Quick check if files are binary equal.
        if fpaths[0] and fpaths[1] and filecmp.cmp(*fpaths):
            continue
        cats = []
        for fpath in fpaths:
            try:
                cats.append(Catalog(fpath, create=True, monitored=False))
            except:
                error_wcl(_("@info",
                            "Cannot parse catalog '%(file)s'.",
                            file=fpath), norem=[fpath])
        nntw = cats_update_effort(cats[0], cats[1], upprogf)
        nntw_total += nntw
    if update_progress:
        update_progress()

    updeff = [
        ("nntw", _("@item", "nominal newly translated words"),
         nntw_total, "%.0f" % nntw_total),
    ]
    return updeff


# Cleanup of temporary paths.
_tmppaths = set()

def record_tmppath (path):

    _tmppaths.add(path)


def cleanup_tmppaths (norem=set()):

    for path in _tmppaths:
        if path in norem:
            continue
        if os.path.isfile(path):
            os.unlink(path)
        elif os.path.isdir(path):
            shutil.rmtree(path)


def error_wcl (msg, norem=set()):

    if not isinstance(norem, set):
        norem = set(norem)
    cleanup_tmppaths(norem)
    error(msg)


if __name__ == '__main__':
    exit_on_exception(main, cleanup_tmppaths)
