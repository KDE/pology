# -*- coding: UTF-8 -*-

import sys, os, re
import locale
import xml.parsers.expat
from pology.misc.resolve import read_entities
from pology.misc.comments import manc_parse_flag_list
from pology.misc.report import report, report_on_msg, report_on_msg_hl
from pology.misc.markup import check_xml_kde4_l1, check_xml_html_l1

# Pipe flag used to manually prevent check for a particular message.
flag_no_check_xml = "no-check-xml"


class Sieve (object):

    def __init__ (self, options, global_options):

        self.nbad = 0

        # Whether to strictly check translations:
        # if False, XML errors in translation are reported only if original
        # itself is valid XML, otherwise errors are reported unconditionally.
        self.strict = False
        if "strict" in options:
            options.accept("strict")
            self.strict = True

        # Files defining external entities.
        self.entity_files = []
        if "entdef" in options:
            options.accept("entdef")
            self.entity_files = options["entdef"].split(",")

        # Read definitions of external entities.
        self.entities = read_entities(*self.entity_files)

        # Indicators to the caller:
        self.caller_sync = False # no need to sync catalogs to the caller
        self.caller_monitored = False # no need for monitored messages


    def process_header (self, hdr, cat):

        # Select type of markup to check based on catalog name.
        if cat.name.startswith(("desktop_", "xml_")):
            self.check_xml = lambda text, ents=None: []
        elif cat.name in ("kdeqt",):
            self.check_xml = check_xml_html_l1
        else:
            self.check_xml = check_xml_kde4_l1


    def process (self, msg, cat):

        # Check only translated messages.
        if not msg.translated:
            return

        # Do not check messages when told so.
        if flag_no_check_xml in manc_parse_flag_list(msg, "|"):
            return

        # In in non-strict mode, check XML of translation only if the
        # original itself is valid XML.
        if not self.strict:
            if (   self.check_xml(msg.msgid, ents=self.entities)
                or self.check_xml(msg.msgid_plural, ents=self.entities)
            ):
                return

        # Check XML in translation.
        highlight = []
        for i in range(len(msg.msgstr)):
            spans = self.check_xml(msg.msgstr[i], ents=self.entities)
            if spans:
                highlight.append(("msgstr", i, spans, msg.msgstr[i]))

        if highlight:
            self.nbad += 1
            report_on_msg_hl(highlight, msg, cat)


    def finalize (self):

        if self.nbad > 0:
            if self.strict:
                report("Total translations with invalid XML (strict): %d"
                       % self.nbad)
            else:
                report("Total translations with invalid XML: %d" % self.nbad)

