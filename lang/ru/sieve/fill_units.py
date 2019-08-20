# -*- coding: UTF-8 -*-

"""
Fill in Russian translations for units with metric prefixes.

Sieve has no options.

@author: Alexander Potashev <aspotashev@gmail.com>
@license: GPLv3
"""

from pology import _
from pology.msgreport import report_msg_content


def setup_sieve (p):

    p.set_desc(_("@info sieve discription",
    "Fill in Russian translations for units with metric prefixes."
    ))


class Sieve (object):

    def __init__ (self, params):
        self.prefixes = [
            ('yotta', u'йотта', 'Y', u'Й'),
            ('zetta', u'зетта', 'Z', u'З'),
            ('exa', u'экса', 'E', u'Э'),
            ('peta', u'пета', 'P', u'П'),
            ('tera', u'тера', 'T', u'Т'),
            ('giga', u'гига', 'G', u'Г'),
            ('mega', u'мега', 'M', u'М'),
            ('kilo', u'кило', 'k', u'к'),
            ('hecto', u'гекто', 'h', u'г'),
            ('deca', u'дека', 'da', u'да'),
            ('', u'', '', u''),
            ('deci', u'деци', 'd', u'д'),
            ('centi', u'санти', 'c', u'с'),
            ('milli', u'милли', 'm', u'м'),
            ('micro', u'микро', u'µ', u'мк'),
            ('nano', u'нано', 'n', u'н'),
            ('pico', u'пико', 'p', u'п'),
            ('femto', u'фемто', 'f', u'ф'),
            ('atto', u'атто', 'a', u'а'),
            ('zepto', u'зепто', 'z', u'з'),
            ('yocto', u'йокто', 'y', u'и'),
        ]

    # {0} -> "giga", "гига"
    # {1} -> "G", "Г"
    def translate_with_unit_prefix(self, text, msgid_fmt, msgstr_fmt):
        for prefix in self.prefixes:
            if text == msgid_fmt.format(prefix[0], prefix[2]):
                return msgstr_fmt.format(prefix[1], prefix[3])

        return None

    def translate_with_unit_prefix_plural(self, texts, msgid_fmts, msgstr_fmts):
        for prefix in self.prefixes:
            if all(texts[i] == msgid_fmts[i].format(prefix[0], prefix[2]) for i in range(len(texts))):
                return list(msgstr_fmt.format(prefix[1], prefix[3]) for msgstr_fmt in msgstr_fmts)

        return None

    def translate_multiple_with_unit_prefix(self, text, unit_pairs):
        for unit in unit_pairs:
            tr = self.translate_with_unit_prefix(text, unit[0], unit[1])
            if tr is not None:
                return tr

        return None

    def process_single(self, msg, cat):
        tr = None

        # Example: "gigaamperes" -> "гигаамперы"
        if msg.msgctxt == u'unit description in lists':
            units = [
                ('{0}amperes', u'{0}амперы'),
                ('{0}ohms', u'{0}омы'),
                ('{0}volts', u'{0}вольты'),
            ]
            tr = self.translate_multiple_with_unit_prefix(msg.msgid, units)

        if msg.msgctxt is not None and msg.msgctxt.endswith(' unit symbol'):
            units = [
                (u'{1}A', u'{1}А'),
                (u'{1}V', u'{1}В'),
                (u'{1}Ω', u'{1}Ом'),
                # ('{0}ohms', u'{0}омы'),
                # ('{0}volts', u'{0}вольты'),
            ]
            tr = self.translate_multiple_with_unit_prefix(msg.msgid, units)

        if msg.msgctxt == 'unit synonyms for matching user input':
            units = [
                (u'{0}ampere;{0}amperes;{1}A', u'{0}ампер;{0}ампера;{0}амперов;{0}амперы;{0}амперах;{1}А'),
                (u'{0}amp;{0}amps;{0}ampere;{0}amperes;{1}A', u'{0}ампер;{0}ампера;{0}амперов;{0}амперы;{0}амперах;{1}А'),
                (u'{0}volt;{0}volts;{1}V', u'{0}вольт;{0}вольта;{0}вольтов;{0}вольты;{0}вольтах;{1}В'),
                (u'{0}ohm;{0}ohms;{1}Ω', u'{0}ом;{0}ома;{0}омов;{0}омы;{0}омах;{1}Ом'),
            ]
            tr = self.translate_multiple_with_unit_prefix(msg.msgid, units)

        if msg.msgctxt == u'amount in units (real)':
            units = [
                ('%1 {0}amperes', u'%1 {0}ампера'),
                ('%1 {0}volts', u'%1 {0}вольта'),
                ('%1 {0}ohms', u'%1 {0}ома'),
            ]
            tr = self.translate_multiple_with_unit_prefix(msg.msgid, units)

        return tr

    def process_plural(self, msg, cat):
        if msg.msgctxt == u'amount in units (integer)':
            unit_pairs = [
                ((u'%1 {0}ampere', u'%1 {0}amperes'),
                 (u'%1 {0}ампер', u'%1 {0}ампера', u'%1 {0}ампер', u'%1 {0}ампер')),
                ((u'%1 {0}ohm', u'%1 {0}ohms'),
                 (u'%1 {0}ом', u'%1 {0}ома', u'%1 {0}ом', u'%1 {0}ом')),
                ((u'%1 {0}volt', u'%1 {0}volts'),
                 (u'%1 {0}вольт', u'%1 {0}вольта', u'%1 {0}вольт', u'%1 {0}вольт')),
            ]

            for unit in unit_pairs:
                tr = self.translate_with_unit_prefix_plural((msg.msgid, msg.msgid_plural), unit[0], unit[1])
                if tr is not None:
                    return tr

            return None

    def process(self, msg, cat):
        # if msg.translated:
        #     return

        if msg.msgid_plural is None:
            tr = self.process_single(msg, cat)
            if tr is not None:
                msg.msgstr[0] = tr
                msg.unfuzzy()
                report_msg_content(msg, cat)
        else:
            tr = self.process_plural(msg, cat)
            if tr is not None:
                for i in range(len(tr)):
                    msg.msgstr[i] = tr[i]
                msg.unfuzzy()
                report_msg_content(msg, cat)

    def finalize(self):
        pass
