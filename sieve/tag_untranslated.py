# -*- coding: UTF-8 -*-

"""
Tag untranslated messages.

Some people like to translate PO files with ordinary text editor,
which may provide no more support for editing PO files other
than e.g. syntax highlighting.
In such a scenario, this sieve can be used to equip untranslated messages
with C{untranslated} flag, for easy lookup in the editor.
E.g. to jump through all incomplete messages (fuzzy and untranslated),
translator can issue C{, fuzzy|, untranslated} regular expression
in editor's search facility.

Note that C{untranslated} flags, being custom, will be lost when the PO file
is merged with the template next time. This is intentional: the only purpose
of the flag is for immediate editing, and the translator may forget to remove
some. There is no reason for the flags to persist in that case. Also, if
the flag is left in after the message has been translated, the subsequent
run of this sieve will remove the flag.

Sieve options:
  - C{branch:<branch_id>}: consider only messages from this branch (summit)
  - C{strip}: instead of adding, strip any C{untranslated} flags

For L{summited<scripts.posummit>} catalogs, the C{branch} option is used to
restrict modifications to messages from the given branch only.
Several branch IDs may be given as a comma-separated list.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

from pology.misc.report import report
from pology.misc.comments import parse_summit_branches


def setup_sieve (p):

    p.set_desc(
    "Tag all untranslated messages."
    )

    p.add_param("strip", bool,
                desc=
    "Remove tags from untranslated messages."
    )
    p.add_param("branch", unicode, seplist=True,
                metavar="BRANCH",
                desc=
    "In summited catalogs, consider only messages belonging to given branch. "
    "Several branches can be given as comma-separated list."
    )


_flag_untranslated = u"untranslated"

class Sieve (object):

    def __init__ (self, params):

        self.strip = params.strip
        self.branches = set(params.branch or [])

        self.ntagged = 0
        self.ncleared = 0


    def process (self, msg, cat):

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

        if not self.strip and may_tag and msg.untranslated:
            if _flag_untranslated not in msg.flag:
                msg.flag.add(_flag_untranslated)
                self.ntagged += 1
        else:
            if _flag_untranslated in msg.flag:
                msg.flag.remove(_flag_untranslated)
                self.ncleared += 1


    def finalize (self):

        if self.ntagged > 0:
            report("Total untranslated messages tagged: %d" % self.ntagged)
        if self.ncleared > 0:
            report("Total untranslated messages cleared of tags: %d"
                   % self.ncleared)

