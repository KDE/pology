# -*- coding: UTF-8 -*-

"""
Embed differences in original text in fuzzy messages into previous fields.

Documented in C{doc/user/sieving.docbook}.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import re

from pology import _, n_
from pology.comments import parse_summit_branches
from pology.diff import word_ediff, word_ediff_to_old
from pology.report import report


def setup_sieve (p):

    p.set_desc(_("@info sieve discription",
    "Diff previous to current fields in fuzzy messages."
    ))

    p.add_param("strip", bool,
                desc=_("@info sieve parameter discription",
    "Remove embedded differences from previous fields."
    ))

    p.add_param("branch", str, seplist=True,
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
                msg = n_("@info:progress",
                         "Added differences to %(num)d fuzzy message.",
                         "Added differences to %(num)d fuzzy messages.",
                         num=self.nmod)
            else:
                msg = n_("@info:progress",
                         "Stripped differences from %(num)d fuzzy message.",
                         "Stripped differences from %(num)d fuzzy messages.",
                         num=self.nmod)
            report("===== " + msg)

