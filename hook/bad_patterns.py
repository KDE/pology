# -*- coding: UTF-8 -*-

"""
Summit hooks for detecting unwanted patterns in translation.
"""

from pology.misc.comments import manc_parse_flag_list
from pology.sieve.bad_patterns import load_patterns
from pology.sieve.bad_patterns import process_patterns, match_patterns
from pology.sieve.bad_patterns import flag_no_bad_patterns


def bad_patterns (rxmatch=False, casesens=True, patterns=[], fromfiles=[]):
    """Factory of hooks to detect unwanted patterns per msgstr.

    Produces hooks with (cat, msg, msgstr) signature, returning None.
    Patterns can be given both as list of strings, and as a list of file
    paths containing patterns (in each file: one pattern per line,
    strip leading and trailing whitespace, skip empty lines, #-comments).
    Detected patterns are reported to stdout.
    If rxmatch is False, patterns are matched by plain substring search,
    otherwise as regular expressions.
    If casesens is True, matching is case sensitive.
    if the message has pipe flag no-bad-patterns, matching is skipped.
    """

    patterns_str = patterns[:]
    for file in fromfiles:
        patterns_str.extend(load_patterns(file))

    patterns_cmp = process_patterns(rxmatch=rxmatch, casesens=casesens,
                                    patterns=patterns_str)

    def hook (cat, msg, msgstr):
        if flag_no_bad_patterns in manc_parse_flag_list(msg, "|"):
            return
        msgfmt = (  "%s:%d(%d): bad pattern detected in translation: %s"
                  % (cat.filename, msg.refline, msg.refentry, "%s"))
        if not casesens:
            msgstr = msgstr.lower()
        match_patterns(msgstr, patterns_cmp, rxmatch=rxmatch,
                       msg=msgfmt, pnames=patterns_str)

    return hook
