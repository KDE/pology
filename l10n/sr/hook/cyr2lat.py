# -*- coding: UTF-8 -*-

"""
Transliterate Cyrillic text into Latin.

Properly converts uppercase digraphs, e.g.
Љубљана→Ljubljana, but ЉУБЉАНА→LJUBLJANA.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

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
    # accented (the keys are now 2-char):
    u'а̑':u'â', u'о̑':u'ô',
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

# Transliteration table English in Serbian Cyrillic by layout -> English.
_dict_c2a_englay = _dict_c2l.copy()
_dict_c2a_englay.update({
    u'љ':u'q', u'њ':u'w', u'ж':u'y', u'џ':u'x',
    u'Љ':u'Q', u'Њ':u'W', u'Ж':u'Y', u'Џ':u'X',
})

def process (text):
    """
    Transliterate from Cyrillic to proper Latin [type F1A hook].

    @return: text
    """

    return _process_w(text, _dict_c2l)


def process_to_stripped (text):
    """
    Transliterate from Cyrillic or Latin to stripped ASCII [type F1A hook].

    @return: text
    """

    return _process_w(text, _dict_cl2a_stripped)


def process_to_englay (text):
    """
    Transliterate from English in Cyrillic by keyboard layout to proper English
    [type F1A hook].

    @return: text
    """

    return _process_w(text, _dict_c2a_englay)


def _process_w (text, trdict):

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
            ntext += c;

    return ntext

