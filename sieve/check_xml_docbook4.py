# -*- coding: UTF-8 -*-

"""
Lightweight validity checking of POs containing Docbook XML.

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

import sys
import os
import re
import locale
import xml.parsers.expat

from pology import rootdir, _, n_
from pology.hook.check_markup import flag_no_check_markup
from pology.misc.markup import check_xml_docbook4_l1, check_placeholder_els
from pology.misc.msgreport import report_on_msg_hl, report_msg_content
from pology.misc.msgreport import report_msg_to_lokalize
from pology.misc.report import report
from pology.misc.stdsvpar import add_param_poeditors
from pology.sieve import parse_sieve_flags


def setup_sieve (p):

    p.set_desc(_("@info sieve discription",
    "Validate text markup in translation in Docbook 4 catalogs."
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

        self.nproblems = 0


    def process (self, msg, cat):

        # Check only translated messages.
        if not msg.translated:
            return

        highlight = []
        self.nproblems += _check_dbmarkup(msg, cat, False, highlight)

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
            msg = (n_("@info:progress",
                      "Found %(num)d problem in Docbook markup "
                      "in translations.",
                      "Found %(num)d problems in Docbook markup "
                      "in translations.",
                      self.nproblems)
                   % dict(num=self.nproblems))
            report("===== %s" % msg)


_meta_msg_msgctxt = set((
))
_meta_msg_msgid = set((
    "translator-credits",
))
_meta_msg_msgid_sw = (
    "@@image:",
)

# NOTE: Also used by check_kde_tp
def _check_dbmarkup (msg, cat, strict, hl):

    # Skip some known meta-messages.
    if msg.msgctxt in _meta_msg_msgctxt or msg.msgid in _meta_msg_msgid:
        return 0
    if msg.msgid.startswith(_meta_msg_msgid_sw):
        return 0

    # Explicit skipping.
    if flag_no_check_markup in parse_sieve_flags(msg):
        return 0

    if not strict and check_xml_docbook4_l1(msg.msgid):
        return 0

    nproblems = 0
    for i in range(len(msg.msgstr)):
        spans = []
        spans.extend(check_xml_docbook4_l1(msg.msgstr[i]))
        spans.extend(check_placeholder_els(msg.msgid, msg.msgstr[i]))
        if spans:
            nproblems += len(spans)
            hl.append(("msgstr", i, spans))

    return nproblems

