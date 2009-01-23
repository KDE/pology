# -*- coding: UTF-8 -*-

from pology.misc.diff import word_ediff, word_ediff_to_old
from pology.misc.comments import parse_summit_branches

import re

class Sieve (object):
    """Embed/remove differences into previous versions of msgctxt/msgid."""

    def __init__ (self, options):

        self.nmod = 0

        # Only strip the present embedded diffs?
        self.strip = False
        if "strip" in options:
            options.accept("strip")
            self.strip = True

        # Summit: consider only messages belonging to given branches.
        self.branches = None
        if "branch" in options:
            self.branches = set(options["branch"].split(","))
            options.accept("branch")


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

        msg.msgctxt_previous = self._diff(msg.msgctxt_previous, msg.msgctxt,
                                          msg.format)
        msg.msgid_previous = self._diff(msg.msgid_previous, msg.msgid,
                                        msg.format)
        msg.msgid_plural_previous = self._diff(msg.msgid_plural_previous,
                                               msg.msgid_plural, msg.format)


    def finalize (self):
        if self.nmod > 0:
            print "Total messages processed for differences: %d" % self.nmod
