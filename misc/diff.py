# -*- coding: UTF-8 -*

"""
Produce special diffs between strings and other interesting objects.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

from difflib import SequenceMatcher
import random
import re

from pology import PologyError, _, n_
from pology.misc.colors import colors_for_file
from pology.file.message import MessageUnsafe
from pology.misc.report import error
from pology.misc.split import split_text


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
_all_wrappers = set((_new_opn, _new_cls, _old_opn, _old_cls))

_tmp_wr = (_new_vtag, _new_opnc, _new_clsc, _old_vtag, _old_opnc, _old_clsc)
_tmp_wrlen = map(len, _tmp_wr)
if max(_tmp_wrlen) != 1 or min(_tmp_wrlen) != 1:
    error(_("@info \"ediff\" is shorthand for \"embedded difference\"",
            "All ediff wrapper elements must be of unit length."))


class _Sequence_diff_wrapper:

    def __init__ (self, obj, reductf=None):
        self.obj = obj
        self._robj = (reductf or (lambda x: x))(obj)

    def __hash__ (self):
        return hash(self._robj)

    def __iter__ (self):
        return iter(self._robj)

    def __eq__ (self, other):
        return self._robj == other._robj


def tdiff (seq_old, seq_new, reductf=None, diffr=False):
    """
    Create tagged difference of two sequences.

    Difference is presented as a list of tuples,
    with each tuple composed of a difference tag and a sequence element.
    Difference tag is string C{"+"}, C{"-"}, or C{" "}, for elements which
    belong to the old, the new, or to both sequences, respectively.

    The list is ordered such that collecting all elements not tagged
    as old will reconstruct the new sequence, and collecting all not tagged
    as new will reconstruct the old sequence.

    If requested by the C{diffr} parameter, also reported is the
    I{difference ratio}, a heuristic measure of difference between two texts.
    0.0 means no difference, and 1.0 that sequences are completely different.

    Examples::

        >>> s1 = "A type of foo".split()
        >>> s2 = "A kind of foo".split()
        >>> tdiff(s1, s2)
        [(' ', 'A'), ('-', 'type'), ('+', 'kind'), (' ', 'of'), (' ', 'foo')]
        >>> word_diff(s1, s2, diffr=True)
        ([(' ', 'A'), ('-', 'type'), ('+', 'kind'), (' ', 'of'), (' ', 'foo')],
        0.25)

    To be able to diff them, sequence elements only need to be hashable.
    However, for compound elements it may be better to diff them
    only by some subset of data, e.g. by one of their string attributes.
    Parameter C{reductf} can be used to specify a reduction function, which
    will be called on each element to produce its diffing representative.

    @param seq_old: sequence to diff from
    @type seq_old: sequence with hashable elements
    @param seq_new: sequence to diff to
    @type seq_new: sequence with hashable elements
    @param reductf: function to produce diffing representatives
    @type reductf: (sequence element) -> diffing representative
    @param diffr: whether to report difference ratio
    @type diffr: bool

    @returns: difference list and possibly difference ratio
    @rtype: [(string, element)...] or ([(string, element)...], float)
    """

    if reductf is not None:
        seq_old = [_Sequence_diff_wrapper(x, reductf) for x in seq_old]
        seq_new = [_Sequence_diff_wrapper(x, reductf) for x in seq_new]

    dlist = []
    seqmatch = SequenceMatcher(None, seq_old, seq_new)
    opcodes = seqmatch.get_opcodes()
    if diffr:
        dr = 1.0 - seqmatch.ratio()
    for opcode, i1, i2, j1, j2 in opcodes:
        if opcode == "equal":
            dlist.extend([(_equ_tag, el) for el in seq_old[i1:i2]])
        elif opcode == "replace":
            dlist.extend([(_old_tag, el) for el in seq_old[i1:i2]])
            dlist.extend([(_new_tag, el) for el in seq_new[j1:j2]])
        elif opcode == "delete":
            dlist.extend([(_old_tag, el) for el in seq_old[i1:i2]])
        elif opcode == "insert":
            dlist.extend([(_new_tag, el) for el in seq_new[j1:j2]])
        else:
            raise PologyError(
                _("@info \"opcode\" is shorthand for \"operation code\"",
                  "Unknown opcode '%(code)s' from sequence matcher.")
                % dict(code=opcode))

    if reductf is not None:
        dlist = [(tag, el.obj) for tag, el in dlist]

    return diffr and (dlist, dr) or dlist


def itdiff (seq_old, seq_new, reductf=None, cutoff=0.6, diffr=False):
    """
    Create interleaved tagged difference of two sequences.

    Similar to L{tdiff}, except that blocks of added/removed elements
    are further heuristically interleaved by similarity, such that
    each removed element may be followed by a similar added element,
    if such has been determined.
    This is useful e.g. to be able to afterwards make inner difference
    of each two paired similar elements (e.g. word diff within line diff).

    Example::

        >>> s1 = "Two blue airplanes".split()
        >>> s2 = "Two bluish ships".split()
        >>> D.tdiff(s1, s2)
        [(' ', 'Two'), ('-', 'blue'), ('-', 'airplanes'), ('+', 'bluish'),
         ('+', 'ships')]
        >>> D.itdiff(s1, s2)
        [(' ', 'Two'), ('-', 'blue'), ('+', 'bluish'), ('-', 'airplanes'),
         ('+', 'ships')]

    To be able to interleave blocks, each element in turn must be
    a sequence in its own. This means that function supplied by C{reductf},
    otherwise of same semantics as in L{tdiff}, here must also produce
    a sequence as diffing representative (e.g. a string).

    Parameter C{cutoff} states the minimal similarity between
    two elements needed for them to be considered similar at all.

    @param seq_old: sequence to diff from
    @type seq_old: sequence with hashable elements
    @param seq_new: sequence to diff to
    @type seq_new: sequence with hashable elements
    @param reductf: function to produce diffing representatives
    @type reductf: (sequence element) -> representative sequence
    @param cutoff: minimal similarity to consider elements similar
    @type cutoff: float [0, 1]
    @param diffr: whether to report difference ratio
    @type diffr: bool

    @returns: interleaved difference list and possibly difference ratio
    @rtype: [(string, element)...] or ([(string, element)...], float)
    """

    dres = tdiff(seq_old, seq_new, reductf=reductf, diffr=diffr)
    if diffr:
        dlist, dr = dres
    else:
        dlist = dres
    lendl = len(dlist)
    idlist = []
    i = 0
    while True:
        while i < lendl and dlist[i][0] == _equ_tag:
            idlist.append(dlist[i])
            i += 1
        if i >= lendl:
            break
        els_old = []
        els_new = []
        while i < lendl and dlist[i][0] != _equ_tag:
            if dlist[i][0] == _old_tag:
                els_old.append(dlist[i][1])
            else:
                els_new.append(dlist[i][1])
            i += 1
        if els_old and els_new:
            idlist.extend(_dinterleave(els_old, els_new, reductf, cutoff))
        else:
            idlist.extend([(_old_tag, x) for x in els_old])
            idlist.extend([(_new_tag, x) for x in els_new])

    return diffr and (idlist, dr) or idlist


def _dinterleave (els_old, els_new, reductf, cutoff):

    reductf = reductf or (lambda x: x)

    #plf = _plinds_full # too expensive
    plf = _plinds_cont
    pls_old = plf(len(els_old), len(els_old) + len(els_new), 0)
    pls_new = plf(len(els_new), len(els_old) + len(els_new), 0)
    pls_old.reverse() # so that last old-new pair is top-bottom
    maxsim = 0.0
    opt_pairs = (pls_old[-1], pls_new[-1])
    i = 0
    for pl_old in pls_old:
        for pl_new in pls_new:
            i += 1
            sim = 0.0
            pairs = zip(pl_old, pl_new)
            for i_old, i_new in pairs:
                if i_old is None or i_new is None:
                    continue
                seq_old = reductf(els_old[i_old])
                seq_new = reductf(els_new[i_new])
                r = SequenceMatcher(None, seq_old, seq_new).ratio()
                if r < cutoff:
                    r = 0.0
                sim += r
            if sim >= maxsim: # >= so that last equal wins
                maxsim = sim
                opt_pairs = pairs
    dlist = []
    for i_old, i_new in opt_pairs:
        if i_old is not None:
            dlist.append((_old_tag, els_old[i_old]))
        if i_new is not None:
            dlist.append((_new_tag, els_new[i_new]))

    return dlist


def _plinds_full (ninds, nplaces, baseind):

    if nplaces < ninds:
        return []
    if ninds <= 0:
        return [(None,) * nplaces]
    else:
        return (  [(baseind,) + x
                   for x in _plinds_full(ninds - 1, nplaces - 1, baseind + 1)]
                + [(None,) + x
                   for x in _plinds_full(ninds, nplaces - 1, baseind)])


def _plinds_cont (ninds, nplaces, baseind):

    pls = []
    insinds = tuple(range(ninds))
    for i in range(nplaces - ninds + 1):
        pls.append((None,) * i + insinds + (None,) * (nplaces - ninds - i))
    return pls


def word_diff (text_old, text_new, markup=False, format=None, diffr=False):
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
    @rtype: [(string, string)...] or ([(string, string)...], float)
    """

    # Special cases, when one or both texts are None, or both are empty.
    specdlist = None
    if text_old is None and text_new is None:
        specdlist = []
        specdr = 0.0
    elif text_old is None:
        specdlist = [(_new_tag + _tagext_none, text_new)]
        specdr = 1.0
    elif text_new is None:
        specdlist = [(_old_tag + _tagext_none, text_old)]
        specdr = 1.0
    elif text_new == "" and text_old == "":
        specdlist = [(_equ_tag, "")]
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

    # Create the tagged difference.
    dlist = tdiff(segments[0], segments[1])

    # Recompute which elements of the difference are intersections.
    dlist_isintr = []
    i_old = 0
    i_new = 0
    for tag, seg in dlist:
        if tag == _old_tag:
            dlist_isintr.append(segment_isintr[0][i_old])
        else:
            dlist_isintr.append(segment_isintr[1][i_new])

        if tag != _new_tag:
            i_old += 1
        if tag != _old_tag:
            i_new += 1

    # Reshuffle so that all old-new elements consecutive but for the
    # intersections are grouped into all old followed by all new,
    # with intersections included in both.
    ndlist = []
    i = 0
    while i < len(dlist):
        while i < len(dlist) and dlist[i][0] == _equ_tag:
            ndlist.append(dlist[i])
            i += 1
        seq_new = []
        seq_old = []
        i_first_diff = i
        i_last_diff = i
        while i < len(dlist) and (dlist[i][0] != _equ_tag or dlist_isintr[i]):
            if dlist[i][0] != _new_tag:
                seq_old.append(dlist[i][1])
            if dlist[i][0] != _old_tag:
                seq_new.append(dlist[i][1])
            if dlist[i][0] != _equ_tag:
                i_last_diff = i
            i += 1
        for iex in range(i_last_diff, i - 1):
            seq_new.pop()
            seq_old.pop()
        i = i_last_diff + 1
        if seq_old:
            ndlist.append((_old_tag, "".join(seq_old)))
        if seq_new:
            ndlist.append((_new_tag, "".join(seq_new)))
    dlist = ndlist

    # Join contiguous new/old/both segments, make tagged tuples.
    ndlist = []
    S_EQU, S_NEW, S_OLD = range(3)
    state = S_EQU
    cseg = []
    len_equ, len_old, len_new = 0, 0, 0
    _sen_tag = "."
    dlist.append((_sen_tag, "")) # sentry
    for tag, seg in dlist:

        if state == S_EQU and tag in (_new_tag, _old_tag, _sen_tag):
            if cseg:
                ndlist.append((_equ_tag, "".join(cseg)))
            cseg = []
            if tag == _new_tag:
                state = S_NEW
            else:
                state = S_OLD

        elif state == S_OLD and tag in (_equ_tag, _new_tag, _sen_tag):
            if cseg:
                ndlist.append((_old_tag, "".join(cseg)))
            cseg = []
            if tag == _equ_tag:
                state = S_EQU
            else:
                state = S_NEW

        elif state == S_NEW and tag in (_equ_tag, _old_tag, _sen_tag):
            if cseg:
                ndlist.append((_new_tag, "".join(cseg)))
            cseg = []
            if tag == _equ_tag:
                state = S_EQU
            else:
                state = S_OLD

        if tag == _old_tag:
            len_old += len(seg)
        elif tag == _new_tag:
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
    @rtype: string/None or (string/None, float)

    @see: L{word_diff}
    """

    dlist, dr = word_diff(text_old, text_new, markup, format, diffr=True)
    if not dlist:
        return diffr and (None, 0.0) or None
    dwraps = _assemble_ewraps(hlto)
    dtext = _assemble_ediff(dlist, dwraps)

    return diffr and (dtext, dr) or dtext


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

    return _word_ediff_to_oldnew(dtext, _capt_old_rx, _capt_new_rx)


def word_ediff_to_new (dtext):
    """
    Recover new version (+) from text with embedded differences.

    @param dtext: text with embedded differences
    @type dtext: string

    @returns: new version of the text
    @rtype: string or None

    @see: L{word_ediff}
    """

    return _word_ediff_to_oldnew(dtext, _capt_new_rx, _capt_old_rx)


def _word_ediff_to_oldnew (dtext, capt_this_rx, capt_other_rx):

    if dtext is None:
        return None
    text = dtext
    text = capt_this_rx.sub(r"\1", text)
    text = capt_other_rx.sub(r"", text)
    text = _unescape_ewraps(text)
    if text.endswith(_tagext_none):
        text = text[:-_tagext_none_len]
        if not text and capt_other_rx.search(dtext):
            return None
    return text


def line_diff (lines_old, lines_new, markup=False, format=None, diffr=False):
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

    @returns: difference list and possibly difference ratios
    @rtype: [[(string, string)...]...]
        or ([([(string, string)...], float)...], float)
    """

    # Create the difference.
    dlist = tdiff(lines_old, lines_new)

    # Reshuffle so that all consecutive old-new lines are grouped into
    # all old followed by all new.
    # For each old-new set, compute word-diffs and weigh diff-ratios.
    wdiffs = []
    sumwdrs = 0.0
    sumws = 0.0
    i = 0
    while i < len(dlist):
        while i < len(dlist) and dlist[i][0] == _equ_tag:
            seg = dlist[i][1]
            wdiffs.append(([(_equ_tag, seg)], 0.0))
            w = len(seg)
            sumwdrs += 0.0 * w
            sumws += w
            i += 1
        seq_new = []
        seq_old = []
        while i < len(dlist) and dlist[i][0] != _equ_tag:
            seg = dlist[i][1]
            if dlist[i][0] != _new_tag:
                seq_old.append(seg)
            if dlist[i][0] != _old_tag:
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
                s1, s2, tag2, rev = seq_old, seq_new, _new_tag, False
            else:
                s1, s2, tag2, rev = seq_new, seq_old, _old_tag, True
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
            wdiffs.extend([([(_old_tag + _tagext_none, x)], 1.0)
                           for x in seq_old])
            w = sum(map(len, seq_old))
            sumwdrs += 1.0 * w
            sumws += w
        elif seq_new:
            wdiffs.extend([([(_new_tag + _tagext_none, x)], 1.0)
                           for x in seq_new])
            w = sum(map(len, seq_new))
            sumwdrs += 1.0 * w
            sumws += w

    # Weighted-averaged diff-ratio.
    dr = sumws > 0.0 and sumwdrs / sumws or 0.0

    return diffr and (wdiffs, dr) or [x[0] for x in wdiffs]


