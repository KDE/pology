# -*- coding: UTF-8 -*-

"""
Insert fallback import paths in scripts.

In case the environment did not setup up C{PYTHONPATH} such that modules
needed by scripts can be found, this module will append all guesses for
import paths to system path. The assumption is that the scripts themselves
are in their default location in Pology tree.

Just import this module at the beginning of each script in this directory
that may benefit from non-standard paths.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import sys
from os.path import realpath, sep, dirname

# Library.
pologypath = sep.join(realpath(sys.argv[0]).split(sep)[:-2])
sys.path.insert(0, pologypath)

# For scripts to import from each other.
scriptpath = dirname(realpath(sys.argv[0]))
sys.path.insert(0, scriptpath)
