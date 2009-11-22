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
from pology.misc.split import proper_words
from pology.misc.diff import editprob

import sys
import os
import shutil
from optparse import OptionParser
import locale


def main ():

    locale.setlocale(locale.LC_ALL, "")

    # Get defaults for command line options from global config.
    cfgsec = pology_config.section("poselfmerge")
    def_minwnex = cfgsec.integer("min-words-exact", 0)
    def_minasfz = cfgsec.real("min-adjsim-fuzzy", 0.0)
    def_fuzzex = cfgsec.real("fuzzy-exact", False)
    def_refuzz = cfgsec.real("rebase-fuzzies", False)
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
        self_merge_pofile(fname, op.do_wrap, op.do_fine_wrap, op.compendiums,
                          op.fuzzy_exact, op.min_words_exact,
                          op.min_adjsim_fuzzy, op.rebase_fuzzies)


def self_merge_pofile (catpath, wrap=True, finewrap=False, compendiums=[],
                       fuzzex=False, minwnex=0, minasfz=0.0, refuzzy=False):

    # Create temporary files for merging.
    ext = ".tmp-selfmerge"
    catpath_mod = catpath + ext
    if ".po" in catpath:
        potpath = catpath.replace(".po", ".pot") + ext
    else:
        potpath = catpath + ".pot" + ext
    shutil.copyfile(catpath, catpath_mod)
    shutil.copyfile(catpath, potpath)

    # From the dummy template, clean all active messages and
    # remove all obsolete messages.
    cat = Catalog(potpath, monitored=False)
    for msg in cat:
        if msg.obsolete:
            cat.remove_on_sync(msg)
        else:
            msg.clear()
    cat.sync()

    # Merge with dummy template.
    merge_pofile(catpath_mod, potpath, wrap=wrap, finewrap=finewrap,
                 cmppaths=compendiums, fuzzex=fuzzex,
                 minwnex=minwnex, minasfz=minasfz, refuzzy=refuzzy)

    # Overwrite original with temporary catalog.
    shutil.move(catpath_mod, catpath)
    os.unlink(potpath)


def merge_pofile (catpath, tplpath, outpath=None, wrap=True, finewrap=False,
                  cmppaths=[], fuzzex=False, minwnex=0, minasfz=0.0,
                  fuzzymatch=True, refuzzy=False, quiet=True,
                  getcat=False, monitored=True):

    # Open catalog for pre-processing.
    cat = Catalog(catpath, monitored=False)

    # In case compendium is being used,
    # collect keys of all non-translated messages,
    # to later check which exact matches need to be fuzzied.
    if cmppaths and (fuzzex or minwnex > 0):
        nontrkeys = set()
        for msg in cat:
            if not msg.translated:
                nontrkeys.add(msg.key)

    # If requested, remove all untranslated messages,
    # and every fuzzy for which previous fields define a message
    # still existing in the catalog.
    # This way, untranslated messages will get fuzzy matched again,
    # and fuzzy messages may get updated translation.
    if refuzzy and fuzzymatch:
        for msg in cat:
            if (    msg.untranslated
                or (    msg.fuzzy and msg.msgid_previous
                    and cat.select_by_key(msg.msgctxt_previous,
                                          msg.msgid_previous))
            ):
                cat.remove_on_sync(msg)

    cat.sync()

    # Merge.
    opts = []
    if outpath:
        opts.append("--output-file %s" % outpath)
    else:
        opts.append("--update")
        opts.append("--backup none")
    if fuzzymatch:
        opts.append("--previous")
    else:
        opts.append("--no-fuzzy-matching")
    if not wrap:
        opts.append("--no-wrap")
    for cmppath in cmppaths:
        if not os.path.isfile(cmppath):
            error("Compendium not found at '%s'." % cmppath)
        opts.append("--compendium %s" % cmppath)
    if quiet:
        opts.append("--quiet")
    fmtopts = " ".join(opts)
    cmdline = "msgmerge %s %s %s" % (fmtopts, catpath, tplpath)
    assert_system(cmdline)

    # If the catalog had only header and no messages,
    # msgmerge will not write out anything.
    # In such case, just copy over existing.
    if outpath and not os.path.isfile(outpath):
        shutil.copyfile(catpath, outpath)

    # Post-process merged catalog if necessary.
    if getcat or finewrap or (cmppaths and (fuzzex or minwnex > 0)) or minasfz:
        # If fine wrapping requested and catalog should not be returned,
        # everything has to be reformatted, so no need to monitor the catalog.
        catpath1 = outpath or catpath
        monitored1 = monitored if getcat else (not finewrap)
        wrapf = select_field_wrapper(wrap, finewrap)
        cat = Catalog(catpath1, monitored=monitored1, wrapf=wrapf)

        # In case compendium is being used,
        # make fuzzy exact matches which do not pass the word limit.
        if cmppaths and (fuzzex or minwnex > 0):
            for msg in cat:
                if (    msg.key in nontrkeys and msg.translated
                    and (fuzzex or len(proper_words(msg.msgid)) < minwnex)
                ):
                    msg.fuzzy = True

        # Eliminate fuzzy matches not passing the adjusted similarity limit.
        if minasfz > 0.0:
            for msg in cat:
                if msg.fuzzy and msg.msgid_previous is not None:
                    if editprob(msg.msgid_previous, msg.msgid) < minasfz:
                        msg.clear()

        if not getcat:
            cat.sync(force=finewrap)
        else:
            return cat


if __name__ == '__main__':
    main()
