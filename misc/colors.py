# -*- coding: UTF-8 -*-
"""
Standard codes for shell colors.

@author: Sébastien Renard <sebastien.renard@digitalfox.org>
@license: GPLv3
"""

BOLD     = '\033[01m'
RED     = '\033[31m'
GREEN     = '\033[32m'
ORANGE     = '\033[33m'
BLUE     = '\033[34m'
PURPLE     = '\033[35m'
CYAN    = '\033[36m'
GREY    = '\033[37m'
RESET     = '\033[0;0m'


_color_names = "BOLD RED GREEN ORANGE BLUE PURPLE CYAN GREY RESET".split()

class _ColorData (object):
    pass


_shell_colors = _ColorData()
for color in _color_names:
    setattr(_shell_colors, color, eval(color))

_noop_colors = _ColorData()
for color in _color_names:
    setattr(_noop_colors, color, "")


def colors_for_file (file):
    """
    Appropriate colors for file descriptor.

    @param file: file for which the colors are requested
    @type file: file descriptor

    @returns: color codes
    @rtype: object with color names as instance variables
    """

    if not _cglobals.outdep or file.isatty():
        return _shell_colors
    else:
        return _noop_colors


def set_coloring_globals (outdep=True):
    """
    Set global options for coloring.

    @param outdep: whether coloring depends on output file descriptor
    @type outdep: bool
    """

    _cglobals.outdep = outdep


class _Data: pass
_cglobals = _Data()
set_coloring_globals()

