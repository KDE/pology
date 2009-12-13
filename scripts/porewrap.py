#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Rewrap keyword text fields in PO files.

Keyword text fields (C{msgid}, C{msgstr}, etc.) in PO files may be wrapped
in arbitrary fashion, without changing their semantics.
(Unlike extracted or translator comments, where it is not safe to assume
that line breaks are not significant.)

Pology can wrap keyword text fields on newline characters only,
on certain column width, and on various logical breaks
(e.g. paragraph tags in markup text).
By default, this script applies all known wrapping types,
but the wrapping policy can be controlled from several sources:
  - command line options C{--wrap} and C{--no-wrap} enable or disable
    wrapping on column, and C{--fine-wrap}/C{--no-fine-wrap} wrapping
    on logical breaks;
  - L{configuration fields<misc.config>} C{[porewrap]/wrap}
    and C{[porewrap]/fine-wrap} may be set to C{yes} or C{no},
    corresponding to previous command line options;
  - catalogs themselves may state what wrapping should be applied.

Catalogs can state wrapping policy through C{Wrapping} or C{X-Wrapping}
header fields. The value is a comma-separated list of wrapping type
keywords, which currently can be: C{basic} (wrapping on column),
C{fine} (wrapping on logical breaks).
For example, not to wrap on column but to wrap on logical breaks::

    msgid ""
    msgstr ""
    "..."
    "X-Wrapping: fine\\n"
    "..."

To specify wrapping within the catalog is advantageous when more people
may be working on it, so that it does not go through constant rewrappings.
Unless told otherwise, all Pology tools will by default recognize and apply
wrapping policy specified like this.

In case when wrapping policies from different sources conflict,
this script decides wrapping policy for a given catalog with following
increasing priority: user configuration, catalog header
(overrides configuration), command line (overrides both configuration
and header).

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import fallback_import_paths

import pology.misc.config as pology_config
from pology.misc.fsops import collect_catalogs
from pology.file.catalog import Catalog
from pology.misc.report import report, error

import sys, os
from optparse import OptionParser
import locale


def main ():

    locale.setlocale(locale.LC_ALL, "")

    # Get defaults for command line options from global config.
    cfgsec = pology_config.section("porewrap")
    def_use_psyco = cfgsec.boolean("use-psyco", True)

    # Setup options and parse the command line.
    usage = u"""
%prog [options] POFILE...
""".strip()
    description = u"""
Rewrap keyword text fields in PO files.

There are more ways to wrap keyword text fields (msgid, msgstr, etc.).
They can be wrapped on newline characters only, on certain column width,
and on various logical breaks (e.g. paragraph tags in markup text).

By default, this script applies all wrapping types known to Pology,
but this can be controlled through Pology user configuration,
through catalog headers, and by command line options.
See documentation for details.
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
    add_wrapping_options(opars)
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

    # Rewrap all catalogs.
    for fname in fnames:
        if op.verbose:
            report("Rewrapping %s ..." % fname)
        cat = Catalog(fname, monitored=False)
        wrapping = select_field_wrapping(cfgsec, cat, op)
        cat.set_wrapping(wrapping)
        cat.sync(force=True)


def add_wrapping_options (opars):

    opars.add_option(
        "--wrap",
        action="store_true", dest="do_wrap", default=None,
        help="Basic wrapping (on colum count).")
    opars.add_option(
        "--no-wrap",
        action="store_false", dest="do_wrap", default=None,
        help="No basic wrapping (on column count).")
    opars.add_option(
        "--fine-wrap",
        action="store_true", dest="do_fine_wrap", default=None,
        help="Fine wrapping (on logical breaks, like some markup tags).")
    opars.add_option(
        "--no-fine-wrap",
        action="store_false", dest="do_fine_wrap", default=None,
        help="No fine wrapping (on logical breaks, like some markup tags).")


def select_field_wrapping (cfgsec=None, cat=None, cmlopt=None):

    # Select maximum wrapping initially.
    wrapping = ["basic", "fine"]

    # Helper to remove and add wrapping types.
    def waddrem (add, wtype):
        if add is False and wtype in wrapping:
            wrapping.remove(wtype)
        elif add is True and wtype not in wrapping:
            wrapping.append(wtype)

    # Restrict wrapping in following priority of overrides.
    # - configuration
    if cfgsec is not None:
        waddrem(cfgsec.boolean("wrap", None), "basic")
        waddrem(cfgsec.boolean("fine-wrap", None), "fine")
    # - catalog
    wrapping_cat = cat.wrapping() if cat is not None else None
    if wrapping_cat is not None:
        waddrem("basic" in wrapping_cat, "basic")
        waddrem("fine" in wrapping_cat, "fine")
    # - command line
    if cmlopt is not None:
        waddrem(cmlopt.do_wrap, "basic")
        waddrem(cmlopt.do_fine_wrap, "fine")

    return tuple(sorted(wrapping))


if __name__ == '__main__':
    main()
