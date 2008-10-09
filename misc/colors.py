# -*- coding: UTF-8 -*-
"""
Standard codes for shell colors.

@author: Sébastien Renard <sebastien.renard@digitalfox.org>
@license: GPLv3
"""

from pology.misc.diff import adapt_spans


BOLD     = '\033[01m'
RED     = '\033[31m'
GREEN     = '\033[32m'
ORANGE     = '\033[33m'
BLUE     = '\033[34m'
PURPLE     = '\033[35m'
CYAN    = '\033[36m'
GREY    = '\033[37m'
RESET     = '\033[0;0m'


def highlight_spans (text, spans, color=RED, ftext=None):
    """
    Highlight spans in text.

    Adds shell colors around defined spans in the text.
    Spans are given as list of index tuples C{[(start1, end1), ...]} where
    start and end index have standard Python semantics.
    Span tuples can have more than two elements, with indices followed by
    additional elements, which are ignored by this function.

    If C{ftext} is not C{None} spans are understood as relative to it,
    and the function will try to adapt them to the main text
    (see L{pology.misc.diff.adapt_spans}).

    @param text: text to be highlighted
    @type text: string
    @param spans: spans to highlight
    @type spans: list of tuples
    @param color: shell color sequence for highlighting
    @type color: string
    @param ftext: text to which spans are actually relative
    @type ftext: string

    @returns: highlighted text
    @rtype: string
    """

    if not spans:
        return text

    # Adapt spans regardless if filtered text has been given or not,
    # to fix any overlapping and put into expected ordering.
    if ftext is None:
        ftext = text
    spans = adapt_spans(text, ftext, spans, merge=True)
    if not spans:
        return text

    ctext = ""
    cstart = 0
    for span in spans:
        ctext += text[cstart:span[0]]
        ctext += color + text[span[0]:span[1]] + RESET
        cstart = span[1]
    ctext += text[span[1]:]

    return ctext