def line_ediff (lines_old, lines_new, markup=False, format=None, hlto=None,
                diffr=False):
    """
    Create word-level embedded difference between old and new lines of text.

    Same as L{line_diff}, but the difference is returned as list of tuples
    of line of text (in which the new segments are wrapped as C{{+...+}},
    and the old segments as C{{-...-}}) and difference ratio for the line.
    See L{word_diff} and L{word_ediff} for description of keyword parameters.

    @returns: lines with embedded differences and possibly difference ratios
    @rtype: [string...] or ([(string, float)...], float)

    @see: L{line_diff}
    """

    dlists, dr = line_diff(lines_old, lines_new, markup, format, diffr=True)
    dwraps = _assemble_ewraps(hlto)
    dlines = [(_assemble_ediff(x[0], dwraps), x[1]) for x in dlists]

    return diffr and (dlines, dr) or [x[0] for x in dlines]


def line_ediff_to_old (dlines):
    """
    Recover old version (-) from lines of text with embedded differences.

    @param dlines: lines of text with embedded differences
    @type dlines: list of strings

    @returns: old version of the lines
    @rtype: list of strings

    @see: L{line_ediff}
    """

    return _line_ediff_to_oldnew(dlines, word_ediff_to_old)


def line_ediff_to_new (dlines):
    """
    Recover new version (+) from lines of text with embedded differences.

    @param dlines: lines of text with embedded differences
    @type dlines: list of strings

    @returns: new version of the lines
    @rtype: list of strings

    @see: L{line_ediff}
    """

    return _line_ediff_to_oldnew(dlines, word_ediff_to_new)


