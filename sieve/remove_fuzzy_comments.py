# -*- coding: UTF-8 -*-

"""
Remove selected manual comments in fuzzy messages.

Being translator's input, manual comments are copied verbatim to fuzzy
messages on merge. Depending on the intent behind the particular comments,
translator may want to automatically remove them for fuzzied messages
(possibly adding them manually again when revisiting messages).

Sieve options for selecting manual comments for removal:
  - C{all}: all manual comments
  - C{nopipe}: embedded lists of no-pipe flags (C{# |, foo, ...})
  - C{pattern:<regex>}: comments matching the regular expression
  - C{exclude:<regex>}: comments not matching the regular expression

Other sieve options:
  - C{case}: do case-sensitive matching (insensitive by default)

The comments are selected for removal by first applying specific criteria
in an unspecified order, then the C{pattern} match, and finaly the
C{exclude} match.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import re


def _accept_negation (options, key, default):

    if key in options:
        options.accept(key)
        return not default
    else:
        return default


class Sieve (object):

    def __init__ (self, options, global_options):

        # Number of modified messages.
        self.nmod = 0

        # Select comments by specific features.
        self.sel_all = _accept_negation(options, "all", False)
        self.sel_nopipe = _accept_negation(options, "nopipe", False)

        # Matching flags for regular expressions.
        self.rxflags = re.U
        if "case" in options:
            options.accept("case")
        else:
            self.rxflags |= re.I

        # Select comments matching the regex.
        self.pattern = None
        if "pattern" in options:
            self.pattern = options["pattern"]
            self.pattern_rx = re.compile(self.pattern, self.rxflags)
            options.accept("pattern")

        # Exclude comments matching the regex.
        self.exclude = None
        if "exclude" in options:
            self.exclude = options["exclude"]
            self.exclude_rx = re.compile(self.exclude, self.rxflags)
            options.accept("exclude")

        # Regex for matching no-pipe flag lists.
        self.nopipe_rx = re.compile(r"^\s*\|,")


    def process (self, msg, cat):

        # Process comments only for fuzzy messages.
        if not msg.fuzzy:
            return

        modcount = msg.modcount

        # Go through manual comments.
        i = 0
        while i < len(msg.manual_comment):
            selected = False
            cmnt = msg.manual_comment[i]

            # Specific selections.
            if not selected and self.sel_all:
                selected = True

            if not selected and self.sel_nopipe:
                selected = self.nopipe_rx.search(cmnt) is not None

            # Inclusion pattern.
            if not selected and self.pattern is not None:
                selected = self.pattern_rx.search(cmnt) is not None

            # Exclusion pattern.
            if selected and self.exclude is not None:
                selected = self.exclude_rx.search(cmnt) is None

            # Apply selection.
            if selected:
                msg.manual_comment.pop(i)
            else:
                i += 1

        if msg.modcount > modcount:
            self.nmod += 1


    def finalize (self):

        if self.nmod > 0:
            print "Total with some comments removed: %d" % (self.nmod,)

