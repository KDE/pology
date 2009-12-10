#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Patch PO files from an embedded diff.

The concept of embedded diffing for PO files is described in detail at
U{http://techbase.kde.org/Localization/Tools/Pology/PO_Embedded_Diffing}.
The usage of this script is also explained in the article.

@warning: This module is a script for end-use. No exposed functionality
should be considered public API, it is subject to change without notice.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import fallback_import_paths

import sys
import os
import locale
import re
from optparse import OptionParser
from tempfile import NamedTemporaryFile

from pology.misc.report import error, warning, report
from pology.misc.msgreport import error_on_msg, warning_on_msg
import pology.misc.config as pology_config
from pology.misc.fsops import str_to_unicode, mkdirpath, collect_catalogs
from pology.file.catalog import Catalog
from pology.file.message import Message, MessageUnsafe
from pology.file.header import Header
from pology.misc.diff import msg_ediff, msg_ediff_to_new, msg_ediff_to_old

import pology.scripts.poediff as ED

_flag_ediff = u"ediff"
_flag_ediff_to_cur = u"%s-to-cur" % _flag_ediff
_flag_ediff_to_new = u"%s-to-new" % _flag_ediff
_flag_ediff_no_match = u"%s-no-match" % _flag_ediff
_flags_all = (
    _flag_ediff,
    _flag_ediff_to_cur, _flag_ediff_to_new,
    _flag_ediff_no_match,
)


def main ():

    locale.setlocale(locale.LC_ALL, "")

    # Get defaults for command line options from global config.
    cfgsec = pology_config.section("poepatch")
    def_do_merge = cfgsec.boolean("merge", True)
    def_use_psyco = cfgsec.boolean("use-psyco", True)

    # Setup options and parse the command line.
    usage = u"""
    %prog [OPTIONS] <EDIFF
    %prog -u [OPTIONS] PATHS...
""".rstrip()
    description = u"""
Apply embedded diff of PO files as patch.
""".strip()
    version = u"""
%prog (Pology) experimental
Copyright © 2009 Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
""".strip()

    opars = OptionParser(usage=usage, description=description, version=version)
    opars.add_option(
        "-p", "--strip", metavar="NUM",
        dest="strip",
        help="strip the smallest prefix containing NUM leading slashes from "
             "each file name found in the ediff file (like in patch(1)); "
             "if not given, only the base name of each file is taken")
    opars.add_option(
        "-d", "--directory", metavar="DIR",
        dest="directory",
        help="append this directory path to any resolved target file path "
             "(similar to patch(1))")
    opars.add_option(
        "-a", "--aggressive",
        action="store_true", dest="aggressive", default=False,
        help="apply every message to a paired message in the target file, "
             "irrespective of whether its non-pairing parts match too")
    opars.add_option(
        "-e", "--embed",
        action="store_true", dest="embed", default=False,
        help="instead of applying resolved newer version of the message, "
             "add the full embedded diff into the target file")
    opars.add_option(
        "-u", "--unembed",
        action="store_true", dest="unembed", default=False,
        help="instead of applying a patch, resolve all embedded differences "
             "in given paths to newer versions of messages")
    opars.add_option(
        "-n", "--no-merge",
        action="store_false", dest="do_merge", default=def_do_merge,
        help="do not try to indirectly pair messages by merging catalogs")
    opars.add_option(
        "-i", "--input", metavar="FILE",
        dest="input",
        help="get embedded difference from file instead of stdout")
    opars.add_option(
        "--no-psyco",
        action="store_false", dest="use_psyco", default=def_use_psyco,
        help="do not try to use Psyco specializing compiler")

    (op, free_args) = opars.parse_args(str_to_unicode(sys.argv[1:]))

    # Could use some speedup.
    if op.use_psyco:
        try:
            import psyco
            psyco.full()
        except ImportError:
            pass

    if not op.unembed:
        if free_args:
            error("too many arguments in command line: %s"
                   % " ".join(free_args))
        if op.strip and not op.strip.isdigit():
            error("option %s expect integer argument" % "--strip")
        apply_ediff(op)
    else:
        paths = []
        for path in free_args:
            if not os.path.exists(path):
                warning("path does not exist: %s" % path)
            if os.path.isdir(path):
                paths.extend(collect_catalogs(path))
            else:
                paths.append(path)
        for path in paths:
            unembed_ediff(path)


def apply_ediff (op):

    # Read the ediff PO.
    dummy_stream_path = "<stdin>"
    if op.input:
        if not os.path.isfile(op.input):
            error("path not a file or does not exist: %s" % op.input)
        edfpath = op.input
        readfh = None
    else:
        edfpath = dummy_stream_path
        readfh = sys.stdin
    try:
        ecat = Catalog(edfpath, monitored=False, readfh=readfh)
    except:
        error("error reading ediff: %s" % edfpath)

    # Split ediff by diffed catalog into original and new file paths,
    # header message, and ordinary messages.
    hmsgctxt = ecat.header.get_field_value(ED._hmsgctxt_field)
    if hmsgctxt is None:
        error("no header field '%s' in ediff" % ED._hmsgctxt_field)
    edsplits = []
    cehmsg = None
    smsgid = u"\x00"
    ecat.add_last(MessageUnsafe(dict(msgctxt=hmsgctxt, msgid=smsgid))) # sentry
    for emsg in ecat:
        if emsg.msgctxt == hmsgctxt:
            if cehmsg:
                # Record previous section.
                edsplits.append((fpaths, cehmsg, cemsgs))
                if emsg.msgid == smsgid: # end sentry, avoid parsing below
                    break

            # Mine original and new file paths out of header.
            fpaths = []
            for fpath in emsg.msgid.split("\n")[:2]:
                # Strip leading "+ "/"- "
                fpath = fpath[2:]
                # Convert to planform path separators.
                fpath = re.sub(r"/+", os.path.sep, fpath)
                # Remove revision indicator.
                p = fpath.find(ED._filerev_sep)
                if p >= 0:
                    fpath = fpath[:p]
                # Strip path and append directory as requested.
                if op.strip:
                    preflen = int(op.strip)
                    lst = fpath.split(os.path.sep, preflen)
                    if preflen + 1 == len(lst):
                        fpath = lst[preflen]
                    else:
                        fpath = os.path.basename(fpath)
                else:
                    fpath = os.path.basename(fpath)
                if op.directory and fpath:
                    fpath = os.path.join(op.directory, fpath)
                # All done.
                fpaths.append(fpath)

            cehmsg = emsg
            cemsgs = []
        else:
            cemsgs.append(emsg)

    # Prepare catalog for rejects and merges.
    rcat = Catalog("", create=True, monitored=False, wrapping=ecat.wrapping())
    ED.init_ediff_header(rcat.header, hmsgctxt=hmsgctxt, extitle="rejects")

    # Apply diff to catalogs.
    for fpaths, ehmsg, emsgs in edsplits:
        # Open catalog for patching.
        fpath1, fpath2 = fpaths
        if fpath1:
            # Diff from an existing catalog, open it.
            if not os.path.isfile(fpath1):
                warning("path '%s' not a file or does not exist, skipping"
                        % fpath1)
                continue
            try:
                cat = Catalog(fpath1)
            except:
                warning("error reading catalog '%s', skipping" % fpath1)
                continue
        elif fpath2:
            # New catalog added in diff, create it (or open if it exists).
            try:
                mkdirpath(os.path.dirname(fpath2))
                cat = Catalog(fpath2, create=True)
                if cat.created():
                    cat.set_wrapping(ecat.wrapping())
            except:
                if os.path.isfile(fpath2):
                    warning("error reading catalog '%s', skipping" % fpath1)
                else:
                    warning("cannot create catalog '%s', skipping" % fpath2)
                continue
        else:
            error("both catalogs in diff indicated not to exist")

        # Do not try to patch catalog with embedded differences
        # (i.e. previously patched using -e).
        if cat.header.get_field_value(ED._hmsgctxt_field) is not None:
            warning("catalog '%s' already contains embedded differences, "
                    "skipping" % cat.filename)
            continue

        # Do not try to patch catalog if the patch contains
        # unresolved split differences.
        if reduce(lambda r, x: r or _flag_ediff_to_new in x.flag,
                  emsgs, False):
            warning("patch for catalog '%s' contains unresolved "
                    "split differences, skipping" % cat.filename)
            continue

        # Patch the catalog.
        rejected_ehmsg = patch_header(cat, ehmsg, ecat, op)
        rejected_emsgs_flags = patch_messages(cat, emsgs, ecat, op)
        any_rejected = rejected_ehmsg or rejected_emsgs_flags
        if fpath2 or any_rejected:
            created = cat.created()
            if cat.sync():
                if not created:
                    if any_rejected and op.embed:
                        report("partially patched (E): %s" % cat.filename)
                    elif any_rejected:
                        report("partially patched: %s" % cat.filename)
                    elif op.embed:
                        report("patched (E): %s" % cat.filename)
                    else:
                        report("patched: %s" % cat.filename)
                else:
                    if op.embed:
                        report("created (E): %s" % cat.filename)
                    else:
                        report("created: %s" % cat.filename)
            else:
                pass #report("unchanged: %s" % cat.filename)
        else:
            os.unlink(fpath1)
            report("removed: %s" % fpath1)

        # If there were any rejects and reembedding is not in effect,
        # record the necessary to present them.
        if any_rejected and not op.embed:
            if not rejected_ehmsg:
                # Clean header diff.
                ehmsg.manual_comment = ehmsg.manual_comment[:1]
                ehmsg.msgstr[0] = u""
            rcat.add_last(ehmsg)
            for emsg, flag in rejected_emsgs_flags:
                # Reembed to avoid any conflicts.
                msg1, msg2, msg1_s, msg2_s = resolve_diff_pair(emsg)
                emsg = msg_ediff(msg1_s, msg2_s,
                                 emsg=msg2_s, ecat=rcat, enoctxt=hmsgctxt)
                if flag:
                    emsg.flag.add(flag)
                rcat.add_last(emsg)

    # If there were any rejects, write them out.
    if len(rcat) > 0:
        # Construct paths for embedded diffs of rejects.
        rsuff = "rej"
        if ecat.filename != dummy_stream_path:
            rpath = ecat.filename
            p = rpath.rfind(".")
            if p < 0:
                p = len(rpath)
            rpath = rpath[:p] + (".%s" % rsuff) + rpath[p:]
        else:
            rpath = "stdin.%s.po" % rsuff

        rcat.filename = rpath
        rcat.sync(force=True, noobsend=True)
        report("*** rejects: %s" % rcat.filename)


# Patch application types.
_pt_merge, _pt_insert, _pt_remove = range(3)

def patch_messages (cat, emsgs, ecat, options):

    # It may happen that a single message from original catalog
    # is paired with more than one from the diff
    # (e.g. single old translated message going into two new fuzzy).
    # Therefore paired messages must be tracked, to know if patched
    # message can be merged into the existing, or it must be inserted.
    pmsgkeys = set()

    # Triplets for splitting directly unapplicable patches into two.
    # Delay building of triplets until needed for the first time.
    striplets_pack = [None]
    def striplets ():
        if striplets_pack[0] is None:
            striplets_pack[0] = build_splitting_triplets(emsgs, cat, options)
        return striplets_pack[0]

    # Check whether diffs apply, and where and how if they do.
    rejected_emsgs_flags = []
    patch_specs = []
    for emsg in emsgs:
        pspecs = msg_apply_diff(cat, emsg, ecat, pmsgkeys, striplets)
        for pspec in pspecs:
            emsg_m, flag = pspec[:2]
            if flag == _flag_ediff or options.embed:
                patch_specs.append(pspec)
            if flag != _flag_ediff:
                rejected_emsgs_flags.append((emsg_m, flag))

    # Sort accepted patches by position of application.
    patch_specs.sort(key=lambda x: x[3])

    # Add accepted patches to catalog.
    incpos = 0
    for emsg, flag, typ, pos, msg1, msg2, msg1_s, msg2_s in patch_specs:
        if pos is not None:
            pos += incpos

        if options.embed:
            # Embedded diff may conflict one of the messages in catalog.
            # Make a new diff of special messages,
            # and embed them either into existing message in catalog,
            # or into new message.
            if typ == _pt_merge:
                tmsg = cat[pos]
                tpos = pos
            else:
                tmsg = MessageUnsafe(msg2 or {})
                tpos = None
            emsg = msg_ediff(msg1_s, msg2_s, emsg=tmsg, ecat=cat, eokpos=tpos)

        if 0:pass
        elif typ == _pt_merge:
            if not options.embed:
                cat[pos].set_inv(msg2)
            else:
                cat[pos].flag.add(flag)
        elif typ == _pt_insert:
            if not options.embed:
                cat.add(Message(msg2), pos)
            else:
                cat.add(Message(emsg), pos)
                cat[pos].flag.add(flag)
            incpos += 1
        elif typ == _pt_remove:
            if pos is None:
                continue
            if not options.embed:
                cat.remove(pos)
                incpos -= 1
            else:
                cat[pos].flag.add(flag)
        else:
            error_on_msg("internal: unknown patch type %d" % typ, emsg, ecat)

    return rejected_emsgs_flags


def msg_apply_diff (cat, emsg, ecat, pmsgkeys, striplets):

    msg1, msg2, msg1_s, msg2_s = resolve_diff_pair(emsg)

    # Try to select existing message from the original messages.
    # Order is important, should try first new, then old
    # (e.g. if an old fuzzy was resolved to new after diff was made).
    msg = None
    if msg2 and msg2 in cat:
        msg = cat[msg2]
    elif msg1 and msg1 in cat:
        msg = cat[msg1]

    patch_specs = []

    # Try to apply the patch.
    if msg_patchable(msg, msg1, msg2):
        # Patch can be directly applied.
        if msg1 and msg2:
            if msg.key not in pmsgkeys:
                typ = _pt_merge
                pos = cat.find(msg)
                pmsgkeys.add(msg.key)
            else:
                typ = _pt_insert
                pos, weight = cat.insertion_inquiry(msg2)
        elif msg2: # patch adds a message
            if msg:
                typ = _pt_merge
                pos = cat.find(msg)
                pmsgkeys.add(msg.key)
            else:
                typ = _pt_insert
                pos, weight = cat.insertion_inquiry(msg2)
        elif msg1: # patch removes a message
            if msg:
                typ = _pt_remove
                pos = cat.find(msg)
                pmsgkeys.add(msg.key)
            else:
                typ = _pt_remove
                pos = None # no position to remove from
        else:
            # Cannot happen.
            error_on_msg("neither old nor new message in diff exists",
                         emsg, ecat)
        patch_specs.append((emsg, _flag_ediff, typ, pos,
                            msg1, msg2, msg1_s, msg2_s))
    else:
        # Patch cannot be applied directly,
        # try to split into old-to-current and current-to-new diffs.
        split_found = False
        if callable(striplets):
            striplets = striplets() # delayed creation of splitting triplets
        for i in range(len(striplets)):
            m1_t, m1_ts, m2_t, m2_ts, m_t, m_ts1, m_ts2 = striplets[i]
            if msg1.inv == m1_t.inv and msg2.inv == m2_t.inv:
                striplets.pop(i) # remove to not slow further searches
                split_found = True
                break
        if split_found:
            # Construct new corresponding diffs.
            em_1c = msg_ediff(m1_ts, m_ts1, emsg=MessageUnsafe(m_t))
            em_c2 = msg_ediff(m_ts2, m2_ts, emsg=MessageUnsafe(m2_t))
            # Current-to-new can be merged or inserted,
            # and old-to-current is then inserted just before it.
            if m_t.key not in pmsgkeys:
                typ = _pt_merge
                pos = cat.find(m_t)
                pmsgkeys.add(m_t.key)
            else:
                typ = _pt_insert
                pos, weight = cat.insertion_inquiry(m2_t)
            # Order of adding patch specs here important for rejects file.
            patch_specs.append((em_1c, _flag_ediff_to_cur, _pt_insert, pos,
                                m1_t, m_t, m1_ts, m_ts1))
            patch_specs.append((em_c2, _flag_ediff_to_new, typ, pos,
                                m_t, m2_t, m_ts2, m2_ts))

    # The patch is totally rejected.
    # Will be inserted if reembedding requested, so compute insertion.
    if not patch_specs:
        typ = _pt_insert
        pos, weight = cat.insertion_inquiry(msg2)
        patch_specs.append((emsg, _flag_ediff_no_match, typ, pos,
                            msg1, msg2, msg1_s, msg2_s))

    return patch_specs


def msg_patchable (msg, msg1, msg2):

    # Check for cases where current message does not match old or new,
    # but there is a transformation that can also be cleanly merged.
    msg_m = msg
    if 0: pass

    # Old and new are translated, but current is fuzzy and has previous fields.
    # Transform current to its previous state, from which it may have became
    # fuzzy by merging with templates.
    elif (    msg and msg.fuzzy and ED.has_prev_fields(msg)
          and msg1 and not msg1.fuzzy and msg2 and not msg2.fuzzy
    ):
        msg_m = MessageUnsafe(msg)
        ED.msg_copy_fields(msg, msg_m, ED._msg_prevcurr_fields)
        ED.msg_null_fields(msg_m, ED._msg_prev_fields)
        msg_m.fuzzy = False

    # Old is None, new is translated, and current is untranslated.
    # Add translation of new to current, since it may have been added as
    # untranslated after merging with templates.
    elif msg and msg.untranslated and not msg1 and msg2 and msg2.translated:
        msg_m = MessageUnsafe(msg)
        ED.msg_copy_fields(msg2, msg_m, ["msgstr"])

    if msg1 and msg2:
        return msg and msg_m.inv in (msg1.inv, msg2.inv)
    elif msg2:
        return not msg or msg_m.inv == msg2.inv
    elif msg1:
        return not msg or msg_m.inv == msg1.inv
    else:
        return not msg


def resolve_diff_pair (emsg):

    # Recover old and new message according to diff.
    # Resolve into copies of ediff message, to preserve non-inv parts.
    emsg1 = MessageUnsafe(emsg)
    msg1_s = msg_ediff_to_old(emsg1, rmsg=emsg1)
    emsg2 = MessageUnsafe(emsg)
    msg2_s = msg_ediff_to_new(emsg2, rmsg=emsg2)

    # Resolve any special pairings.
    msg1, msg2 = msg1_s, msg2_s
    if not msg1_s or not msg2_s:
        # No special cases if either message non-existant.
        pass

    # Cases f-nf-*.
    elif msg1_s.fuzzy and not msg2_s.fuzzy:
        # Case f-nf-ecc.
        if (    not ED.has_prev_fields(msg2_s)
            and not ED.msg_eq_fields(msg1_s, msg2_s, ED._msg_curr_fields)
        ):
            msg1 = MessageUnsafe(msg1_s)
            ED.msg_copy_fields(msg1_s, msg1, ED._msg_currprev_fields)
            ED.msg_copy_fields(msg2_s, msg1, ED._msg_curr_fields)
        # Case f-nf-necc.
        elif ED.has_prev_fields(msg2_s):
            msg1 = MessageUnsafe(msg1_s)
            msg2 = MessageUnsafe(msg2_s)
            ED.msg_copy_fields(msg2_s, msg1, ED._msg_prevcurr_fields)
            ED.msg_null_fields(msg2, ED._msg_prev_fields)

    # Cases nf-f-*.
    elif not msg1_s.fuzzy and msg2_s.fuzzy:
        # Case nf-f-ecp.
        if (    not ED.has_prev_fields(msg1_s)
            and not ED.msg_eq_fields(msg1_s, msg2_s, ED._msg_curr_fields)
        ):
            msg2 = MessageUnsafe(msg2_s)
            ED.msg_copy_fields(msg1_s, msg2, ED._msg_currprev_fields)
        # Case nf-f-necp.
        elif ED.has_prev_fields(msg1_s):
            msg1 = MessageUnsafe(msg1_s)
            msg2 = MessageUnsafe(msg2_s)
            ED.msg_copy_fields(msg1_s, msg2, ED._msg_prev_fields)
            ED.msg_null_fields(msg1, ED._msg_prev_fields)

    return msg1, msg2, msg1_s, msg2_s


def build_splitting_triplets (emsgs, cat, options):

    # Create catalogs of old and new messages.
    cat1 = Catalog("", create=True, monitored=False)
    cat2 = Catalog("", create=True, monitored=False)
    for emsg in emsgs:
        msg1, msg2, msg1_s, msg2_s = resolve_diff_pair(emsg)
        if msg1:
            cat1.add_last(msg1)
        if msg2:
            cat2.add_last(msg2)
    # Make headers same, to avoid any diffs there.
    cat1.header = cat.header
    cat2.header = cat.header

    # Write created catalogs to disk if
    # msgmerge may be used on files during diffing.
    if options.do_merge:
        tmpfs = [] # to avoid garbage collection until the function returns
        for tcat, tsuff in ((cat1, "1"), (cat2, "2")):
            tmpf = NamedTemporaryFile(prefix="poepatch-split-%s-" % tsuff,
                                      suffix=".po")
            tmpfs.append(tmpf)
            tcat.filename = tmpf.name
            tcat.sync(force=True)

    # Create the old-to-current and current-to-new diffs.
    ecat_1c = Catalog("", create=True, monitored=False)
    ED.diff_cats(cat1, cat, ecat_1c, options.do_merge, wadd=False, wrem=False)
    ecat_c2 = Catalog("", create=True, monitored=False)
    ED.diff_cats(cat, cat2, ecat_c2, options.do_merge, wadd=False, wrem=False)

    # Mine splitting triplets out of diffs.
    sdoublets_1c = {}
    for emsg in ecat_1c:
        m1_t, m_t, m1_ts, m_ts1 = resolve_diff_pair(emsg)
        sdoublets_1c[m_t.key] = [m1_t, m1_ts, m_t, m_ts1]
    sdoublets_c2 = {}
    for emsg in ecat_c2:
        m_t, m2_t, m_ts2, m2_ts = resolve_diff_pair(emsg)
        sdoublets_c2[m_t.key] = [m_t, m_ts2, m2_t, m2_ts]
    common_keys = set(sdoublets_1c).intersection(sdoublets_c2)
    striplets = []
    for key in common_keys:
        m1_t, m1_ts, m_t, m_ts1 = sdoublets_1c[key]
        m_t, m_ts2, m2_t, m2_ts = sdoublets_c2[key]
        striplets.append((m1_t, m1_ts, m2_t, m2_ts, m_t, m_ts1, m_ts2))

    return striplets


def patch_header (cat, ehmsg, ecat, options):

    if not ehmsg.msgstr[0]: # no header diff, only metadata
        return None

    ehmsg_clean = clear_header_metadata(ehmsg)

    # Create reduced headers.
    hmsg1 = msg_ediff_to_old(ehmsg_clean)
    hmsg2 = msg_ediff_to_new(ehmsg_clean)
    hmsg = not cat.created() and cat.header.to_msg() or None
    hdrs = []
    for m in (hmsg, hmsg1, hmsg2):
        h = m is not None and reduce_header_fields(Header(m)) or None
        hdrs.append(h)
    rhdr, rhdr1, rhdr2 = hdrs

    # Decide if the header can be cleanly patched.
    clean = False
    if not rhdr:
        clean = rhdr1 or rhdr2
    else:
        clean = (rhdr1 and rhdr == rhdr1) or (rhdr2 and rhdr == rhdr2)

    if clean:
        if not options.embed:
            if hmsg2:
                cat.header = Header(hmsg2)
            else:
                # Catalog will be removed if no messages are rejected,
                # and otherwise the header should stay as-is.
                pass
        else:
            if cat.created():
                cat.header = Header(hmsg2)
            ehmsg = MessageUnsafe(ehmsg)
            ehmsg.flag.add(_flag_ediff)
            hmsgctxt = ED.get_msgctxt_for_headers(cat)
            ehmsg.msgctxt = hmsgctxt
            cat.header.set_field(ED._hmsgctxt_field, hmsgctxt)
            cat.add(Message(ehmsg), 0)
        return None
    else:
        return ehmsg


# Clear header diff message of metadata.
# A copy of the message is returned.
def clear_header_metadata (ehmsg):

    ehmsg = MessageUnsafe(ehmsg)
    ehmsg.manual_comment.pop(0)
    ehmsg.msgctxt = None
    ehmsg.msgid = u""

    return ehmsg


# Remove known unimportant fields from the header,
# to ignore them on comparisons.
def reduce_header_fields (hdr):

    rhdr = Header(hdr)
    for field in (
        "POT-Creation-Date",
        "PO-Revision-Date",
        "Last-Translator",
        "X-Generator",
    ):
        rhdr.remove_field(field)

    return rhdr


def unembed_ediff (path, all=False, old=False):

    try:
        cat = Catalog(path)
    except:
        warning("error reading catalog '%s', skipping" % path)
        return

    hmsgctxt = cat.header.get_field_value(ED._hmsgctxt_field)
    if hmsgctxt is not None:
        cat.header.remove_field(ED._hmsgctxt_field)

    uehmsg = None
    unembedded = {}
    for msg in cat:
        ediff_flag = None
        for flag in _flags_all:
            if flag in msg.flag:
                ediff_flag = flag
                msg.flag.remove(flag)
        if not ediff_flag and not all:
            continue
        if ediff_flag in (_flag_ediff_no_match, _flag_ediff_to_new):
            # Throw away fully rejected embeddings, i.e. reject the patch.
            # For split-difference embeddings, throw away the current-to-new;
            # this effectively rejects the patch, which is safest thing to do.
            cat.remove_on_sync(msg)
        elif hmsgctxt is not None and msg.msgctxt == hmsgctxt:
            if uehmsg:
                warning_on_msg("unembedding results in duplicate header, "
                               "previous header at %d(#%d); skipping"
                               % (uehmsg.refline, uehmsg.refentry), msg, cat)
                return
            msg_ediff_to_x = not old and msg_ediff_to_new or msg_ediff_to_old
            hmsg = msg_ediff_to_x(clear_header_metadata(msg))
            if hmsg.msgstr and hmsg.msgstr[0]:
                cat.header = Header(hmsg)
            cat.remove_on_sync(msg)
            uehmsg = msg
        else:
            msg1, msg2, msg1_s, msg2_s = resolve_diff_pair(msg)
            tmsg = (not old and (msg2,) or (msg1,))[0]
            if tmsg is not None:
                if tmsg.key in unembedded:
                    msg_p = unembedded[tmsg.key]
                    warning_on_msg("unembedding results in duplicate message, "
                                   "previous message at %d(#%d); skipping"
                                   % (msg_p.refline, msg_p.refentry), msg, cat)
                    return
                msg.set(msg2)
                unembedded[tmsg.key] = msg
            else:
                cat.remove_on_sync(msg)

    if cat.sync():
        report("unembedded: %s" % cat.filename)


if __name__ == '__main__':
    main()
