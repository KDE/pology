# -*- coding: UTF-8 -*-

"""
Reductions of Serbian text convenient in various special uses.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

from pology.l10n.sr.hook.accents import remove_accents
from pology.l10n.sr.hook.wconv import hictoecq, hictoicq


_srcyr = u"абвгдђежзијклљмнњопрстћуфхцчџШАБВГДЂЕЖЗИЈКЛЉМНЊОПРСТЋУФХЦЧЏШ"


def words_ec (text):
    """
    Reduce text to space-separated Ekavian Cyrillic words [type F1A hook].

    All non-letter sections are replaced with a space,
    and all words containing characters not in Serbian Cyrillic are removed.
    In case the text contains dialect and script hybridization,
    it is passed through L{hictoec()<l10n.sr.hook.wconv.hictoic>}
    to resolve it into clean Ekavian Cyrillic.
    In case the text contains accent marks, it is passed through
    L{remove_accents()<l10n.sr.hook.accents.remove>} to remove them.
    """

    return _words_w(remove_accents(hictoecq(text)))


def words_ec_lw (text):
    """
    Reduce text to space-separated Ekavian Cyrillic words, in lower case
    [type F1A hook].

    Like L{words_ec}, but the result is lowercased.
    """

    return words_ec(text).lower()


def words_ic (text):
    """
    Reduce text to space-separated Ijekavian Cyrillic words [type F1A hook].

    Like L{words_ec}, but if the text was hybrid it is resolved into
    clean Ijekavian Cyrillic (see L{hictoic()<l10n.sr.hook.wconv.hictoic>}).
    """

    return _words_w(remove_accents(hictoicq(text)))


def words_ic_lw (text):
    """
    Reduce text to space-separated Ijekavian Cyrillic words, in lower case
    [type F1A hook].

    Like L{words_ic}, but the result is lowercased.
    """

    return words_ic(text).lower()


def _words_w (text):

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
        if pp < p and allsrcyr:
            words.append(text[pp:p])

    return " ".join(words)

