# -*- coding: UTF-8 -*

"""
Conversions between scripts and dialects in Serbian.

Serbian standard literary language can be written in two dialects,
Ekavian and Ijekavian, and two scripts, Cyrillic and Latin.
Dialects and scripts can be freely combined, resulting in four
official writing standards: Ekavian Cyrillic, Ekavian Latin,
Ijekavian Cyrillic, and Ijekavian Latin.
Some automatic and semi-automatic conversions between them are possible.


Script Transliteration
======================

For plain text containing only Serbian words (including well adapted loans),
it is trivial to transliterate from Cyrillic to Latin script.
It is only necessary to take care when converting Cyrillic Љ, Њ, Џ into
Latin digraphs Lj, Nj, Dž, because sometimes they should be full upper-case
(e.g. Љубљана→Ljubljana, ЉУБЉАНА→LJUBLJANA).
But this is easily algorithmically resolvable, by checking if
the previous or the next letter are upper-case too.

To transliterate from Latin to Cyrillic is somewhat harder, because
in rare cases digraphs nj, lj, dž may not be single, but standalone letters;
i.e. they do not map Cyrillic to љ, њ, џ, but to лј, нј, дж
(dablju→даблју, konjunkcija→конјункција, nadživeti→надживети).
The only way to handle this is by having a dictionary of special cases.

Furthermore, in today's practice texts are rarely clean as assumed above.
They are frequently riddled with foreign Latin phrases (such as proper names)
quasiphrases (such as electronic addresses), and constructive elements
(such as markup tags). On the other hand, foreign Cyrillic phrases are
quite infrequent (may be found e.g. in texts on linguistic topics).
This means that in practice transliteration from Cyrillic to Latin
remains straightforward, but from Latin to Cyrillic decidedly not so.


Script Hybridization
====================

Sometimes the result of direct transliteration from Cyrillic to Latin
is against the established Latin practice in a certain field,
even if valid according to official orthography.
Then it becomes necessary to specially handle some parts of the text
(e.g. transliterations or lack thereof of foreign proper names).

Alternatives directives are a way to compose "hybrid" Cyrillic-Latin text,
out of which both ordinary Cyrillic and non-directly transliterated Latin
texts can be automatically derived.
For example, this hybrid text::

    Различите ~@/линукс/Linux/ дистрибуције...

can be automatically resolved into::

    Различите линукс дистрибуције...
    Različite Linux distribucije...

String C{~@} is the head of alternatives directive.
It is followed by a single character, which is then used to delimit
Cyrillic and Latin parts, in that order, out of surrounding text.
(For all details on format of alternatives directives, see
L{resolve_alternatives()< pology.misc.resolve.resolve_alternatives>}).
Transliteration from Cyrillic to Latin is performed only on text
outside of alternatives directives.


Dialect Hybridization
=====================

Both Ekavian and Ijekavian dialect may be represented within single text.
Such hybrid text is basically Ijekavian, but jat-reflexes are marked
by inserting a reflex mark character, C{›}, just before the part of
the word that differs from Ekavian form::

    Д›ио б›иљежака о В›јештичјој р›ијеци.

Straight Ijekavian text is then obtained by just removing reflex marks,
and Ekavian by applying rules such as је→е, ије→е, ио→ео, etc.::

    Дио биљежака о Вјештичјој ријеци.
    Део бележака о Вештичјој реци.

In some special cases this does not work. For example::

    Л›ијено се окрете, па се насм›ија.

would resolve into part unusual part wrong Ekavian form::

    Лено се окрете, па се насмеа.

In such cases, reflex mark is simply inserted one letter earlier::

    ›Лијено се окрете, па се нас›мија.

and special-case rules (such as мија→меја, etc.) are applied instead.

For extremely rare special cases, it is possible to directly provide
different forms for Ekavian and Ijekavian, in that order,
by using alternatives directive::

    Гд›је с' ~#/то/ба/ пошо̑?

Compared to alternatives directives for scripts, the only difference is
that here the directive head is C{~#}.
Alternatives directives for script and dialect can thus be mixed
without conflicts, in single text and even interwoven
(when interweaving, different delimiters must be used).


@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

from pology.misc.report import warning
from pology.misc.resolve import resolve_alternatives_simple
from pology.misc.resolve import resolve_alternatives


# Transliteration table Serbian Cyrillic->Latin.
_dict_c2l = {
    u'а':u'a', u'б':u'b', u'в':u'v', u'г':u'g', u'д':u'd', u'ђ':u'đ',
    u'е':u'e', u'ж':u'ž', u'з':u'z', u'и':u'i', u'ј':u'j', u'к':u'k',
    u'л':u'l', u'љ':u'lj',u'м':u'm', u'н':u'n', u'њ':u'nj',u'о':u'o',
    u'п':u'p', u'р':u'r', u'с':u's', u'т':u't', u'ћ':u'ć', u'у':u'u',
    u'ф':u'f', u'х':u'h', u'ц':u'c', u'ч':u'č', u'џ':u'dž',u'ш':u'š',
    u'А':u'A', u'Б':u'B', u'В':u'V', u'Г':u'G', u'Д':u'D', u'Ђ':u'Đ',
    u'Е':u'E', u'Ж':u'Ž', u'З':u'Z', u'И':u'I', u'Ј':u'J', u'К':u'K',
    u'Л':u'L', u'Љ':u'Lj',u'М':u'M', u'Н':u'N', u'Њ':u'Nj',u'О':u'O',
    u'П':u'P', u'Р':u'R', u'С':u'S', u'Т':u'T', u'Ћ':u'Ć', u'У':u'U',
    u'Ф':u'F', u'Х':u'H', u'Ц':u'C', u'Ч':u'Č', u'Џ':u'Dž',u'Ш':u'Š',
    # accented NFC:
    u'ѐ':u'è', u'ѝ':u'ì', u'ӣ':u'ī', u'ӯ':u'ū',
    u'Ѐ':u'È', u'Ѝ':u'Ì', u'Ӣ':u'Ī', u'Ӯ':u'Ū',
    # frequent accented from NFD to NFC (keys now 2-char):
    u'а̂':u'â', u'о̂':u'ô', u'а̑':u'ȃ', u'о̑':u'ȏ',
}

# Transliteration table Serbian Cyrillic->ASCII, basic stripped.
_dict_c2a_stripped = _dict_c2l.copy()
_dict_c2a_stripped.update({
    u'ђ':u'dj', u'ж':u'z', u'ћ':u'c', u'ч':u'c', u'џ':u'dz', u'ш':u's',
    u'Ђ':u'Dj', u'Ж':u'Z', u'Ћ':u'C', u'Ч':u'C', u'Џ':u'Dz', u'Ш':u'S',
})

# Transliteration table Serbian Latin->ASCII, basic stripped.
_dict_l2a_stripped = {
    u'đ':u'dj', u'ž':u'z', u'ć':u'c', u'č':u'c', u'š':u's',
    u'Đ':u'Dj', u'Ž':u'Z', u'Ć':u'C', u'Č':u'C', u'Š':u'S',
}

# Transliteration table Serbian any->ASCII, basic stripped.
_dict_cl2a_stripped = {}
_dict_cl2a_stripped.update(_dict_c2a_stripped)
_dict_cl2a_stripped.update(_dict_l2a_stripped)

# Transliteration table English in Serbian Cyrillic->Latin, by keyboard layout.
_dict_c2a_englay = _dict_c2l.copy()
_dict_c2a_englay.update({
    u'љ':u'q', u'њ':u'w', u'ж':u'y', u'џ':u'x',
    u'Љ':u'Q', u'Њ':u'W', u'Ж':u'Y', u'Џ':u'X',
})


def  ctol (text):
    """
    Transliterate text from Cyrillic to proper Latin [type F1A hook].
    """

    return _ctol_w(text, _dict_c2l)


def cltoa (text):
    """
    Transliterate text from Cyrillic or Latin to stripped ASCII
    [type F1A hook].
    """

    return _ctol_w(text, _dict_cl2a_stripped)


def ectol (text):
    """
    Transliterate text from English in Cyrillic by keyboard layout
    to proper English [type F1A hook].
    """

    return _ctol_w(text, _dict_c2a_englay)


def _ctol_w (text, trdict):

    # NOTE: Converted directly from C++ code,
    # perhaps something more efficient is possible.

    tlen = len(text)
    ntext = u""
    for i in range(tlen):
        c = text[i]
        c2 = text[i:i+2]
        r = trdict.get(c2) or trdict.get(c)
        if r is not None:
            if len(r) > 1 and c.isupper() \
            and (   (i + 1 < tlen and text[i + 1].isupper()) \
                 or (i > 0 and text[i - 1].isupper())):
                ntext += r.upper()
            else:
                ntext += r
        else:
            ntext += c

    return ntext


_shyb_althead = "~@"


def hctoc (text):
    """
    Resolve hybrid Cyrillic text with script alternatives into
    plain Cyrillic text [type F1A hook].
    """

    return resolve_alternatives_simple(text, 1, 2, althead=_shyb_althead)


def hctol (text):
    """
    Resolve hybrid Cyrillic text with script alternatives into
    plain Latin text [type F1A hook].
    """

    return resolve_alternatives_simple(text, 2, 2, althead=_shyb_althead,
                                       outfilter=ctol)


# Jat-reflex map Cyrillic->Cyrillic and Latin->Latin.
_reflex_map = {
    # - basic
    u"ије": u"е",
    u"ИЈЕ": u"Е",
    u"иј": u"е",
    u"ИЈ": u"Е",
    u"је": u"е",
    u"ЈЕ": u"Е",
    u"ље": u"ле",
    u"ЉЕ": u"ЛЕ",
    u"ње": u"не",
    u"ЊЕ": u"НЕ",
    u"ио": u"ео",
    u"ИО": u"ЕО",
    u"иљ": u"ел",
    u"ИЉ": u"ЕЛ",

    # - special cases
    u"лије": u"ли",
    u"ЛИЈЕ": u"ЛИ",
    u"лијен": u"лењ",
    u"Лијен": u"Лењ",
    u"ЛИЈЕН": u"ЛЕЊ",
    u"мија": u"меја",
    u"МИЈА": u"МЕЈА",
    u"мије": u"мејe",
    u"МИЈЕ": u"МЕЈE",
    u"није": u"ни",
    u"НИЈЕ": u"НИ",
}
_reflex_map.update(map(lambda x: map(ctol, x), _reflex_map.items()))
_max_reflex_len = max(map(lambda x: len(x), _reflex_map.keys()))

_reflex_mark = u"›"
_reflex_mark_len = len(_reflex_mark)
_dhyb_althead = "~#"


def hitoi (text):
    """
    Resolve hybrid Ijekavian text with reflex marks and dialect alternatives
    into plain Ijekavian text [type F1A hook].
    """

    return _hitoi_w(text)


def _hitoi_w (text, silent=False):

    ntext = text.replace(_reflex_mark, "")
    srcname = None
    if not silent:
        srcname="<text>"
    ntext = resolve_alternatives_simple(ntext, 2, 2, althead=_dhyb_althead,
                                        srcname=srcname)

    return ntext


def hitoe (text):
    """
    Resolve hybrid Ijekavian text with reflex marks and dialect alternatives
    into plain Ekavian text [type F1A hook].
    """

    return _hitoe_w(text)


def _hitoe_w (text, silent=False):

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

        # Try to resolve jat-reflex.
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
                warning("Unknown jat-reflex at '%s...', skipped." % dreflex)

    ntext = "".join(segs)
    ntext = resolve_alternatives_simple(ntext, 1, 2, althead=_dhyb_althead,
                                        srcname="<text>")

    return ntext


def validate_dhyb (text):
    """
    Check whether dialect-hybrid text is valid [type V1A hook].
    """

    spans = []
    p = 0
    while True:
        pp = p
        p = text.find(_reflex_mark, p)
        if p < 0:
            break
        p += _reflex_mark_len

        # Check if jat-reflex can be resolved.
        for rl in range(_max_reflex_len, 0, -1):
            reflex = text[p:(p + rl + 1)]
            ekvform = _reflex_map.get(reflex)
            if ekvform is not None:
                break
        if not ekvform:
            start, end = p - _reflex_mark_len, p + _max_reflex_len + 1
            dreflex = text[start:end]
            errmsg = "Unknown jat-reflex at '%s...'." % dreflex
            spans.append((start, end, errmsg))

    d1, ngood, allgood = resolve_alternatives(text, 1, 2, althead=_dhyb_althead)
    if not allgood:
        errmsg = ("Malformed Ekavian-Ijekavian alternatives directive "
                  "encountered after %d good directives." % ngood)
        spans.append((0, 0, errmsg))

    return spans

