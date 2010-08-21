# -*- coding: utf-8 -*-

"""
Make some comparations between the translation and the riginal text.

@author: Javier Viñal <fjvinal@gmail.com>
@license: GPLv3
"""

import re

from pology import _, n_

_auto_cmnt_tag_rx = re.compile(r"^\s*Tag:\s*(%s)\s*$" % "|".join("""
    trans_comment literallayout option programlisting othercredit author email holder
    surname personname affiliation address sect1 chapter chapterinfo date command option
    refentrytitle refentryinfo refname synopsis literal varname term glossterm
    filename envar userinput cmdsynopsis
""".split()), re.U|re.I)

def remove_tags_without_translation (msg, cat):
    """
    Remove all paragraph that belong to contexts that do not 
    have need of translation.[type F4A hook].

    @return: number of errors
    """

    if msg.msgctxt in ("EMAIL OF TRANSLATORS", "NAME OF TRANSLATORS", "ROLES OF TRANSLATORS"):
        msg.msgid = ""
        msg.msgid_plural = ""
        msg.msgstr = ""
        return 0

    # Avoid specially tagged messages.
    for tag in msg.auto_comment:
        if _auto_cmnt_tag_rx.search(tag):
            msg.msgid = ""
            msg.msgid_plural = ""
            msg.msgstr = ""
            return 0

    if msg.msgctxt:
        if _auto_cmnt_tag_rx.search(msg.msgctxt):
            msg.msgid = ""
            msg.msgid_plural = ""
            msg.msgstr = ""
            return 0

    return 0

def test_if_empty_translation (msg, cat):
    """
    Compare the translalion qith the original text, to test if the translation
    is empty.[type V4A hook].

    @return: number of errors
    """
    
    if len(msg.msgstr) == 0 and len(msg.msgid) > 0:
        return [("msgstr", 0, [])]

    return ""

def test_if_very_long_translation (msg, cat):
    """
    Compare the translalion qith the original text, to test if the transaled text 
    is much longer than the original.[type V4A hook].

    @return: number of errors
    """
    
    if msg.msgctxt in ("EMAIL OF TRANSLATORS", "NAME OF TRANSLATORS", "ROLES OF TRANSLATORS"):
        return []

    if len(msg.msgstr) > 2 * len(msg.msgid):
        return [("msgstr", 0, [])]

    return []

def test_if_not_translated (msg, cat):
    """
    Compare the translalion qith the original text, to test if the paragraph is 
    not translated.[type V4A hook].

    @return: number of errors
    """

    if msg.msgctxt in ("EMAIL OF TRANSLATORS", "NAME OF TRANSLATORS", "ROLES OF TRANSLATORS"):
        return []

    if msg.msgid == msg.msgstr:
        for tag in msg.auto_comment:
           if _auto_cmnt_tag_rx.search(tag):
               return []
        
        if msg.msgctxt:
            if _auto_cmnt_tag_rx.search(msg.msgctxt):
                return []

        return [("msgstr", 0, [])]

    return []
