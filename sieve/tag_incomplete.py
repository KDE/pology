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
C{incomplete} flag is forgotten when the message is translated, the subsequent
run of this sieve will remove the flag.

Sieve options:
  - C{branch:<branch_id>}: consider only messages from this branch (summit)
  - C{strip}: instead of adding, strip any C{incomplete} flags

For L{summited<scripts.posummit>} catalogs, the C{branch} option is used to
restrict modifications to messages from the given branch only.
Several branch IDs may be given as a comma-separated list.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

from pology.misc.comments import parse_summit_branches


class Sieve (object):

    def __init__ (self, options):

        self.ntagged = 0
        self.ncleared = 0

        # Strip the present flags instead?
        self.strip = False
        if "strip" in options:
            options.accept("strip")
            self.strip = True

        # Summit: consider only messages belonging to given branches.
        self.branches = None
        if "branch" in options:
            self.branches = set(options["branch"].split(","))
            options.accept("branch")


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

        if not self.strip and may_tag and not msg.translated:
            if flag_incomplete not in msg.flag:
                msg.flag.add(flag_incomplete)
                self.ntagged += 1
        else:
            if flag_incomplete in msg.flag:
                msg.flag.remove(flag_incomplete)
                self.ncleared += 1


    def finalize (self):

        if self.ntagged > 0:
            print "Total incomplete flags added: %d" % (self.ntagged,)
        if self.ncleared > 0:
            print "Total incomplete flags removed: %d" % (self.ncleared,)

