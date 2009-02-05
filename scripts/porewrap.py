#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import fallback_import_paths

import pology.misc.config as pology_config
from pology.misc.wrap import select_field_wrapper
from pology.misc.fsops import collect_catalogs
from pology.file.catalog import Catalog
from pology.misc.report import error

import sys, os
from optparse import OptionParser
import locale


def main ():

    locale.setlocale(locale.LC_ALL, "")

    # Get defaults for command line options from global config.
    cfgsec = pology_config.section("porewrap")
    def_do_wrap = cfgsec.boolean("wrap", True)
    def_do_fine_wrap = cfgsec.boolean("fine-wrap", True)
    def_use_psyco = cfgsec.boolean("use-psyco", True)

    # Setup options and parse the command line.
    usage = u"""
%prog [options] POFILE...
""".strip()
    description = u"""
Rewrap PO files considering text structure more finely (markup tags, etc.)
""".strip()
    version = u"""
%prog (Pology) experimental
Copyright © 2007 Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
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
        opars.error("Must provide at least one input file.")

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

    # Rewrap all catalogs.
    for fname in fnames:
        if op.verbose: print "Rewrapping %s ..." % (fname,),
        cat = Catalog(fname, monitored=False, wrapf=wrap_func)
        cat.sync(force=True)
        if op.verbose: print ""


if __name__ == '__main__':
    main()
