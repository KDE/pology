# -*- coding: utf-8 -*-

"""
Remove special substrings from parts of the message.

@author: Javier Viñal <fjvinal@gmail.com>
@license: GPLv3
"""

import re

from pology import rootdir, _, n_
from pology.fsops import system_wd
from pology.report import report, warning, format_item_list

# Capitals words in valid contexts in the translated text according with Spanish grammar
# (beggining of paragraph, after some punctuation characters and after a new line)
_valid_capital_word = re.compile("(?u)^[A-ZÑÇÁÉÍÓÚ]\w*|[.:?!>«\"]\s*[A-ZÑÇÁÉÍÓÚ]\w*|\\n\s*[A-ZÑÇÁÉÍÓÚ]\w*")

# All capital words in the original English text,
_ent_capital_word = re.compile("(?u)[A-Z]\w*")
# All plural full capital words (acronyms) without the final 's'.
_ent_capital_word_plural = re.compile("(?u)[A-Z]+(?=s)")

def remove_paired_capital_words (msg, cat):
    """
    Remove all capital words from original text and from translated text, except that are located
    in a place where may be a capital word according the Spanish grammar.[type F4A hook].

    @return: number of errors
    """

    # Obtains all capitals words in the original English text. 
    ents_orig = set()
    ents_orig.update(_ent_capital_word.findall(msg.msgid))
    ents_orig.update(_ent_capital_word_plural.findall(msg.msgid))

    # Obtains capitals words in valid contexts in the translated text.
    ents_trans = set()
    for i in range(len(msg.msgstr)):
        ents_trans.update(_valid_capital_word.findall(msg.msgstr[i]))
    
    # Joins both set of words an remove it from the message.
    for ent in ents_trans.union(ents_orig):
        msg.msgstr[i] = msg.msgstr[i].replace(ent, "")
        
    # The remainning words could have wrong capitalization in the translated message.

    #if msg.msgid_plural:
    #    ents_orig = set()
    #    ents_orig.update(_ent_capital_word.findall(msg.msgid_plural))

    #    ents_trans = set()
    #    for i in range(len(msg.msgstr_plural)):
    #        ents_trans.update(_valid_capital_word.findall(msg.msgstr_plural[i]))
    
    #    for ent in ents_trans.union(ents_orig):
    #        msg.msgstr_plural[i] = msg.msgstr_plural[i].replace(ent, "")

    #ents_trans = set()
    #for i in range(len(msg.msgstr)):
    #    ents_trans.update(_ent_capital_word.findall(msg.msgstr[i]))
    
    #for ent in ents_trans:
    #    report("===== Buscando: " + ent + "\n")

        #if system_wd("grep -q -f lang/es/spell/dict.aspell -e " + ent, rootdir()):
        #    continue
        #else:
        #    msg.msgstr[i] = msg.msgstr[i].replace(ent, "")
 
    return 0
    
_ent_parameter = re.compile("(\%\d)")

def remove_paired_parameters (msg, cat):
    """
    Remove all parameters from original, and from translation
    all that are also found in original [type F4A hook].

    @return: number of errors
    """

    ents_orig = set()
    ents_orig.update(_ent_parameter.findall(msg.msgid))
    for ent in ents_orig:
        msg.msgid = msg.msgid.replace(ent, "")

    if msg.msgid_plural:
        ents_orig.update(_ent_parameter.findall(msg.msgid_plural))
        for ent in ents_orig:
            msg.msgid_plural = msg.msgid_plural.replace(ent, "")

    for i in range(len(msg.msgstr)):
        ents_trans = set(_ent_parameter.findall(msg.msgstr[i]))
        for ent in ents_trans.intersection(ents_orig):
            msg.msgstr[i] = msg.msgstr[i].replace(ent, "")

    return 0
