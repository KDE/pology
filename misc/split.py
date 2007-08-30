# -*- coding: UTF-8 -*-

import re

_split_rx = re.compile(r"[^\w]+|\w+", re.UNICODE)
_split_rx_markup = re.compile(r"[^\w]*<.*?>[^\w<]*|[^\w]+|\w+", re.UNICODE)
_word_rx = re.compile(r"^\w", re.UNICODE)

def split_text (text, markup=False):
    """Split text into words and intersections.

    Parameters:
      text   - text to split
      markup - whether text contains markup tags

    Return list of words and list of intersections, packed in a tuple.

    There is always an intersection before the first and after the last word,
    even if empty; i.e. there is always one more of interesections than words.
    """

    if markup:
        split_rx = _split_rx_markup
        word_rx = _word_rx
    else:
        split_rx = _split_rx
        word_rx = _word_rx

    words = []
    intrs = []
    lastword = False
    for m in split_rx.finditer(text):
        seg = m.group(0)
        if word_rx.search(seg):
            lastword = True
            words.append(seg)
            #print "word {%s}" % (seg,)
        else:
            lastword = False
            intrs.append(seg)
            #print "intr {%s}" % (seg,)

    if lastword:
        intrs.append(u"")
    if len(intrs) == len(words):
        intrs.insert(0, u"")

    return (words, intrs)
