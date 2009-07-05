# -*- coding: UTF-8 -*-

"""
Lightweight validity checking of POs containing Docbook XML.

Docbook is a complex XML application, and nothing short of full validation
of XML files generated from translated POs can show it correct for sure.
This sieve just checks for well-formedness and mere existance of a tag in
Docbook subset, and on a single PO entry level.

Sieve options:
  - C{showmsg}: show content of the message, with errors highlighted

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import sys
import os
import re
import locale
import xml.parsers.expat
from pology.misc.report import report
from pology.misc.msgreport import report_on_msg_hl, report_msg_content
from pology.misc.msgreport import report_msg_to_lokalize
from pology.misc.markup import check_xml_docbook4_l1, check_placeholder_els
from pology import rootdir


_meta_msg_msgctxt = set((
))
_meta_msg_msgid = set((
    "translator-credits",
))
_meta_msg_msgid_sw = (
    "@@image:",
)

class Sieve (object):

    def __init__ (self, options):

        self.nbad = 0

        self.showmsg = False
        if "showmsg" in options:
            options.accept("showmsg")
            self.showmsg = True

        self.lokalize = False
        if "lokalize" in options:
            options.accept("lokalize")
            self.lokalize = True

        # Indicators to the caller:
        self.caller_sync = False # no need to sync catalogs to the caller
        self.caller_monitored = False # no need for monitored messages


    def process (self, msg, cat):

        # Check only translated messages.
        if not msg.translated:
            return

        # Skip some known meta-messages.
        if msg.msgctxt in _meta_msg_msgctxt or msg.msgid in _meta_msg_msgid:
            return
        if msg.msgid.startswith(_meta_msg_msgid_sw):
            return

        # Check XML in translation.
        highlight = []
        for i in range(len(msg.msgstr)):
            errspans = []
            # Basic Docbook validity.
            errspans.extend(check_xml_docbook4_l1(msg.msgstr[i]))
            # Congruence of placeholder elements, for POs created by xml2po.
            errspans.extend(check_placeholder_els(msg.msgid, msg.msgstr[i]))

            # Add to bad spans.
            if errspans:
                highlight.append(("msgstr", i, errspans))

        # Report problems.
        if highlight:
            if self.showmsg:
                report_msg_content(msg, cat, showmsg=self.showmsg,
                                   highlight=highlight, delim=("-" * 20))
            else:
                report_on_msg_hl(highlight, msg, cat)
            if self.lokalize:
                report_msg_to_lokalize(msg, cat, highlight)
            self.nbad += 1


    def finalize (self):

        if self.nbad > 0:
            report("Total translations with invalid Docbook: %d" % self.nbad)

