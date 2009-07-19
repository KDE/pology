#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Merge PO file with itself, to produce fuzzy matches on similar messages.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import fallback_import_paths

from pology.misc.report import report, error
import pology.misc.config as pology_config
from pology.misc.wrap import select_field_wrapper
from pology.misc.fsops import collect_catalogs
from pology.file.catalog import Catalog
from pology.file.message import MessageUnsafe
from pology.misc.fsops import assert_system

import sys
import os
import shutil
from optparse import OptionParser
import locale


def main ():

    locale.setlocale(locale.LC_ALL, "")

    # Get defaults for command line options from global config.
    cfgsec = pology_config.section("poselfmerge")
    def_do_wrap = cfgsec.boolean("wrap", True)
    def_do_fine_wrap = cfgsec.boolean("fine-wrap", True)
    def_use_psyco = cfgsec.boolean("use-psyco", True)

    # Setup options and parse the command line.
    usage = u"""
%prog [options] POFILE...
""".strip()
    description = u"""
Merge PO file with itself, to produce fuzzy matches on similar messages.
""".strip()
    version = u"""
%prog (Pology) experimental
Copyright © 2009 Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
""".strip()

    opars = OptionParser(usage=usage, description=description, version=version)
    opars.add_option(
        "-f", "--files-from", metavar="FILE",
        dest="files_from",
        help="get list of input files from FILE (one file per line)")
    opars.add_option(
        "--no-wrap",
        action="store_false", dest="do_wrap", default=def_do_wrap,
        help="no basic wrapping (on column)")
    opars.add_option(
        "--no-fine-wrap",
        action="store_false", dest="do_fine_wrap", default=def_do_fine_wrap,
        help="no fine wrapping (on markup tags, etc.)")
    opars.add_option(
        "--no-psyco",
        action="store_false", dest="use_psyco", default=def_use_psyco,
        help="do not try to use Psyco specializing compiler")
    opars.add_option(
        "-v", "--verbose",
        action="store_true", dest="verbose", default=False,
        help="output more detailed progress info")
    (op, fargs) = opars.parse_args()

    if len(fargs) < 1 and not op.files_from:
        opars.error("No input files given.")

    # Could use some speedup.
    if op.use_psyco:
        try:
            import psyco
            psyco.full()
        except ImportError:
            pass

    # Assemble list of files.
    file_or_dir_paths = fargs
    if op.files_from:
        flines = open(op.files_from, "r").readlines()
        file_or_dir_paths.extend([f.rstrip("\n") for f in flines])
    fnames = collect_catalogs(file_or_dir_paths)

    # Decide on wrapping policy.
    wrap_func = select_field_wrapper(basic=op.do_wrap, fine=op.do_fine_wrap)

    # Self-merge all catalogs.
    for fname in fnames:
        if op.verbose:
            report("Self-merging %s ..." % fname)
        self_merge_catalog(fname, wrap_func)


def self_merge_catalog (catpath, wrapf):

    # Create temporary files for merging.
    ext = ".tmp-selfmerge"
    catpath_mod = catpath + ext
    if ".po" in catpath:
        potpath = catpath.replace(".po", ".pot") + ext
    else:
        potpath = catpath + ".pot" + ext
    shutil.copyfile(catpath, catpath_mod)
    shutil.copyfile(catpath, potpath)

    # From the file to be merged, remove all untranslated messages,
    # and every fuzzy for which the previous fields define a message
    # still existing in the catalog.
    # This way, untranslated messages will get fuzzy matched again,
    # and fuzzy messages may get updated translation.
    cat = Catalog(catpath_mod, monitored=False)
    for msg in cat:
        if (    msg.untranslated
            or (    msg.fuzzy and msg.msgid_previous
                and cat.select_by_key(msg.msgctxt_previous, msg.msgid_previous))
        ):
            cat.remove_on_sync(msg)
    cat.sync()

    # From the file to be the template,
    # remove all obsolete messages.
    # (Not even this needs to be done with newer version of msgmerge,
    # but just in case.)
    cat = Catalog(potpath, monitored=False)
    for msg in cat:
        if msg.obsolete:
            cat.remove_on_sync(msg)
    cat.sync()

    # Merge.
    cmdline = ("msgmerge --quiet --previous --update --backup none %s %s"
               % (catpath_mod, potpath))
    assert_system(cmdline)

    # Open merged catalog to wrap properly.
    cat = Catalog(catpath_mod, monitored=False, wrapf=wrapf)
    cat.sync(force=True)

    # Overwrite original with temporary catalog.
    shutil.move(catpath_mod, catpath)
    os.unlink(potpath)


if __name__ == '__main__':
    main()
