# -*- coding: utf-8 -*-

"""
Remove special substrings from parts of the message.

@author: Javier Viñal <fjvinal@gmail.com>
@license: GPLv3
"""

import re
#from pology import PologyError, datadir, _, n_
#from pology.report import report, warning, format_item_list


# Capitals words in valid contexts in the translated text according with Spanish grammar
# (beggining of paragraph, after some punctuation characters and after a new line)
_valid_capital_word_middle = re.compile("(?<=[.:?!>»\"]\s)[^\W]*?[A-ZÁÉÍÓÚÀÈÌÒÙÂÊÎÔÛÄËÏÖÜĀ][^\W]*", re.U)
_valid_capital_word_initial = re.compile("^[^\W]*?[A-ZÁÉÍÓÚÀÈÌÒÙÂÊÎÔÛÄËÏÖÜĀ][^\W]*", re.U)

# All capital words in the original English text,
_ent_capital_word = re.compile("[^\W]*?[A-ZÁÉÍÓÚÀÈÌÒÙÂÊÎÔÛÄËÏÖÜĀ][^\W]*", re.U)
# All plural full capital words (acronyms) without the final 's'.
_ent_capital_word_plural = re.compile("[A-Z0-9ÁÉÍÓÚÀÈÌÒÙÂÊÎÔÛÄËÏÖÜĀ]+(?=\'?s\b)", re.U)

def remove_paired_capital_words (msg, cat):
    """
    Remove all capital words from original text and from translated text, except that are located
    in a place where may be a capital word according the Spanish grammar.[type F4A hook].

    @return: number of errors
    """
    
    # Obtains capitals words in valid contexts in the translated text.
    for i in range(len(msg.msgstr)):
        ents = set()
        ents.update(_valid_capital_word_middle.findall(msg.msgstr[i]))
        ents.update(_valid_capital_word_initial.findall(msg.msgstr[i]))
        if i == 0:
            # Obtains all capitals words in the original English text.
            ents.update(_ent_capital_word.findall(msg.msgid))
            ents.update(_ent_capital_word_plural.findall(msg.msgid))
        else:
            if msg.msgid_plural:
		ents.update(_ent_capital_word.findall(msg.msgid_plural))
		ents.update(_ent_capital_word_plural.findall(msg.msgid_plural))
	# Joins both set of words an remove them from the message.
        for ent in ents:
	    # report(_("@info", "Palabra en mayusculas: %(info)s \n", info=ent))
            # msg.msgstr[i] = msg.msgstr[i].replace(ent, "~")
            msg.msgstr[i] = re.sub(r'\b' + ent + r'\b', '~', msg.msgstr[i], re.U)

    # The remainning words could have wrong capitalization in the translated message.
	
    # TODO: Look the remaining words in a Spanish dictionary.
	
    return 0


_ent_parameter = re.compile("(%\d%?|\$\{.+?\}|\$\w+|%(?:\d\$)?[ds]|%\|.+?\|)", re.U)

def remove_paired_parameters (msg, cat):
    """
    Remove format strings from the original text, and from translation
    all that are also found in the original text [type F4A hook].

    @return: number of errors
    """

    pars_orig = set()
    pars_orig.update(_ent_parameter.findall(msg.msgid))

    pars_orig_plural = set()
    if msg.msgid_plural:
        pars_orig_plural.update(_ent_parameter.findall(msg.msgid_plural))

    for i in range(len(msg.msgstr)):
        pars_trans = set(_ent_parameter.findall(msg.msgstr[i]))
        if i == 0:
            for par in pars_trans.intersection(pars_orig):
                msg.msgid = msg.msgid.replace(par, "~")
                msg.msgstr[i] = msg.msgstr[i].replace(par, "~")
        else:
            for par in pars_trans.intersection(pars_orig_plural):
                msg.msgid_plural = msg.msgid_plural.replace(par, "~")
                msg.msgstr[i] = msg.msgstr[i].replace(par, "~")

    return 0

_ent_xml_entity = re.compile("\<\/?\w+\>")


_auto_comment_tag = ("trans_comment", "literallayout", "option", "programlisting", "othercredit",
    "author", "email", "holder",
    "surname", "personname", "affiliation", "address", "sect1", "chapter", "chapterinfo", "date", "command", "option",
    "refentrytitle", "refentryinfo", "refname", "synopsis", "literal", "varname", "term", "glossterm",
    "filename", "entry", "envar", "userinput", "cmdsynopsis", "releaseinfo", "language", "Name",
    "City", "Region", "Region/state", "unit", "Query", "Kgm")

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
        for i in range(len(msg.msgstr)):
            msg.msgstr[i] = ""
        return 0

    # Avoid specially tagged messages.
    for tagline in msg.auto_comment:
        for tag in tagline.split():
            if tag in _auto_comment_tag:
                msg.msgid = ""
                if msg.msgid_plural:
                    msg.msgid_plural = ""
                for i in range(len(msg.msgstr)):
                    msg.msgstr[i] = ""
                return 0

    if msg.msgctxt:
        for tag in msg.msgctxt.split():
            if tag in _auto_comment_tag:
                msg.msgid = ""
                if msg.msgid_plural:
                    msg.msgid_plural = ""
                for i in range(len(msg.msgstr)):
                    msg.msgstr[i] = ""
                return 0

    return 0
