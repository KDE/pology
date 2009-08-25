# -*- coding: UTF-8 -*

"""
Process yekavian text with marked yat-reflexes.

Yat-reflexes are marked by inserting a special character, C{›},
just before the part of the word that differs from ekavian form::

    Д›ио б›иљежака о В›јештичјој р›ијеци.

or, for special cases where this would not work, one letter earlier::

    Не до›лијевај уље на ватру, ›нијесам се с›мијао.

For extremely rare cases, it is possible to provide a substring in
both ekavian and yekavian forms, in that order::

    Гд›је с' ~#/то/ба/ пошо̑?

where any character may be consistently used instead of C{/}.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

from pology.misc.report import warning
from pology.misc.resolve import resolve_alternatives_simple
from pology.misc.resolve import resolve_alternatives


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
    u"лијен": u"лењ",
    u"мија": u"меја",
    u"мије": u"мејe",
    u"није": u"ни",
}
_max_reflex_len = max(map(lambda x: len(x), _reflex_map.keys()))
# ...using map() instead of [] to avoid x in global environment.

_reflex_mark = u"›"
_reflex_mark_len = len(_reflex_mark)
_ije_althead = "~#"


def to_e (text):
    """
    Resolve marked yekavian into clean ekavian text [type F1A hook].

    @return: text
    """

    return _to_e_worker(text, silent=False)


def to_e_s (text):
    """
    Like L{to_e}, but it silently ignores problems [type F1A hook].

    @return: text
    """

    return _to_e_worker(text, silent=True)


def _to_e_worker (text, silent=False):
    """
    Worker for C{to_e*} hooks.
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
            segs.append(text[(p - _reflex_mark_len):p])
            if not silent:
                dreflex = text[(p - _reflex_mark_len):(p + _max_reflex_len + 1)]
                warning("unknown yat-reflex at '%s...', skipped" % dreflex)

    ntext = "".join(segs)
    ntext = resolve_alternatives_simple(ntext, 1, 2, althead=_ije_althead,
                                        srcname="<text>")

    return ntext


def to_ije (text):
    """
    Resolve marked yekavian into clean yekavian text [type F1A hook].

    @return: text
    """

    return _to_ije_worker(text, silent=False)


def to_ije_s (text):
    """
    Like L{to_ije}, but it silently ignores problems [type F1A hook].

    @return: text
    """

    return _to_ije_worker(text, silent=True)


def _to_ije_worker (text, silent=False):
    """
    Worker for C{to_ije*} hooks.
    """

    ntext = text.replace(_reflex_mark, "")
    srcname = None
    if not silent:
        srcname="<text>"
    ntext = resolve_alternatives_simple(ntext, 2, 2, althead=_ije_althead,
                                        srcname=srcname)

    return ntext


def validate (text):
    """
    Check whether all marked yat-reflexes are known [type V1A hook].

    @return: type V1A hook
    @rtype: C{(text) -> spans}
    """

    spans = []
    p = 0
    while True:
        pp = p
        p = text.find(_reflex_mark, p)
        if p < 0:
            break
        p += _reflex_mark_len

        # Check if yat-reflex can be resolved.
        for rl in range(_max_reflex_len, 0, -1):
            reflex = text[p:(p + rl + 1)]
            ekvform = _reflex_map.get(reflex)
            if ekvform is not None:
                break
        if not ekvform:
            start, end = p - _reflex_mark_len, p + _max_reflex_len + 1
            dreflex = text[start:end]
            errmsg = "unknown yat-reflex at '%s...'" % dreflex
            spans.append((start, end, errmsg))

    d1, ngood, allgood = resolve_alternatives(text, 1, 2, althead=_ije_althead)
    if not allgood:
        errmsg = ("malformed ekavian-yekavian alternative encountered "
                  "after %d good" % ngood)
        spans.append((0, 0, errmsg))

    return spans

