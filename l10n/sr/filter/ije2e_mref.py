# -*- coding: UTF-8 -*

"""
Transform iyekavian text with marked yat-reflexes into ekavian.

Yat-reflexes are marked by inserting a special character, C{›},
just before the part of the word that differs from ekavian form::

    Д›ио б›иљежака о В›јештичјој р›ијеци.

or, for special cases where this would not work, one letter earlier::

    Не до›лијевај уље на ватру, ›нијесам се с›мијао.

For extremely rare cases, it is possible to provide a substring in
both ekavian and iyekavian forms, in that order::

    Гд›је с' ~#/то/ба/ пошо̑?

where any character may be consistently used instead of C{/}.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

from pology.misc.report import warning
from pology.misc.resolve import resolve_alternatives_simple


_reflex_map = {
    # - basic
    u"ије": u"е",
    u"иј": u"е",
    u"је": u"е",
    u"ље": u"ле",
    u"ње": u"не",
    u"ио": u"ео",
    u"иљ": u"ел",

    # - special cases (include one prev. letter)
    u"лије": u"ли",
    u"мија": u"меја",
    u"мије": u"мејe",
    u"није": u"ни",
}
_max_reflex_len = max(map(lambda x: len(x), _reflex_map.keys()))
# ...using map() instead of [] to avoid x in global environment.

_reflex_mark = u"›"
_reflex_mark_len = len(_reflex_mark)
_ije_althead = "~#"


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

        # Try to resolve yat-reflex.
        for rl in range(_max_reflex_len, 0, -1):
            reflex = text[p:(p + rl + 1)]
            ekvform = _reflex_map.get(reflex)
            if ekvform is not None:
                break

        if ekvform:
            segs.append(ekvform)
            p += len(reflex)
        else:
            dreflex = text[(p - _reflex_mark_len):(p + _max_reflex_len + 1)]
            warning("unknown yat-reflex '%s...', skipped" % dreflex)
            segs.append(text[(p - _reflex_mark_len):p])

    ntext = "".join(segs)
    ntext = resolve_alternatives_simple(ntext, 1, 2, althead=_ije_althead)

    return ntext

