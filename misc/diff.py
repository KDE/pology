# -*- coding: UTF-8 -*-

from pology.misc.split import split_text

import re
from difflib import ndiff

_opn_ch = u"{"
_cls_ch = u"}"
_pls_ch = u"+"
_mns_ch = u"-" #–

def diff_texts (text_old, text_new, markup=False, format=None):
    """Create text with embedded differences between new (+) and old (-).

    Parameters::

      text_old - the older text
      text_new - the newer text
      markup - whether <...> markup can be expected in the texts
      format - gettext format flag

    Return a tuple of string with embedded differences and difference ratio.
    """

    # Split text into segments: words and intersections, combined into
    # single lists for old and new text.
    segments = []
    for text in (text_old, text_new):
        lw, li = split_text(text, markup, format)
        segments.append([])
        map(lambda x, y: segments[-1].extend([x, y]), li, lw + [''])
        # Remove empty segments.
        segments[-1] = [x for x in segments[-1] if x]

    # Create the difference.
    dlist = list(ndiff(segments[0], segments[1]))

    # Remove non-difference segments.
    dlist = [x for x in dlist if x[:1] in "+- "]

    # Format the embedded output.
    S_EQU, S_NEW, S_OLD = range(3)
    dtext = ""
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

    diff_ratio = 1.0 - float(len_equ) / float(len_new + len_old + len_equ)

    return dtext, diff_ratio


_capt_old_rx = re.compile(  "\\" + _opn_ch + "\\" + _mns_ch + "(.*?)" \
                          + "\\" + _mns_ch + "\\" + _cls_ch, re.U|re.S)
_capt_new_rx = re.compile(  "\\" + _opn_ch + "\\" + _pls_ch + "(.*?)" \
                          + "\\" + _pls_ch + "\\" + _cls_ch, re.U|re.S)


def diff_to_old (dtext):
    """Get old version (-) from text with embedded differences."""

    text = dtext
    text = _capt_new_rx.sub("", text)
    text = _capt_old_rx.sub("\\1", text)
    return text


def diff_to_new (dtext):
    """Get new version (+) from text with embedded differences."""

    text = dtext
    text = _capt_new_rx.sub("\\1", text)
    text = _capt_old_rx.sub("", text)
    return text

