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
L{resolve_alternatives()< pology.resolve.resolve_alternatives>}).
Transliteration from Cyrillic to Latin is performed only on text
outside of alternatives directives.


Dialect Hybridization
=====================

Both Ekavian and Ijekavian dialect may be represented within single text.
Such hybrid text is basically Ijekavian, but jat-reflexes are marked
by inserting one of the jat-reflex ticks C{›}, C{‹}, C{▹}, C{◃}::

    Д‹ио б‹иљежака о В›јештичјој р›ијеци.

Clean Ijekavian text is then obtained by just removing jat-reflex ticks
preceding valid jat-reflexes, and Ekavian by applying the jat-reflex map::

    Дио биљежака о Вјештичјој ријеци.
    Део бележака о Вештичјој реци.

The jat-reflex mapping rules are as follows, grouped by tick:
  - ›ије→е, ›је→е
  - ‹иј→еј, ‹иљ→ел, ‹ио→ео, ‹ље→ле, ‹ње→не
  - ▹ије→и, ▹је→и
  - ◃ијел→ео, ◃ијен→ењ, ◃ит→ет, ◃ил→ел, ◃јел→ео, ◃тн→тњ, ◃шње→сне

For very rare special cases, it is possible to directly provide
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

from pology import PologyError, _, n_
from pology.diff import word_diff, tdiff
from pology.report import warning, format_item_list
from pology.resolve import resolve_alternatives_simple
from pology.resolve import resolve_alternatives


# Transliteration table Serbian Cyrillic->Latin.
_dict_c2l = {
    'а':'a', 'б':'b', 'в':'v', 'г':'g', 'д':'d', 'ђ':'đ',
    'е':'e', 'ж':'ž', 'з':'z', 'и':'i', 'ј':'j', 'к':'k',
    'л':'l', 'љ':'lj','м':'m', 'н':'n', 'њ':'nj','о':'o',
    'п':'p', 'р':'r', 'с':'s', 'т':'t', 'ћ':'ć', 'у':'u',
    'ф':'f', 'х':'h', 'ц':'c', 'ч':'č', 'џ':'dž','ш':'š',
    'А':'A', 'Б':'B', 'В':'V', 'Г':'G', 'Д':'D', 'Ђ':'Đ',
    'Е':'E', 'Ж':'Ž', 'З':'Z', 'И':'I', 'Ј':'J', 'К':'K',
    'Л':'L', 'Љ':'Lj','М':'M', 'Н':'N', 'Њ':'Nj','О':'O',
    'П':'P', 'Р':'R', 'С':'S', 'Т':'T', 'Ћ':'Ć', 'У':'U',
    'Ф':'F', 'Х':'H', 'Ц':'C', 'Ч':'Č', 'Џ':'Dž','Ш':'Š',
    # accented NFC:
    'ѐ':'è', 'ѝ':'ì', 'ӣ':'ī', 'ӯ':'ū',
    'Ѐ':'È', 'Ѝ':'Ì', 'Ӣ':'Ī', 'Ӯ':'Ū',
    # frequent accented from NFD to NFC (keys now 2-char):
    'а̂':'â', 'о̂':'ô', 'а̑':'ȃ', 'о̑':'ȏ',
}

# Transliteration table Serbian Cyrillic->ASCII, basic stripped.
_dict_c2a_stripped = _dict_c2l.copy()
_dict_c2a_stripped.update({
    'ђ':'dj', 'ж':'z', 'ћ':'c', 'ч':'c', 'џ':'dz', 'ш':'s',
    'Ђ':'Dj', 'Ж':'Z', 'Ћ':'C', 'Ч':'C', 'Џ':'Dz', 'Ш':'S',
})

# Transliteration table Serbian Latin->ASCII, basic stripped.
_dict_l2a_stripped = {
    'đ':'dj', 'ž':'z', 'ć':'c', 'č':'c', 'š':'s',
    'Đ':'Dj', 'Ž':'Z', 'Ć':'C', 'Č':'C', 'Š':'S',
}

# Transliteration table Serbian any->ASCII, basic stripped.
_dict_cl2a_stripped = {}
_dict_cl2a_stripped.update(_dict_c2a_stripped)
_dict_cl2a_stripped.update(_dict_l2a_stripped)

