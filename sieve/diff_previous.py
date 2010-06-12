# -*- coding: UTF-8 -*-

"""
Embed differences in original text in fuzzy messages into previous fields.

When catalogs are merged with C{--previous} option to C{msgmerge},
fuzzy messages will retain previous version of original text
(C{msgid}, etc.) under C{#|} comments.
This sieve makes an I{embedded difference} from previous to current
original text, placing it into previous fields. For example, the message::

    #: main.c:110
    #, fuzzy
    #| msgid "The Record of The Witch River"
    msgid "Records of The Witch River"
    msgstr "Beleška o Veštičjoj reci"

will become after sieving::

    #: main.c:110
    #, fuzzy
    #| msgid "{-The Record-}{+Records+} of The Witch River"
    msgid "Records of The Witch River"
    msgstr "Beleška o Veštičjoj reci"

Text editors may even provide highlighting for the wrapped difference segments
(e.g. Kwrite/Kate).

Sieve parameters:
  - C{strip}: remove embedded differences from previous fields
  - C{branch:<branch_id>}: process only messages from this branch (summit)

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import re

from pology import _, n_
from pology.misc.comments import parse_summit_branches
from pology.misc.diff import word_ediff, word_ediff_to_old
from pology.misc.report import report


def setup_sieve (p):

    p.set_desc(_("@info sieve discription",
    "Diff previous to current fields in fuzzy messages."
    ))

    p.add_param("strip", bool,
                desc=_("@info sieve parameter discription",
    "Remove embedded differences from previous fields."
    ))

    p.add_param("branch", unicode, seplist=True,
                metavar=_("@info sieve parameter value placeholder", "BRANCH"),
                desc=_("@info sieve parameter discription",
    "In summit catalogs, process only messages belonging to given branch. "
    "Several branches can be given as comma-separated list."
    ))


class Sieve (object):

    def __init__ (self, params):

        self.nmod = 0

        self.strip = params.strip
        self.branches = set(params.branch or [])


    def _diff (self, msgold, msgnew, format):

        # Remove any previous diff.
        msgold_clean = word_ediff_to_old(msgold)

        # Create the diff or only put back the clean text.
        if not self.strip:
            return word_ediff(msgold_clean, msgnew,
                              markup=True, format=format)
        else:
            return msgold_clean


    def process (self, msg, cat):

        # Summit: if branches were given, skip the message if it does not
        # belong to any of the given branches.
        if self.branches:
            msg_branches = parse_summit_branches(msg)
            if not set.intersection(self.branches, msg_branches):
                return

        # Skip if message is not fuzzy or does not have previous fields.
        if not msg.fuzzy or msg.msgid_previous is None:
            # Remove any stray previous fields.
            msg.msgctxt_previous = None
            msg.msgid_previous = None
            msg.msgid_plural_previous = None
            return

        # Skip message if obsolete fuzzy.
        if msg.obsolete:
            return

        oldcount = msg.modcount

        msg.msgctxt_previous = self._diff(msg.msgctxt_previous, msg.msgctxt,
                                          msg.format)
        msg.msgid_previous = self._diff(msg.msgid_previous, msg.msgid,
                                        msg.format)
        msg.msgid_plural_previous = self._diff(msg.msgid_plural_previous,
                                               msg.msgid_plural, msg.format)

        if msg.modcount > oldcount:
            self.nmod += 1


    def finalize (self):

        if self.nmod > 0:
            if not self.strip:
                msg = (n_("@info:progress",
                          "Added differences to %(num)d fuzzy message.",
                          "Added differences to %(num)d fuzzy messages.",
                          self.nmod)
                       % dict(num=self.nmod))
            else:
                msg = (n_("@info:progress",
                          "Stripped differences from %(num)d fuzzy message.",
                          "Stripped differences from %(num)d fuzzy messages.",
                          self.nmod)
                       % dict(num=self.nmod))
            report("===== %s" % msg)

