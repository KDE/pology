# -*- coding: UTF-8 -*-

"""
Detect unwanted patterns in translation.
"""

from pology.misc.comments import manc_parse_flag_list
from pology.sieve.bad_patterns import load_patterns
from pology.sieve.bad_patterns import process_patterns, match_patterns
from pology.sieve.bad_patterns import flag_no_bad_patterns
from pology.misc.msgreport import report_on_msg


def bad_patterns (rxmatch=False, casesens=True, patterns=[], fromfiles=[]):
    """
    Detect unwanted patterns in text [hook factory].

    Patterns can be given both as list of strings, and as a list of file
    paths containing patterns (in each file: one pattern per line,
    strip leading and trailing whitespace, skip empty lines, #-comments).
    Detected patterns are reported to stdout.

    If C{rxmatch} is C{False}, patterns are matched by plain substring search,
    otherwise as regular expressions.
    If C{casesens} is True, matching is case sensitive.

    If the message has pipe flag C{no-bad-patterns}, check is skipped.

    @param rxmatch: whether to take pattern as regular expression
    @type rxmatch: bool
    @param casesens: whether the match should be case-sensitive
    @type casesens: bool
    @param patterns: patterns to match the text
    @type patterns: list of strings
    @param fromfiles: file paths from which to read patterns
    @type fromfiles: list of strings

    @return: type S3A hook
    @rtype: C{(text, msg, cat)->numerr}
    """

    patterns_str = patterns[:]
    for file in fromfiles:
        patterns_str.extend(load_patterns(file))

    patterns_cmp = process_patterns(rxmatch=rxmatch, casesens=casesens,
                                    patterns=patterns_str)

    def hook (text, msg, cat):
        if flag_no_bad_patterns in manc_parse_flag_list(msg, "|"):
            return 0

        # Report-handler for bad patterns.
        def badhandle (name):
            if name:
                report_on_msg("bad pattern detected: %s" % name, msg, cat)
            else:
                report_on_msg("bad pattern detected", msg, cat)

        if not casesens:
            text = text.lower()
        mps = match_patterns(text, patterns_cmp, rxmatch=rxmatch,
                             mhandle=badhandle, pnames=patterns_str)
        return len(mps)

    return hook