def _line_ediff_to_oldnew (dlines, word_ediff_to_x):

    lines = []
    for dline in dlines:
        line = word_ediff_to_x(dline)
        if line is not None:
            lines.append(line)
    return lines


def _assemble_ediff (dlist, dwraps):

    if not dlist:
        return None

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

    If an input span is invalid in any way,
    it is carried over verbatim into result.

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

    if not spans:
        return spans

    # Resolve negative spans.
    # Select out spans with invalid start or end.
    flen = len(ftext)
    fspans = []
    invalid_spans = []
    for span in spans:
        start, end = span[:2]
        valid = True

        if isinstance(start, int):
            if start < 0:
                start = flen - start
        else:
            valid = False

        if isinstance(end, int):
            if end < 0:
                end = flen - end
        else:
            valid = False

        if valid:
            fspans.append((start, end) + span[2:])
        else:
            invalid_spans.append(span)

    # Create character-level difference from original to filtered text.
    dlist = tdiff(otext, ftext)

    # For each span, go through the difference and... do some magic.
    aspans = []
    for fspan in fspans:
        aspan = []
        for filtered_index, first in zip(fspan[:2], (True, False)):
            original_index = 0
            original_index_atdiff = 0
            track_index = 0
            adapted_index = None
            stop_at_next_eq = False
            for dtag, dseg in dlist:
                slen = len(dseg)
                if dtag == _new_tag:
                    track_index += slen
                elif dtag == _old_tag:
                    original_index += slen
                else:
                    original_index += slen
                    track_index += slen
                    original_index_atdiff = original_index
                    if stop_at_next_eq:
                        break
                if track_index >= filtered_index:
                    exlen = track_index - filtered_index # 0 if char-level diff
                    if dtag == _equ_tag:
                        adapted_index = original_index - exlen
                        break
                    else: # dtag must be _new_tag
                        if first:
                            adapted_index = original_index_atdiff
                            break
                        else:
                            stop_at_next_eq = True
            if stop_at_next_eq:
                adapted_index = original_index
            if adapted_index is None:
                break
            aspan.append(adapted_index)
        if adapted_index is not None:
            aspan.extend(fspan[2:])
            aspans.append(tuple(aspan))

    # Merge spans if requested.
    if merge:
        # Sort by start index immediately, for priority of extra elements.
        aspans.sort(key=lambda x: x[0])
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
        maspans.sort(key=lambda x: x[0])
        aspans = maspans

    # Put invalid spans back.
    aspans.extend(invalid_spans)

    return aspans


