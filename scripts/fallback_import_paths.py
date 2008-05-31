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
import os

pologypath = os.path.sep.join(sys.argv[0].split(os.path.sep)[:-3])
sys.path.append(pologypath)
