# -*- coding: UTF-8 -*-

"""
Equip catalog headers within KDE Translation Project with extra information.

This sieve applies L{hook.equip_header.equip_header_tp_kde} to catalog headers.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

from pology.hook.equip_header import equip_header_tp_kde


def setup_sieve (p):

    p.set_desc(
    "Equip catalog headers within KDE Translation Project "
    "with extra information."
    )


class Sieve (object):

    def __init__ (self, params):

        pass


    def process_header (self, hdr, cat):

        equip_header_tp_kde(hdr, cat)