_dt_state, _dt_single, _dt_list = range(3)

_msg_diff_parts = (
    ("obsolete", _dt_state),
    ("fuzzy", _dt_state),
    ("manual_comment", _dt_list),
    ("msgctxt_previous", _dt_single),
    ("msgid_previous", _dt_single),
    ("msgid_plural_previous", _dt_single),
    ("msgctxt", _dt_single),
    ("msgid", _dt_single),
    ("msgid_plural", _dt_single),
    ("msgstr", _dt_list),
)
_msg_dpart_types = dict(_msg_diff_parts)

_msg_curr_fields = (
    "msgctxt", "msgid", "msgid_plural",
)
_msg_currprev_fields = [(x, x + "_previous") for x in _msg_curr_fields]


def msg_diff (msg1, msg2, pfilter=None, addrem=None, diffr=False):
    """
    Create word-level difference between extraction-invariant parts of messages.

    For which parts of a message are considered extraction-invariant,
    see description of L{inv<file.message.Message_base>} instance variable
    of message objects.

    There are two return modes, depending on the value of C{diffr} parameter.

    If C{diffr} is C{False}, the difference is returned as list of 3-tuples of
    differences by message part: (part name, part item, word difference).
    The part name can be used to fetch the part value from the message,
    using L{get()<file.message.Message_base.get>} method of message objects.
    The part item is C{None} for singular message parts (e.g. C{msgid}),
    and index for list parts (e.g. C{msgstr}).
    See L{word_diff<misc.diff.word_diff>} for the format
    of word-level difference.

    If C{diffr} is C{True}, then each part difference has a fourth element,
    the difference ratio; see L{word_diff} for its semantics. Additionally,
    the total difference ratio is computed, based on partial ones
    (also counting the zero difference of parts which were equal).
    The return value is now a 2-tuple of list of part differences
    (as 4-tuples) and the total difference ratio.

    Either of the messages can be given as C{None}. In case only one of
    the messages is C{None}, the difference of C{msgid} field will show
    that this field does not exist in the non-existant message (according to
    format of non-existant counterparts of L{word_diff<misc.diff.word_diff>}).
    If both messages are C{None}, the difference is empty list, as the
    messages are same, even if non-existant.

    Every C{msgstr} field can be passed through a filter before differencing,
    using the C{pfilter} parameter.

    Instead of constructing the full difference, using the C{addrem} parameter
    only equal, added, or removed segments can be reported.
    The value of this parameter is a string, such that the first character
    selects the type of partial difference: one of ('=', "e') for equal,
    ('+', 'a') for added, and ('-', 'r') for removed segments, and the
    rest of the string is used as separator to join the selected segments
    (if the separator is empty, space is used instead).

    @param msg1: the message from which to make the difference
    @type msg1: L{Message_base<file.message.Message_base>} or None
    @param msg2: the message to which to make the difference
    @type msg2: L{Message_base<file.message.Message_base>} or None
    @param pfilter: filter to be applied to translation prior to differencing
    @type pfilter: callable
    @param addrem: report equal, added or removed segments instead of
        full difference, joined by what follows the selection character
    @type addrem: string
    @param diffr: whether to report difference ratio
    @type diffr: bool

    @return: difference list
    @rtype: [(string, int/None, [(string, string)...])...]
        or ([(string, int/None, [(string, string)...], float)...], float)
    """

    # Create thoroughly empty dummy messages in place of null messages.
    mod_msgs = []
    for msg in (msg1, msg2):
        if msg is None:
            msg = MessageUnsafe()
            msg.msgid = None
            msg.msgstr = []
        mod_msgs.append(msg)
    msg1, msg2 = mod_msgs

    # For partial differencing, decide upon which part of diffs to take.
    ar_dtyp = None
    if addrem:
        mode = addrem[0]
        ar_sep = unicode(addrem[1:] or " ")
        if mode in ("=", "e"):
            ar_dtyp = _equ_tag
        elif mode in ("+", "a"):
            ar_dtyp = _new_tag
        elif mode in ("-", "r"):
            ar_dtyp = _old_tag
        else:
            raise PologyError(
                _("@info",
                  "Unknown selection mode '%(mode)s' for partial differencing.")
                % dict(mode=mode))

    # Diff two texts under the given diffing options.
    def _twdiff (text1, text2, islines=False, cpfilter=None):

        f_diff = islines and line_diff or word_diff

        if cpfilter:
            if not islines:
                text1 = cpfilter(text1)
                text2 = cpfilter(text2)
            else:
                text1 = [cpfilter(x) for x in text1]
                text2 = [cpfilter(x) for x in text2]

        format = (msg2 or msg1).format
        wdiff, dr = f_diff(text1, text2,
                           markup=True, format=format, diffr=True)
        if addrem:
            if not islines:
                wdiff_part = None
                ar_segs = [x for t, x in wdiff if t == ar_dtyp]
                if text1 is not None or text2 is not None:
                    wdiff_part = ar_sep.join(ar_segs)
            else:
                wdiff_part = []
                for wdiff1, dr1 in wdiff:
                    ar_segs = [x for t, x in wdiff1 if t == ar_dtyp]
                    dr1 = 1.0 - dr1
                    if text1 or text2:
                        wdiff_part += [(ar_sep.join(ar_segs), dr1)]
            wdiff = wdiff_part
            dr = 1.0 - dr

        return wdiff, dr

    # Create diffs of relevant parts.
    part_diffs = []
    sumdr = 0.0
    sumw = 0.0 # ...unless something cleverer comes up, weigh each part same.
    for part, typ in _msg_diff_parts:
        if typ == _dt_single:
            val1 = msg1.get(part)
            val2 = msg2.get(part)
            wdiff, dr = _twdiff(val1, val2)
            part_diffs.append((part, None, wdiff, dr))
            sumdr += dr * 1.0
            sumw += 1.0
        elif typ == _dt_list:
            lst1 = msg1.get(part)
            lst2 = msg2.get(part)
            cpf = part == "msgstr" and pfilter or None
            wdiffs, totdr = _twdiff(lst1, lst2, islines=True, cpfilter=cpf)
            item = 0
            for wdiff, dr in wdiffs:
                part_diffs.append((part, item, wdiff, dr))
                item += 1
                sumdr += dr * 1.0
                sumw += 1.0
        elif typ == _dt_state:
            st1 = msg1.get(part) and part or ""
            st2 = msg2.get(part) and part or ""
            wdiff, dr = word_diff(st1, st2, diffr=True)
            part_diffs.append((part, None, wdiff, dr))
            sumdr += dr * 1.0
            sumw += 1.0
        else:
            raise PologyError(
                _("@info",
                  "Unhandled message part '%(part)s' encountered "
                  "while differencing.")
                % dict(part=part))

    if diffr:
        dr = sumw and sumdr / sumw or 0.0
        return part_diffs, dr
    else:
        return [x[:3] for x in part_diffs]


