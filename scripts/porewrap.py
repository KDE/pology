#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Rewrap message strings in PO files.

Documented in C{doc/user/misctools.docbook#sec-mirewrap}.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import locale
import os
import sys

import fallback_import_paths

from pology import version, _, n_
from pology.catalog import Catalog
from pology.colors import ColorOptionParser
import pology.config as pology_config
from pology.fsops import collect_paths_cmdline, collect_catalogs
from pology.report import report, error
from pology.stdcmdopt import add_cmdopt_filesfrom


def main ():

    locale.setlocale(locale.LC_ALL, "")

    # Get defaults for command line options from global config.
    cfgsec = pology_config.section("porewrap")

    # Setup options and parse the command line.
    usage = _("@info command usage",
        "%(cmd)s [options] POFILE...",
        cmd="%prog")
    desc = _("@info command description",
        "Rewrap message strings in PO files.")
    ver = _("@info command version",
        u"%(cmd)s (Pology) %(version)s\n"
        u"Copyright © 2007, 2008, 2009, 2010 "
        u"Chusslove Illich (Часлав Илић) &lt;%(email)s&gt;",
        cmd="%prog", version=version(), email="caslav.ilic@gmx.net")

    opars = ColorOptionParser(usage=usage, description=desc, version=ver)
    opars.add_option(
        "-v", "--verbose",
        action="store_true", dest="verbose", default=False,
        help=_("@info command line option description",
               "More detailed progress information."))
    add_wrapping_options(opars)
    add_cmdopt_filesfrom(opars)

    (op, fargs) = opars.parse_args()

    if len(fargs) < 1 and not op.files_from:
        opars.error(_("@info", "No input files given."))

    # Could use some speedup.
    try:
        import psyco
        psyco.full()
    except ImportError:
        pass

    # Assemble list of files.
    fnames = collect_paths_cmdline(rawpaths=fargs,
                                   filesfrom=op.files_from,
                                   respathf=collect_catalogs,
                                   abort=True)

    # Rewrap all catalogs.
    for fname in fnames:
        if op.verbose:
            report(_("@info:progress", "Rewrapping: %(file)s", file=fname))
        cat = Catalog(fname, monitored=False)
        wrapping = select_field_wrapping(cfgsec, cat, op)
        cat.set_wrapping(wrapping)
        cat.sync(force=True)


# FIXME: Move to pology.stdcmdopt.
def add_wrapping_options (opars):

    opars.add_option(
        "--wrap",
        action="store_true", dest="do_wrap", default=None,
        help=_("@info command line option description",
               "Basic wrapping: on colum count."))
    opars.add_option(
        "--no-wrap",
        action="store_false", dest="do_wrap", default=None,
        help=_("@info command line option description",
               "No basic wrapping."))
    opars.add_option(
        "--fine-wrap",
        action="store_true", dest="do_fine_wrap", default=None,
        help=_("@info command line option description",
               "Fine wrapping: on logical breaks, like some markup tags."))
    opars.add_option(
        "--no-fine-wrap",
        action="store_false", dest="do_fine_wrap", default=None,
        help=_("@info command line option description",
               "No fine wrapping."))


# FIXME: Move to pology.?.
def select_field_wrapping (cfgsec=None, cat=None, cmlopt=None):

    # Default wrapping.
    wrapping = ["basic"]

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
