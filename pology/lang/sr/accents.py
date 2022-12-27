# -*- coding: UTF-8 -*-

"""
Process letter accents in Serbian Cyrillic text.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

# All accented letters in Serbian Cyrillic, for a given non-accented letter.
_accents = {
    "а": ("а̀", "а́", "а̏", "а̑", "а̄", "а̂", "â", "ȃ"),
    "А": ("А̀", "А́", "А̏", "А̑", "А̄", "А̂", "Â", "Ȃ"),
    # ...with Latin long-falling/genitive a in NFC, used sometimes as makeshift
    "е": ("ѐ", "е́", "е̏", "е̑", "е̄", "е̂", "ѐ"),
    "Е": ("Ѐ", "Е́", "Е̏", "Е̑", "Е̄", "Е̂", "Ѐ"),
    "и": ("ѝ", "и́", "и̏", "и̑", "ӣ", "и̂", "ѝ", "ӣ"),
    "И": ("Ѝ", "И́", "И̏", "И̑", "Ӣ", "И̂", "Ѝ", "Ӣ"),
    "о": ("о̀", "о́", "о̏", "о̑", "о̄", "о̂", "ȏ", "ô"),
    "О": ("О̀", "О́", "О̏", "О̑", "О̄", "О̂", "Ȏ", "Ô"),
    # ...with Latin long-falling/genitive o in NFC, used sometimes as makeshift
    "у": ("у̀", "у́", "у̏", "у̑", "ӯ", "у̂", "ӯ"),
    "У": ("У̀", "У́", "У̏", "У̑", "Ӯ", "У̂", "Ӯ"),
    "р": ("р̀", "р́", "р̏", "р̑", "р̄", "р̂"),
    "Р": ("Р̀", "Р́", "Р̏", "Р̑", "Р̄", "Р̂"),
}

# All accented letters bunched together,
# and inverted mapping (base for each accented letter).
_accents_flat = set()
_accents_inverted = {}
for base, accents in list(_accents.items()):
    _accents_flat.update(set(accents))
    for accent in accents:
        _accents_inverted[accent] = base
del base, accents # do not pollute exports

_max_accent_len = max(list(map(len, list(_accents_flat))))
_min_accent_len = min(list(map(len, list(_accents_flat))))
_accent_len_range = list(range(_max_accent_len, _min_accent_len - 1, -1))

# FIXME: The graphing sequences with slashes and backslashes are far
# too easy to happen accidentally; think of something better.
_agraphs_unused = {
    r"\а": r"а̀",
    r"/а": r"а́",
    r"\\а": r"а̏",
    r"//а": r"а̑",
    r"~а": r"а̄",
    r"\А": r"А̀",
    r"/А": r"А́",
    r"\\А": r"А̏",
    r"//А": r"А̑",
    r"~А": r"А̄",

    r"\е": r"ѐ",
    r"/е": r"е́",
    r"\\е": r"е̏",
    r"//е": r"е̑",
    r"~е": r"е̄",
    r"\Е": r"Ѐ",
    r"/Е": r"Е́",
    r"\\Е": r"Е̏",
    r"//Е": r"Е̑",
    r"~Е": r"Е̄",

    r"\и": r"ѝ",
    r"/и": r"и́",
    r"\\и": r"и̏",
    r"//и": r"и̑",
    r"~и": r"ӣ",
    r"\И": r"Ѝ",
    r"/И": r"И́",
    r"\\И": r"И̏",
    r"//И": r"И̑",
    r"~И": r"Ӣ",

    r"\о": r"о̀",
    r"/о": r"о́",
    r"\\о": r"о̏",
    r"//о": r"о̑",
    r"~о": r"о̄",
    r"\О": r"О̀",
    r"/О": r"О́",
    r"\\О": r"О̏",
    r"//О": r"О̑",
    r"~О": r"О̄",

    r"\у": r"у̀",
    r"/у": r"у́",
    r"\\у": r"у̏",
    r"//у": r"у̑",
    r"~у": r"ӯ",
    r"\У": r"У̀",
    r"/У": r"У́",
    r"\\У": r"У̏",
    r"//У": r"У̑",
    r"~У": r"Ӯ",

    r"\р": r"р̀",
    r"/р": r"р́",
    r"\\р": r"р̏",
    r"//р": r"р̑",
    r"~р": r"р̄",
    r"\Р": r"Р̀",
    r"/Р": r"Р́",
    r"\\Р": r"Р̏",
    r"//Р": r"Р̑",
    r"~Р": r"Р̄",
}

_agraphs = {
    #ur"^а": ur"а̂",
    #ur"^о": ur"о̂",
    #ur"^А": ur"А̂",
    #ur"^О": ur"О̂",
    # ...use Latin NFC forms at places for the moment.
    r"^а" : r"â",
    r"^о" : r"ô",
    r"^А" : r"Â",
    r"^О" : r"Ô",
}

_max_agraph_len = max(list(map(len, list(_agraphs.keys()))))
_min_agraph_len = min(list(map(len, list(_agraphs.keys()))))
_agraph_len_range = list(range(_max_agraph_len, _min_agraph_len - 1, -1))


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