_dcmnt_field = "auto_comment" # to use manual_comment would be bad idea
_dcmnt_head = u"ediff:"
_dcmnt_head_esc = u"~" # must be single character
_dcmnt_sep = u", "
_dcmnt_asep = u" "
_dcmnt_ind_state = u"state"
_dcmnt_ind_ctxtpad = u"ctxtpad"
_dcmnt_ind_infsep = u"infsep"
_dcmnt_all_inds = ( # ordered
    _dcmnt_ind_state, _dcmnt_ind_ctxtpad, _dcmnt_ind_infsep,
)
_ctxtpad_sep = u"|"
_ctxtpad_noctxt = u"~"
_ctxtpad_alnums = u"abcdefghijklmnopqrstuvwxyz0123456789"
_infsep_blk = u"~="
_infsep_minlen = 20

def msg_ediff (msg1, msg2, pfilter=None, addrem=None,
               emsg=None, ecat=None, eokpos=None, enoctxt=None,
               emptydc=False, hlto=None, diffr=False):
    """
    Create word-level embedded difference between extraction-invariant
    parts of messages.

    Like L{msg_diff}, but instead of difference list the result is a message
    with embedded differences, of the kind produced by L{word_ediff}.
    See L{msg_diff} for description C{pfilter} and C{addrem} parameters,
    and L{word_ediff} for the format of embedded differences.
    Additionally, if C{pfilter} is given, C{msgstr} fields will be diffed
    both with and without the filter, and if the two diffs are not equal,
    both embeddings are going to be presented in the field,
    suitably visually separated.

    By default, a new message with embedded difference will be constructed,
    of the type of first non-None of C{msg2} and C{msg1}.
    Alternatively, the difference can be embedded into the message supplied
    by C{emsg} parameter.

    If resulting messages with embedded differences are to be inserted
    into a catalog, that catalog can be given by the C{ecat} parameter.
    Then, if the key of the resulting message would conflict one of
    those already in the catalog, its context will be appropriately padded
    to avoid the conflict.
    This is done by adding a pipe character and an unspecified number
    of alphanumerics (generally junk-looking) to the end of the C{msgctxt}.
    In case the conflict with a particular message in the catalog is
    acceptable (e.g. when resulting message is to be inserted in its place),
    the position of this message can be given by the C{eokpos} parameter.
    In case a certain value of C{msgctxt} should be padded regardless
    of whether there is a conflict or not,
    this value can be given by C{enoctxt} parameter.

    An additional automatic comment starting with C{ediff:}
    may be added to the message, possibly followed by some indicators
    necessary to complete the difference specification. These include:

      - C{state <STATE_DIFF> ...}: changes in message state, like
        C{obsolete} and C{fuzzy}; e.g. C{state {+obsolete+}} means
        that the message has been obsoleted from C{msg1} to C{msg2},
        while C{state {-obsolete-}} means that it has been was revived.

      - C{ctxtpad <STRING>}: padding alphanumerics added to the C{msgctxt}
        field to avoid key collision with one of the messages from C{ecat}.

      - C{infsep <BLOCK> <LENGTH>}: if C{pfilter} was used, this indicator
        states the building block and length in blocks of in-field separators.

    By default the difference comment is not added if there are no indicators,
    but it may be forced by setting C{emptydc} parameter to C{True}.

    Embedded differences can be additionally highlighted for an output
    descriptor given by C{hlto} parameter (e.g. colorized for the shell).

    If C{diffr} is C{True}, aside from the message with embedded differences,
    the total difference ratio is returned (see L{msg_diff}).
    If C{pfilter} is given, the ratio refers to difference under filter.

    @param msg1: the message from which to make the difference
    @type msg1: L{Message_base<file.message.Message_base>} or None
    @param msg2: the message to which to make the difference
    @type msg2: L{Message_base<file.message.Message_base>} or None
    @param pfilter: filter to be applied to translation prior to differencing
    @type pfilter: callable
    @param addrem: report equal, added or removed segments instead of
        full difference, joined by what follows the selection character
    @type addrem: string
    @param emsg: message to embedd the difference to
    @type emsg: L{Message_base<file.message.Message_base>}
    @param ecat: catalog of messages to avoid key conflict with
    @type ecat: L{Catalog<file.catalog.Catalog>}
    @param eokpos: position into C{ecat} where key conflict is ignored
    @type eokpos: int
    @param enoctxt: C{msgctxt} string that should be padded unconditionally
    @type enoctxt: string
    @param emptydc: whether to add difference comment even if empty
    @type emptydc: bool
    @param hlto: destination to produce highlighting for
    @type hlto: file
    @param diffr: whether to report difference ratio
    @type diffr: bool

    @return: message with embedded differences (or None)
        and possibly difference ratio
    @rtype: type(emsg or msg2 or msg1 or None) or (type(~), float)
    """

    if msg1 is None and msg2 is None:
        return not diffr and (None, 0.0) or None

    # Compute the difference.
    wdiffs, totdr = msg_diff(msg1, msg2, addrem=addrem, diffr=True)
    wdiffs_pf = []
    if pfilter:
        wdiffs_pf, totdr = msg_diff(msg1, msg2, pfilter=pfilter,
                                    addrem=addrem, diffr=True)

    # Construct list of embedded diffs out of original difference list.
    dwraps = _assemble_ewraps(hlto)
    if not addrem:
        mtoe = lambda x: (x[0], x[1], _assemble_ediff(x[2], dwraps), x[3])
        ediffs = map(mtoe, wdiffs)
        ediffs_pf = map(mtoe, wdiffs_pf)
    else:
        ediffs = wdiffs
        ediffs_pf = wdiffs_pf

    # Construct the message to embed differences into.
    if emsg is None:
        tmsg = msg2 or msg1
        emsg = type(tmsg)()
        for part, typ in _msg_diff_parts:
            tval = tmsg.get(part)
            if tval is not None:
                setattr(emsg, part, type(tval)(tval))

    # Indicators for the difference comment.
    indargs = {}

    # Determine field separator for raw/filtered differences.
    if ediffs_pf:
        infseplen = _infsep_minlen
        infsepinc = 5
        infseplen_p = infseplen - 1
        while infseplen_p < infseplen:
            infsep = _infsep_blk * infseplen
            infseplen_p = infseplen
            for part, item, ediff, dr in ediffs + ediffs_pf:
                if ediff and infsep in ediff:
                    infseplen += infsepinc
                    break
        indargs[_dcmnt_ind_infsep] = [_infsep_blk, str(infseplen)]

    # Embed differences.
    for i in range(len(ediffs)):
        part, item, ediff, dr = ediffs[i]
        typ = _msg_dpart_types[part]
        if typ == _dt_single:
            setattr(emsg, part, ediff)
        elif typ == _dt_list:
            lst = emsg.get(part)
            lst.extend([u""] * (item + 1 - len(lst)))
            if ediffs_pf:
                ediff_pf = ediffs_pf[i][2]
                if ediff_pf and ediff_pf != ediff:
                    ediff += "\n" + infsep + "\n" + ediff_pf
            lst[item] = ediff
        elif typ == _dt_state:
            stag, spart = wdiffs[i][2][0]
            if stag != _equ_tag:
                if _dcmnt_ind_state not in indargs:
                    indargs[_dcmnt_ind_state] = []
                indargs[_dcmnt_ind_state].append(ediff)
            sval = bool(stag in (_new_tag, _equ_tag) and spart)
            setattr(emsg, part, sval)
        else:
            raise PologyError(
                _("@info",
                  "Unhandled message part '%(part)s' encountered "
                  "while differencing.")
                % dict(part=part))

    # Pad context to avoid conflicts.
    if (   (ecat is not None and emsg in ecat and ecat.find(emsg) != eokpos)
        or (enoctxt is not None and emsg.msgctxt == enoctxt)
    ):
        noctxtind = emsg.msgctxt is None and _ctxtpad_noctxt or ""
        octxt = emsg.msgctxt or u""
        while True:
            padding = "".join([random.choice(_ctxtpad_alnums)
                               for x in range(5)])
            emsg.msgctxt = octxt + _ctxtpad_sep + padding + noctxtind
            if (    emsg not in ecat
                and (enoctxt is None or emsg.msgctxt != enoctxt)
            ):
                break
        indargs[_dcmnt_ind_ctxtpad] = [padding]

    # If any of the existing comments looks like diff comment, escape it.
    ecomments = emsg.get(_dcmnt_field)
    for i in range(len(ecomments)):
        scmnt = ecomments[i].strip()
        p = scmnt.find(_dcmnt_head)
        if p >= 0 and scmnt[:p] == _dcmnt_head_esc * p:
            nwp = 0
            while scmnt[nwp].isspace():
                nwp += 1
            ecomments[i] = scmnt[:nwp] + _dcmnt_head_esc + scmnt[nwp:]

    # Add diff comment.
    if indargs or emptydc:
        inds = []
        for ind in _dcmnt_all_inds: # to have deterministic ordering
            alst = indargs.get(ind)
            if alst is not None:
                inds.append(_dcmnt_asep.join([ind] + alst))
        dcmnt = _dcmnt_head
        if inds:
            dcmnt += " " + _dcmnt_sep.join(inds)
        ecomments.insert(0, dcmnt)

    return diffr and (emsg, totdr) or emsg


