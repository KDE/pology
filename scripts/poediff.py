#!/usr/bin/env python
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
import time

import fallback_import_paths

from pology import version, _, n_
from pology.catalog import Catalog
from pology.message import MessageUnsafe
from pology.colors import ColorOptionParser, set_coloring_globals, cjoin
import pology.config as pology_config
from pology.fsops import str_to_unicode, collect_catalogs
from pology.diff import msg_ediff
from pology.merge import merge_pofile
from pology.report import error, warning, report, format_item_list
from pology.report import list_options
from pology.stdcmdopt import add_cmdopt_colors
from pology.vcs import available_vcs, make_vcs

from posummit import fuzzy_match_source_files


_hmsgctxt_field = u"X-Ediff-Header-Context" # by spec
_hmsgctxt_el = u"~" # by spec
_filerev_sep = u" <<< " # by spec


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

    # Create the diff.
    ecat, ndiffed = diff_pairs(pspecs, op.do_merge,
                               colorize=(not op.output), shdr=op.strip_headers,
                               noobs=op.skip_obsolete)

    # Write out the diff, if any messages diffed.
    if ndiffed > 0:
        hmsgctxt = ecat.header.get_field_value(_hmsgctxt_field)
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
            file.write(diffstr.encode(ecat.encoding))
            file.close()
        else:
            report(diffstr)

    # Clean up.
    cleanup_tmppaths()


def diff_pairs (pspecs, merge,
                colorize=False, wrem=True, wadd=True, shdr=False, noobs=False):

    # Create diffs of messages.
    # Note: Headers will be collected and diffed after all messages,
    # to be able to check if any decoration to their message keys is needed.
    wrappings = {}
    ecat = Catalog("", create=True, monitored=False)
    hspecs = []
    ndiffed = 0
    for fpaths, vpaths in pspecs:
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
                             merge, colorize, wrem, wadd, noobs)
        hspecs.append(([not x.created() and x.header or None
                        for x in cats], vpaths, tpos, cndiffed))
        ndiffed += cndiffed
        # Collect and count wrapping policy used for to-catalog.
        wrapping = cats[1].wrapping()
        if wrapping not in wrappings:
            wrappings[wrapping] = 0
        wrappings[wrapping] += 1

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


def init_ediff_header (ehdr, hmsgctxt=_hmsgctxt_el, extitle=None):

    cfgsec = pology_config.section("user")
    user = cfgsec.string("name", "J. Random Translator")
    email = cfgsec.string("email", None)

    listtype = type(ehdr.title)

    if extitle is not None:
        title = u"+- ediff (%s) -+" % extitle
    else:
        title = u"+- ediff -+"
    ehdr.title = listtype([title])

    year = time.strftime("%Y")
    if email:
        author = u"%s <%s>, %s." % (user, email, year)
    else:
        author = u"%s, %s." % (user, year)
    #ehdr.author = listtype([author])
    ehdr.author = listtype([])

    ehdr.copyright = u""
    ehdr.license = u""
    ehdr.comment = listtype()

    rfv = ehdr.replace_field_value # shortcut

    rfv("Project-Id-Version", u"ediff")
    ehdr.remove_field("Report-Msgid-Bugs-To")
    ehdr.remove_field("POT-Creation-Date")
    rfv("PO-Revision-Date", unicode(time.strftime("%Y-%m-%d %H:%M%z")))
    enc = "UTF-8" # strictly, input catalogs may have different encodings
    rfv("Content-Type", u"text/plain; charset=%s" % enc)
    rfv("Content-Transfer-Encoding", u"8bit")
    if email:
        translator = u"%s <%s>" % (user, email)
    else:
        translator = u"%s" % user
    rfv("Last-Translator", translator)
    rfv("Language-Team", u"Differs")
    # FIXME: Something smarter? (Not trivial.)
    ehdr.remove_field("Plural-Forms")

    # Context of header messages in the catalog.
    ehdr.set_field(_hmsgctxt_field, hmsgctxt)


