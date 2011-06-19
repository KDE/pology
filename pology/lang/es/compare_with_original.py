# -*- coding: utf-8 -*-

"""
Make some comparations between the translation and the original text.

@author: Javier Viñal <fjvinal@gmail.com>
@license: GPLv3
"""

import re
import pology.external.pyaspell as A
from pology import _, n_, split


def test_if_empty_translation (msg, cat):
    """
    Compare the translation with the original text, testing if the translation
    is empty.

    [type V4A hook].
    @return: parts
    """
    for i in range(len(msg.msgstr)):
        if i > 0:
             lm = len(msg.msgid_plural)
        else:
             lm = len(msg.msgid)
        if lm > 0 and len(msg.msgstr[i]) == 0:
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

   
    for i in range(len(msg.msgstr)):
        if i > 0:
            lm = len(msg.msgid_plural.split())
        else:
            lm = len(msg.msgid.split())
        if lm > 0 and len(msg.msgstr[i].split()) > (1.5 * lm + 3):
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

    for i in range(len(msg.msgstr)):
        if len(msg.msgstr[i]) > 0:
            if i > 0:
                lm = len(msg.msgid_plural.split())
            else:
                lm = len(msg.msgid.split())
            if lm > (1.5 * len(msg.msgstr[i].split()) +  3):
                return [("msgstr", 0, [(0, 0, None)])]    

    return []

_valid_word = re.compile("(?u)^[^\W\d_]+$")
def test_if_not_translated (msg, cat):
    """
    Compare the translation with the original text, testing if the paragraph is 
    not translated.

    [type V4A hook].
    @return: parts
    """
  
    for i in range(len(msg.msgstr)):
        if i > 0:
           msgid = msg.msgid_plural
        else:
           msgid = msg.msgid
           
        if len(msgid) > 0 and msgid == msg.msgstr[i]:
            dict_en = A.Aspell((("lang", "en"),("encoding", "utf-8")))
            dict_local = A.Aspell(("encoding", "utf-8"))
            wordList = split.proper_words(msgid, markup=True, accels=['&'])
            for word in wordList:
	        word = word.encode("utf-8")
	        if _valid_word.match(word):
                    if dict_en.check(word) and not dict_local.check(word):
                        dict_en.close()
                        dict_local.close()
                        return [("msgstr", 0, [(0, 0, None)])]
            dict_en.close()
            dict_local.close()

    return []


_ent_new_line = re.compile("\\n")

def test_paired_new_lines (msg, cat):
    """
    Compare number of new lines between original and translated text. 

    [type V4A hook].
    @return: parts
    """
    for i in range(len(msg.msgstr)):
        if i > 0:
             msgid = msg.msgid_plural
        else:
             msgid = msg.msgid
             
        cont_orig = len(_ent_new_line.findall(msgid))
        cont_trans = len(_ent_new_line.findall(msg.msgstr[i]))
    
        if cont_orig < cont_trans:
            return [("msgstr", 0, [(0, 0, "Sobran saltos de linea en la traducción")])]
    
        if cont_orig > cont_trans:
            return [("msgstr", 0, [(0, 0, "Faltan saltos de linea en la traducción")])]


    return []

_ent_tab = re.compile("\\t")

def test_paired_tabs (msg, cat):
    """
    Compare number of tabs between original and translated text. 
    
    [type V4A hook].
    @return: parts
    """
    for i in range(len(msg.msgstr)):
        if i > 0:
             msgid = msg.msgid_plural
        else:
             msgid = msg.msgid

        cont_orig = len(_ent_tab.findall(msgid))
        cont_trans = len(_ent_tab.findall(msg.msgstr[i]))
    
        if cont_orig < cont_trans:
            return [("msgstr", 0, [(0, 0, "Sobran tabuladores en la traducción")])]
    
        if cont_orig > cont_trans:
            return [("msgstr", 0, [(0, 0, "Faltan tabuladores en la traducción")])]

    return []
