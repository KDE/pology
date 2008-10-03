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
from pology.misc.report import report, report_on_msg
from pology.misc.markup import collect_xml_spec_l1
from pology import rootdir

# ----------------------------------------
# Informal Docbook specification.

# Collect tags and attributes from the companion file.
specpath = os.path.join(rootdir(), "misc", "check_xml_docbook4-spec.txt")
docbook_tagattrs = collect_xml_spec_l1(specpath)

# Add dummy top tag.
dummy_top = "dummytop123"
docbook_tagattrs[dummy_top] = {}

# ----------------------------------------
# Check well-formedness and existence of tags.

# Links to current state for the handlers.
_c_cat = None
_c_msg = None
_c_quiet = False
_c_errcnt = 0


# Handler to check existence of tags.
def _handler_start_element (name, attrs):

    global _c_errcnt

    # Check existence of tag.
    if name not in docbook_tagattrs:
        _c_errcnt += 1
        if not _c_quiet:
            report_on_msg("unrecognized Docbook tag: %s" % name, _c_msg, _c_cat)
        return

    # Check applicability of attributes.
    for attr in attrs:
        if attr not in docbook_tagattrs[name]:
            _c_errcnt += 1
            if not _c_quiet:
                report_on_msg(  "invalid attribute for Docbook tag <%s>: %s"
                              % (name, attr), _c_msg, _c_cat)


# Check current msgstr.
def check_xml_docbook (cat, msg, msgstr, quiet=False):

    # Link current state for handlers.
    global _c_cat; _c_cat = cat
    global _c_msg; _c_msg = msg
    global _c_quiet; _c_quiet = quiet
    global _c_errcnt; _c_errcnt = 0

    text = msgstr

    # Make sure the text has a top tag, for the parser not to bitch.
    text = "<%s>%s</%s>" % (dummy_top, text, dummy_top)

    # Parse the text.
    p = xml.parsers.expat.ParserCreate()
    p.UseForeignDTD() # not to barf on non-default XML entities
    p.StartElementHandler = _handler_start_element

    try:
        p.Parse(text.encode("UTF-8"), True)
    except xml.parsers.expat.ExpatError, inst:
        if not quiet:
            report_on_msg("Docbook parsing: %s" % inst, _c_msg, _c_cat)
        return False

    if not match_placeholder_tags(msg.msgid, msgstr):
        return False

    return _c_errcnt == 0


# Test whether all <placeholder-N/> tags in msgid are present in msgstr.
_placeholder_rx = re.compile(r"<\s*placeholder-(\d+)\s*/\s*>")

def match_placeholder_tags (msgid, msgstr):

    if "placeholder-" in msgid:
        msgid_plnums = set()
        for m in _placeholder_rx.finditer(msgid):
            msgid_plnums.add(m.group(1))
        msgstr_plnums = set()
        for m in _placeholder_rx.finditer(msgstr):
            msgstr_plnums.add(m.group(1))
        missing_plnums = list(msgid_plnums.difference(msgstr_plnums))
        extra_plnums = list(msgstr_plnums.difference(msgid_plnums))
        if missing_plnums:
            tags = ["<placeholder-%s/>" % x for x in missing_plnums]
            report_on_msg("Missing placeholder tags in translation: %s"
                          % ", ".join(tags), _c_msg, _c_cat)
            return False
        elif extra_plnums: # do not report both, single glitch may cause them
            tags = ["<placeholder-%s/>" % x for x in extra_plnums]
            report_on_msg("Extra placeholder tags in translation: %s"
                          % ", ".join(tags), _c_msg, _c_cat)
            return False

    return True

# ----------------------------------------
# The checker sieve.

_meta_msg_msgctxt = set([
])
_meta_msg_msgid = set([
    "translator-credits",
])
_meta_msg_msgid_sw = [
    "@@image:",
]

class Sieve (object):
    """Weakly check validity of Docbook XML."""

    def __init__ (self, options, global_options):

        self.nbad = 0

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
        for sw in _meta_msg_msgid_sw:
            if msg.msgid.startswith(sw):
                return

        # Check XML in translation.
        for msgstr in msg.msgstr:
            if not check_xml_docbook(cat, msg, msgstr):
                self.nbad += 1


    def finalize (self):

        if self.nbad > 0:
            report("Total translations with invalid Docbook: %d" % self.nbad)