# Transliteration table English in Serbian Cyrillic->Latin, by keyboard layout.
_dict_c2a_englay = _dict_c2l.copy()
_dict_c2a_englay.update({
    'љ':'q', 'њ':'w', 'ж':'y', 'џ':'x',
    'Љ':'Q', 'Њ':'W', 'Ж':'Y', 'Џ':'X',
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
    ntext = ""
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


# Head of alternatives directives for script.
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


def cltoh (textc, textl, delims="/|¦", full=False):
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


_padc_chr = "\u0004"
_padc_alphas = ("љ", "њ", "џ", "Љ", "Њ", "Џ")

def _padc (text):

    for alpha in _padc_alphas:
        text = text.replace(alpha, _padc_chr + alpha)
    return text

def _unpadc (text):

    for alpha in _padc_alphas:
        text = text.replace(_padc_chr + alpha, alpha)
    return text


# Ijekavian to Ekavian map (Latin script and letter cases derived afterwards).
# All Ijekavian-Ekavian form pairs have to be unique across all groups.
# Within a group, one Ijekavian form must not be in the prefix of another.
_reflex_spec = (
    ("›", {
        "ије": "е",
        "је": "е",
    }),
    ("‹", {
        "иј": "еј", # гријати → грејати
        "иљ": "ел", # биљешка → белешка
        "ио": "ео", # дио → део
        "ље": "ле", # љето → лето
        "ње": "не", # гњев → гнев
    }),
    ("▹", {
        "ије": "и", # налијевати → наливати
        "је": "и", # утјецај → утицај
    }),
    ("◃", {
        "ијел": "ео", # бијел → бео
        "ијен": "ењ", # лијен → лењ
        "ил": "ел", # вриједила → вредела
        "ит": "ет", # вриједити → вредети
        "јел": "ео", # одјел → одео
        "тн": "тњ", # љетни → летњи
        "шње": "сне", # побјешњели → побеснели
    }),
)

def _derive_reflex_specs (reflex_spec):

    reflex_spec_dehyb = []
    reflex_spec_hyb = {}
    for tick, refmap in reflex_spec:
        # Derive data for dehybridization.
        # Derive Latin cases (must be done before other cases).
        refmap.update([list(map(ctol, x)) for x in list(refmap.items())])
        # Derive cases with first letter in uppercase.
        refmap.update([list(map(str.capitalize, x)) for x in list(refmap.items())])
        # Derive cases with all letters in uppercase.
        refmap.update([list(map(str.upper, x)) for x in list(refmap.items())])
        # Compute minimum and maximum reflex lengths.
        ijklen_min = min(list(map(len, list(refmap.keys()))))
        ijklen_max = max(list(map(len, list(refmap.keys()))))
        reflex_spec_dehyb.append((tick, refmap, ijklen_min, ijklen_max))

        # Derive data for hybridization:
        # {(ekvlen, ijklen, btrk): {ijkfrm: [(ekvfrm, tick)...]}}
        for ijkfrm, ekvfrm in list(refmap.items()):
            # Compute backtracking from position of jat-reflex difference.
            btrk = 0
            while (    btrk < len(ijkfrm) and btrk < len(ekvfrm)
                   and ijkfrm[btrk] == ekvfrm[btrk]
            ):
                btrk += 1
            pkey = (btrk, len(ekvfrm), len(ijkfrm))
            if pkey not in reflex_spec_hyb:
                reflex_spec_hyb[pkey] = {}
            if ijkfrm not in reflex_spec_hyb[pkey]:
                reflex_spec_hyb[pkey][ijkfrm] = []
            reflex_spec_hyb[pkey][ijkfrm].append((ekvfrm, tick))

    # Convert hybridization data into list of pairs.
    # Sort such that on hybridization reflexes are tried by
    # increasing backtrack,
    # decreasing smaller length of the two reflexes,
    # decreasing greater lenght of the two reflexes.
    tmplst = []
    pkeys = list(reflex_spec_hyb.keys())
    pkeys.sort(key=lambda x: (x[0], -min(x[1], x[2]), -max(x[1], x[2])))
    reflex_spec_hyb = [k + (reflex_spec_hyb[k],) for k in pkeys]

    return reflex_spec_dehyb, reflex_spec_hyb

_reflex_spec_dehyb, _reflex_spec_hyb = _derive_reflex_specs(_reflex_spec)

# Head of alternatives directives for dialect.
_dhyb_althead = "~#"


def hitoe (text):
    """
    Resolve hybrid Ijekavian text with jat-reflex ticks and dialect alternatives
    into plain Ekavian text [type F1A hook].
    """

    return _hito_w(text)


def hitoeq (text):
    """
    Like L{hitoe}, but does not output warnings on problems [type F1A hook].
    """

    return _hito_w(text, silent=True)


def hitoi (text):
    """
    Resolve hybrid Ijekavian text with jat-reflex ticks and dialect alternatives
    into plain Ijekavian text [type F1A hook].
    """

    return _hito_w(text, toijek=True)


def hitoiq (text):
    """
    Like L{hitoi}, but does not output warnings on problems [type F1A hook].
    """

    return _hito_w(text, toijek=True, silent=True)


def _hito_w (text, toijek=False, silent=False, validate=False):

    errspans = [] if validate else None
    for tick, refmap, ijklen_min, ijklen_max in _reflex_spec_dehyb:
        text = _hito_w_simple(text, tick, refmap, ijklen_min, ijklen_max,
                              toijek, silent, errspans)

    srcname = "<text>" if (not silent and not validate) else None
    selalt = 1 if not toijek else 2
    text, ngood, allgood = resolve_alternatives(text, selalt, 2,
                                                althead=_dhyb_althead,
                                                srcname=srcname)
    if not allgood and validate:
        errmsg = n_("@info \"alternatives directive\" is a term",
                    "Malformed Ekavian-Ijekavian alternatives directive "
                    "encountered after %(num)d good directive.",
                    "Malformed Ekavian-Ijekavian alternatives directive "
                    "encountered after %(num)d good directives.",
                    num=ngood)
        errspans.append((0, 0, errmsg))

    if not validate:
        return text
    else:
        return errspans


def _hito_w_simple (text, tick, refmap, ijklen_min, ijklen_max,
                    toijek, silent, errspans):

    segs = []
    p = 0
    while True:
        pp = p
        p = text.find(tick, p)
        if p < 0:
            segs.append(text[pp:])
            break
        segs.append(text[pp:p])
        pp = p
        p += len(tick)
        if p >= len(text) or not text[p:p + 1].isalpha():
            segs.append(tick)
            continue

        ijklen = ijklen_min
        ekvfrm = None
        while ijklen <= ijklen_max and ekvfrm is None:
            ijkfrm = text[p:p + ijklen]
            ekvfrm = refmap.get(ijkfrm)
            ijklen += 1

        if ekvfrm is not None:
            segs.append(ekvfrm if not toijek else ijkfrm)
            p += len(ijkfrm)
        else:
            segs.append(tick)
            errmsg = _("@info \"jat\" is the name of an old Serbian letter",
                       "Unknown jat-reflex starting from '%(snippet)s'.",
                       snippet=text[pp:pp + 20])
            if not silent:
                warning(errmsg)
            if errspans is not None:
                errspans.append((pp, pp + ijklen_max, errmsg))

    return "".join(segs)


def validate_dhyb (text):
    """
    Check whether dialect-hybrid text is valid [type V1A hook].
    """

    return _hito_w(text, silent=True, validate=True)


def hitoei (htext):
    """
    Resolve hybrid Ijekavian-Ekavain text into clean Ekavian and Ijekavian.

    @param htext: hybrid text
    @type htext: string

    @returns: Ekavian and Ijekavian text
    @rtype: (string, string)
    """

    return hitoe(htext), hitoi(htext)


def tohi (text1, text2, ekord=None, delims="/|¦", parthyb=False):
    """
    Construct hybrid Ijekavian text out of Ekavian and Ijekavian texts.

    Hybridization is performed by merging Ekavian and Ijekavian forms
    into Ijekavian forms with inserted jat-reflex ticks.
    Input texts can be both in Cyrillic and Latin, and piecewise so.
    Texts also do not have to be clean Ekavian and Ijekavian,
    as hybridization is performed only at difference segments.
    Order of text arguments is not important as long as all difference
    segments can be merged (i.e. the function is comutative in that case).

    If a difference segment cannot be merged by jat-reflex ticks,
    then the resolution depends on C{ekord} parameter.
    If it is C{None}, then the segment of C{text2} is taken into result.
    If it is C{1} or C{2}, then the segments of C{text1} and C{text2}
    are combined in a dialect alternatives directive (C{~#/.../.../});
    the number determines which segment is put first in the directive
    (i.e. considered Ekavian), that of C{text1} or of C{text2}.
    Any other value of C{ekord} leads to undefined behavior.

    It is possible that input texts are already partially hybridized,
    and only some parts of them need to be additionally hybridized.
    Setting C{parthyb} to C{True} will tell the function to detect
    and skip already hybridized segments, and hybridize only the rest.

    @param text1: first text
    @type text1: string
    @param text2: second text
    @type text2: string
    @param ekord: enumerates the text to be considered Ekavian
        when adding alternatives directives
    @type ekord: None, 1, 2
    @param delims: possible delimiter characters for alternatives directives
    @type delims: string
    @param parthyb: whether input texts are already partially hybridized
    @type parthyb: bool

    @returns: hybrid Ijekavian text
    @rtype: string
    """

    len1 = len(text1); len2 = len(text2)
    i1 = 0; i1p = 0; i2 = 0; i2p = 0
    segs = []
    while True:
        while i1 < len1 and i2 < len2 and text1[i1] == text2[i2]:
            if not parthyb:
                i1 += 1
                i2 += 1
            else:
                i1 += _step_over_hyb(text1, i1)
                i2 += _step_over_hyb(text2, i2)
        if i1 == len1 and i2 == len2:
            segs.append(text1[i1p:]) # same as text2[i2p:]
            break
        # Try to hybridize difference by jat-reflex ticks.
        tick = None
        for texte, texti, ie, ii, order12 in (
            (text1, text2, i1, i2, True),
            (text2, text1, i2, i1, False),
        ):
            frms = []
            for btrk, lene, leni, refmap in _reflex_spec_hyb:
                ieb = ie - btrk
                iib = ii - btrk
                if ieb < 0 or iib < 0:
                    continue
                frme = texte[ieb:ieb + lene]
                frmi = texti[iib:iib + leni]
                for cfrme, ctick in refmap.get(frmi, []):
                    if cfrme == frme:
                        tick = ctick
                        break
                if tick: break
            if tick: break
        if tick:
            # Hybridization by difference marks possible.
            segs.append(text1[i1p:i1 - btrk]) # same as text2[i2p:i2 - btrk]
            segs.append(tick + frmi)
            i1p = i1 - btrk + (lene if order12 else leni)
            i2p = i2 - btrk + (leni if order12 else lene)
        else:
            # Hybridization by difference marks not possible.
            # Use alternatives directive, or pure Ijekavian.
            i1b = i1; i2b = i2
            while (    i1b > i1p and i2b > i2p
                   and (text1[i1b - 1].isalpha() + text2[i2b - 1].isalpha() == 1)
            ):
                i1b -= 1; i2b -= 1
            segs.append(text1[i1p:i1b])
            wdiff = word_diff(text1[i1b:], text2[i2b:])
            frm1s = []
            frm2s = []
            while wdiff and wdiff[0][0] != " ":
                tag, seg = wdiff.pop(0)
                if tag != "+":
                    frm1s.append(seg)
                if tag != "-":
                    frm2s.append(seg)
            frm1 = "".join(frm1s)
            frm2 = "".join(frm2s)
            i1p = i1b + len(frm1)
            i2p = i2b + len(frm2)
            if ekord == 1:
                segs.append(_dhyb_althead + _delimit([frm1, frm2], delims))
            elif ekord == 2:
                segs.append(_dhyb_althead + _delimit([frm2, frm1], delims))
            else:
                segs.append(frm2)
        i1 = i1p
        i2 = i2p

    htext = "".join(segs)

    return htext


_reflex_spec_dehyb_by_tick = dict((x[0], x[1:]) for x in _reflex_spec_dehyb)

def _step_over_hyb (text, pos):

    refspec = _reflex_spec_dehyb_by_tick.get(text[pos])
    if refspec is not None: # there is a reflex
        refmap, ijklen_min, ijklen_max = refspec
        ijklen = ijklen_min
        ekvfrm = None
        while ijklen <= ijklen_max and ekvfrm is None:
            ijkfrm = text[pos + 1:pos + 1 + ijklen]
            ekvfrm = refmap.get(ijkfrm)
            ijklen += 1
        if ekvfrm is not None:
            steplen = 1 + len(ijkfrm)
        else: # malformed reflex
            steplen = 1
    elif text.startswith(_dhyb_althead): # there is an alternatives directive
        if pos + len(_dhyb_althead) < len(text):
            sep = text[pos + len(_dhyb_althead)]
            pos2 = text.find(sep, pos + len(_dhyb_althead) + 1)
            if pos2 < len(text):
                pos3 = text.find(sep, pos2 + 1)
                if pos3 < len(text):
                    steplen = pos3 - pos
                else: # malformed directive
                    steplen = 1
            else: # malformed directive
                steplen = 1
        else: # malformed directive
            steplen = 1
    else: # there is plain text
        steplen = 1

    return steplen


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
        fmtalts = format_item_list(["{%s}" % x for x in alts])
        raise PologyError(
            _("@info",
              "No delimiter from '%(delimstr)s' can be used for "
              "alternatives directive containing: %(snippetlist)s.",
              delimstr=delims, snippetlist=fmtalts))

    return delim + delim.join(alts) + delim

