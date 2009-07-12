# -*- coding: UTF-8 -*-

"""
Resolve hybrid Serbian text into final variants.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import pology.l10n.sr.hook.cyr2lat as C2L
from pology.misc.resolve import resolve_alternatives_simple


def alts_to_cyr (text):
    """
    Resolve Cyrillic text with alternatives into final Cyrillic text.

    Alternative directives are a way to have hybrid Cyrillic text out
    of which non-directly transliterated Latin text can be constructed,
    as well as ordinary Cyrillic text.
    For example, this function and L{alts_to_lat} will resolve the text::

        Различите ~@/линукс/Linux/ дистрибуције...

    into, respectively::

        Различите линукс дистрибуције...
        Različite Linux distribucije...

    See L{resolve_alternatives()< pology.misc.resolve.resolve_alternatives>}
    function for more details on format of alternatives directives.

    @return: text with resolved alternatives
    """

    return resolve_alternatives_simple(text, 1, 2)


def alts_to_lat (text):
    """
    Resolve Cyrillic text with alternatives into final Latin text.

    See L{alts_to_cyr()}.
    """

    return resolve_alternatives_simple(text, 2, 2, outfilter=C2L.process)

