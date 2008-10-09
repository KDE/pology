# -*- coding: UTF-8 -*

"""
Producing diffs between texts.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

from pology.misc.split import split_text

import re
from difflib import ndiff


_new_tag = "+"

_new_vtag = "+"
_new_opnc = "{"
_new_clsc = "}"

_old_tag = "-"

_old_vtag = "-"
_old_opnc = "{"
_old_clsc = "}"

_equ_tag = " "


def word_diff (text_old, text_new, markup=False, format=None):
    """
    Create word-level difference between old and new text.

    The difference is computed by looking at texts as collections of words
    and intersegments. Difference is presented as a list of tuples,
    with each tuple composed of a difference tag and a text segment.
    Difference tag is string C{"+"}, C{"-"}, or C{" "}, for text segments
    which are new, old, or present in both texts, respectively.
    The list is ordered such that joining all text segments not marked
    as old will reconstruct the new text, and joining all not marked
    as new will reconstruct the old text. For example::

        >>> s1 = "A new type of foo."
        >>> s2 = "A new kind of bar."
        >>> text_diff(s1, s2)
        []

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

    @returns: difference list and difference ratio
    @rtype: list of tuples, float
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

    # Join contiguous new/old/both segments, make tagged tuples.
    ndlist = []
    S_EQU, S_NEW, S_OLD = range(3)
    state = S_EQU
    cseg = []
    len_equ, len_old, len_new = 0, 0, 0
    dlist.append(". ") # sentry
    for el in dlist:
        segtype = el[0]

        if state == S_EQU and segtype in ("+", "-", "."):
            if cseg:
                ndlist.append((_equ_tag, "".join(cseg)))
            cseg = []
            if segtype == "+":
                state = S_NEW
            else:
                state = S_OLD

        elif state == S_OLD and segtype in (" ", "+", "."):
            if cseg:
                ndlist.append((_old_tag, "".join(cseg)))
            cseg = []
            if segtype == " ":
                state = S_EQU
            else:
                state = S_NEW

        elif state == S_NEW and segtype in (" ", "-", "."):
            if cseg:
                ndlist.append((_new_tag, "".join(cseg)))
            cseg = []
            if segtype == " ":
                state = S_EQU
            else:
                state = S_OLD

        seg = el[2:]
        if segtype == "-":
            len_old += len(seg)
        elif segtype == "+":
            len_new += len(seg)
        else:
            len_equ += len(seg)
        if seg:
            cseg.append(seg)

    dlist = ndlist

    len_all = len_new + len_old + len_equ
    if len_all > 0:
        diff_ratio = 1.0 - float(len_equ) / float(len_all)
    else:
        diff_ratio = 0.0

    return dlist, diff_ratio


def word_ediff (text_old, text_new, markup=False, format=None):
    """
    Create word-level embedded difference between old and new texts.

    Same as L{word_diff}, but the difference is returned as text in
    which the new segments are wrapped as C{{+...+}}, and the old
    segments as C{{-...-}}.

    @returns: string with embedded differences and difference ratio
    @rtype: string, float

    @see: L{word_diff}
    """

    dlist, diff_ratio = word_diff(text_old, text_new, markup, format)
    dtext = []
    for segtag, segtext in dlist:
        if segtag == _new_tag:
            dtext.append(  _new_opnc + _new_vtag
                         + segtext
                         + _new_vtag + _new_clsc)
        elif segtag == _old_tag:
            dtext.append(  _old_opnc + _old_vtag
                         + segtext
                         + _old_vtag + _old_clsc)
        else:
            dtext.append(segtext)
    dtext = type(text_new)().join(dtext)

    return dtext, diff_ratio


_capt_old_rx = re.compile(  "\\" + _old_opnc + "\\" + _old_vtag + "(.*?)" \
                          + "\\" + _old_vtag + "\\" + _old_clsc, re.U|re.S)
_capt_new_rx = re.compile(  "\\" + _new_opnc + "\\" + _new_vtag + "(.*?)" \
                          + "\\" + _new_vtag + "\\" + _new_clsc, re.U|re.S)


