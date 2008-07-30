# -*- coding: UTF-8 -*

"""
Transform iyekavian text with marked yat-reflexes into clean iyekavian.

See L{ije2e_mref} for explanation of the markup.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

from pology.misc.report import warning
from pology.misc.resolve import resolve_alternatives_simple

from pology.l10n.sr.filter.ije2e_mref import _reflex_mark


_reflex_mark_len = len(_reflex_mark)


def process (text):
    """
    Filter's main processor.
    """

    segs = []
    p = 0
    while True:
        pp = p
        p = text.find(_reflex_mark, p)
        if p < 0:
            segs.append(text[pp:])
            break
        segs.append(text[pp:p])
        p += _reflex_mark_len

    ntext = "".join(segs)
    ntext = resolve_alternatives_simple(ntext, 2, 2, althead="~#")

    return ntext

