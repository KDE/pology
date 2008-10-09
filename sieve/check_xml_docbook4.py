# -*- coding: UTF-8 -*-

"""
Lightweight validity checking of POs containing Docbook XML.

Docbook is a complex XML application, and nothing short of full validation
of XML files generated from translated POs can show it correct for sure.
This sieve just checks for well-formedness and mere existance of a tag in
Docbook subset, and on a single PO entry level.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import sys
import os
import re
import locale
import xml.parsers.expat
from pology.misc.report import report, report_on_msg, report_msg_content
from pology.misc.markup import check_xml_docbook4_l1
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
    """Weakly check validity of Docbook XML."""

    def __init__ (self, options, global_options):

        self.nbad = 0

        self.showmsg = False
        if "showmsg" in options:
            options.accept("showmsg")
            self.showmsg = True

        # Indicators to the caller:
        self.caller_sync = False # no need to sync catalogs to the caller
        self.caller_monitored = False # no need for monitored messages


    def process (self, msg, cat):

        # Check only translated messages.
        if not msg.translated:
            return

        # FIXME: Freak message in konqueror_browser.po that puts
        # Python's difflib.ndiff() into endless loop.
        if msg.msgid.startswith("1, 7, 9, 11, 13, 15, 17, 19"):
            return

        # Skip some known meta-messages.
        if msg.msgctxt in _meta_msg_msgctxt or msg.msgid in _meta_msg_msgid:
            return
        if msg.msgid.startswith(_meta_msg_msgid_sw):
            return

        # Check XML in translation.
        one_bad = False

        highlight = []
        errmsgs = []
        for i in range(len(msg.msgstr)):
            errspans = []
            # Basic Docbook validity.
            errspans.extend(check_xml_docbook4_l1(msg.msgstr[i]))
            # Correspondence of <placeholder-N/>, for POs created by xml2po.
            errspans.extend(_match_placeholder_tags(msg.msgid, msg.msgstr[i]))

            # Add to bad spans.
            if errspans:
                highlight.append(("msgstr", i, errspans))

        # Report problems.
        if highlight:
            report_msg_content(msg, cat, onlynotes=(not self.showmsg),
                               highlight=highlight, delim=("-" * 40))
            self.nbad += 1


    def finalize (self):

        if self.nbad > 0:
            report("Total translations with invalid Docbook: %d" % self.nbad)


# Test whether all <placeholder-N/> tags in msgid are present in msgstr.
_placeholder_rx = re.compile(r"<\s*placeholder-(\d+)\s*/\s*>")

def _match_placeholder_tags (msgid, msgstr):

    spans = []

    msgid_plnums = set()
    for m in _placeholder_rx.finditer(msgid):
        msgid_plnums.add(m.group(1))
    msgstr_plnums = set()
    for m in _placeholder_rx.finditer(msgstr):
        msgstr_plnums.add(m.group(1))
    missing_plnums = list(msgid_plnums.difference(msgstr_plnums))
    extra_plnums = list(msgstr_plnums.difference(msgid_plnums))
    if missing_plnums:
        tags = "".join(["<placeholder-%s/>" % x for x in missing_plnums])
        errmsg = ("Missing placeholder tags in translation: %s" % tags)
        spans.append((0, 0, errmsg))
    elif extra_plnums: # do not report both, single glitch may cause them
        tags = "".join(["<placeholder-%s/>" % x for x in extra_plnums])
        errmsg = ("Extra placeholder tags in translation: %s" % tags)
        spans.append((0, 0, errmsg))

    return spans