def msg_ediff_to_new (emsg, rmsg=None):
    """
    Resolve message with embedded difference to the newer message.

    Message cannot be properly resolved if C{hlto} or C{addrem} parameters
    to L{msg_ediff} were used on embedding.
    If this function is called on such a message, the result is undefined.

    By default a new message object is created, but using the C{rmsg}
    parameter, en existing message can be given to be filled with all
    the resolved parts (keeping its own, ignored parts). This message can
    be the C{emsg} itself.

    If the resolved message evaluates to no message, the function
    returns C{None}, and C{rmsg} is not touched if it was given.

    Any states indicated as added by the difference comment are ignored
    in favor of the actual states of embedded difference message.
    The two sets should normally be equal, but if they are not,
    the actual state in effect overrides the indicated added state.

    @param emsg: resolvable message with embedded differences
    @type emsg: L{Message_base<file.message.Message_base>} or None
    @param rmsg: message to fill in the resolved parts
    @type rmsg: L{Message_base<file.message.Message_base>}

    @return: resolved message (or None)
    @rtype: type of first non-None of rmsg, emsg, or None
    """

    return _msg_ediff_to_x(emsg, rmsg, new=True)


def msg_ediff_to_old (emsg, rmsg=None):
    """
    Resolve message with embedded difference to the older message.

    Like L{msg_ediff_to_new}, only constructing the opposite message
    (except that states indicated as removed by difference comment are
    never ignored, i.e. they always override actual states).
    See L{msg_ediff_to_new} for parameters and return values.
    """

    return _msg_ediff_to_x(emsg, rmsg, new=False)


