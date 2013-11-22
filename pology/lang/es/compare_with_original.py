# -*- coding: utf-8 -*-

"""
Make some comparations between the translation and the original text.

@author: Javier Viñal <fjvinal@gmail.com>
@license: GPLv3
"""

import re
import string
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
            return [("msgstr", 0, [(0, 0, u'La traducción parece estar vacía')])]

    return []


_purepunc = re.compile("^\W+$", re.U)

def test_if_purepunc (msg, cat):
    """
    Compare the translation with the original text, testing if the translation
    is different when the original text has not alphanumeric text.

    [type V4A hook].
    @return: parts
    """
    if msg.msgctxt in ("EMAIL OF TRANSLATORS", "NAME OF TRANSLATORS", "ROLES OF TRANSLATORS"):
	return []

    if msg.msgid in ("Your emails", "Your names", "CREDIT_FOR_TRANSLATORS", "ROLES_OF_TRANSLATORS"):
	return []

    for i in range(len(msg.msgstr)):
        msgstr = msg.msgstr[i]
	if i > 0:
            msgid = msg.msgid_plural
        else:
            msgid = msg.msgid

        if _purepunc.match(msgid):
            msgid = msgid.replace('"', '')
            msgid = msgid.replace("'", "")
	    msgid = msgid.replace(" ", "")
            msgstr = msgstr.replace('"', '')
            msgstr = msgstr.replace("'", "")
            msgstr = msgstr.replace(u"«", "")
            msgstr = msgstr.replace(u"»", "")
	    msgstr = msgstr.replace(" ", "")
            if msgid != msgstr:    
                return [("msgstr", 0, [(0, 0, u'Se ha traducido un texto no alfanumérico')])]

    return []

def test_if_non_printable_characters (msg, cat):
    """
    Compare the translation with the original text, testing if the translation
    is different when the original text has not alphanumeric text.

    [type V4A hook].
    @return: parts
    """
    if msg.msgctxt in ("EMAIL OF TRANSLATORS", "NAME OF TRANSLATORS", "ROLES OF TRANSLATORS"):
	return []

    if msg.msgid in ("Your emails", "Your names", "CREDIT_FOR_TRANSLATORS", "ROLES_OF_TRANSLATORS"):
	return []

    for i in range(len(msg.msgstr)):
	msgstr = msg.msgstr[i]
	if i > 0:
	    msgid = msg.msgid_plural
	else:
	    msgid = msg.msgid
	for c in msgstr:
	    if (c not in string.printable) and (c not in msgid) and (c not in u"áéíóúüñçÁÉÍÓÚÜÑÇ¿¡|«»©ºª/"):
		return [("msgstr", 0, [(0, 0, u'La traducción contiene caracteres no imprimibles')])]
	    elif (c in string.punctuation) and (c not in msgid) and (c not in u"«»©.,;:_-(|)ºª/"):
		return [("msgstr", 0, [(0, 0, u'La traducción contiene signos de puntuación no incluidos en el original')])]
    return []

def test_if_very_long_translation (msg, cat):
    """
    Compare the translation with the original text, testing if the transaled text
    is much longer than the original (As much twice with a correction for small text).

    [type V4A hook].
    @return: parts
    """
    if msg.msgctxt in ("EMAIL OF TRANSLATORS", "NAME OF TRANSLATORS", "ROLES OF TRANSLATORS"):
        return []

    if msg.msgid in ("Your emails", "Your names", "CREDIT_FOR_TRANSLATORS", "ROLES_OF_TRANSLATORS"):
	return []

    for i in range(len(msg.msgstr)):
        if i > 0:
            lm = len(msg.msgid_plural.split())
        else:
            lm = len(msg.msgid.split())
        if lm > 0 and len(msg.msgstr[i].split()) > (1.6 * lm + 5):
            return [("msgstr", 0, [(0, 0, u'La traducción parece demasiado larga')])]

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

    if msg.msgid in ("Your emails", "Your names", "CREDIT_FOR_TRANSLATORS", "ROLES_OF_TRANSLATORS"):
	return []

    for i in range(len(msg.msgstr)):
        if len(msg.msgstr[i]) > 0:
            if i > 0:
                lm = len(msg.msgid_plural.split())
            else:
                lm = len(msg.msgid.split())
            if lm > (1.6 * len(msg.msgstr[i].split()) +  5):
                return [("msgstr", 0, [(0, 0, u'La traducción parece demasiado corta')])]

    return []


_valid_word = re.compile("^\w+$", re.U)
_capital_word = re.compile("^[A-ZÑÇÁÉÍÓÚÁÉÍÓÚÂÊÎÔÛÄËÏÖÜĀ]+$", re.U)
_proper_name = re.compile("^\W*?[A-ZÑÇÁÉÍÓÚÁÉÍÓÚÂÊÎÔÛÄËÏÖÜĀ]\w+(\W+?[A-ZÑÇÁÉÍÓÚÁÉÍÓÚÂÊÎÔÛÄËÏÖÜĀ]\w+)+\W*$", re.U)

