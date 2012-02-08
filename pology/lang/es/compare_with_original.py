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
        if lm > 0 and len(msg.msgstr[i].split()) > (1.6 * lm + 5):
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
            if lm > (1.6 * len(msg.msgstr[i].split()) +  5):
                return [("msgstr", 0, [(0, 0, None)])]    

    return []

_valid_word = re.compile(r"(?u)^[^\W\d_]+$")
_capital_word = re.compile(r"(?u)^[A-Z]+$")



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
	        if _valid_word.match(word) and not _capital_word.match(word):
                    if dict_en.check(word) and not dict_local.check(word):
                        dict_en.close()
                        dict_local.close()
                        return [("msgstr", 0, [(0, 0, None)])]
            dict_en.close()
            dict_local.close()

    return []


_ent_new_line = re.compile(r"\\n")

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
            return [("msgstr", 0, [(0, 0, u"Sobran saltos de linea en la traducción")])]
    
        if cont_orig > cont_trans:
            return [("msgstr", 0, [(0, 0, u"Faltan saltos de linea en la traducción")])]


    return []

    
_ent_tab = re.compile(r"\\t")

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
            return [("msgstr", 0, [(0, 0, u"Sobran tabuladores en la traducción")])]
    
        if cont_orig > cont_trans:
            return [("msgstr", 0, [(0, 0, u"Faltan tabuladores en la traducción")])]

    return []
    

_ent_function = re.compile(r"\w[\w\d]*(\_[\w\d]+)*\(\)")

def test_paired_functions (msg, cat):
    """
    Compare functions names between original and translated text. 
    
    [type V4A hook].
    @return: parts
    """
    for i in range(len(msg.msgstr)):
        if i > 0:
             msgid = msg.msgid_plural
        else:
             msgid = msg.msgid

        function_orig = _ent_function.findall(msgid)
        function_trans = _ent_function.findall(msg.msgstr[i])
    
        if function_orig != function_trans:
            return [("msgstr", 0, [(0, 0, u"Nombres de función distintos en la traducción")])]
 
    return []
    
    
_ent_parameter = re.compile(r"\-\-\w[\w\d]*(\-[\w\d]+)*")

def test_paired_parameters (msg, cat):
    """
    Compare parameters names between original and translated text. 
    
    [type V4A hook].
    @return: parts
    """
    for i in range(len(msg.msgstr)):
        if i > 0:
             msgid = msg.msgid_plural
        else:
             msgid = msg.msgid

        parameter_orig = _ent_parameter.findall(msgid)
        parameter_trans = _ent_parameter.findall(msg.msgstr[i])
    
        if parameter_orig != parameter_trans:
            return [("msgstr", 0, [(0, 0, u"Nombres de parámetros distintos en la traducción")])]
 
    return []

    
_ent_number = re.compile(r"[^\%][\dXx]+([\.\,\:\/][\dXx]+)+")

def test_paired_numbers (msg, cat):
    """
    Compare numbers and dates between original and translated text. 
    
    [type V4A hook].
    @return: parts
    """
    for i in range(len(msg.msgstr)):
        if i > 0:
             msgid = msg.msgid_plural
        else:
             msgid = msg.msgid

        number_orig = _ent_number.findall(msgid)
        number_trans = _ent_number.findall(msg.msgstr[i])
    
        if number_orig != number_trans:
            return [("msgstr", 0, [(0, 0, u"Valores de números distintos en la traducción")])]
 
    return []

