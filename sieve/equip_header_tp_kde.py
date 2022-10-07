# -*- coding: UTF-8 -*-

"""
Equip catalog headers within KDE Translation Project with extra information.

Documented in C{doc/user/sieving.docbook}.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

from pology import _, n_
from pology.proj.kde.header import equip_header


def setup_sieve (p):

    p.set_desc(_("@info sieve discription",
    "Equip catalog headers within KDE Translation Project "
    "with extra information."
    ))


class Sieve (object):

    def __init__ (self, params):

        pass


    def process_header (self, hdr, cat):

        equip_header(hdr, cat)