def test_if_not_translated (msg, cat):
    """
    Compare the translation with the original text, testing if the paragraph is
    not translated.

    [type V4A hook].
    @return: parts
    """
    
    if msg.msgctxt in ("EMAIL OF TRANSLATORS", "NAME OF TRANSLATORS", "ROLES OF TRANSLATORS"):
        return []

    if msg.msgid in ("Your emails", "Your names", "CREDIT_FOR_TRANSLATORS", "ROLES_OF_TRANSLATORS"):
	return []

    for i in range(len(msg.msgstr)):
        if i > 0:
            msgid = msg.msgid_plural
        else:
            msgid = msg.msgid
            
        if _proper_name.match(msg.msgstr[i]) or _purepunc.match(msgid):
	    continue

        if len(msgid) > 0 and msgid == msg.msgstr[i]:
             for word in split.proper_words(msgid, markup=True, accels=['&']):
                if _valid_word.match(word) and not _capital_word.match(word):
                    word = word.encode("utf-8")
                    e = A.Aspell(("lang", "en")) #, ("encoding", "utf-8"))
		    l = A.Aspell(("lang", "es")) #, ("encoding", "utf-8"))
                    if e.check(word) and not l.check(word):
                        e.close()
                        l.close()
                        return [("msgstr", 0, [(0, 0, u'El párrafo parece no estar traducido')])]
		    e.close()
		    l.close()

    return []

_ent_accel = re.compile("\&[A-Za-zÑÇñç](?!\w+\;)", re.U)

def test_paired_accelerators (msg, cat):
    """
    Compare number of accelerators (&) between original and translated text.

    [type V4A hook].
    @return: parts
    """

    if msg.msgctxt in ("EMAIL OF TRANSLATORS", "NAME OF TRANSLATORS", "ROLES OF TRANSLATORS"):
        return []

    if msg.msgid in ("Your emails", "Your names", "CREDIT_FOR_TRANSLATORS", "ROLES_OF_TRANSLATORS"):
	return []

    for i in range(len(msg.msgstr)):
        if i > 0:
            msgid = msg.msgid_plural
        else:
            msgid = msg.msgid

        cont_orig = len(_ent_accel.findall(msgid))
        cont_tran = len(_ent_accel.findall(msg.msgstr[i]))

        if cont_orig < cont_tran:
            return [("msgstr", 0, [(0, 0, u"Sobran aceleradores «&» en la traducción")])]
        elif cont_orig > cont_tran:
            return [("msgstr", 0, [(0, 0, u"Faltan aceleradores «&» en la traducción")])]
    return []


def test_paired_strings (msg, cat):
    """
    Compare number of some strings between original and translated text.

    [type V4A hook].
    @return: parts
    """

    if msg.msgctxt in ("EMAIL OF TRANSLATORS", "NAME OF TRANSLATORS", "ROLES OF TRANSLATORS"):
        return []

    if msg.msgid in ("Your emails", "Your names", "CREDIT_FOR_TRANSLATORS", "ROLES_OF_TRANSLATORS"):
	return []

    for i in range(len(msg.msgstr)):
        if i > 0:
            msgid = msg.msgid_plural
        else:
            msgid = msg.msgid

        for s in ([r"\t", u"tabuladores"],
                  [r"\n", u"saltos de línea"]
                  ):
            cont_orig = msgid.count(s[0])
            cont_tran = msg.msgstr[i].count(s[0])

            if cont_orig < cont_tran:
                return [("msgstr", 0, [(0, 0, u"Sobran " + s[1] + u" en la traducción")])]
            elif cont_orig > cont_tran:
                return [("msgstr", 0, [(0, 0, u"Faltan " + s[1] + u" en la traducción")])]
    return []


def test_paired_brackets (msg, cat):
    """
    Compare number of some brackets between original and translated text.

    [type V4A hook].
    @return: parts
    """

    if msg.msgctxt in ("EMAIL OF TRANSLATORS", "NAME OF TRANSLATORS", "ROLES OF TRANSLATORS"):
        return []

    if msg.msgid in ("Your emails", "Your names", "CREDIT_FOR_TRANSLATORS", "ROLES_OF_TRANSLATORS"):
	return []

    for i in range(len(msg.msgstr)):
        if i > 0:
            msgid = msg.msgid_plural
        else:
            msgid = msg.msgid

        for s in ([u"(", u")", u"paréntesis"],
                  [u"{", u"}", u"llaves"],
                  [u"[", u"]", u"corchetes"],
                  [u"«", u"»", u"comillas españolas"]
                  ):
            cont_orig_open = msgid.count(s[0])
            cont_orig_close = msgid.count(s[1])
            if cont_orig_open != cont_orig_close:
                continue
            cont_tran_open = msg.msgstr[i].count(s[0])
            cont_tran_close = msg.msgstr[i].count(s[1])

            if cont_tran_open < cont_tran_close:
                return [("msgstr", 0, [(0, 0, u"Sobran " + s[2] + u" en la traducción")])]
            elif cont_tran_open > cont_tran_close:
                return [("msgstr", 0, [(0, 0, u"Faltan " + s[2] + u" en la traducción")])]
    return []

