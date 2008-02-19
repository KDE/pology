# -*- coding: UTF-8 -*-

"""
Mark fuzzy and untranslated messages as incomplete.

Some people like to translate with non-dedicated tools, such as an ordinary
text editor, which may provide no more support for editing PO files other
than e.g. syntax highlighting. In such a scenario, this sieve can be used
to equip both fuzzy and untranslated messages with C{incomplete} flag,
for easy lookup in the editor.

Note that C{incomplete} flags, being custom, will be lost when the PO file
is merged with the template next time. This is intentional: the only purpose
of the flag is for immediate editing, and the translator may forget to remove
some. There is no reason for the flags to persist in that case. Also, if an
C{incomplete} tag is forgotten when the message is translated, the subsequent
run of this sieve will remove the flag.

Sieve options:
  - C{branch:<branch_id>}: consider only messages from this branch (summit)

For L{summited<posummit>} catalogs, the C{branch} option is used to restrict
modifications to messages from the given branch only. Several branch IDs
may be given as a comma-separated list.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

from pology.misc.comments import parse_summit_branches


class Sieve (object):

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
            msg_branches = parse_summit_branches(msg)
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

