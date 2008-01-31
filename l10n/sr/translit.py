# -*- coding: UTF-8 -*-

"""
Transliteration of Serbian scripts.

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


def sr_c2l (text):
    """
    Transliterate Serbian Cyrillic text to Serbian Latin.

    Properly converts uppercase digraphs, e.g.
    Љубљана→Ljubljana, but ЉУБЉАНА→LJUBLJANA.

    @param text: Cyrillic text to transform
    @type text: string

    @returns: the text in Latin
    @rtype: string
    """

    tlen = len(text)
    ntext = ""
    for i in range(tlen):
        c = text[i]
        c2 = text[i:i+2]
        r = _dict_c2l.get(c2) or _dict_c2l.get(c)
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

