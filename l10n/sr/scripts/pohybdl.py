#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import fallback_import_paths

import sys
import os
import locale
from optparse import OptionParser
from tempfile import NamedTemporaryFile

from pology.misc.fsops import str_to_unicode, collect_catalogs
from pology.misc.report import report, error
from pology.misc.msgreport import warning_on_msg, report_msg_content
from pology.misc.vcs import available_vcs, make_vcs
from pology.file.catalog import Catalog
from pology.file.message import MessageUnsafe
from pology.misc.diff import msg_ediff, msg_ediff_to_new
from pology.l10n.sr.hook.wconv import eitoh, hitoe, hitoi


def _main ():

    locale.setlocale(locale.LC_ALL, "")

    usage = u"""
  %prog [OPTIONS] VCS [IJPATHS...]
""".rstrip()
    description = u"""
Compose hybridized Ijekavian-Ekavian translation out of clean translations.
""".strip()
    version = u"""
%prog (Pology) experimental
Copyright © 2009 Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
""".strip()

    opars = OptionParser(usage=usage, description=description, version=version)
    opars.add_option(
        "-a", "--accept-changes",
        action="store_true", dest="accept_changes", default=False,
        help="Accept messages which have some changes between base "
             "and reconstructed base text.")
    opars.add_option(
        "-f", "--files-from", metavar="FILE",
        action="append", dest="files_from", default=[],
        help="Get list of input files from FILE, which contains one file path "
             "per line; can be repeated to collect paths from several files.")
    opars.add_option(
        "-i", "--ijekavian-base",
        action="store_true", dest="ijekavian_base", default=False,
        help="Base text is Ijekavian and modified text is Ekavian.")
    opars.add_option(
        "-r", "--base-revision", metavar="REV",
        action="store", dest="base_revision", default=None,
        help="Use the given revision as base for hybridization, "
             "instead of local latest revision.")

    (options, free_args) = opars.parse_args(str_to_unicode(sys.argv[1:]))

    try:
        import psyco
        psyco.full()
    except ImportError:
        pass

    # Create VCS.
    if len(free_args) < 1:
        showvcs = list(set(available_vcs()).difference(["none"]))
        showvcs.sort()
        error("Version control system not given (can be one of: %s)."
              % ", ".join(showvcs))
    vcskey = free_args.pop(0)
    if vcskey not in available_vcs(flat=True):
        error("Unknown version control system '%s'." % vcskey)
    vcs = make_vcs(vcskey)

    # Collect list of raw paths supplied through command line.
    # If none supplied, assume current working directory.
    paths = None
    if free_args:
        paths = free_args
    if options.files_from:
        if paths is None:
            paths = []
        for fpath in options.files_from:
            lines = open(fpath).read().split("\n")
            paths.extend(filter(lambda x: x, lines))
    if paths is None:
        paths = ["."]

    # Sanity checks on paths.
    for path in paths:
        if not os.path.exists(path):
            error("Path '%s' does not exist." % path)
        if not vcs.is_versioned(path):
            error("Path '%s' is not under version control." % path)

    # Collect PO files in given paths.
    popaths = collect_catalogs(paths)

    # Go by modified PO file and hybridize it.
    for path in popaths:
        # Extract local head counterpart.
        tmpf = NamedTemporaryFile(prefix="pohybdl-export-", suffix=".po")
        if not vcs.export(path, options.base_revision, tmpf.name):
            error("Version control system cannot export file '%s'." % path)
        # Hybridize by comparing local head and modified file.
        hybdl(path, tmpf.name, options.accept_changes, options.ijekavian_base)


def hybdl (path, path0, accekch=False, ijekbase=False):

    cat = Catalog(path)
    cat0 = Catalog(path0, monitored=False)

    nhybridized = 0
    nstopped = 0
    for msg in cat:

        # Unembed diff if message was diffed for review.
        # Replace ediff with manual review flag.
        diffed = False
        for flag in msg.flag:
            if flag.startswith("ediff"):
                msg.flag.remove(flag)
                diffed = True
        if diffed:
            msg_ediff_to_new(msg, msg)
            msg.flag.add(u"reviewed")

        # Fetch original message.
        msg0 = cat0.get(msg)
        if msg0 is None:
            warning_on_msg("Message does not exist in the original catalog.",
                           msg, cat)
            nstopped += 1
            continue
        if len(msg.msgstr) != len(msg0.msgstr):
            warning_on_msg("Number of translations not same as in "
                           "the original message.", msg, cat)
            nstopped += 1
            continue
        if msg.msgstr == msg0.msgstr:
            # No changes, nothing new to hybridize.
            continue

        # Hybridize translation.
        if not ijekbase:
            hito0, hito1 = hitoe, hitoi
            hybf = lambda t0, t1: eitoh(t0, t1, refonly=True)
        else:
            hito0, hito1 = hitoi, hitoe
            hybf = lambda t0, t1: eitoh(t1, t0, refonly=True)
        textsh = []
        texts0 = []
        texts0r = []
        for text0, text in zip(msg0.msgstr, msg.msgstr):
            text0 = hito0(text0) # if there is already some hybridization
            text1 = hito1(text) # ditto
            texth = hybf(text0, text1)
            textsh.append(texth)
            if not accekch:
                texts0.append(text0)
                texts0r.append(hito0(texth))
        if texts0 == texts0r:
            for i, texth in zip(range(len(msg.msgstr)), textsh):
                msg.msgstr[i] = texth
            nhybridized += 1
        else:
            nstopped += 1
            msg0r = MessageUnsafe(msg)
            msg0.msgstr = texts0
            msg0r.msgstr = texts0r
            msg_ediff(msg0, msg0r, emsg=msg0r, hlto=sys.stdout)
            report_msg_content(msg0r, cat, delim=("-" * 20))

    if nstopped == 0:
        if cat.sync():
            report("! %s (%d)" % (path, nhybridized))
    else:
        report("%s: %d suspicious messages." % (path, nstopped))
        nhybridized = 0

    return nhybridized


if __name__ == '__main__':
    _main()