def get_msgctxt_for_headers (cat):

    hmsgctxt = u""
    good = False
    while not good:
        hmsgctxt += _hmsgctxt_el
        good = True
        for msg in cat:
            if hmsgctxt == msg.msgctxt:
                good = False
                break

    return hmsgctxt


_msg_curr_fields = [
    "msgctxt", "msgid", "msgid_plural",
]
_msg_prev_fields = [x + "_previous" for x in _msg_curr_fields]
_msg_currprev_fields = zip(_msg_curr_fields, _msg_prev_fields)
_msg_prevcurr_fields = zip(_msg_prev_fields, _msg_curr_fields)


def diff_cats (cat1, cat2, ecat,
               merge=True, colorize=False, wrem=True, wadd=True, noobs=False):

    # Remove obsolete messages if they are not to be diffed.
    if noobs:
        for cat in (cat1, cat2):
            rmobs_no_sync(cat)

    # Clean up inconsistencies in messages.
    for cat in (cat1, cat2):
        for msg in cat:
            msg_cleanup(msg)

    # Delay inverting of catalogs until necessary.
    def icat_w (cat, icat_pack):
        if icat_pack[0] is None:
            #print "===> inverting: %s" % cat.filename
            icat = Catalog("", create=True, monitored=False)
            for msg in cat:
                imsg = msg_invert_cp(msg)
                if imsg not in icat:
                    icat.add_last(imsg)
            icat_pack[0] = icat
        return icat_pack[0]

    icat1_pack = [None]
    icat1 = lambda: icat_w(cat1, icat1_pack)

    icat2_pack = [None]
    icat2 = lambda: icat_w(cat2, icat2_pack)

    # Delay merging of catalogs until necessary.
    def mcat_w (cat1, cat2, mcat_pack):
        if mcat_pack[0] is None:
            #print "===> merging: %s -> %s" % (cat1.filename, cat2.filename)
            # Merge is done if requested and both catalogs exist.
            if merge and not cat1.created() and not cat2.created():
                mcat_pack[0] = merge_pofile(cat1.filename, cat2.filename,
                                            getcat=True, monitored=False,
                                            quiet=True, abort=True)
                if noobs:
                    rmobs_no_sync(mcat_pack[0])
            else:
                mcat_pack[0] = {} # only tested for membership
        return mcat_pack[0]

    mcat12_pack = [None]
    mcat12 = lambda: mcat_w(cat1, cat2, mcat12_pack)

    mcat21_pack = [None]
    mcat21 = lambda: mcat_w(cat2, cat1, mcat21_pack)

    # Pair messages:
    # - first try to find an old message for each new
    # - then try to find a new message for each unpaired old
    # - finally add remaining unpaired messages to be diffed with None
    msgs1_paired = set()
    msgs2_paired = set()
    dpairs = []

    for msg2 in cat2:
        msg1 = get_msg_pair(msg2, cat1, icat1, mcat12)
        if msg1 and msg1 not in msgs1_paired:
            # Record pairing.
            msgs1_paired.add(msg1)
            msgs2_paired.add(msg2)
            dpairs.append((msg1, msg2))

    for msg1 in cat1:
        if msg1 in msgs1_paired:
            continue
        msg2 = get_msg_pair(msg1, cat2, icat2, mcat21)
        if msg2 and msg2 not in msgs2_paired:
            # Record pairing.
            msgs1_paired.add(msg1)
            msgs2_paired.add(msg2)
            dpairs.append((msg1, msg2))

    for msg2 in (wadd and cat2 or []):
        if msg2 not in msgs2_paired:
            dpairs.append((None, msg2))

    for msg1 in (wrem and cat1 or []):
        if msg1 not in msgs1_paired:
            dpairs.append((msg1, None))


    # Order the pairings such that they follow order of messages in
    # the new catalog wherever the new message exists.
    # For the unpaired old messages, do heuristic analysis of any
    # renamings of source files, and then insert diffed messages
    # according to source references of old messages.
    dpairs_by2 = [x for x in dpairs if x[1]]
    dpairs_by2.sort(key=lambda x: x[1].refentry)
    dpairs_by1 = [x for x in dpairs if not x[1]]
    fnsyn = None
    if dpairs_by1:
        fnsyn = fuzzy_match_source_files(cat2, [cat1])

    # Make the diffs.
    # Must not add diffed messages directly to global ediff catalog,
    # because then heuristic insertion would throw them all over.
    # Instead add to local ediff catalog, then copy in order to global.
    ndiffed = 0
    lecat = Catalog("", create=True, monitored=False)
    for cdpairs, cfnsyn in ((dpairs_by2, None), (dpairs_by1, fnsyn)):
        for msg1, msg2 in cdpairs:
            ndiffed += add_msg_diff(msg1, msg2, lecat, colorize, cfnsyn)
    for emsg in lecat:
        ecat.add(emsg, len(ecat))

    return ndiffed


