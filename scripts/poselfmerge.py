#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Merge PO file with itself, to produce fuzzy matches on similar messages.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import locale
from optparse import OptionParser
import os
import shutil
import sys

import fallback_import_paths

from pology.file.catalog import Catalog
from pology.file.message import MessageUnsafe
import pology.misc.config as pology_config
from pology.misc.fsops import collect_catalogs
from pology.misc.merge import merge_pofile
from pology.misc.report import report, error
import pology.scripts.porewrap as REW


def main ():

    locale.setlocale(locale.LC_ALL, "")

    # Get defaults for command line options from global config.
    cfgsec = pology_config.section("poselfmerge")
    def_minwnex = cfgsec.integer("min-words-exact", 0)
    def_minasfz = cfgsec.real("min-adjsim-fuzzy", 0.0)
    def_fuzzex = cfgsec.boolean("fuzzy-exact", False)
    def_refuzz = cfgsec.boolean("rebase-fuzzies", False)
    def_use_psyco = cfgsec.boolean("use-psyco", True)

    # Setup options and parse the command line.
    usage = u"""
%prog [options] POFILE...
""".strip()
    description = u"""
Merge PO file with itself, to produce fuzzy matches on similar messages.

Wrapping behavior and options are same as in '%s' script.
""".strip() % ("porewrap")
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
        "-C", "--compendium",  metavar="POFILE",
        action="append", dest="compendiums", default=[],
        help="Catalog with existing translations, to additionally use for "
             "direct and fuzzy matches (can be repeated).")
    opars.add_option(
        "-W", "--min-words-exact",  metavar="NUMBER",
        action="store", dest="min_words_exact", default=def_minwnex,
        help="When using compendium, in case of exact match, "
             "minimum number of words that original text must have "
             "to accept translation without making it fuzzy. "
             "Zero means to always accept an exact match.")
    opars.add_option(
        "-A", "--min-adjsim-fuzzy",  metavar="NUMBER",
        action="store", dest="min_adjsim_fuzzy", default=def_minasfz,
        help="When using compendium, in case of fuzzy match, "
             "minimum adjusted similarity to accept the match. "
             "Range is 0.0-1.0, where 0 means to always accept the match, "
             "and 1 to never accept; a resonable threshold is 0.6-0.8.")
    opars.add_option(
        "-x", "--fuzzy-exact",
        action="store_true", dest="fuzzy_exact", default=def_fuzzex,
        help="When using compendium, make all exact matches fuzzy.")
    opars.add_option(
        "-b", "--rebase-fuzzies",
        action="store_true", dest="rebase_fuzzies", default=def_refuzz,
        help="Before merging, clear those fuzzy messages whose predecessor "
             "(determined by previous fields) is still in the catalog.")
    REW.add_wrapping_options(opars)
    opars.add_option(
        "--no-psyco",
        action="store_false", dest="use_psyco", default=def_use_psyco,
        help="Do not try to use Psyco specializing compiler.")
    opars.add_option(
        "-v", "--verbose",
        action="store_true", dest="verbose", default=False,
        help="Output more detailed progress info.")
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

    # Convert non-string options to needed types.
    try:
        op.min_words_exact = int(op.min_words_exact)
    except:
        error("Value to option %s must be integer (given: %s)."
              % ("--min-words-exact", op.min_words_exact))
    try:
        op.min_adjsim_fuzzy = float(op.min_adjsim_fuzzy)
    except:
        error("Value to option %s must be real (given: %s)."
              % ("--min-adjsim-fuzzy", op.min_ajdsim_fuzzy))

    # Self-merge all catalogs.
    for fname in fnames:
        if op.verbose:
            report("Self-merging %s ..." % fname)
        self_merge_pofile(fname, op.compendiums,
                          op.fuzzy_exact, op.min_words_exact,
                          op.min_adjsim_fuzzy, op.rebase_fuzzies,
                          cfgsec, op)


def self_merge_pofile (catpath, compendiums=[],
                       fuzzex=False, minwnex=0, minasfz=0.0, refuzzy=False,
                       cfgsec=None, cmlopt=None):

    # Create temporary files for merging.
    ext = ".tmp-selfmerge"
    catpath_mod = catpath + ext
    if ".po" in catpath:
        potpath = catpath.replace(".po", ".pot") + ext
    else:
        potpath = catpath + ".pot" + ext
    shutil.copyfile(catpath, catpath_mod)
    shutil.copyfile(catpath, potpath)

    # Open catalog for pre-processing.
    cat = Catalog(potpath, monitored=False)

    # Decide wrapping policy.
    wrapping = REW.select_field_wrapping(cfgsec, cat, cmlopt)

    # From the dummy template, clean all active messages and
    # remove all obsolete messages.
    for msg in cat:
        if msg.obsolete:
            cat.remove_on_sync(msg)
        else:
            msg.clear()
    cat.sync()

    # Merge with dummy template.
    merge_pofile(catpath_mod, potpath, update=True, wrapping=wrapping,
                 cmppaths=compendiums, fuzzex=fuzzex,
                 minwnex=minwnex, minasfz=minasfz, refuzzy=refuzzy,
                 abort=True)

    # Overwrite original with temporary catalog.
    shutil.move(catpath_mod, catpath)
    os.unlink(potpath)


if __name__ == '__main__':
    main()
