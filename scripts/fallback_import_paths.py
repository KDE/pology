# -*- coding: UTF-8 -*-

"""
Insert fallback import paths in scripts.

In case the C{PYTHONPATH} environment variable does not contain path
to Pology library modules needed by scripts, this module will append
all guesses for Pology library paths to system path.
The assumption is that scripts themselves are in their default location
in Pology source tree.

Import this module before any imports from Pology library, in each script
in this directory that depends on Pology library::

    try:
        import fallback_import_paths
    except:
        pass

    from pology.foo import bar
    from pology.qwyx import baz
    ...

The try-except wrapper is needed because when scripts are properly installed,
this module will not be available (nor needed).

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import sys
from os.path import realpath, sep, dirname

pologypath = sep.join(realpath(sys.argv[0]).split(sep)[:-2])
sys.path.insert(0, pologypath)
