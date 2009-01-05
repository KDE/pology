# -*- coding: UTF-8 -*

"""
Producing diffs between texts.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import re
from difflib import ndiff

from pology.misc.split import split_text
from pology.misc.colors import colors_for_file


_new_tag = "+"

_new_vtag = "+"
_new_opnc = "{"
_new_clsc = "}"

_old_tag = "-"

_old_vtag = "-"
_old_opnc = "{"
_old_clsc = "}"

_equ_tag = " "

_tagext_none = "~"
_tagext_none_len = len(_tagext_none)

_new_opn = _new_opnc + _new_vtag
_new_cls = _new_vtag + _new_clsc
_old_opn = _old_opnc + _old_vtag
_old_cls = _old_vtag + _old_clsc


def word_diff (text_old, text_new, markup=False, format=None,
               diffr=False):
    """
    Create word-level difference between old and new text.

    The difference is computed by looking at texts as collections of words
    and intersegments. Difference is presented as a list of tuples,
    with each tuple composed of a difference tag and a text segment.
    Difference tag is string C{"+"}, C{"-"}, or C{" "}, for text segments
    which are new, old, or present in both texts, respectively.
    If one of the texts is C{None}, as opposed to empty string,
    a tilde is appended to the base difference tag.

    The list is ordered such that joining all text segments not marked
    as old will reconstruct the new text, and joining all not marked
    as new will reconstruct the old text.

    If requested by the C{diffr} parameter, also reported is the
    I{difference ratio}, a heuristic measure of difference between two texts.
    0.0 means no difference, and 1.0 that the texts are completely different.

    Differencing may take into account when the texts are expected to have
    XML-like markup, or when they are of certain format defined by Gettext.

    Examples::

        >>> s1 = "A new type of foo."
        >>> s2 = "A new kind of foo."
        >>> word_diff(s1, s2)
        [(' ', 'A new '), ('+', 'kind'), ('-', 'type'), (' ', ' of foo.')]
        >>> word_diff(s1, s2, diffr=True)
        ([(' ', 'A new '), ('+', 'kind'), ('-', 'type'), (' ', ' of foo.')],
        0.36363636363636365)
        >>> word_diff(s1, None, diffr=True)
        ([('-~', 'A new type of foo.')], 1.0)
        >>> word_diff(None, s2, diffr=True)
        ([('+~', 'A new kind of foo.')], 1.0)

    @param text_old: the old text
    @type text_old: string or None
    @param text_new: the new text
    @type text_new: string or None
    @param markup: whether C{<...>} markup can be expected in the texts
    @type markup: bool
    @param format: Gettext format flag (e.g. C{"c-format"}, etc.)
    @type format: string
    @param diffr: whether to report difference ratio
    @type diffr: bool

    @returns: difference list and possibly difference ratio
    @rtype: list of tuples or (list of tuples, float)
    """

    # Special cases, when one or both texts are None, or both are empty.
    specdlist = None
    specdr = 1.0
    if text_old is None and text_new is None:
        specdlist = []
    elif text_old is None:
        specdlist = [("+" + _tagext_none, text_new)]
    elif text_new is None:
        specdlist = [("-" + _tagext_none, text_old)]
    elif text_new == "" and text_old == "":
        specdlist = [(" ", "")]
        specdr = 0.0
    if specdlist is not None:
        return diffr and (specdlist, specdr) or specdlist

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

    # Reshuffle so that all old-new elements consecutive but for the
    # intersections are grouped into all old followed by all new,
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
            if dlist[i][0] != "+":
                seq_old.append(dlist[i])
            if dlist[i][0] != "-":
                seq_new.append(dlist[i])
            if dlist[i][0] in "+-":
                i_last_diff = i
            i += 1
        for iex in range(i_last_diff, i - 1):
            seq_new.pop()
            seq_old.pop()
        i = i_last_diff + 1
        if seq_old:
            ndlist.append("- " + "".join([x[2:] for x in seq_old]))
        if seq_new:
            ndlist.append("+ " + "".join([x[2:] for x in seq_new]))
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

    return diffr and (dlist, diff_ratio) or dlist


def word_ediff (text_old, text_new, markup=False, format=None, hlto=None,
                diffr=False):
    """
    Create word-level embedded difference between old and new texts.

    Same as L{word_diff}, but the difference is returned as text in
    which the new segments are wrapped as C{{+...+}}, and the old
    segments as C{{-...-}}.
    If a difference wrapper is already contained in the text, it will be
    escaped by inserting a tilde, e.g. C{"{+...+}"} -> C{"{~+...+~}"}.
    If even an escaped wrapper is contained in the text, another tilde
    is inserted, and so on.

    If one of the texts is C{None}, then the whole other text is wrapped
    as suitable difference, and a tilde added to its end to indicate that
    the other text was C{None}.
    If neither of the texts is C{None}, but after differencing the tilde
    appears in the end of embedded difference, it is escaped by another
    tilde.
    If both texts are C{None}, C{None} is returned as the difference.

    The C{hlto} parameter can be used to additionally highlight
    embedded difference for an output descriptor pointed to by it
    (e.g. colorized for the shell if given as C{sys.stdout}).
    If highlighting is applied, L{word_ediff_to_old} and L{word_ediff_to_new}
    cannot be used to recover the original texts.

    See L{word_diff} for description of other parameters.

    @param hlto: destination to produce extra highlighting for
    @type hlto: file descriptor

    @returns: string with embedded differences and possibly difference ratio
    @rtype: string or None or (string or None, float)

    @see: L{word_diff}
    """

    dlist, diff_ratio = word_diff(text_old, text_new, markup, format, diffr=True)
    if not dlist:
        return diffr and (None, 0.0) or None
    dwraps = _assemble_ewraps(hlto)
    dtext = _assemble_ediff(dlist, dwraps)

    return diffr and (dtext, diff_ratio) or dtext


_capt_old_rx = re.compile(  "\\" + _old_opnc + "\\" + _old_vtag + "(.*?)" \
                          + "\\" + _old_vtag + "\\" + _old_clsc, re.U|re.S)
_capt_new_rx = re.compile(  "\\" + _new_opnc + "\\" + _new_vtag + "(.*?)" \
                          + "\\" + _new_vtag + "\\" + _new_clsc, re.U|re.S)


def word_ediff_to_old (dtext):
    """
    Recover old version (-) from text with embedded differences.

    @param dtext: text with embedded differences
    @type dtext: string

    @returns: old version of the text
    @rtype: string or None

    @see: L{word_ediff}
    """

    return _word_ediff_to_oldnew(dtext, "", "\\1")


def word_ediff_to_new (dtext):
    """
    Recover new version (+) from text with embedded differences.

    @param dtext: text with embedded differences
    @type dtext: string

    @returns: new version of the text
    @rtype: string or None

    @see: L{word_ediff}
    """

    return _word_ediff_to_oldnew(dtext, "\\1", "")


def _word_ediff_to_oldnew (dtext, repl_old, repl_new):

    if dtext is None:
        return None
    text = dtext
    text = _capt_old_rx.sub(repl_new, text)
    text = _capt_new_rx.sub(repl_old, text)
    text = _unescape_ewraps(text)
    if text.endswith(_tagext_none):
        text = text[:-_tagext_none_len]
        if not text:
            return None
    return text


def line_word_diff (lines_old, lines_new, markup=False, format=None,
                    diffr=False):
    """
    Create word-level difference between old and new lines of text.

    First makes a difference on a line-level, and then for each set of
    differing lines a difference on word-level, using L{word_diff}.
    Difference is presented as a list of tuples of word diffs and ratios
    as constructed by L{word_diff}.
    See L{word_diff} for description of keyword parameters.
    The difference ratio is computed as line-length weighted average
    of word difference ratios per line.

    @param lines_old: old lines of text
    @type lines_old: string

    @param lines_new: new lines of text
    @type lines_new: string

    @returns: difference list and possibly difference ratio
    @rtype: list of word-diffs or (list of word-diffs, float)
    """

    # Create the difference.
    # For basic diffing, indicate lines with content by adding them a newline.
    dlist = list(ndiff(lines_old, lines_new))
    # Remove non-diff segments and split into tag-segment pairs.
    dlist = [(x[0], x[2:]) for x in dlist if x[:1] in "+- "]

    # Reshuffle so that all consecutive old-new lines are grouped into
    # all old followed by all new.
    # For each old-new set, compute word-diffs and weigh diff-ratios.
    wdiffs = []
    sumwdrs = 0.0
    sumws = 0.0
    i = 0
    while i < len(dlist):
        while i < len(dlist) and dlist[i][0] not in "+-":
            seg = dlist[i][1]
            wdiffs.append(([(" ", seg)], 0.0))
            w = len(seg)
            sumwdrs += 0.0 * w
            sumws += w
            i += 1
        seq_new = []
        seq_old = []
        while i < len(dlist) and dlist[i][0] in "+-":
            seg = dlist[i][1]
            if dlist[i][0] != "+":
                seq_old.append(seg)
            if dlist[i][0] != "-":
                seq_new.append(seg)
            i += 1
        if seq_old and seq_new:
            # Decide which line to pair with which by minimal local diff ratio.
            # FIXME: Now it tries to place best first line, then second, etc.
            # For higher precision, test all combinations.
            lold = len(seq_old)
            lnew = len(seq_new)
            lmax = max(lold, lnew)
            lmin = min(lold, lnew)
            if lold <= lnew:
                s1, s2, tag2, rev = seq_old, seq_new, "+", False
            else:
                s1, s2, tag2, rev = seq_new, seq_old, "-", True
            i1 = 0
            i2 = 0
            while i1 < lmin:
                mindr = 1.1
                mwdiff = []
                mj2 = -1
                for j2 in range(i2, lmax - lmin + i1 + 1):
                    if not rev:
                        t1, t2 = s1[i1], s2[j2]
                    else:
                        t1, t2 = s2[j2], s1[i1]
                    wdiff, dr = word_diff(t1, t2, markup, format, diffr=True)
                    if mindr > dr:
                        mindr = dr
                        mwdiff = wdiff
                        mj2 = j2
                for j2 in range(i2, mj2):
                    wdiffs.append(([(tag2 + _tagext_none, s2[j2])], 1.0))
                    w = len(s2[j2])
                    sumwdrs += 1.0 * w
                    sumws += w
                i2 = mj2
                wdiffs.append((mwdiff, mindr))
                w = len(s2[i2])
                sumwdrs += mindr * w
                sumws += w
                i1 += 1
                i2 += 1
            for j2 in range(i2, lmax):
                wdiffs.append(([(tag2 + _tagext_none, s2[j2])], 1.0))
                w = len(s2[j2])
                sumwdrs += 1.0 * w
                sumws += w
        elif seq_old:
            wdiffs.extend([([("-" + _tagext_none, x)], 1.0) for x in seq_old])
            w = sum(map(len, seq_old))
            sumwdrs += 1.0 * w
            sumws += w
        elif seq_new:
            wdiffs.extend([([("+" + _tagext_none, x)], 1.0) for x in seq_new])
            w = sum(map(len, seq_new))
            sumwdrs += 1.0 * w
            sumws += w

    # Weighted-averaged diff-ratio.
    dr = sumws > 0.0 and sumwdrs / sumws or 0.0

    return diffr and (wdiffs, dr) or [x[0] for x in wdiffs]


def line_word_ediff (lines_old, lines_new, markup=False, format=None, hlto=None,
                     diffr=False):
    """
    Create word-level embedded difference between old and new lines of text.

    Same as L{line_word_diff}, but the difference is returned as list of tuples
    of line of text (in which the new segments are wrapped as C{{+...+}},
    and the old segments as C{{-...-}}) and difference ratio for the line.
    See L{word_diff} and L{word_ediff} for description of keyword parameters.

    @returns: list of lines and partial difference ratios, and total ratio
    @rtype: list of (string, float), float

    @see: L{line_word_diff}
    """

    dlists, diff_ratio = line_word_diff(lines_old, lines_new, markup, format,
                                        diffr=True)
    dwraps = _assemble_ewraps(hlto)
    dlines = [(_assemble_ediff(x[0], dwraps), x[1]) for x in dlists]

    return diffr and (dlines, diff_ratio) or [x[0] for x in dlines]


def line_word_ediff_to_old (dlines):
    """
    Recover old version (-) from lines of text with embedded differences.

    @param dlines: lines of text with embedded differences
    @type dlines: list of strings

    @returns: old version of the lines
    @rtype: list of strings

    @see: L{line_word_ediff}
    """

    return _line_word_ediff_to_oldnew(dlines, "", "\\1")


def line_word_ediff_to_new (dlines):
    """
    Recover new version (+) from lines of text with embedded differences.

    @param dlines: lines of text with embedded differences
    @type dlines: list of strings

    @returns: new version of the lines
    @rtype: list of strings

    @see: L{line_word_ediff}
    """

    return _line_word_ediff_to_oldnew(dlines, "\\1", "")


def _line_word_ediff_to_oldnew (dlines, repl_old, repl_new):

    lines = []
    for dline in dlines:
        line = _word_ediff_to_oldnew(dline, repl_old, repl_new)
        if line is not None:
            lines.append(line)
    return lines


def _assemble_ediff (dlist, dwraps):

    old_opn, old_cls, new_opn, new_cls = dwraps
    dtext = []
    other_none = False
    for segtag, segtext in dlist:
        wext = ""
        if segtag.endswith(_tagext_none):
            # Can happen only if there is a single difference segment.
            segtag = segtag[:-_tagext_none_len]
            other_none = True
        segtext = _escape_ewraps(segtext)
        if segtag == _new_tag:
            dtext.append(new_opn + segtext + new_cls + wext)
        elif segtag == _old_tag:
            dtext.append(old_opn + segtext + old_cls + wext)
        else:
            dtext.append(segtext)
            haseqseg = True
    dtext = u"".join(dtext)

    if other_none:
        # Indicate the other string was none.
        dtext += _tagext_none
    elif dtext.endswith(_tagext_none):
        # Escape any trailing other-none markers.
        dtext += _tagext_none

    if segtag[-_tagext_none_len:] == _tagext_none:
        # Can happen only if there is exactly one difference segment.
        wext = _tagext_none
        segtag = segtag[:-_tagext_none_len:]

    return dtext


def _assemble_ewraps (hlto):

    if not hlto:
        old_opn = _old_opn
        old_cls = _old_cls
        new_opn = _new_opn
        new_cls = _new_cls
    else:
        C = colors_for_file(hlto)
        old_opn = C.RED + _old_opn
        old_cls = _old_cls + C.RESET
        new_opn = C.BLUE + _new_opn
        new_cls = _new_cls + C.RESET

    return old_opn, old_cls, new_opn, new_cls


def _escape_ewraps (text):

    return _escunesc_ewraps(text, False)


def _unescape_ewraps (text):

    return _escunesc_ewraps(text, True)


_ediff_esc = _tagext_none
_ediff_esc_len = len(_ediff_esc)

def _escunesc_ewraps (text, unescape):

    for wstart, wend in (
        (_old_opnc, _old_vtag),
        (_old_vtag, _old_clsc),
        (_new_opnc, _new_vtag),
        (_new_vtag, _new_clsc),
    ):
        segs = []
        p = 0
        tlen = len(text)
        lwstart = len(wstart)
        lwend = len(wend)
        while True:
            pp = p
            p = text.find(wstart, p)
            if p < 0:
                segs.append(text[pp:])
                break
            segs.append(text[pp:p])
            pp = p
            p += lwstart
            nesc = 0
            while p < tlen and text[p:p + _ediff_esc_len] == _ediff_esc:
                p += _ediff_esc_len
                nesc += 1
            if p == tlen or text[p:p + lwend] != wend or (unescape and nesc < 1):
                segs.append(text[pp:p])
            else:
                if not unescape:
                    segs.append(text[pp:p] + _ediff_esc + wend)
                else:
                    segs.append(text[pp:p - _ediff_esc_len] + wend)
                p += lwend
        text = u"".join(segs)

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
    @type merge: bool

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

