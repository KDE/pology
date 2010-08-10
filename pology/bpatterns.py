# -*- coding: UTF-8 -*-

"""
Detect unwanted patterns in translation.

@note: This module is deprecated.
Use L{rules<pology.rules>} through C{check-rules} sieve instead.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import re
import codecs

from pology import _, n_
from pology.comments import manc_parse_flag_list
from pology.msgreport import report_on_msg, report_msg_content


def bad_patterns (rxmatch=False, casesens=True, patterns=None, fromfiles=None):
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

    patterns_str = list(patterns or [])
    for file in fromfiles:
        patterns_str.extend(_load_patterns(file))

    patterns_cmp = _process_patterns(rxmatch=rxmatch, casesens=casesens,
                                     patterns=patterns_str)

    def hook (text, msg, cat):
        if _flag_no_bad_patterns in manc_parse_flag_list(msg, "|"):
            return 0

        indspans = _match_patterns(text, patterns_cmp)
        for pind, span in indspans:
            pstr = patterns_str[pind]
            report_on_msg(_("@info",
                            "Bad pattern '%(pattern)s' detected.",
                            pattern=pstr), msg, cat)
        return len(indspans)

    return hook


def bad_patterns_msg (rxmatch=False, casesens=True,
                      patterns=None, fromfiles=None):
    """
    Detect unwanted patterns in translation [hook factory].

    Like L{bad_patterns}, but checks and reports on all C{msgstr}
    fields in the message.

    @return: type S4A hook
    @rtype: C{(msg, cat)->numerr}
    """

    return _bad_patterns_msg_w(rxmatch, casesens, patterns, fromfiles, False)


def bad_patterns_msg_sp (rxmatch=False, casesens=True,
                         patterns=None, fromfiles=None):
    """
    Detect unwanted patterns in translation, report spans [hook factory].

    Like L{bad_patterns_msg}, but reports parts instead of writing to stdout.

    @return: type V4A hook
    @rtype: C{(msg, cat)->parts}
    """

    return _bad_patterns_msg_w(rxmatch, casesens, patterns, fromfiles, True)


# Worker for bad_patterns_msg* hooks.
def _bad_patterns_msg_w (rxmatch, casesens, patterns, fromfiles, partrep):

    patterns_str = list(patterns or [])
    for file in fromfiles or []:
        patterns_str.extend(_load_patterns(file))

    patterns_cmp = _process_patterns(rxmatch=rxmatch, casesens=casesens,
                                     patterns=patterns_str)

    def hook (msg, cat):
        if _flag_no_bad_patterns in manc_parse_flag_list(msg, "|"):
            return 0

        parts = []
        nbad = 0
        for i in range(len(msg.msgstr)):
            indspans = _match_patterns(msg.msgstr[i], patterns_cmp)
            spans = []
            for pind, span in indspans:
                emsg = _("@info",
                         "Bad pattern '%(pattern)s' detected.",
                         pattern=patterns_str[pind])
                spans.append(span + (emsg,))
                nbad += 1
            if spans:
                parts.append(("msgstr", i, spans))

        if partrep:
            return parts
        else:
            if parts:
                report_msg_content(msg, cat, highlight=parts, delim=("-" * 20))
            return nbad

    return hook


# Pipe flag used to manually prevent matching for a particular message.
_flag_no_bad_patterns = "no-bad-patterns"


# Load pattern string from the file:
# one pattern per non-empty line in the file,
# leading and trailing whitespace stripped,
# #-comments possible.
def _load_patterns (filepath):

    ifl = codecs.open(filepath, "r", "UTF-8")

    rem_cmnt_rx = re.compile(r"#.*")
    patterns = []
    for line in ifl.readlines():
        line = rem_cmnt_rx.sub("", line).strip()
        if line:
            patterns.append(line)

    return patterns


# Process given list of pattern strings.
# If rxmatch is True, patterns are compiled into regexes.
# If casesens is False, re.I flag is used in regex compilation, or
# if regex patterns are not requested, patterns are lower-cased.
def _process_patterns (patterns, rxmatch=False, casesens=True):

    patterns_cmp = []
    if rxmatch:
        rx_flags = re.U
        if not casesens:
            rx_flags |= re.I
        for pattern in patterns:
            patterns_cmp.append(re.compile(pattern, rx_flags))
    else:
        for pattern in patterns:
            if not casesens:
                patterns_cmp.append(pattern.lower())
            else:
                patterns_cmp.append(pattern)

    return patterns_cmp


# Try to match the text by all patterns in the list.
# A pattern can be either a plain string for substring search,
# or a compiled regular expression.
# Returns a list of (pattern_index, span) tuples for patterns that matched.
def _match_patterns (text, patterns):

    matched_patterns = []
    for i in range(len(patterns)):
        pattern = patterns[i]

        span = None
        if isinstance(pattern, basestring):
            p = text.find(pattern)
            if p >= 0:
                span = (p, p + len(pattern))
        else:
            m = pattern.search(text)
            if m:
                span = m.span()

        if span:
            matched_patterns.append((i, span))

    return matched_patterns

