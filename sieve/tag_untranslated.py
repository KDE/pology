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
  - C{strip}: instead of adding, strip any C{untranslated} flags
  - C{wfuzzy}: add C{untranslated} flags to fuzzy messages too
  - C{branch:<branch_id>}: consider only messages from this branch (summit)

For L{summited<scripts.posummit>} catalogs, the C{branch} option is used to
restrict modifications to messages from the given branch only.
Several branch IDs may be given as a comma-separated list.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

from pology import _, n_
from pology.misc.comments import parse_summit_branches
from pology.misc.report import report


def setup_sieve (p):

    p.set_desc(_("@info sieve discription",
    "Tag all untranslated messages with '%(flag)s' flag."
    ) % dict(flag=_flag_untranslated))

    p.add_param("strip", bool,
                desc=_("@info sieve parameter discription",
    "Remove tags from messages."
    ))
    p.add_param("wfuzzy", bool,
                desc=_("@info sieve parameter discription",
    "Also add tags to fuzzy messages."
    ))
    p.add_param("branch", unicode, seplist=True,
                metavar=_("@info sieve parameter value placeholder", "BRANCH"),
                desc=_("@info sieve parameter discription",
    "In summit catalogs, consider only messages belonging to given branch. "
    "Several branches can be given as comma-separated list."
    ))


_flag_untranslated = u"untranslated"

class Sieve (object):

    def __init__ (self, params):

        self.strip = params.strip
        self.wfuzzy = params.wfuzzy
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

        ok_msg = msg.untranslated
        if self.wfuzzy and not ok_msg:
            ok_msg = msg.fuzzy

        if not self.strip and may_tag and ok_msg:
            if _flag_untranslated not in msg.flag:
                msg.flag.add(_flag_untranslated)
                self.ntagged += 1
        else:
            if _flag_untranslated in msg.flag:
                msg.flag.remove(_flag_untranslated)
                self.ncleared += 1


    def finalize (self):

        if self.ntagged > 0:
            msg = (n_("@info:progress",
                      "Tagged %(num)d untranslated message.",
                      "Tagged %(num)d untranslated messages.",
                      self.ntagged)
                   % dict(num=self.ntagged))
            report("===== %s" % msg)
        if self.ncleared > 0:
            msg = (n_("@info:progress",
                      "Cleared untranslated tag from %(num)d message.",
                      "Cleared untranslated tag from %(num)d messages.",
                      self.ncleared)
                   % dict(num=self.ncleared))
            report("===== %s" % msg)

