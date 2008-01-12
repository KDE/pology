# -*- coding: UTF-8 -*-

from pology.sieve.stats import get_summit_branches


class Sieve (object):
    """Add flag "incomplete" to untranslated and fuzzy messages."""

    def __init__ (self, options, global_options):

        self.nmatch = 0

        # Summit: consider only messages belonging to given branches.
        self.branches = None
        if "branch" in options:
            self.branches = set(options["branch"].split(","))
            options.accept("branch")

        # Indicators to the caller:
        # - monitor to avoid unnecessary reformatting when unfuzzied
        self.caller_monitored = True


    def process (self, msg, cat):

        flag_incomplete = u"incomplete"

        # Skip obsolete messages.
        if msg.obsolete:
            return

        # Summit: if branches were given, considered the message for
        # tagging based on whether it belongs to any of the given branches.
        may_tag = True
        if self.branches:
            msg_branches = get_summit_branches(msg)
            if not set.intersection(self.branches, msg_branches):
               may_tag = False

        # Add flag if message may be tagged and is not translated.
        if may_tag and not msg.translated:
            msg.flag.add(flag_incomplete)
            self.nmatch += 1
            msg.modcount = 1 # in case of non-monitored messages

        # Remove flag if already there, but the message is either
        # not to be tagged or no longer incomplete.
        elif flag_incomplete in msg.flag and (not may_tag or msg.translated):
            msg.flag.remove(flag_incomplete)
            msg.modcount = 1 # in case of non-monitored messages


    def finalize (self):

        if self.nmatch > 0:
            print "Total incomplete tagged: %d" % (self.nmatch,)

