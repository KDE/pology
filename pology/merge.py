# -*- coding: UTF-8 -*-

"""
Merge PO files.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import os
import shutil
from tempfile import NamedTemporaryFile

from pology import PologyError, _, n_
from pology.catalog import Catalog
from pology.diff import editprob
from pology.fsops import unicode_to_str
from pology.split import proper_words


def merge_pofile (catpath, tplpath,
                  outpath=None, update=False, wrapping=None,
                  fuzzymatch=True, cmppaths=None, quiet=False,
                  fuzzex=False, minwnex=0, minasfz=0.0, refuzzy=False,
                  getcat=False, monitored=True,
                  ignpotdate=False, abort=False):
    """
    Merge a PO file with the PO template.

    This function is a frontend to C{msgmerge} command,
    providing some additional features on demand.

    This function is usually used in one of three ways:
      - create a new PO file: the path is given with C{outpath} parameter
      - update the original PO file: C{update} is set to C{True}
            and C{outpath} is not given
      - only get merged catalog object: C{getcat} is set to C{True} and
            neither C{outpath} nor C{update} are issued;
            no PO file gets created or modified (except for temporaries,
            which are cleaned up on return)
      - check whether merging is possible: neither of C{outpath},
            C{update}, or C{getcat} are issued;
            if C{True} is returned, merging succedded.

    The return value differs based on C{getcat}.
    If C{getcat} is C{False}, the return value is C{True} if merging
    succedded (C{msgmerge} exited normally), and C{False} if not.
    If C{getcat} is C{True}, a catalog object on the merged catalog
    is returned if the merging succedded, and C{None} if not.
    However, if C{abort} is set to C{True}, if C{msgmerge} fails
    the program aborts with an error message.

    When catalog object is returned, its sync state is undefined.
    If it needs to be in sync before use, it should be synced manually.

    @param catpath: path to PO file to merge
    @type catpath: string
    @param tplpath: path to PO template
    @type tplpath: string
    @param outpath: path to output PO file
    @type outpath: string
    @param update: whether to update the PO file in place
    @type update: bool
    @param wrapping: the wrapping policy (see the parameter of the same name
        to L{catalog constructor<file.catalog.Catalog>})
    @type wrapping: sequence of strings
    @param fuzzymatch: whether to perform fuzzy matching
    @type fuzzymatch: bool
    @param cmppaths: paths to compendium files to be used on merging
    @type cmppaths: sequence of strings
    @param quiet: whether C{msgmerge} should operate quietly
    @type quiet: bool
    @param fuzzex: whether to fuzzy exact matches from compendia
    @type fuzzex: bool
    @param minwnex: minimal number of words in the original in exact match
        from compendia to not fuzzy the message (a very large number
        approximates C{fuzzex} set to C{True}).
    @type minwnex: int
    @param refuzzy: whether to "rebase" fuzzy messages, i.e. remove prior
        to merging those fuzzy messages whose translated counterparts
        (determined by previous fields) still exist in the catalog.
        This puts possibly newer translation into such messages,
        or even leads to a better fuzzy match.
    @type refuzzy: bool
    @param getcat: whether to return catalog object on merged file
    @type getcat: L{Catalog<file.catalog.Catalog>} or C{None}
    @param monitored: if C{getcat} is in effect, whether to open catalog
        in monitoring mode (like the parameter to catalog constructor)
    @type monitored: bool
    @param ignpotdate: whether to ignore changed C{POT-Creation-Date}
        if there were no other changes, resetting it to original value
    @type ignpotdate: bool
    @param abort: whether to abort execution if C{msgmerge} fails
    @type abort: bool

    @returns: whether merging succedded, or catalog object
    @rtype: bool or L{Catalog<file.catalog.Catalog>} or C{None}
    """

    if wrapping is not None:
        wrap = "basic" in wrapping
        otherwrap = set(wrapping).difference(["basic"])
    else:
        wrap = True
        otherwrap = False

    # Store original catalog if change in template creation date
    # alone should be ignored, for check at the end.
    if ignpotdate:
        orig_cat = Catalog(catpath, monitored=False)

    # Determine which special operations are to be done.
    correct_exact_matches = cmppaths and (fuzzex or minwnex > 0)
    correct_fuzzy_matches = minasfz > 0.0
    rebase_existing_fuzzies = refuzzy and fuzzymatch

    # Pre-process catalog if necessary.
    if correct_exact_matches or rebase_existing_fuzzies:
        may_modify = rebase_existing_fuzzies
        cat = Catalog(catpath, monitored=may_modify)

        # In case compendium is being used,
        # collect keys of all non-translated messages,
        # to later check which exact matches need to be fuzzied.
        if correct_exact_matches:
            nontrkeys = set()
            for msg in cat:
                if not msg.translated:
                    nontrkeys.add(msg.key)

        # If requested, remove all untranslated messages,
        # and every fuzzy for which previous fields define a message
        # still existing in the catalog.
        # This way, untranslated messages will get fuzzy matched again,
        # and fuzzy messages may get updated translation.
        if rebase_existing_fuzzies:
            for msg in cat:
                if msg.untranslated:
                    cat.remove_on_sync(msg)
                elif msg.fuzzy and msg.msgid_previous:
                    omsgs = cat.select_by_key(msg.msgctxt_previous,
                                              msg.msgid_previous)
                    if omsgs:
                        omsg = omsgs[0]
                        if omsg.translated and omsg.msgstr != msg.msgstr:
                            cat.remove_on_sync(msg)

        if may_modify:
            cat.sync()

    # Prepare temporary file if output path not given and not in update mode.
    if not outpath and not update:
        tmpf = NamedTemporaryFile(prefix="pology-merged-", suffix=".po")
        outpath = tmpf.name

    # Merge.
    opts = []
    if not update:
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
    for cmppath in (cmppaths or []):
        if not os.path.isfile(cmppath):
            raise PologyError(
                _("@info",
                  "Compendium does not exist at '%(path)s'.",
                  path=cmppath))
        opts.append("--compendium %s" % cmppath)
    if quiet:
        opts.append("--quiet")
    fmtopts = " ".join(opts)
    cmdline = "msgmerge %s %s %s" % (fmtopts, catpath, tplpath)
    mrgres = os.system(unicode_to_str(cmdline))
    if mrgres != 0:
        if abort:
            raise PologyError(
                _("@info",
                  "Cannot merge PO file '%(file1)s' with template '%(file2)s'.",
                  file1=catpath, file2=tplpath))
        return None if getcat else False

    # If the catalog had only header and no messages,
    # msgmerge will not write out anything.
    # In such case, just copy the initial file to output path.
    if outpath and not os.path.isfile(outpath):
        shutil.copyfile(catpath, outpath)
    # If both the output path has been given and update requested,
    # copy the output file over the initial file.
    if update and outpath and catpath != outpath:
        shutil.copyfile(outpath, catpath)

    # Post-process merged catalog if necessary.
    if (   getcat or otherwrap or correct_exact_matches
        or correct_fuzzy_matches or ignpotdate
    ):
        # If fine wrapping requested and catalog should not be returned,
        # everything has to be reformatted, so no need to monitor the catalog.
        catpath1 = outpath or catpath
        monitored1 = monitored if getcat else (not otherwrap)
        cat = Catalog(catpath1, monitored=monitored1, wrapping=wrapping)

        # In case compendium is being used,
        # make fuzzy exact matches which do not pass the word limit.
        if correct_exact_matches:
            for msg in cat:
                if (    msg.key in nontrkeys and msg.translated
                    and (fuzzex or len(proper_words(msg.msgid)) < minwnex)
                ):
                    msg.fuzzy = True

        # Eliminate fuzzy matches not passing the adjusted similarity limit.
        if correct_fuzzy_matches:
            for msg in cat:
                if msg.fuzzy and msg.msgid_previous is not None:
                    if editprob(msg.msgid_previous, msg.msgid) < minasfz:
                        msg.clear()

        # Revert template creation date change if it was the only change.
        if ignpotdate:
            fname = "POT-Creation-Date"
            orig_potdate = orig_cat.header.get_field_value(fname)
            new_potdate = cat.header.get_field_value(fname)
            cat.header.replace_field_value(fname, orig_potdate)
            if cat != orig_cat:
                cat.header.replace_field_value(fname, new_potdate)

        if not getcat:
            cat.sync(force=otherwrap)

    return cat if getcat else True

