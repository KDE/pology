#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import pology.misc.wrap as wrap
from pology.file.catalog import Catalog

import sys, os
from optparse import OptionParser

def error (msg, code=1):
    cmdname = os.path.basename(sys.argv[0])
    sys.stderr.write("%s: error: %s\n" % (cmdname, msg))
    sys.exit(code)

def main ():
    # Setup options and parse the command line.
    usage = u"""
%prog [options] POFILE...
""".strip()
    description = u"""
Rewraps PO files considering some markup tags as unconditional breaks too.
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
        action="store_false", dest="do_wrap", default=True,
        help="do not break long unsplit lines into several lines")
    opars.add_option(
        "--no-psyco",
        action="store_false", dest="use_psyco", default=True,
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
    fnames = fargs
    if op.files_from:
        flines = open(op.files_from, "r").readlines()
        fnames.extend([f.rstrip("\n") for f in flines])

    # Decide on wrapping policy.
    if op.do_wrap:
        wrap_func = wrap.wrap_field_ontag
    else:
        wrap_func = wrap.wrap_field_ontag_unwrap

    # Rewrap all catalogs.
    for fname in fnames:
        if op.verbose: print "Rewrapping %s ..." % (fname,),
        cat = Catalog(fname, monitored=False, wrapf=wrap_func)
        cat.sync(force=True)
        if op.verbose: print ""

if __name__ == '__main__':
    main()
