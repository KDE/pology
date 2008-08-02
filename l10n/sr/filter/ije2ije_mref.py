# -*- coding: UTF-8 -*

"""
Transform iyekavian text with marked yat-reflexes into clean iyekavian.

See L{ije2e_mref} for explanation of the markup.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

from pology.misc.report import warning
from pology.misc.resolve import resolve_alternatives_simple

from pology.l10n.sr.filter.ije2e_mref import _reflex_mark, _ije_althead


def process (text):
    """
    Filter's main processor.
    """

    ntext = text.replace(_reflex_mark, "")
    ntext = resolve_alternatives_simple(ntext, 2, 2, althead=_ije_althead)

    return ntext

