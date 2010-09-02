# -*- coding: UTF-8 -*-

"""
Check catalogs covering Docbook 4.x documents for various problems.

Docbook is a complex XML application, and nothing short of full validation
of XML files generated from translated POs can show if markup is valid.
This sieve just checks for well-formedness and mere existance of a tag in
Docbook subset, and on the level of single PO message.
But this is already enough to catch most of the typical translation errors.

Sieve options:
  - C{showmsg}: show content of the message, with errors highlighted
  - C{lokalize}: open catalogs at failed messages in Lokalize

A message can be excluded from checking by adding C{no-check-markup}
L{sieve flag<sieve.parse_sieve_flags>}.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

from pology import _, n_
from pology.markup import check_docbook4_msg
from pology.msgreport import report_on_msg_hl, report_msg_content
from pology.msgreport import report_msg_to_lokalize
from pology.report import report
from pology.sieve import add_param_poeditors


def setup_sieve (p):

    p.set_desc(_("@info sieve discription",
    "Check catalogs covering Docbook 4.x documents for various problems."
    ))

    p.add_param("showmsg", bool, defval=False,
                desc=_("@info sieve parameter discription",
    "Also show the full message which has a problem."
    ))
    add_param_poeditors(p)


class Sieve (object):

    def __init__ (self, params):

        self.showmsg = params.showmsg
        self.lokalize = params.lokalize

        # Indicators to the caller:
        self.caller_sync = False # no need to sync catalogs to the caller
        self.caller_monitored = False # no need for monitored messages

        self.check = check_docbook4_msg(strict=False, entities=None)

        self.nproblems = 0


    def process (self, msg, cat):

        # Check only translated messages.
        if not msg.translated:
            return

        highlight = self.check(msg, cat)
        self.nproblems += sum(len(x[2]) for x in highlight)

        # Report problems.
        if highlight:
            if self.showmsg:
                report_msg_content(msg, cat, showmsg=self.showmsg,
                                   highlight=highlight, delim=("-" * 20))
            else:
                report_on_msg_hl(highlight, msg, cat)
            if self.lokalize:
                report_msg_to_lokalize(msg, cat, highlight)


    def finalize (self):

        if self.nproblems > 0:
            msg = n_("@info:progress",
                     "Found %(num)d problem in Docbook markup "
                     "in translations.",
                     "Found %(num)d problems in Docbook markup "
                     "in translations.",
                     num=self.nproblems)
            report("===== " + msg)

