# -*- coding: utf-8 -*-

"""
Make some comparations between the translation and the riginal text.

@author: Javier Viñal <fjvinal@gmail.com>
@license: GPLv3
"""

import re
import enchant
from pology import _, n_, split

auto_comment_tag = ["trans_comment", "literallayout", "option", "programlisting", "othercredit", "author", "email", "holder", 
    "surname", "personname", "affiliation", "address", "sect1", "chapter", "chapterinfo", "date", "command", "option", 
    "refentrytitle", "refentryinfo", "refname", "synopsis", "literal", "varname", "term", "glossterm", 
    "filename", "entry", "envar", "userinput", "cmdsynopsis", "releaseinfo"]

def remove_tags_without_translation (msg, cat):
    """
    Remove all paragraph that belong to contexts that do not 
    have need of translation.
    
    [type F4A hook].
    @return: number of errors
    """
 
    if msg.msgctxt in ("EMAIL OF TRANSLATORS", "NAME OF TRANSLATORS", "ROLES OF TRANSLATORS"):
        msg.msgid = ""
        msg.msgid_plural = ""
        msg.msgstr[0] = ""
        return 0

    # Avoid specially tagged messages.
    for tagline in msg.auto_comment:
        for tag in tagline.split():
            if tag in auto_comment_tag:
                msg.msgid = ""
                msg.msgid_plural = ""
                msg.msgstr[0] = ""
                return 0

    if msg.msgctxt:
        for tag in msg.msgctxt.split(): 
            if tag in auto_comment_tag:
                msg.msgid = ""
                msg.msgid_plural = ""
                msg.msgstr[0] = "" 
                return 0

    return 0

def test_if_empty_translation (msg, cat):
    """
    Compare the translation with the original text, testing if the translation
    is empty.

    [type V4A hook].
    @return: parts
    """
  
    if len(msg.msgstr[0]) == 0 and len(msg.msgid) > 0:
        return [("msgstr", 0, [(0, 0, None)])]

    return ""

def test_if_very_long_translation (msg, cat):
    """
    Compare the translation with the original text, testing if the transaled text 
    is much longer than the original (As much twice with a correction for small text).
    
    [type V4A hook].
    @return: parts
    """
    if msg.msgctxt in ("EMAIL OF TRANSLATORS", "NAME OF TRANSLATORS", "ROLES OF TRANSLATORS"):
        return []

    if len(msg.msgid) > 0:
        if len(msg.msgstr[0]) > (2 * len(msg.msgid) + 12 / len(msg.msgid)):
            return [("msgstr", 0, [(0, 0, None)])]    

    return []

def test_if_very_short_translation (msg, cat):
    """
    Compare the translation with the original text, testing if the transaled text 
    is much shorter than the original.
    
    [type V4A hook].
    @return: parts
    """
    
    if msg.msgctxt in ("EMAIL OF TRANSLATORS", "NAME OF TRANSLATORS", "ROLES OF TRANSLATORS"):
        return []

    if len(msg.msgstr[0]) > 0:
        if len(msg.msgid) > (2 * len(msg.msgstr[0]) + 12 / len(msg.msgstr[0])):
            return [("msgstr", 0, [(0, 0, None)])]    

    return []


def test_if_not_translated (msg, cat):
    """
    Compare the translalion qith the original text, to test if the paragraph is 
    not translated.

    [type V4A hook].
    @return: parts
    """

    if len(msg.msgid) == 0:
        return []
    
    if msg.msgid == msg.msgstr[0]:
        dict_en = enchant.Dict("en_US")
        dict_local = enchant.Dict()
        wordList = split.proper_words(msg.msgid, markup=True, accels=['&'])
        for word in wordList:
            if dict_en.check(word) and not dict_local.check(word):
                    return [("msgstr", 0, [(0, 0, None)])]    

    return []
