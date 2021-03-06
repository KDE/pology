# -*- coding: UTF-8 -*-

"""
Standard command line options.

This module defines command lines options frequently used by various scripts,
in a form suitable for adding to their option lists.

All functions in this module take an C{optparse.OptionParser} instance,
possibly followed by some optional parameters, and return C{None}.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

from pology import _, n_
from pology.colors import get_coloring_types
from pology.report import format_item_list


def add_cmdopt_incexc (opars, ormatch=False):
    """
    Regular expressions to include and exclude files and directories
    by matching names and paths.

    @param ormatch: whether multiple expressions are linked by OR operation
    @type ormatch: bool

    @see: L{build_path_selector()<fsops.build_path_selector>}
    """

    if not ormatch:
        inclink = _("@info command line option description (partial: incexc)",
                    "The option can be repeated, in which case a file "
                    "is included only if all expressions match it.")
        exclink = _("@info command line option description (partial: incexc)",
                    "The option can be repeated, in which case a file "
                    "is excluded only if all expressions match it.")
    else:
        inclink =  _("@info command line option description (partial: incexc)",
                     "The option can be repeated, in which case a file "
                     "is included if at least one expression matches it.")
        exclink =  _("@info command line option description (partial: incexc)",
                     "The option can be repeated, in which case a file "
                     "is excluded if at least one expression matches it.")

    opars.add_option(
        "-e", "--exclude-name",
        metavar=_("@info command line value placeholder", "REGEX"),
        dest="exclude_names", action="append",
        help=_("@info command line option description. "
               "%(incexc)s is one of the above partial descriptions.",
               "Exclude from processing files with names "
               "(base name without extension) "
               "matching given regular expression. %(incexc)s",
               incexc=exclink))
    opars.add_option(
        "-E", "--exclude-path",
        metavar=_("@info command line value placeholder", "REGEX"),
        dest="exclude_paths", action="append",
        help=_("@info command line option description. "
               "%(incexc)s is one of the partial descriptions above.",
               "Exclude from processing files with paths "
               "matching given regular expression. %(incexc)s",
               incexc=exclink))
    opars.add_option(
        "-i", "--include-name",
        metavar=_("@info command line value placeholder", "REGEX"),
        dest="include_names", action="append",
        help=_("@info command line option description. "
               "%(incexc)s is one of the above partial descriptions.",
               "Include into processing only files with names "
               "(base name without extension) "
               "matching given regular expression. %(incexc)s",
               incexc=inclink))
    opars.add_option(
        "-I", "--include-path",
        metavar=_("@info command line value placeholder", "REGEX"),
        dest="include_paths", action="append",
        help=_("@info command line option description. "
               "%(incexc)s is one of the above partial descriptions.",
               "Include into processing only files with paths "
               "matching given regular expression. %(incexc)s",
               incexc=inclink))


def add_cmdopt_filesfrom (opars, cmnts=True, incexc=True):
    """
    File paths from which to collect list of file and directory paths.

    If C{cmnts} is set to C{True}, lines can be comments.
    If C{incexc} is set to C{True}, lines can be inclusion and exclusion
    directives.

    @param cmnts: whether to enable comments
    @type cmnts: bool
    @param incexc: whether to enable inclusion/exclusion regexes
    @type incexc: bool

    @see: L{collect_paths_from_file()<fsops.collect_paths_from_file>}
    """

    shead = _("@info command line option description (partial: head)",
              "Collect paths of files and directories from given file, "
              "which contains one path per line. "
              "If a path is not absolute, it is considered relative "
              "to current working directory.")
    scmnts = _("@info command line option description (partial: cmnts)",
               "Lines starting with '#' are treated as comments "
               "and skipped.")
    sincexc = _("@info command line option description (partial: incexc)",
                "Lines starting with ':' are treated as directives "
                "to include or exclude files/directories from processing, "
                "as follows: "
                ":-REGEX excludes by base name without extension; "
                ":/-REGEX excludes by full path; "
                ":+REGEX includes by base name without extension; "
                ":/+REGEX excludes by full path. "
                "If read directories are expanded into subpaths, "
                "these directives apply to those paths too.")
    stail = _("@info command line option description (partial: tail)",
              "The option can be repeated to collect paths "
              "from several files.")

    vd = dict(head=shead, cmnts=scmnts, incexc=sincexc, tail=stail)
    if cmnts and incexc:
        help = _("@info command line option description; "
                 "combined from the partial descriptions above",
                 "%(head)s %(cmnts)s %(incexc)s %(tail)s", **vd)
    elif incexc:
        help = _("@info command line option description; "
                 "combined from the partial descriptions above",
                 "%(head)s %(incexc)s %(tail)s", ** vd)
    elif cmnts:
        help = _("@info command line option description; "
                 "combined from the partial descriptions above",
                 "%(head)s %(cmnts)s %(tail)s", **vd)
    else:
        help = _("@info command line option description; "
                 "combined from the partial descriptions above",
                 "%(head)s %(tail)s", **vd)

    opars.add_option(
        "-f", "--files-from",
        metavar=_("@info command line value placeholder", "FILE"),
        dest="files_from", action="append",
        help=help)


def add_cmdopt_colors (opars):
    """
    Options for syntax coloring in output.
    """

    opars.add_option(
        "-R", "--raw-colors",
        action="store_true", dest="raw_colors", default=False,
        help=_("@info command line option description",
               "Syntax coloring in output independent of destination "
               "(whether terminal or file)."))
    defctype = "term"
    opars.add_option(
        "--coloring-type",
        metavar=_("@info command line value placeholder", "TYPE"),
        action="store", dest="coloring_type", default=defctype,
        help=_("@info command line option description",
               "Type of syntax coloring in output. "
               "Available types: %(typelist)s; default: %(type)s.",
               typelist=format_item_list(get_coloring_types()), type=defctype))


def add_cmdopt_wrapping (opars):
    """
    Options for wrapping in catalogs when writing them out.
    """

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
               "Fine wrapping: on logical breaks (e.g. some markup tags)."))
    opars.add_option(
        "--no-fine-wrap",
        action="store_false", dest="do_fine_wrap", default=None,
        help=_("@info command line option description",
               "No fine wrapping."))

