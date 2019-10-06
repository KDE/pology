#!/usr/bin/python2
# coding: utf8

"""
Fill in some comets' names that follow specific patterns.
Run against kstars.po.

Sieve has no options.

@author: Alexander Potashev <aspotashev@gmail.com>
@license: GPLv3
"""

from pology import _, n_
from pology.report import report
from pology.msgreport import report_msg_content
import os
import re


def setup_sieve (p):

    p.set_desc(_("@info sieve discription",
    "Fill in some comets' names that follow specific patterns."
    ))


class Sieve (object):

    def __init__ (self, params):
        pass
        # Other dates should have the following format: (yyyy-mm-dd)
        self.date_re = re.compile("^[0-9][0-9][0-9][0-9]\-[0-9][0-9]\-[0-9][0-9]$")

    def translate (self, msg):
        if msg.msgctxt == "Asteroid name (optional)" and re.match(r'\([0-9]{4} [A-Z]{2}[0-9]{1,3}\)', msg.msgid):
            return msg.msgid
        if msg.msgctxt == 'Comet name (optional)':
            m = re.match(r'([CP]/[0-9]* [A-Z0-9\-]{2,5}) \(([a-zA-Z ]*)\)', msg.msgid)
            if m:
                code = m.group(1)
                name = m.group(2)

                tr_name = {
                    u'Great comet': u'Большая комета',
                    u'PANSTARRS': u'Pan-STARRS',
                    u'LINEAR': u'LINEAR',
                    u'Lemmon': u'обзор Маунт-Леммон',
                    u'NEOWISE': u'NEOWISE',
                    u'Catalina': u'обзор Каталина',
                    u'Borisov': u'Борисов',
                    u'Messier': u'Мессье',
                    u'Pons': u'Понс',
                    u'Гершель': u'Гершель',
                    u'Olbers': u'Ольберс',
                    u'Winnecke': u'Виннеке',
                    u'WISE': u'WISE',
                    u'Tempel': u'Темпель',
                    u'STEREO': u'STEREO',
                    u'SOHO': u'SOHO',
                    u'Spacewatch': u'Spacewatch',
                    u'SOLWIND': u'Solwind',
                    u'Shoemaker': u'Шумейкер',
                    u'NEAT': u'NEAT',
                    u'McNaught': u'Макнот',
                    u'Christensen': u'Кристенсен',
                    u'Barnard': u'Барнард',
                    u'LONEOS': u'LONEOS',
                    u'Lovejoy': u'Лавджой',
                    u'Machholz': u'Макхольц',
                    u'Mechain': u'Мешен',
                    u'SMM': u'SolarMax',
                    u'Boattini': u'Боаттини',
                    u'Bradfield': u'Брэдфилд',
                    u'Mueller': u'Мюллер',
                    u'Alcock': u'Алкок',
                    u'Blathwayt': u'Блатуэйт',
                    u'Borrelly': u'Борелли',
                    u'Brorsen': u'Брорзен',
                    u'Burnham': u'Бёрнхем',
                    u'du Toit': u'Дю Туа',
                    u'Gambart': u'Гамбар',
                    u'Giacobini': u'Джакобини',
                    u'Gibbs': u'Гиббс',
                    u'Hill': u'Хилл',
                    u'Honda': u'Хонда',
                    u'IRAS': u'IRAS',
                    u'Klinkerfues': u'Клинкерфус',
                    u'Kohoutek': u'Когоутек',
                    u'Lovas': u'Ловас',
                    u'Mauvais': u'Мовэ',
                    u'Mellish': u'Меллиш',
                    u'Petersen': u'Петерсон',
                    u'Read': u'Рид',
                    u'Siding Spring': u'Сайдинг-Спринг',
                    u'Skjellerup': u'Скьеллеруп',
                    u'Swift': u'Свифт',
                    u'Yanaka': u'Янака',
                    u'Brooks': u'Брукс',
                    u'Galle': u'Галле',
                    u'Skiff': u'Скифф',
                    u'Wilson': u'Уилсон',
                    u'Herschel': u'Гершель',
                    u'Perrine': u'Перрайн',
                }
                if name in tr_name:
                    return u'{} ({})'.format(code, tr_name[name])
                else:
                    print('unknown: %s' % name)

        return None

    def process (self, msg, cat):
        new_msgstr = self.translate(msg)
        if new_msgstr is not None and (msg.fuzzy or msg.msgstr[0] != new_msgstr):
            msg.msgstr[0] = new_msgstr
            msg.unfuzzy()
            report_msg_content(msg, cat)

    def finalize (self):
        ""
