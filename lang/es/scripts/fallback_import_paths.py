# -*- coding: UTF-8 -*-

"""
Insert fallback import paths in scripts for Spanish language.

Used within scripts for Spanish language like its counterpart
for general scripts (scripts/fallback_import_paths.py).

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import sys
from os.path import realpath, sep

pologypath = sep.join(realpath(sys.argv[0]).split(sep)[:-4])
sys.path.insert(0, pologypath)
