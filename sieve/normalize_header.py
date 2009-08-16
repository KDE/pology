# -*- coding: UTF-8 -*-

"""
Check and rearrange content of PO header into canonical form.

This sieve applies the L{normalize_header<hook.normalize_header>} hook
to catalog headers.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

from pology.hook.normalize_header import normalize_header


def setup_sieve (p):

    p.set_desc(
    "Check and rearrange content of PO header into canonical form."
    )


class Sieve (object):

    def __init__ (self, params):

        pass


    def process_header (self, hdr, cat):

        normalize_header(hdr, cat)

