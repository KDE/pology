# -*- coding: utf-8 -*-

"""
Remove special substrings from parts of the message.

@author: Javier Viñal <fjvinal@gmail.com>
@license: GPLv3
"""

import re

from pology import _, n_

_ent_capital_word = re.compile(r"([A-Z]\w+\b)")

def remove_paired_capital_words (msg, cat):
    """
    Remove all capital words from original, and from translation
    all that are also found in original [type F4A hook].

    @return: number of errors
    """

    ents_orig = set()
    ents_orig.update(_ent_capital_word.findall(msg.msgid))
    for ent in ents_orig:
        msg.msgid = msg.msgid.replace(ent, "")

    if msg.msgid_plural:
        ents_orig.update(_ent_capital_word.findall(msg.msgid_plural))
        for ent in ents_orig:
            msg.msgid_plural = msg.msgid_plural.replace(ent, "")

    for i in range(len(msg.msgstr)):
        ents_trans = set(_ent_capital_word.findall(msg.msgstr[i]))
        for ent in ents_trans.intersection(ents_orig):
            msg.msgstr[i] = msg.msgstr[i].replace(ent, "")

    return 0
    
_ent_parameter = re.compile(r"(\%\d)")

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
