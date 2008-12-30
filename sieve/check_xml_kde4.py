# -*- coding: UTF-8 -*-

import sys, os, re
import locale
import xml.parsers.expat
from pology.misc.entities import read_entities
from pology.misc.comments import manc_parse_flag_list
from pology.misc.report import report
from pology.misc.msgreport import report_on_msg, report_on_msg_hl
from pology.misc.markup import check_xml_kde4_l1, check_xml_qtrich_l1
from pology.hook.check_markup import flag_no_check_xml

# Pure Qt POs in KDE repository.
qt_catnames = (
    "kdeqt", "libphonon", "phonon_gstreamer", "phonon-xine",
    "kdgantt1", "kdgantt",
)
qt_catname_ends = (
    "_qt",
)

def is_qt_cat (name):

    if name in qt_catnames:
        return True
    for end in qt_catname_ends:
        if name.endswith(end):
            return True
    return False


def _check_qt_w_adds (text, ents):

    res = []

    # Basic Qt check.
    res.extend(check_xml_qtrich_l1(text, ents))

    # No Transcript.
    tsfence = "|/|"
    p = text.find(tsfence)
    if p >= 0:
        res.append((p, p + len(tsfence),
                    "Qt POs cannot contain scripted messages"))

    return res


def setup_sieve (p):

    p.set_desc(
    "Validate text markup and few other details in KDE4 POs. "
    "These include full-bread KDE4 POs (most are such), "
    "pure Qt POs (e.g. in qt module), and pure text POs (e.g. desktop_*)."
    )
    p.add_param("entdef", unicode, multival=True,
                metavar="FILE",
                desc=
    "File defining any external entities used in messages "
    "(parameter can be repeated to add more files). Entity file "
    "defines entities one per line, in the format:"
    "\n\n"
    "<!ENTITY entname 'entvalue'>"
    )
    p.add_param("strict", bool, defval=False,
                desc=
    "Check translations strictly: report problems in translation regardless "
    "of whether original itself is valid (default is to check translation "
    "only if original passes checks)."
    )


class Sieve (object):

    def __init__ (self, params, options):

        self.nbad = 0

        # Whether to strictly check translations.
        self.strict = params.strict

        # Files defining external entities.
        self.entity_files = params.entdef or []

        # Read definitions of external entities.
        self.entities = read_entities(self.entity_files)

        # Indicators to the caller:
        self.caller_sync = False # no need to sync catalogs to the caller
        self.caller_monitored = False # no need for monitored messages


    def process_header (self, hdr, cat):

        # Select type of markup to check based on catalog name.
        if cat.name.startswith("desktop_") or cat.name.startswith("xml_"):
            self.check_xml = lambda text, ents=None: []
        elif is_qt_cat(cat.name):
            self.check_xml = _check_qt_w_adds
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
                or self.check_xml(msg.msgid_plural or u"", ents=self.entities)
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
                report("Total translations with problems (strict): %d"
                       % self.nbad)
            else:
                report("Total translations with problems: %d" % self.nbad)