# Determine the pair of the message in the catalog, if any.
def get_msg_pair (msg, ocat, icat, mcat):

    # If no direct match, try pivoting around any previous fields.
    # Iterate through test catalogs in this order,
    # to delay construction of those which are not necessary.
    for tcat in (ocat, icat, mcat):
        if callable(tcat):
            tcat = tcat()
        omsg = tcat.get(msg)
        if not omsg and msg.fuzzy:
            omsg = tcat.get(msg_invert_cp(msg))
        if tcat is not ocat: # tcat is one of pivot catalogs
            omsg = ocat.get(msg_invert_cp(omsg))
        if omsg:
            break

    return omsg


# Out of a message with previous fields,
# construct a lightweight message with previous and current fields exchanged.
# If there are no previous fields, return None.
# To be used only for lookups
def msg_invert_cp (msg):

    if msg is None:
        return None

    lmsg = MessageUnsafe()
    if has_prev_fields(msg):
        # Need to invert only key fields, but whadda hell.
        for fcurr, fprev in _msg_currprev_fields:
            setattr(lmsg, fcurr, msg.get(fprev))
            setattr(lmsg, fprev, msg.get(fcurr))
    else:
        return lmsg.set_key(msg)

    return lmsg


def add_msg_diff (msg1, msg2, ecat, colorize, fnsyn=None):

    # Skip diffing if old and new messages are "same".
    if msg1 and msg2 and msg1.inv == msg2.inv:
        return 0

    # Create messages for special pairings.
    msg1_s, msg2_s = create_special_diff_pair(msg1, msg2)

    # Create the diff.
    tmsg = msg2 or msg1
    emsg = msg2_s or msg1_s
    if emsg is tmsg:
        emsg = MessageUnsafe(tmsg)
    emsg = msg_ediff(msg1_s, msg2_s, emsg=emsg, ecat=ecat, colorize=colorize)

    # Add to the diff catalog.
    if fnsyn is None:
        ecat.add(emsg, len(ecat))
    else:
        ecat.add(emsg, srefsyn=fnsyn)

    return 1


