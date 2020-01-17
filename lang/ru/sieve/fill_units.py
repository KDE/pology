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
            ('yotta', 'йотта', 'Y', 'Й'),
            ('zetta', 'зетта', 'Z', 'З'),
            ('exa', 'экса', 'E', 'Э'),
            ('peta', 'пета', 'P', 'П'),
            ('tera', 'тера', 'T', 'Т'),
            ('giga', 'гига', 'G', 'Г'),
            ('mega', 'мега', 'M', 'М'),
            ('kilo', 'кило', 'k', 'к'),
            ('hecto', 'гекто', 'h', 'г'),
            ('deca', 'дека', 'da', 'да'),
            ('', '', '', ''),
            ('deci', 'деци', 'd', 'д'),
            ('centi', 'санти', 'c', 'с'),
            ('milli', 'милли', 'm', 'м'),
            ('micro', 'микро', 'µ', 'мк'),
            ('nano', 'нано', 'n', 'н'),
            ('pico', 'пико', 'p', 'п'),
            ('femto', 'фемто', 'f', 'ф'),
            ('atto', 'атто', 'a', 'а'),
            ('zepto', 'зепто', 'z', 'з'),
            ('yocto', 'йокто', 'y', 'и'),

            ('yobi', 'йоби',  'Yi', 'Йи'),
            ('zebi', 'зеби',  'Zi', 'Зи'),
            ('exbi', 'эксби', 'Ei', 'Эи'),
            ('pebi', 'пеби',  'Pi', 'Пи'),
            ('tebi', 'теби',  'Ti', 'Ти'),
            ('gibi', 'гиби',  'Gi', 'Ги'),
            ('mebi', 'меби',  'Mi', 'Ми'),
            ('kibi', 'киби',  'Ki', 'Ки'),
        ]

    # {0} -> "giga", "гига"
    # {1} -> "G", "Г"
    def translate_with_unit_prefix(self, text, msgid_fmt, msgstr_fmt, bytes_exception):
        for prefix in self.prefixes:
            if text == msgid_fmt.format(prefix[0], prefix[2]):
                if bytes_exception and prefix[0] == 'kilo':
                    return msgstr_fmt.format(prefix[1], 'К') # килобайт/КБ
                else:
                    return msgstr_fmt.format(prefix[1], prefix[3])

        return None

    def translate_with_unit_prefix_plural(self, texts, msgid_fmts, msgstr_fmts):
        for prefix in self.prefixes:
            if all(texts[i] == msgid_fmts[i].format(prefix[0], prefix[2]) for i in range(len(texts))):
                return list(msgstr_fmt.format(prefix[1], prefix[3]) for msgstr_fmt in msgstr_fmts)

        return None

    def translate_multiple_with_unit_prefix(self, text, unit_pairs, bytes_exception=False):
        for unit in unit_pairs:
            tr = self.translate_with_unit_prefix(text, unit[0], unit[1], len(unit) > 2 and unit[2])
            if tr is not None:
                return tr

        return None

    def process_single(self, msg, cat):
        tr = None

        # Example: "gigaamperes" -> "гигаамперы"
        if msg.msgctxt == 'unit description in lists':
            units = [
                ('{0}amperes', '{0}амперы'),
                ('{0}ohms', '{0}омы'),
                ('{0}volts', '{0}вольты'),
                ('{0}bytes', '{0}байты'),
                ('{0}bits', '{0}биты'),
                ('{0}watts', '{0}ватты'),
            ]
            tr = self.translate_multiple_with_unit_prefix(msg.msgid, units)

        if msg.msgctxt is not None and msg.msgctxt.endswith(' unit symbol'):
            units = [
                ('{1}A', '{1}А'),
                ('{1}V', '{1}В'),
                ('{1}Ω', '{1}Ом'),
                # ('{0}ohms', u'{0}омы'),
                # ('{0}volts', u'{0}вольты'),
                ('{1}b', '{1}бит'),
                ('{1}W', '{1}Вт'),
            ]
            tr = self.translate_multiple_with_unit_prefix(msg.msgid, units)

        if msg.msgctxt == 'unit synonyms for matching user input':
            # TODO replace these tuples with a structure
            units = [
                ('{0}ampere;{0}amperes;{1}A', '{0}ампер;{0}ампера;{0}амперов;{0}амперы;{0}амперах;{1}А', False),
                ('{0}amp;{0}amps;{0}ampere;{0}amperes;{1}A', '{0}ампер;{0}ампера;{0}амперов;{0}амперы;{0}амперах;{1}А', False),
                ('{0}volt;{0}volts;{1}V', '{0}вольт;{0}вольта;{0}вольтов;{0}вольты;{0}вольтах;{1}В', False),
                ('{0}ohm;{0}ohms;{1}Ω', '{0}ом;{0}ома;{0}омов;{0}омы;{0}омах;{1}Ом', False),
                ('{1}B;{0}byte;{0}bytes', '{1}Б;{0}байт;{0}байта;{0}байтов;{0}байты;{0}байтах', True),
                ('{1}b;{0}bit;{0}bits', '{1}бит;{0}бит;{0}бита;{0}битов;{0}биты;{0}битах', False),
                ('{0}watt;{0}watts;{1}W', '{0}ватт;{0}ватта;{0}ваттов;{0}ватты;{0}ваттах;{1}Вт', False),
            ]
            tr = self.translate_multiple_with_unit_prefix(msg.msgid, units)

        if msg.msgctxt == 'amount in units (real)':
            units = [
                ('%1 {0}amperes', '%1 {0}ампера'),
                ('%1 {0}volts', '%1 {0}вольта'),
                ('%1 {0}ohms', '%1 {0}ома'),
                ('%1 {0}bytes', '%1 {0}байт'),
                ('%1 {0}bits', '%1 {0}бит'),
                ('%1 {0}watts', '%1 {0}ватт'),
            ]
            tr = self.translate_multiple_with_unit_prefix(msg.msgid, units)

        return tr

    def process_plural(self, msg, cat):
        if msg.msgctxt == 'amount in units (integer)':
            unit_pairs = [
                (('%1 {0}ampere', '%1 {0}amperes'),
                 ('%1 {0}ампер', '%1 {0}ампера', '%1 {0}ампер', '%1 {0}ампер')),
                (('%1 {0}ohm', '%1 {0}ohms'),
                 ('%1 {0}ом', '%1 {0}ома', '%1 {0}ом', '%1 {0}ом')),
                (('%1 {0}volt', '%1 {0}volts'),
                 ('%1 {0}вольт', '%1 {0}вольта', '%1 {0}вольт', '%1 {0}вольт')),
                (('%1 {0}byte', '%1 {0}bytes'),
                 ('%1 {0}байт', '%1 {0}байта', '%1 {0}байт', '%1 {0}байт')),
                (('%1 {0}bit', '%1 {0}bits'),
                 ('%1 {0}бит', '%1 {0}бита', '%1 {0}бит', '%1 {0}бит')),
                (('%1 {0}watt', '%1 {0}watts'),
                 ('%1 {0}ватт', '%1 {0}ватта', '%1 {0}ватт', '%1 {0}ватт')),
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
