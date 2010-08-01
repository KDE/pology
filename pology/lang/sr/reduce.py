# -*- coding: UTF-8 -*-

"""
Reductions of Serbian text convenient in various special uses.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

from pology.lang.sr.accents import remove_accents
from pology.lang.sr.wconv import hictoecq, hictoicq


_srcyr = u"абвгдђежзијклљмнњопрстћуфхцчџшАБВГДЂЕЖЗИЈКЛЉМНЊОПРСТЋУФХЦЧЏШ"


def words_ec (text):
    """
    Reduce text to space-separated Ekavian Cyrillic words [type F1A hook].

    Words containing only Serbian Cyrillic characters are extracted,
    sorted, and joined by spaces into a string.
    In case the text contains dialect and script hybridization,
    it is passed through L{hictoec()<lang.sr.wconv.hictoic>}
    to resolve it into clean Ekavian Cyrillic.
    In case the text contains accent marks, it is passed through
    L{remove_accents()<lang.sr.accents.remove_accents>} to remove them.
    """

    return _words_w(remove_accents(hictoecq(text)))


def words_ec_lw (text):
    """
    Reduce text to space-separated Ekavian Cyrillic words, in lower case
    [type F1A hook].

    Like L{words_ec}, but the result is lowercased.
    """

    return words_ec(text.lower())


def words_ic (text):
    """
    Reduce text to space-separated Ijekavian Cyrillic words [type F1A hook].

    Like L{words_ec}, but if the text was hybrid it is resolved into
    clean Ijekavian Cyrillic (see L{hictoic()<lang.sr.wconv.hictoic>}).
    """

    return _words_w(remove_accents(hictoicq(text)))


def words_ic_lw (text):
    """
    Reduce text to space-separated Ijekavian Cyrillic words, in lower case
    [type F1A hook].

    Like L{words_ic}, but the result is lowercased.
    """

    return words_ic(text.lower())


def _dlc_select (w):

    return u"е" in w or u"и" in w
    # ...no len(w) >= 3 because an accelerator marker may have split the word.


def words_ic_lw_dlc (text):
    """
    Reduce text to space-separated Ijekavian Cyrillic words containing
    at least three letters, one of which is 'е' or 'и', in lower case
    [type F1A hook].

    Like L{words_ic}, but the result is lowercased.
    """

    return _words_w(remove_accents(hictoicq(text.lower())),
                    select=_dlc_select)


def _words_w (text, select=None):

    words = []
    tlen = len(text)
    p = 0
    while p < tlen:
        while p < tlen and not text[p].isalpha():
            p += 1
        pp = p
        allsrcyr = True
        while p < tlen and text[p].isalpha():
            if text[p] not in _srcyr:
                allsrcyr = False
            p += 1
        word = text[pp:p]
        if word and allsrcyr and (not select or select(word)):
            words.append(word)

    words.sort()

    return " ".join(words)