_ent_function = re.compile("(?:\w+\:\:)*\w+\(\)", re.U)
_ent_parameter = re.compile("(?<=\W)\-\-\w+(?:\-\w+)*", re.U)

def test_paired_expressions (msg, cat):
    """
    Compare expressions (functions, parameters) between original and translated text.
    Should be the same.

    [type V4A hook].
    @return: parts
    """
    if msg.msgctxt in ("EMAIL OF TRANSLATORS", "NAME OF TRANSLATORS", "ROLES OF TRANSLATORS"):
        return []

    if msg.msgid in ("Your emails", "Your names", "CREDIT_FOR_TRANSLATORS", "ROLES_OF_TRANSLATORS"):
	return []

    for i in range(len(msg.msgstr)):
        if i > 0:
            msgid = msg.msgid_plural
        else:
            msgid = msg.msgid

        for expr in ([_ent_function, u"Nombres de función"],
                     [_ent_parameter, u"Parámetros de orden"]
                     ):
            expr_orig = sorted(expr[0].findall(msgid))
            expr_trans = sorted(expr[0].findall(msg.msgstr[i]))

            if expr_orig != expr_trans:
                return [("msgstr", 0, [(0, 0, expr[1] + u" distintos en la traducción")])]

    return []


_ent_number = re.compile("\d+(?:[\s.,:/-]\d+)*", re.U)
_not_digit = re.compile("\D", re.U)

def test_paired_numbers (msg, cat):
    """
    Compare numbers and dates between original and translated text.
    Should be the same (except for commas/colons and one digit numbers)

    [type V4A hook].
    @return: parts
    """
    if msg.msgctxt in ("EMAIL OF TRANSLATORS", "NAME OF TRANSLATORS", "ROLES OF TRANSLATORS"):
        return []
 
    if msg.msgid in ("Your emails", "Your names", "CREDIT_FOR_TRANSLATORS", "ROLES_OF_TRANSLATORS"):
	return []
   
    for i in range(len(msg.msgstr)):
        if i > 0:
            msgid = msg.msgid_plural
        else:
            msgid = msg.msgid

        number_orig = []
        for number in _ent_number.findall(msgid):
            if len(number) > 1:
                number_orig += _not_digit.split(number)

        number_trans = []
        for number in _ent_number.findall(msg.msgstr[i]):
            if len(number) > 1:
                number_trans += _not_digit.split(number)

        if sorted(number_orig) != sorted(number_trans):
            return [("msgstr", 0, [(0, 0, u"Valores de números distintos en la traducción")])]

    return []

_ent_context_tags = re.compile("\<(application|bcode|command|email|envar|filename|icode|link)\>(.+?)\<\/\1\>", re.U)

def test_paired_context_tags (msg, cat):
    """
    Compare context tags between original and translated text.
    Some of them should not be changed in the translation.

    [type V4A hook].
    @return: parts
    """
    if msg.msgctxt in ("EMAIL OF TRANSLATORS", "NAME OF TRANSLATORS", "ROLES OF TRANSLATORS"):
        return []

    if msg.msgid in ("Your emails", "Your names", "CREDIT_FOR_TRANSLATORS", "ROLES_OF_TRANSLATORS"):
	return []

    for i in range(len(msg.msgstr)):
        if i > 0:
            msgid = msg.msgid_plural
        else:
            msgid = msg.msgid

        for tag in _ent_context_tags.findall(msgid):
            if not (tag[1] in msg.msgstr[i]):
                return [("msgstr", 0, [(0, 0, u"Valor de etiqueta de contexto" + tag[1] + u"traducido indebidamente")])]

    return []

_ent_xml_entities = re.compile("\<\/?\w+?\>", re.U)

def test_paired_xml_entities (msg, cat):
    """
    Compare xml entities between original and translated text.
    Some of them should not be changed in the translation.

    [type V4A hook].
    @return: parts
    """
    if msg.msgctxt in ("EMAIL OF TRANSLATORS", "NAME OF TRANSLATORS", "ROLES OF TRANSLATORS"):
        return []

    if msg.msgid in ("Your emails", "Your names", "CREDIT_FOR_TRANSLATORS", "ROLES_OF_TRANSLATORS"):
	return []

    for i in range(len(msg.msgstr)):
        if i > 0:
            msgid = msg.msgid_plural
        else:
            msgid = msg.msgid

        for tag in _ent_xml_entities.findall(msgid):
            if not (tag in msg.msgstr[i]):
                return [("msgstr", 0, [(0, 0, u"Etiqueta XML" + tag + u"no encontrada en la traducción")])]

        for tag in _ent_xml_entities.findall(msg.msgstr[i]):
            if not (tag in msgid):
                return [("msgstr", 0, [(0, 0, u"Etiqueta XML" + tag + u"no encontrada en el texto original")])]

    return []
