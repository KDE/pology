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
from pology.misc.diff import word_diff, tdiff


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


def hctocl (htext):
    """
    Resolve hybrid Cyrillic-Latin text into clean Cyrillic and clean Latin.

    @param htext: hybrid text
    @type htext: string

    @returns: Cyrillic and Latin texts
    @rtype: (string, string)
    """

    return hctoc(htext), hctol(htext)


def cltoh (textc, textl, delims=u"/|¦", full=False):
    """
    Construct hybrid Cyrillic text out of clean Cyrillic and Latin texts.

    Hybridization is performed by inserting alternatives directives
    for parts which cannot be resolved by direct transliteration.
    If C{full} is set to C{True}, complete texts are unconditionally
    wrapped into single alternatives directive.

    @param textc: Cyrillic text
    @type textc: string
    @param textl: Latin text
    @type textl: string
    @param delims: possible delimiter characters
    @type delims: string
    @param full: whether to wraf full texts as single alternatives directive
    @type full: bool

    @returns: hybrid Cyrillic text
    @rtype: string
    """

    if not full:
        wdiff = word_diff(ctol(textc), textl)
        textc = _padc(textc)
        segs = []
        i = 0
        ic = 0
        while i < len(wdiff):
            tag, seg = wdiff[i]
            if tag == " ":
                segc = textc[ic:ic + len(seg)]
                segs.append(segc)
            else:
                seg2 = wdiff[i + 1][1] if i + 1 < len(wdiff) else ""
                if tag == "-":
                    segc = textc[ic:ic + len(seg)]
                    segl = seg2
                else:
                    segc = textc[ic:ic + len(seg2)]
                    segl = seg
                i += 1
                segs.append(_shyb_althead + _delimit([segc, segl], delims))
            ic += len(seg)
            i += 1
        return _unpadc("".join(segs))

    else:
        return _shyb_althead + _delimit([textc, textl], delims)

    return "".join(segs)


_padc_chr = u"\u0004"
_padc_alphas = (u"љ", u"њ", u"џ", u"Љ", u"Њ", u"Џ")

def _padc (text):

    for alpha in _padc_alphas:
        text = text.replace(alpha, _padc_chr + alpha)
    return text

def _unpadc (text):

    for alpha in _padc_alphas:
        text = text.replace(_padc_chr + alpha, alpha)
    return text


# Jat-reflex map (Latin script and letter cases derived afterwards).
_reflex_map = {
    # - basic cases
    u"ије": u"е",
    u"иј": u"е",
    u"је": u"е",
    u"ље": u"ле",
    u"ње": u"не",
    u"ио": u"ео",
    u"иљ": u"ел",
    # - special cases
    u"лије": u"ли",
    u"лијен": u"лењ",
    u"мија": u"меја",
    u"мије": u"мејe",
    u"мију": u"меју",
    u"није": u"ни",
    u"бијел": u"бео",
    u"цијел": u"цео",
}
# Derive Latin cases.
_reflex_map.update([map(ctol, x) for x in _reflex_map.items()]) # must be first
# Derive cases with first letter in uppercase.
_reflex_map.update([map(unicode.capitalize, x) for x in _reflex_map.items()])
# Derive cases with all letters in uppercase.
_reflex_map.update([map(unicode.upper, x) for x in _reflex_map.items()])

_max_reflex_btrk = 1 # at most one previous character for special cases
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


def hitoiq (text):
    """
    Like L{hitoi}, but does not output warnings on problems [type F1A hook].
    """

    return _hitoi_w(text, silent=True)


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


def hitoeq (text):
    """
    Like L{hitoe}, but does not output warnings on problems [type F1A hook].
    """

    return _hitoe_w(text, silent=True)


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
        if not text[p:p + 1].isalpha():
            segs.append(_reflex_mark)
            continue

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

    srcname = None
    if not silent:
        srcname="<text>"
    ntext = "".join(segs)
    ntext = resolve_alternatives_simple(ntext, 1, 2, althead=_dhyb_althead,
                                        srcname=srcname)

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


def hitoei (htext):
    """
    Resolve hybrid Ijekavian-Ekavain text into clean Ekavian and Ijekavian.

    @param htext: hybrid text
    @type htext: string

    @returns: Ekavian and Ijekavian text
    @rtype: (string, string)
    """

    return hitoe(htext), hitoi(htext)