def create_special_diff_pair (msg1, msg2):

    msg1_s, msg2_s = msg1, msg2

    if not msg1 or not msg2:
        # No special cases if either message non-existant.
        pass

    # Cases f-nf-*.
    elif msg1.fuzzy and has_prev_fields(msg1) and not msg2.fuzzy:
        # Case f-nf-ecc.
        if msg_eq_fields(msg1, msg2, _msg_curr_fields):
            msg1_s = MessageUnsafe(msg1)
            msg_copy_fields(msg1, msg1_s, _msg_prevcurr_fields)
            msg_null_fields(msg1_s, _msg_prev_fields)
        # Case f-nf-necc.
        else:
            msg1_s = MessageUnsafe(msg1)
            msg2_s = MessageUnsafe(msg2)
            msg_copy_fields(msg1, msg1_s, _msg_prevcurr_fields)
            msg_copy_fields(msg1, msg2_s, _msg_currprev_fields)

    # Cases nf-f-*.
    elif not msg1.fuzzy and msg2.fuzzy and has_prev_fields(msg2):
        # Case nf-f-ecp.
        if msg_eq_fields(msg1, msg2, _msg_currprev_fields):
            msg2_s = MessageUnsafe(msg2)
            msg_null_fields(msg2_s, _msg_prev_fields)
        # Case nf-f-necp.
        else:
            msg1_s = MessageUnsafe(msg1)
            msg2_s = MessageUnsafe(msg2)
            msg_copy_fields(msg2, msg1_s, _msg_prev_fields)
            msg_copy_fields(msg2, msg2_s, _msg_currprev_fields)

    return msg1_s, msg2_s


def diff_hdrs (hdr1, hdr2, vpath1, vpath2, hmsgctxt, ecat, colorize):

    hmsg1, hmsg2 = [x and MessageUnsafe(x.to_msg()) or None
                    for x in (hdr1, hdr2)]

    ehmsg = hmsg2 and MessageUnsafe(hmsg2) or None
    ehmsg, dr = msg_ediff(hmsg1, hmsg2, emsg=ehmsg, ecat=ecat,
                          colorize=colorize, diffr=True)
    if dr == 0.0:
        # Revert to empty message if no difference between headers.
        ehmsg = MessageUnsafe()

    # Add visual paths as old/new segments into msgid.
    vpaths = [vpath1, vpath2]
    # Always use slashes as path separator, for portability of ediffs.
    vpaths = [x.replace(os.path.sep, "/") for x in vpaths]
    ehmsg.msgid = u"- %s\n+ %s" % tuple(vpaths)
    # Add trailing newline if msgstr has it, again to appease msgfmt.
    if ehmsg.msgstr[0].endswith("\n"):
        ehmsg.msgid += "\n"

    # Add context identifying the diffed message as header.
    ehmsg.msgctxt = hmsgctxt

    # Add conspicuous separator at the top of the header.
    ehmsg.manual_comment.insert(0, u"=" * 76)

    return ehmsg, dr > 0.0


# Remove previous fields if inconsistent with the message in total.
def msg_cleanup (msg):

    # Non-fuzzy messages should have no previous fields.
    # msgid_previous must be present, or there must be no previous fields.
    if not msg.fuzzy or msg.msgid_previous is None:
        for field in _msg_prev_fields:
            if msg.get(field) is not None:
                setattr(msg, field, None)


def msg_eq_fields (m1, m2, fields):

    if (m1 is None) != (m2 is None):
        return False
    elif m1 is None and m2 is None:
        return True

    for field in fields:
        if not isinstance(field, tuple):
            field = (field, field)
        if m1.get(field[0]) != m2.get(field[1]):
            return False

    return True


def has_prev_fields (m):

    return m.msgid_previous is not None


def msg_copy_fields (m1, m2, fields):

    if m1 is None:
        m1 = MessageUnsafe()

    for field in fields:
        if not isinstance(field, tuple):
            field = (field, field)
        setattr(m2, field[1], m1.get(field[0]))


def msg_null_fields (m, fields):

    for field in fields:
        setattr(m, field, None)


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
                    vpath = fpath_m + _filerev_sep + rev_m
                else:
                    vpath = fpath
                fpaths.append(fpath)
                vpaths.append(vpath)
            pspecs.append((fpaths, vpaths))

    return pspecs


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


def rmobs_no_sync (cat):

    for msg in cat:
        if msg.obsolete:
            cat.remove_on_sync(msg)
    cat.sync_map()


if __name__ == '__main__':
    try:
        main()
    except:
        cleanup_tmppaths()
        raise
