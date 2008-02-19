# -*- coding: UTF-8 -*-

from pology.misc.diff import diff_texts, diff_to_old, diff_to_new
from pology.misc.comments import parse_summit_branches

import re

class Sieve (object):
    """Embed/remove differences into previous versions of msgctxt/msgid."""

    def __init__ (self, options, global_options):

        self.nmod = 0

        # Only strip the present embedded diffs?
        self.strip = False
        if "strip" in options:
            options.accept("strip")
            self.strip = True

        # Embed differences only if less different than this.
        self.limit = 1.0
        if "limit" in options:
            options.accept("limit")
            self.limit = float(options["limit"])

        # Summit: consider only messages belonging to given branches.
        self.branches = None
        if "branch" in options:
            self.branches = set(options["branch"].split(","))
            options.accept("branch")

        # Indicators to the caller:
        # - monitor to avoid unnecessary reformatting
        self.caller_monitored = True


    def _diff (self, msgold, msgnew, format):

        # Remove any previous diff.
        previous_clean = diff_to_old(msgold)

        # Create the diff or only put back the clean text.
        if not self.strip:
            diff, diff_ratio = diff_texts(previous_clean, msgnew,
                                          markup=True, format=format)
            # Use the diff only if not too much difference.
            if diff_ratio < self.limit:
                return diff
            else:
                return previous_clean
        else:
            return previous_clean


    def process (self, msg, cat):

        # Summit: if branches were given, skip the message if it does not
        # belong to any of the given branches.
        if self.branches:
            msg_branches = parse_summit_branches(msg)
            if not set.intersection(self.branches, msg_branches):
                return

        # Differentiate the msgctxt.
        if msg.msgctxt_previous and msg.msgctxt:
            msg.msgctxt_previous = self._diff(msg.msgctxt_previous, msg.msgctxt,
                                              msg.format)
            msg.modcount = 1 # in case of non-monitored messages

        # Differentiate the msgid.
        if msg.msgid_previous and msg.msgid:
            msg.msgid_previous = self._diff(msg.msgid_previous, msg.msgid,
                                            msg.format)
            msg.modcount = 1 # in case of non-monitored messages

        # Differentiate the msgid_plural.
        if msg.msgid_plural_previous and msg.msgid_plural:
            msg.msgid_plural_previous = self._diff(msg.msgid_plural_previous,
                                                   msg.msgid_plural, msg.format)
            msg.modcount = 1 # in case of non-monitored messages


    def finalize (self):
        if self.nmod > 0:
            print "Total messages processed for differences: %d" % self.nmod
