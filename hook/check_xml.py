# -*- coding: UTF-8 -*-

"""
Check validity of XML markup.
"""

from pology.misc.comments import manc_parse_flag_list
from pology.sieve.check_xml_kde4 import check_xml as check_xml_kde4_base
from pology.sieve.check_xml_kde4 import flag_no_check_xml


def check_xml_kde4 (strict=False, entities={}):
    """Factory of hooks to check KDE4 XML markup per msgstr.

    Produces hooks with (cat, msg, msgstr) signature, returning None.
    Markup errors are reported to stdout.
    If the check is not strict, msgstr is checked only if msgid itself is
    valid KDE4 XML markup.
    A dictionary of external XML entities (name, value) may be provided
    if such appear in the translation, for the check not to warn about
    unknown entities.
    if the message has pipe flag no-check-xml, check is skipped.
    """

    if strict:
        def hook (cat, msg, msgstr):
            if flag_no_check_xml in manc_parse_flag_list(msg, "|"):
                return
            check_xml_kde4_base(cat, msg, msgstr, ents=entities)
    else:
        def hook (cat, msg, msgstr):
            if flag_no_check_xml in manc_parse_flag_list(msg, "|"):
                return
            if (    check_xml_kde4_base(cat, msg, msg.msgid,
                                        quiet=True, ents=entities)
                and check_xml_kde4_base(cat, msg, msg.msgid_plural,
                                        quiet=True, ents=entities)):
                check_xml_kde4_base(cat, msg, msgstr,
                                    quiet=False, ents=entities)

    return hook
