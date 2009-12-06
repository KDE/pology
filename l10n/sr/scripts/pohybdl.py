#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import fallback_import_paths

import sys
import os
import locale
from optparse import OptionParser
from tempfile import NamedTemporaryFile

from pology.misc.fsops import str_to_unicode
from pology.misc.report import report, error
from pology.misc.msgreport import warning_on_msg, report_msg_content
from pology.misc.vcs import available_vcs, make_vcs
from pology.file.catalog import Catalog
from pology.file.message import MessageUnsafe
from pology.misc.diff import msg_ediff, msg_ediff_to_new
from pology.l10n.sr.hook.wconv import eitoh, hitoe


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
        help="Accept messages which have some changes between initial "
             "and reconstructed Ekavian translation.")

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

    # Sanity checks on paths.
    paths = free_args or ["."] # default to CWD if no paths given
    for path in paths:
        if not os.path.exists(path):
            error("Path '%s' does not exist." % path)
        if not vcs.is_versioned(path):
            error("Path '%s' is not under version control." % path)


    # Collect modified PO files in given paths.
    modpaths = []
    for path in paths:
        for path in vcs.to_commit(path):
            if path.endswith(".po"):
                modpaths.append(path)

    # Go by modified PO file and hybridize it.
    for path in modpaths:
        # Extract local head counterpart.
        tmpf = NamedTemporaryFile(prefix="pohybdl-export-", suffix=".po")
        if not vcs.export(path, None, tmpf.name):
            error("Version control system cannot export file '%s'." % path)
        # Hybridize by comparing local head and modified file.
        hybdl(path, tmpf.name, options.accept_changes)


def hybdl (path, path0, accekch=False):

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
        textsh = []
        texts0e = []
        texts1e = []
        for text0, text in zip(msg0.msgstr, msg.msgstr):
            texth = eitoh(text0, text, refonly=True)
            textsh.append(texth)
            if not accekch:
                texts0e.append(hitoe(text0))
                texts1e.append(hitoe(texth))
        if texts0e == texts1e:
            for i, texth in zip(range(len(msg.msgstr)), textsh):
                msg.msgstr[i] = texth
            nhybridized += 1
        else:
            nstopped += 1
            msg1 = MessageUnsafe(msg)
            msg0.msgstr = texts0e
            msg1.msgstr = texts1e
            msg_ediff(msg0, msg1, emsg=msg1, hlto=sys.stdout)
            report_msg_content(msg1, cat, delim=("-" * 20))

    if nstopped == 0:
        if cat.sync():
            report("! %s (%d)" % (path, nhybridized))
    else:
        report("%s: %d suspicious messages." % (path, nstopped))
        nhybridized = 0

    return nhybridized


if __name__ == '__main__':
    _main()

