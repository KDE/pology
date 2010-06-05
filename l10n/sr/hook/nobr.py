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

from pology.l10n.sr.hook.wconv import ctol

nobrhyp_char = u"\u2011"

def to_nobr_hyphens (mode=0, wchars="", unsafe=False):
    """
    Replace some ordinary hyphens with no-break hyphens [hook factory].

    An ordinary hyphen is replaced in one of the following modes,
    as given by the C{mode} parameter:
      - 0: if the hyphen is in between two letters, and either preceded
            or followed by at most four letters
      - 1: if the hyphen is in between two letters and followed by
            exactly one letter

    Using the C{wchars} parameter, some extra characters other than letters
    can be treated as equal to letters.

    Note that the function by default substitutes the hyphen only if
    there are some Cyrillic letters (or an extra character) in the context,
    as otherwise the hyphen may be a part of URL, command, etc.
    This can be relaxed by setting C{unsafe} to C{True},
    when all letters are treated equally.

    @param mode: replacement mode
    @type mode: int
    @param wchars: extra characters to consider parts of the word
    @type wchars: string
    @param unsafe: whether to replace hyphen even if no Cyrillic letters nearby
    @type unsafe: bool

    @return: type F1A hook
    @rtype: C{(text) -> text}
    """

    wchars = wchars.replace("-", "") # just in case

    nobrhyp_rxstrs = []
    if mode == 0:
        # Catching possible replacement by text before hyphen.
        nobrhyp_rxstrs.append(ur"\b(\w{1,4})(-)([\w%s])" % wchars)
        # Catching possible replacement by text after hyphen.
        nobrhyp_rxstrs.append(ur"([\w%s])(-)(\w{1,4})\b" % wchars)
    elif mode == 1:
        # Catching possible replacement by text after hyphen.
        nobrhyp_rxstrs.append(ur"([\w%s])(-)(\w{1})\b" % wchars)
    else:
        raise StandardError(
            _("@info",
              "Unknown hyphen replacement mode %(mode)s.")
            % dict(mode=mode))
    nobrhyp_rxs = [re.compile(x, re.U) for x in nobrhyp_rxstrs]

    # Function to produce replacement for matched pattern.
    if not unsafe:
        def nobrhyp_repl (m):
            # Replace hyphen with no-break hyphen only if there is at least one
            # Cyrillic letter in the match, or one of extra characters.
            if ctol(m.group()) != m.group() or m.group(1) in wchars:
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
            for nobrhyp_rx in nobrhyp_rxs:
                text = nobrhyp_rx.sub(nobrhyp_repl, text)
            if text_prev == text:
                break

        return text

    return hook