def ediff_to_old (dtext):
    """
    Recover old version (-) from text with embedded differences.

    @param dtext: text with embedded differences
    @type dtext: string

    @returns: old version of the text
    @rtype: string

    @see: L{word_ediff}
    """

    text = dtext
    text = _capt_new_rx.sub("", text)
    text = _capt_old_rx.sub("\\1", text)
    return text


def ediff_to_new (dtext):
    """
    Recover new version (+) from text with embedded differences.

    @param dtext: text with embedded differences
    @type dtext: string

    @returns: new version of the text
    @rtype: string

    @see: L{word_ediff}
    """

    text = dtext
    text = _capt_new_rx.sub("\\1", text)
    text = _capt_old_rx.sub("", text)
    return text


def adapt_spans (otext, ftext, spans, merge=True):
    """
    Adapt matched spans in filtered text to original text.

    Sometimes text gets filtered before being matched, and when a match
    is found in the filtered text, it needs to be reported relative to
    the original text. This function will heuristically adapt matched spans
    relative to the filtered text back to the original text.

    Spans are given as list of index tuples C{[(start1, end1), ...]} where
    start and end index have standard Python semantics (may be negative too).
    If C{merge} is C{True}, any spans that overlap or abut after adaptation
    will be merged into a single span, ordered by increasing start index,
    and empty spans removed; otherwise each adapted span will strictly
    correspond to the input span at that position.

    Span tuples may have more elements past the start and end indices.
    They will be ignored, but preserved; if merging is in effect,
    extra elements will be preserved for only the frontmost of
    the overlapping spans (undefined for which if there are several).

    If any of the input spans are invalid, the results are undefined.

    @param otext: original text
    @type otext: string
    @param ftext: filtered text
    @type ftext: string
    @param spans: matched spans
    @type spans: list of index tuples
    @param merge: whether to merge overlapping spans
    @type bool

    @returns: adapted spans
    @rtype: list of index tuples
    """

    # Resolve negative spans.
    flen = len(ftext)
    fspans = []
    for span in spans:
        start, end = span[:2]
        if start < 0:
            start = flen - start
        if end < 0:
            end = flen - end
        fspans.append((start, end) + span[2:])

    # Create character-level difference from original to filtered text.
    dlist = list(ndiff(otext, ftext))
    dlist = [x for x in dlist if x[:1] in "+- "] # remove non-diff segments
    dlist = [(x[:1], x[2:]) for x in dlist] # split into (type, segment) pairs

    # For each span, go through the difference and... do some magic.
    aspans = []
    for fspan in fspans:
        #print "======> span to adapt:", fspan
        aspan = []
        for filtered_index, end_extra in zip(fspan[:2], (0, 1)):
            #print ">>> index to adapt:", filtered_index
            original_index = 0
            track_index = 0
            for dtype, dseg in dlist:
                slen = len(dseg)
                if dtype == "+":
                    track_index += slen
                elif dtype == "-":
                    original_index += slen
                else:
                    original_index += slen
                    track_index += slen
                #print dtype, dseg, track_index, original_index
                if dtype not in ("+", "-"):
                    if track_index + end_extra > filtered_index:
                        original_index -= track_index - filtered_index
                        break
            #print "<<< adapted index:", original_index
            aspan.append(original_index)
        aspan.extend(fspan[2:])

        aspans.append(tuple(aspan))

    # Merge spans if requested.
    if merge:
        # Sort by start index immediately, for priority of extra elements.
        aspans.sort(lambda x, y: cmp(x[0], y[0]))
        maspans = []
        while len(aspans) > 0:
            cstart, cend = aspans[0][:2]
            extras = aspans[0][2:]
            if cstart >= cend:
                aspans.pop(0) # remove empty spans
                continue
            i = 0
            while i < len(aspans):
                start, end = aspans[i][:2]
                if cend >= start and cstart <= end:
                    cstart = min(cstart, start)
                    cend = max(cend, end)
                    aspans.pop(i)
                else:
                    i += 1
            maspans.append((cstart, cend) + extras)
        # Sort by start index.
        maspans.sort(lambda x, y: cmp(x[0], y[0]))
        aspans = maspans

    return aspans

