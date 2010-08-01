# -*- coding: UTF-8 -*-

"""
Remove selected manual comments in fuzzy messages.

Being translator's input, manual comments are copied verbatim to fuzzy
messages on merge. Depending on the intent behind the particular comments,
translator may want to automatically remove them for fuzzied messages
(possibly adding them manually again when revisiting messages).

Sieve parameters for selecting manual comments for removal:
  - C{all}: all manual comments
  - C{nopipe}: embedded lists of no-pipe flags (C{# |, foo, ...})
  - C{pattern:<regex>}: comments matching the regular expression
  - C{exclude:<regex>}: comments not matching the regular expression

Other sieve parameters:
  - C{case}: do case-sensitive matching (insensitive by default)

Comments are selected for removal by first applying specific criteria
in an unspecified order, then the C{pattern} match, and finally the
C{exclude} match.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import re

from pology import _, n_
from pology.report import report


def setup_sieve (p):

    p.set_desc(_("@info sieve discription",
    "Remove selected manual comments from fuzzy messages."
    ))

    p.add_param("all", bool, defval=False,
                desc=_("@info sieve parameter discription",
    "Remove all manual comments."
    ))
    p.add_param("nopipe", bool, defval=False,
                desc=_("@info sieve parameter discription",
    "Remove embedded lists of no-pipe flags (# |, foo, ...)."
    ))
    p.add_param("pattern", unicode,
                metavar=_("@info sieve parameter value placeholder", "REGEX"),
                desc=_("@info sieve parameter discription",
    "Remove comments matching the regular expression."
    ))
    p.add_param("exclude", unicode,
                metavar=_("@info sieve parameter value placeholder", "REGEX"),
                desc=_("@info sieve parameter discription",
    "Remove comments not matching the regular expression."
    ))
    p.add_param("case", bool, defval=False,
                desc=_("@info sieve parameter discription",
    "Case-sensitive pattern matching."
    ))



class Sieve (object):

    def __init__ (self, params):

        self.sel_all = params.all
        self.sel_nopipe = params.nopipe

        self.rxflags = re.U
        if not params.case:
            self.rxflags |= re.I

        self.pattern = None
        if params.pattern:
            self.pattern = params.pattern
            self.pattern_rx = re.compile(self.pattern, self.rxflags)

        self.exclude = None
        if params.exclude:
            self.exclude = params.exclude
            self.exclude_rx = re.compile(self.exclude, self.rxflags)

        # Regex for matching no-pipe flag lists.
        self.nopipe_rx = re.compile(r"^\s*\|,")

        # Number of modified messages.
        self.nmod = 0


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
            msg = n_("@info:progress",
                     "Removed some comments from %(num)d fuzzy message.",
                     "Removed some comments from %(num)d fuzzy messages.",
                     num=self.nmod)
            report("===== " + msg)