def eitoh (texte, texti, delims=u"/|¦", refonly=False):
    """
    Construct hybrid Ijekavian text out of clean Ekavian and Ijekavian texts.

    Hybridization is performed by inserting reflex marks where possible,
    and alternatives directives by dialect otherwise.
    Both input texts should be in same script, Cyrillic or Latin.

    If alternatives directives should not be used, but only reflex marks,
    C{refonly} is set to C{True}. In that case, segments which cannot be
    hybridized by reflex marks will be left as they are in Ijekavian text.
    The intention behind this is that alternatives directives have
    been added manually where necessary, and that other changes are fixes
    made during conversion of Ekavian to Ijekavian text
    which hold for both dialects.

    @param texte: Ekavian text
    @type texte: string
    @param texti: Ijekavian text
    @type texti: string
    @param delims: possible delimiter characters
    @type delims: string
    @param refonly: whether to only use reflex marks
    @type refonly: bool

    @returns: hybrid Ijekavian text
    @rtype: string
    """

    # If character-level diff is done at once, weird segments may appear.
    # Instead, first diff on word-level, then on character-level.
    wdiff = word_diff(texte, texti)
    cdiff = []
    i = 0
    while i < len(wdiff):
        tag1, seg1 = wdiff[i]
        tag2, seg2 = wdiff[i + 1] if i + 1 < len(wdiff) else ("", "")
        if (tag1 == "-" and tag2 == "+") or (tag1 == "+" and tag2 == "-"):
            if tag1 == "+" and tag2 == "-": # reverse from expected order
                seg1, seg2 = seg2, seg1
            cdiff.extend(tdiff(seg1, seg2))
            i += 2
        else:
            cdiff.extend([(tag1, c) for c in seg1])
            i += 1

    lenc = len(cdiff)
    ie = 0; iep = 0; ii = 0; iip = 0; ic = 0
    segs = []
    while True:
        while ic < lenc and cdiff[ic][0] == " ":
            ic += 1; ie += 1; ii += 1
        if ic == lenc:
            segs.append(texte[iep:])
            break
        # Try to hybridize difference by reflex marks.
        for btrk in range(_max_reflex_btrk, -1, -1):
            ieb = ie - btrk
            iib = ii - btrk
            if ieb < iep or iib < iip:
                continue
            maxrlen = _max_reflex_len - _max_reflex_btrk + btrk
            frme = None
            for rlen in range(maxrlen, 0, -1):
                frmi = texti[iib:iib + rlen]
                frme = _reflex_map.get(frmi)
                if frme is not None and frme == texte[ieb:ieb + len(frme)]:
                    # Advance the diff according to this reflex pair
                    # and check that it covers both reflexes equally.
                    icn = ic
                    le = len(frme); li = len(frmi)
                    while le > 0  and li > 0:
                        if cdiff[icn][0] != "+":
                            le -= 1
                        if cdiff[icn][0] != "-":
                            li -= 1
                        icn += 1
                    if le == 0 and li == 0:
                        break
            if frme is not None:
                break
        if frme is not None:
            # Hybridization by reflex mark possible.
            segs.append(texte[iep:ieb])
            segs.append(_reflex_mark + frmi)
            iep = ieb + len(frme)
            iip = iib + len(frmi)
            ic = icn
        else:
            # Hybridization by reflex mark not possible.
            # Use alternatives directive, or pure Ijekavian.
            frme = ""; frmi = ""
            segs.append(texte[iep:ie])
            while ic < lenc and cdiff[ic][0] != " ":
                tag, c = cdiff[ic]
                if tag == "-":
                    frme += c; ie += 1
                else:
                    frmi += c; ii += 1
                ic += 1
            iep = ie
            iip = ii
            if not refonly:
                segs.append(_dhyb_althead + _delimit([frme, frmi], delims))
            else:
                segs.append(frmi)
        ie = iep
        ii = iip

    return "".join(segs)


def hictoec (text):
    """
    Resolve hybrid Ijekavian-Ekavian Cyrillic-Latin text into
    clean Ekavian Cyrillic text [type F1A hook].
    """

    return hctoc(hitoe(text))


def hictoecq (text):
    """
    Like L{hictoec}, but does not output warnings on problems [type F1A hook].
    """

    return hctoc(hitoeq(text))


def hictoel (text):
    """
    Resolve hybrid Ijekavian-Ekavian Cyrillic-Latin text into
    clean Ekavian Latin text [type F1A hook].
    """

    return hctol(hitoe(text))


def hictoic (text):
    """
    Resolve hybrid Ijekavian-Ekavian Cyrillic-Latin text into
    clean Ijekavian Cyrillic text [type F1A hook].
    """

    return hctoc(hitoi(text))


def hictoicq (text):
    """
    Like L{hictoic}, but does not output warnings on problems [type F1A hook].
    """

    return hctoc(hitoiq(text))


def hictoil (text):
    """
    Resolve hybrid Ijekavian-Ekavian Cyrillic-Latin text into
    clean Ijekavian Latin text [type F1A hook].
    """

    return hctol(hitoi(text))


def hictoall (htext):
    """
    Resolve hybrid Ijekavian-Ekavian Cyrillic-Latin text into
    all four clean variants.

    @param htext: hybrid text
    @type htext: string

    @returns: Ekavian Cyrillic, Ekavian Latin, Ijekavian Cyrillic,
        and Ijekavian Latin text
    @rtype: (string, string, string, string)
    """

    htextc = hctoc(htext)
    htextl = hctol(htext)

    return hitoe(htextc), hitoe(htextl), hitoi(htextc), hitoi(htextl)


def _delimit (alts, delims):

    good = False
    for delim in delims:
        good = True
        for alt in alts:
            if delim in alt:
                good = False
                break
        if good:
            break

    if not good:
        raise StandardError("No delimiter from '%s' can be used for "
                            "alternatives directive on: %s."
                            % (delims, " ".join(["{%s}" % x for x in alts])))

    return delim + delim.join(alts) + delim

