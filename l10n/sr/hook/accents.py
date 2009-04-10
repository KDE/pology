# -*- coding: UTF-8 -*-

"""
Process letter accents in Serbian Cyrillic text.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

# All accented letters in Serbian Cyrillic, for a given non-accented letter.
_accents = {
    u"а": (u"а̀", u"а́", u"а̏", u"а̑", u"а̄", u"а̂", u"â", u"ȃ"),
    u"А": (u"А̀", u"А́", u"А̏", u"А̑", u"А̄", u"А̂", u"Â", u"Ȃ"),
    # ...with Latin long-falling/genitive a in NFC, used sometimes as makeshift
    u"е": (u"ѐ", u"е́", u"е̏", u"е̑", u"е̄", u"е̂"),
    u"Е": (u"Ѐ", u"Е́", u"Е̏", u"Е̑", u"Е̄", u"Е̂"),
    u"и": (u"ѝ", u"и́", u"и̏", u"и̑", u"ӣ", u"и̂"),
    u"И": (u"Ѝ", u"И́", u"И̏", u"И̑", u"Ӣ", u"И̂"),
    u"о": (u"о̀", u"о́", u"о̏", u"о̑", u"о̄", u"о̂", u"ȏ", u"ô"),
    u"О": (u"О̀", u"О́", u"О̏", u"О̑", u"О̄", u"О̂", u"Ȏ", u"Ô"),
    # ...with Latin long-falling/genitive o in NFC, used sometimes as makeshift
    u"у": (u"у̀", u"у́", u"у̏", u"у̑", u"ӯ", u"у̂"),
    u"У": (u"У̀", u"У́", u"У̏", u"У̑", u"Ӯ", u"У̂"),
    u"р": (u"р̀", u"р́", u"р̏", u"р̑", u"р̄", u"р̂"),
    u"Р": (u"Р̀", u"Р́", u"Р̏", u"Р̑", u"Р̄", u"Р̂"),
}

# All accented letters bunched together,
# and inverted mapping (base for each accented letter).
_accents_flat = set()
_accents_inverted = {}
for base, accents in _accents.items():
    _accents_flat.update(set(accents))
    for accent in accents:
        _accents_inverted[accent] = base
del base, accents # do not pollute exports

_max_accent_len = max(map(len, list(_accents_flat)))
_min_accent_len = min(map(len, list(_accents_flat)))
_accent_len_range = range(_max_accent_len, _min_accent_len - 1, -1)

# FIXME: The graphing sequences with slashes and backslashes are far
# too easy to happen accidentally; think of something better.
_agraphs_unused = {
    ur"\а": ur"а̀",
    ur"/а": ur"а́",
    ur"\\а": ur"а̏",
    ur"//а": ur"а̑",
    ur"~а": ur"а̄",
    ur"\А": ur"А̀",
    ur"/А": ur"А́",
    ur"\\А": ur"А̏",
    ur"//А": ur"А̑",
    ur"~А": ur"А̄",

    ur"\е": ur"ѐ",
    ur"/е": ur"е́",
    ur"\\е": ur"е̏",
    ur"//е": ur"е̑",
    ur"~е": ur"е̄",
    ur"\Е": ur"Ѐ",
    ur"/Е": ur"Е́",
    ur"\\Е": ur"Е̏",
    ur"//Е": ur"Е̑",
    ur"~Е": ur"Е̄",

    ur"\и": ur"ѝ",
    ur"/и": ur"и́",
    ur"\\и": ur"и̏",
    ur"//и": ur"и̑",
    ur"~и": ur"ӣ",
    ur"\И": ur"Ѝ",
    ur"/И": ur"И́",
    ur"\\И": ur"И̏",
    ur"//И": ur"И̑",
    ur"~И": ur"Ӣ",

    ur"\о": ur"о̀",
    ur"/о": ur"о́",
    ur"\\о": ur"о̏",
    ur"//о": ur"о̑",
    ur"~о": ur"о̄",
    ur"\О": ur"О̀",
    ur"/О": ur"О́",
    ur"\\О": ur"О̏",
    ur"//О": ur"О̑",
    ur"~О": ur"О̄",

    ur"\у": ur"у̀",
    ur"/у": ur"у́",
    ur"\\у": ur"у̏",
    ur"//у": ur"у̑",
    ur"~у": ur"ӯ",
    ur"\У": ur"У̀",
    ur"/У": ur"У́",
    ur"\\У": ur"У̏",
    ur"//У": ur"У̑",
    ur"~У": ur"Ӯ",

    ur"\р": ur"р̀",
    ur"/р": ur"р́",
    ur"\\р": ur"р̏",
    ur"//р": ur"р̑",
    ur"~р": ur"р̄",
    ur"\Р": ur"Р̀",
    ur"/Р": ur"Р́",
    ur"\\Р": ur"Р̏",
    ur"//Р": ur"Р̑",
    ur"~Р": ur"Р̄",
}

_agraphs = {
    #ur"^а": ur"а̂",
    #ur"^о": ur"о̂",
    #ur"^А": ur"А̂",
    #ur"^О": ur"О̂",
    # ...use Latin NFC forms at places for the moment.
    ur"^а" : ur"â",
    ur"^о" : ur"ô",
    ur"^А" : ur"Â",
    ur"^О" : ur"Ô",
}

_max_agraph_len = max(map(len, _agraphs.keys()))
_min_agraph_len = min(map(len, _agraphs.keys()))
_agraph_len_range = range(_max_agraph_len, _min_agraph_len - 1, -1)


def resolve_agraphs (text):
    """
    Convert accent graphs into real accented letters [type F1A hook].

    Accented Cyrillic letters still cannot be widely entered directly
    by keyboard, and in such cases this module allows converting graphical
    accent-letter representations into actual Unicode compositions.

    @note: At the moment, only genitive endings are supported.

    @return: text
    """

    return _apply_mapping(text, _agraphs, _agraph_len_range)


def remove_accents (text):
    """
    Remove accents from all accented letters [type F1A hook].

    Sometimes it is convenient to operate on text without accents,
    e.g. when checking spelling.

    @return: text
    """

    return _apply_mapping(text, _accents_inverted, _accent_len_range)


def _apply_mapping (text, mapping, mlenrange):

    p = 0
    pp = 0
    tsegs = []
    ltext = len(text)
    while p < ltext:
        for mlen in mlenrange:
            mapfrom = text[p:p + mlen]
            mapto = mapping.get(mapfrom)
            if mapto:
                tsegs.append(text[pp:p])
                tsegs.append(mapto)
                p += mlen - 1
                pp = p + 1
                break
        p += 1
    tsegs.append(text[pp:p])

    return "".join(tsegs)

