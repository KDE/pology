#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import sys
import os
import locale
from optparse import OptionParser
from tempfile import NamedTemporaryFile

from pology.misc.fsops import str_to_unicode
from pology.misc.report import report, error
from pology.misc.msgreport import warning_on_msg
from pology.misc.vcs import available_vcs, make_vcs
from pology.file.catalog import Catalog
from pology.misc.diff import msg_ediff_to_new
from pology.l10n.sr.hook.wconv import eitoh


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

        hybridize_in_ijekavized(path, tmpf.name)
        del tmpf


def hybridize_in_ijekavized (path, path0):

    cat = Catalog(path)
    cat0 = Catalog(path0, monitored=False)

    nhybridized = 0
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
            continue
        if len(msg.msgstr) != len(msg0.msgstr):
            warning_on_msg("Number of translations not same as in "
                           "the original message.", msg, cat)
            continue

        # Hybridize translation.
        oldcount = msg.modcount
        for i in range(len(msg.msgstr)):
            text = msg.msgstr[i]
            text0 = msg0.msgstr[i]
            msg.msgstr[i] = eitoh(text0, text, refonly=True)
        if msg.modcount > oldcount:
            nhybridized += 1

    if cat.sync():
        report("! %s (%d)" % (path, nhybridized))


if __name__ == '__main__':
    _main()