def _msg_ediff_to_x (emsg, rmsg, new):

    if new:
        word_ediff_to_x = word_ediff_to_new
        word_ediff_to_o = word_ediff_to_old
        line_ediff_to_x = line_ediff_to_new
        ignore_state_diff = True
    else:
        word_ediff_to_x = word_ediff_to_old
        word_ediff_to_o = word_ediff_to_new
        line_ediff_to_x = line_ediff_to_old
        ignore_state_diff = False

    # Work on copy if target message not given.
    if rmsg is None:
        rmsg = type(emsg)(emsg)

    # Since rmsg can be emsg itself, collect all attributes to set,
    # and set them in the end.
    atts_vals = []

    # Parse everything out of diff comment,
    # unescape comments which looked like diff comment and were escaped.
    states = {}
    ctxtpad = None
    infsep = None
    cmnts = []
    for cmnt in list(emsg.get(_dcmnt_field)):
        scmnt = cmnt.strip()
        p = scmnt.find(_dcmnt_head)
        if p == 0:
            dcmnt = scmnt[len(_dcmnt_head):]
            # FIXME: Checks for unknown indicators and bad arguments.
            for indargs in dcmnt.split(_dcmnt_sep.strip()):
                lst = indargs.strip().split(_dcmnt_asep)
                ind, args = lst[0], [word_ediff_to_x(x) for x in lst[1:]]
                if 0: pass
                elif ind == _dcmnt_ind_state:
                    for arg in args:
                        if _msg_dpart_types.get(arg) == _dt_state:
                            states[arg] = True
                    args_o = [word_ediff_to_o(x) for x in lst[1:]]
                    for arg in args_o:
                        if _msg_dpart_types.get(arg) == _dt_state:
                            states[arg] = False
                elif ind == _dcmnt_ind_ctxtpad:
                    ctxtpad = args[0]
                elif ind == _dcmnt_ind_infsep:
                    infsep = args[0] * int(args[1])
        else:
            if p > 0 and scmnt[:p] == _dcmnt_head_esc * p:
                nwp = 0
                while cmnt[nwp].isspace():
                    nwp += 1
                cmnt = cmnt[:nwp] + cmnt[nwp + 1:]
            cmnts.append(cmnt)

    listtype = type(rmsg.msgstr)

    # Put back cleaned comments.
    atts_vals.append((_dcmnt_field, listtype(cmnts)))

    # Remove context padding.
    if ctxtpad:
        val = emsg.get("msgctxt")
        p = val.rfind(ctxtpad or u"")
        if (   p < 0
            or val[p - len(_ctxtpad_sep):p] != _ctxtpad_sep
            or val[p + len(ctxtpad):] not in (_ctxtpad_noctxt, "")
        ):
            raise PologyError(_("@info", "Malformed padded context."))
        if val[p + len(ctxtpad):] != _ctxtpad_noctxt:
            val = val[:p - len(_ctxtpad_sep)]
        else:
            val = None
        msgctxt_nopad = val

    # Resolve parts.
    for part, typ in _msg_diff_parts:
        if ctxtpad and part == "msgctxt":
            val = msgctxt_nopad
        else:
            val = emsg.get(part)
        if typ == _dt_single:
            nval = word_ediff_to_x(val)
            if nval == None and part == "msgid":
                return None
            atts_vals.append((part, nval))
        elif typ == _dt_list:
            lst = []
            for el in val:
                if infsep:
                    p = el.find(infsep)
                    if p >= 0: # strip filtered difference
                        el = el[:p - 1] # -1 to remove newline
                lst.append(el)
            nlst = listtype(line_ediff_to_x(lst))
            if nlst == [] and part == "msgstr":
                return None
            atts_vals.append((part, nlst))
        elif typ == _dt_state:
            if not ignore_state_diff:
                val = states.get(part)
                if val is not None:
                    atts_vals.append((part, val))
        else:
            raise PologyError(
                _("@info",
                  "Unhandled message part '%(part)s' encountered "
                  "while resolving difference.")
                % dict(part=part))

    # Set resolved parts for real.
    for att, val in atts_vals:
        setattr(rmsg, att, val)

    return rmsg


