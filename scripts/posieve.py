#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
Sieve messages in collections of PO files.

Compatibility wrapper; the implementation is in C{pology.scripts.posieve}.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

try:
    import fallback_import_paths
except Exception:
    pass

from pology.fsops import exit_on_exception
from pology.scripts.posieve import main


if __name__ == '__main__':
    exit_on_exception(main)
