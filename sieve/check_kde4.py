# -*- coding: utf-8 -*-

"""
Check native KDE4 PO files for various problems.

Documented in C{doc/user/sieving.docbook}.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

from pology import _, n_
from pology.markup import flag_no_check_markup
from pology.markup import validate_kde4_l1
from pology.msgreport import report_on_msg, report_on_msg_hl
from pology.msgreport import report_msg_to_lokalize
from pology.report import report
from pology.sieve import add_param_poeditors
from pology.sieve import parse_sieve_flags


def setup_sieve (p):

    p.set_desc(_("@info sieve discription",
    "Check native KDE4 PO files for various problems."
    ))
    p.add_param("strict", bool, defval=False,
                desc=_("@info sieve parameter discription",
    "Check for problems in translation regardless of whether the original "
    "itself is free of problems (default is to check translation only if "
    "the original has no problems)."
    ))
    add_param_poeditors(p)


class Sieve (object):

    def __init__ (self, params):

        self.strict = params.strict

        self.lokalize = params.lokalize

        # Indicators to the caller:
        self.caller_sync = False # no need to sync catalogs to the caller
        self.caller_monitored = False # no need for monitored messages

        self.nproblems = 0


    def process (self, msg, cat):

        # Check only translated messages.
        if not msg.translated:
            return

        # Do not check messages when told so.
        if flag_no_check_markup in parse_sieve_flags(msg):
            return

        # In in non-strict mode, check XML of translation only if the
        # original itself is valid XML.
        if not self.strict:
            if (   validate_kde4_l1(msg.msgid, ents={})
                or validate_kde4_l1(msg.msgid_plural or "", ents={})
            ):
                return

        highlight = []
        for i in range(len(msg.msgstr)):
            spans = validate_kde4_l1(msg.msgstr[i], ents={})
            if spans:
                self.nproblems += 1
                highlight.append(("msgstr", i, spans, msg.msgstr[i]))

        if highlight:
            report_on_msg_hl(highlight, msg, cat)
            if self.lokalize:
                report_msg_to_lokalize(msg, cat, highlight)


    def finalize (self):

        if self.nproblems > 0:
            if not self.strict:
                msg = n_("@info:progress",
                         "Found %(num)d problem in KDE4 translations.",
                         "Found %(num)d problems in KDE4 translations.",
                         num=self.nproblems)
            else:
                msg = n_("@info:progress",
                         "Found %(num)d problem in KDE4 translations "
                         "(strict mode).",
                         "Found %(num)d problems in KDE4 translations "
                         "(strict mode).",
                         num=self.nproblems)
            report("===== " + msg)