def editprob (oldtext, newtext):
    """
    Compute the probability that a human would rather edit the old text
    to obtain the new text, then write it from scratch.

    Classical algorithms to compute similarity ratio between two texts
    sometimes produce high ratios for texts which a human would unlikely
    consider similar enough to make one text by editing the other,
    and vice versa.
    This functions uses some heuristics to derive the probability
    that one text was really edited by a human into the other.

    Not commutative in general.

    If one of the texts is given as C{None}, the result is 0.0;
    if both are C{None}, the result is 1.0.

    @param oldtext: candidate for initial text
    @type oldtext: string
    @param newtext: current text
    @type newtext: string

    @returns: the probability of editing the old into the new text [0, 1]
    @rtype: float
    """

    if oldtext == newtext:
        return 1.0
    if not oldtext or not newtext:
        return 0.0

    # Consider always the case of editing from longer to shorter text.
    if len(oldtext) < len(newtext):
        shorttext, longtext = oldtext, newtext
    else:
        shorttext, longtext = newtext, oldtext

    # Construct diff.
    sm = SequenceMatcher(None, longtext, shorttext)
    mblocks = sm.get_matching_blocks()
    mblocks = sorted(mblocks, key=lambda x: x[1])
    mblocks.insert(0, (0, 0, 0))

    # Acummulate probability.
    ep = 0.0
    for i in range(1, len(mblocks) - 1):
        lm = mblocks[i][2]
        ld1 = mblocks[i][1] - (mblocks[i - 1][1] + mblocks[i - 1][2])
        ld2 = mblocks[i + 1][1] - (mblocks[i][1] + mblocks[i][2])
        cf = (float(lm) / (lm + ld1 + ld2))**2
        # ...if cf would be set to 1, probability would be equal
        # to ordinary similarity ratio.
        ep += lm * cf
    ep /= len(shorttext)

    # Correct for different lengths of texts.
    rl = float(len(shorttext)) / len(longtext)
    ep *= 1 - (rl - 1)**4

    return ep

