# -*- coding: UTF-8 -*

"""
Retain only Katakana words in the text, separated by spaces.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""


def katakana (text):
    """
    Type F1A hook.

    @return: text
    """

    ntext = []
    for i in range(len(text)):
        c = text[i]
        if _is_katakana(c):
            ntext.append(c)
        elif c == u"・":
            c_prev = text[i-1:i]
            c_next = text[i+1:i+2]
            if _is_katakana(c_prev) and _is_katakana(c_next):
                ntext.append(c)
        else:
            if ntext and ntext[-1] != " ":
                ntext.append(" ")
    ntext = ("".join(ntext)).strip()
    return ntext


def _is_katakana (c):

    return (c >= u"ァ" and c <= u"ヴ") or c == u"ー"

