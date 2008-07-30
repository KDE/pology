# -*- coding: UTF-8 -*

"""
Producing diffs between texts.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

from pology.misc.split import split_text

import re
from difflib import ndiff

_opn_ch = u"{"
_cls_ch = u"}"
_pls_ch = u"+"
_mns_ch = u"-" #–

def diff_texts (text_old, text_new, markup=False, format=None):
    """
    Create text with embedded differences between old and new texts.

    The difference is computed by looking at texts as collections of words
    and intersegments. Segments present only in the new text are embedded
    as C{{+...+}}, and segments only in the old text as C{{-...-}}.

    Differencing may take into account when the texts are expected to have
    XML-like markup, or when they are of certain format defined by Gettext.

    Also reported is the I{difference ratio}, a heuristic measure of
    difference between two texts. 0.0 means no difference, and 1.0 that
    the texts are completely different.

    @param text_old: the old text
    @type text_old: string

    @param text_new: the new text
    @type text_new: string

    @param markup: whether C{<...>} markup can be expected in the texts
    @type markup: bool

    @param format: Gettext format flag (e.g. C{"c-format"}, etc.)
    @type format: string

    @returns: string with embedded differences and difference ratio
    @rtype: string, float
    """

    # Split text into segments: words and intersections, combined into
    # single lists for old and new text. Use words as is, but split
    # intersections further into single characters.
    segments = []
    segment_isintr = []

    def add_segment (intr, word):
        segments[-1].extend(list(intr) + [word])
        segment_isintr[-1].extend([True] * len(intr) + [False])

    for text in (text_old, text_new):
        lw, li = split_text(text, markup, format)
        segments.append([])
        segment_isintr.append([])
        map(add_segment, li, lw + [''])

    # Create the difference.
    dlist = list(ndiff(segments[0], segments[1]))
    dlist = [x for x in dlist if x[:1] in "+- "] # remove non-diff segments

    # Recompute which elements of the difference are intersections.
    dlist_isintr = []
    i_old = 0
    i_new = 0
    for el in dlist:
        if el[0] == "-":
            dlist_isintr.append(segment_isintr[0][i_old])
        else:
            dlist_isintr.append(segment_isintr[1][i_new])

        if el[0] != "+":
            i_old += 1
        if el[0] != "-":
            i_new += 1

    # Reshuffle so that all new/old elements consecutive but for the
    # intersections are grouped into all new followed by all old,
    # with intersections included in both.
    ndlist = []
    i = 0
    while i < len(dlist):
        while i < len(dlist) and dlist[i][0] not in "+-":
            ndlist.append(dlist[i])
            i += 1
        seq_new = []
        seq_old = []
        i_first_diff = i
        i_last_diff = i
        while i < len(dlist) and (dlist[i][0] in "+-" or dlist_isintr[i]):
            if dlist[i][0] != "-":
                seq_new.append(dlist[i])
            if dlist[i][0] != "+":
                seq_old.append(dlist[i])
            if dlist[i][0] in "+-":
                i_last_diff = i
            i += 1
        for iex in range(i_last_diff, i - 1):
            seq_new.pop()
            seq_old.pop()
        i = i_last_diff + 1
        if seq_new:
            ndlist.append("+ " + "".join([x[2:] for x in seq_new]))
        if seq_old:
            ndlist.append("- " + "".join([x[2:] for x in seq_old]))
    dlist = ndlist
    dlist_intr = None # no longer valid

    # Format the embedded output.
    S_EQU, S_NEW, S_OLD = range(3)
    dtext = type(text_new)("")
    state = S_EQU
    len_equ, len_old, len_new = 0, 0, 0
    for el in dlist:
        if state == S_EQU:
            if el.startswith("+"):
                dtext += _opn_ch + _pls_ch
                state = S_NEW
            elif el.startswith("-"):
                dtext += _opn_ch + _mns_ch
                state = S_OLD

        elif state == S_OLD:
            if el.startswith(" "):
                dtext += _mns_ch + _cls_ch
                state = S_EQU
            elif el.startswith("+"):
                dtext += _mns_ch + _cls_ch + _opn_ch + _pls_ch
                state = S_NEW

        elif state == S_NEW:
            if el.startswith(" "):
                dtext +=  _pls_ch + _cls_ch
                state = S_EQU
            elif el.startswith("-"):
                dtext += _pls_ch + _cls_ch + _opn_ch + _mns_ch
                state = S_OLD

        seg = el[2:]
        if el.startswith("-"):
            len_old += len(seg)
        elif el.startswith("+"):
            len_new += len(seg)
        else:
            len_equ += len(seg)

        dtext += seg

    if state == S_OLD:
        dtext += _mns_ch + _cls_ch
    elif state == S_NEW:
        dtext += _pls_ch + _cls_ch

    len_all = len_new + len_old + len_equ
    if len_all > 0:
        diff_ratio = 1.0 - float(len_equ) / float(len_all)
    else:
        diff_ratio = 0.0

    return dtext, diff_ratio


_capt_old_rx = re.compile(  "\\" + _opn_ch + "\\" + _mns_ch + "(.*?)" \
                          + "\\" + _mns_ch + "\\" + _cls_ch, re.U|re.S)
_capt_new_rx = re.compile(  "\\" + _opn_ch + "\\" + _pls_ch + "(.*?)" \
                          + "\\" + _pls_ch + "\\" + _cls_ch, re.U|re.S)


def diff_to_old (dtext):
    """
    Recover old version (-) from text with embedded differences.

    @param dtext: text with embedded differences
    @type dtext: string

    @returns: old version of the text
    @rtype: string

    @see: L{diff_texts}
    """

    text = dtext
    text = _capt_new_rx.sub("", text)
    text = _capt_old_rx.sub("\\1", text)
    return text


def diff_to_new (dtext):
    """
    Recover new version (+) from text with embedded differences.

    @param dtext: text with embedded differences
    @type dtext: string

    @returns: new version of the text
    @rtype: string

    @see: L{diff_texts}
    """

    text = dtext
    text = _capt_new_rx.sub("\\1", text)
    text = _capt_old_rx.sub("", text)
    return text

