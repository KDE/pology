# -*- coding: UTF-8 -*-

"""
Tag untranslated messages.

Documented in C{doc/user/sieving.docbook}.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

from pology import _, n_
from pology.comments import parse_summit_branches
from pology.report import report


def setup_sieve (p):

    p.set_desc(_("@info sieve discription",
    "Tag all untranslated messages with '%(flag)s' flag.",
    flag=_flag_untranslated
    ))

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
            msg = n_("@info:progress",
                     "Tagged %(num)d untranslated message.",
                     "Tagged %(num)d untranslated messages.",
                     num=self.ntagged)
            report("===== " + msg)
        if self.ncleared > 0:
            msg = n_("@info:progress",
                     "Cleared untranslated tag from %(num)d message.",
                     "Cleared untranslated tag from %(num)d messages.",
                     num=self.ncleared)
            report("===== " + msg)

