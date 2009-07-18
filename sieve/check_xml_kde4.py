# -*- coding: utf-8 -*-

"""
Check validity of markup that can be encountered in native KDE4 catalogs.

KDE4 catalogs can contain a mix of KUIT and Qt rich text markup.

Sieve parameters:
  - C{strict}: require translation to be valid even if original is not
  - C{entdef}: file with entity definitions other than the default HTML
  - C{lokalize}: open catalogs at failed messages in Lokalize

By default, translation is checked for validity only if the original passes
the same check, which need not be the case always.
This can be changed by issuing the C{strict} parameter, when translation
will be checked regardless of the original.
If this is used, check can be skipped for a particular message by adding
C{no-check-markup} L{sieve flag<sieve.parse_sieve_flags>}.

If entities other thand 

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import sys, os, re
import locale
import xml.parsers.expat
from pology.misc.entities import read_entities
from pology.misc.report import report
from pology.misc.msgreport import report_on_msg, report_on_msg_hl
from pology.misc.msgreport import report_msg_to_lokalize
from pology.misc.markup import check_xml_kde4_l1
from pology.hook.check_markup import flag_no_check_markup
from pology.sieve import parse_sieve_flags


_tsfence = "|/|"


def setup_sieve (p):

    p.set_desc(
    "Validate text markup in translation in native KDE4 catalogs."
    )
    p.add_param("strict", bool, defval=False,
                desc=
    "Check for problems in translation regardless of whether the original "
    "itself is free of problems (default is to check translation only if "
    "the original has no problems)."
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
    p.add_param("lokalize", bool, defval=False,
                desc=
    "Show reported messages in Lokalize."
    )


class Sieve (object):

    def __init__ (self, params):

        self.strict = params.strict

        self.entity_files = params.entdef or []
        self.entities = read_entities(self.entity_files)

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
            if (   check_xml_kde4_l1(msg.msgid, ents=self.entities)
                or check_xml_kde4_l1(msg.msgid_plural or u"", ents=self.entities)
            ):
                return

        highlight = []
        for i in range(len(msg.msgstr)):
            spans = check_xml_kde4_l1(msg.msgstr[i], ents=self.entities)
            if spans:
                self.nproblems += 1
                highlight.append(("msgstr", i, spans, msg.msgstr[i]))

        if highlight:
            report_on_msg_hl(highlight, msg, cat)
            if self.lokalize:
                report_msg_to_lokalize(msg, cat, highlight)


    def finalize (self):

        if self.nproblems > 0:
            if self.strict:
                report("Total KDE4 markup problems in translation (strict): %d"
                       % self.nproblems)
            else:
                report("Total KDE4 markup problems in translation: %d"
                       % self.nproblems)

