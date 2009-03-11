# -*- coding: UTF-8 -*-

"""
Equip text with no-break characters where possibly helpful.

The way text is wrapped in UI, by a general wrapping algorithm,
is sometimes really not appropriate for Serbian ortography.
For example, hyphen-separated case ending should not be wrapped.
This module contains functions to heuristically replace ordinary
with no-break characters, where such bad breaks can be expected.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import re

from pology.l10n.sr.hook.cyr2lat import process as sr_c2l

nobrhyp_char = u"\u2011"

def to_nobr_hyphens (wchars="", unsafe=False):
    """
    Replace some ordinary with no-break hyphens [hook factory].

    The ordinary hyphen is replaced if it is in between two letters,
    and either preceded or followed by at most four letters.
    Using the C{wchars} parameter, some extra characters other than letters
    can be treated as equal to letters.

    Note that the function by default substitutes the hyphen only if
    there are some Cyrillic letters (or an extra character) in the context,
    as otherwise the hyphen may be a part of URL, command, etc.
    This can be relaxed by setting C{unsafe} to C{True},
    when all letters are treated equally.

    @param wchars: extra characters to consider parts of the word
    @type wchars: string
    @param unsafe: whether to replace hyphen even if no Cyrillic letters nearby
    @type unsafe: bool

    @return: type F1A hook
    @rtype: C{(text) -> text}
    """

    wchars = wchars.replace("-", "") # just in case

    # Catching possible replacement by text before hyphen.
    nobrhyp_be_rx = re.compile(ur"\b(\w{1,4})(-)([\w%s])" % wchars, re.U)

    # Catching possible replacement by text after hyphen.
    nobrhyp_af_rx = re.compile(ur"([\w%s])(-)(\w{1,4})\b" % wchars, re.U)

    # Function to produce replacement for matched pattern.
    if not unsafe:
        def nobrhyp_repl (m):
            # Replace hyphen with no-break hyphen only if there is at least one
            # Cyrillic letter in the match, or one of extra characters.
            if sr_c2l(m.group()) != m.group() or m.group(1) in wchars:
                return m.group(1) + nobrhyp_char + m.group(3)
            else:
                return m.group()
    else:
        def nobrhyp_repl (m):
            # Replace hyphen with no-break hyphen unconditionally.
            return m.group(1) + nobrhyp_char + m.group(3)

    def hook (text):

        # Quick check, is there any hypen at all in the string?
        if text.find("-") < 0:
            return text

        # Replace as long as the string changes, as there are situations
        # that the regexes will not catch in one pass (e.g. аб-вг-дђ).
        while True:
            text_prev = text
            text = nobrhyp_be_rx.sub(nobrhyp_repl, text)
            text = nobrhyp_af_rx.sub(nobrhyp_repl, text)
            if text_prev == text:
                break

        return text

    return hook

