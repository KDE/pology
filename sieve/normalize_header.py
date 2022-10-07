# -*- coding: UTF-8 -*-

"""
Check and rearrange content of PO header into canonical form.

Documented in C{doc/user/sieving.docbook}.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

from pology import _, n_
from pology.normalize import canonical_header


def setup_sieve (p):

    p.set_desc(_("@info sieve discription",
    "Check and rearrange content of PO header into canonical form."
    ))


class Sieve (object):

    def __init__ (self, params):

        pass


    def process_header (self, hdr, cat):

        canonical_header(hdr, cat)

