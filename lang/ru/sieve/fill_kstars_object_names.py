#!/usr/bin/python2
# coding: utf8

"""
Fill in some comets' names that follow specific patterns.
Run against kstars.po.

Sieve has no options.

@author: Alexander Potashev <aspotashev@gmail.com>
@license: GPLv3
"""

import re

from pology import _
from pology.msgreport import report_msg_content

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
                    'Great comet': 'Большая комета',
                    'PANSTARRS': 'Pan-STARRS',
                    'LINEAR': 'LINEAR',
                    'Lemmon': 'обзор Маунт-Леммон',
                    'NEOWISE': 'NEOWISE',
                    'Catalina': 'обзор Каталина',
                    'Borisov': 'Борисов',
                    'Messier': 'Мессье',
                    'Pons': 'Понс',
                    'Гершель': 'Гершель',
                    'Olbers': 'Ольберс',
                    'Winnecke': 'Виннеке',
                    'WISE': 'WISE',
                    'Tempel': 'Темпель',
                    'STEREO': 'STEREO',
                    'SOHO': 'SOHO',
                    'Spacewatch': 'Spacewatch',
                    'SOLWIND': 'Solwind',
                    'Shoemaker': 'Шумейкер',
                    'NEAT': 'NEAT',
                    'McNaught': 'Макнот',
                    'Christensen': 'Кристенсен',
                    'Barnard': 'Барнард',
                    'LONEOS': 'LONEOS',
                    'Lovejoy': 'Лавджой',
                    'Machholz': 'Макхольц',
                    'Mechain': 'Мешен',
                    'SMM': 'SolarMax',
                    'Boattini': 'Боаттини',
                    'Bradfield': 'Брэдфилд',
                    'Mueller': 'Мюллер',
                    'Alcock': 'Алкок',
                    'Blathwayt': 'Блатуэйт',
                    'Borrelly': 'Борелли',
                    'Brorsen': 'Брорзен',
                    'Burnham': 'Бёрнхем',
                    'du Toit': 'Дю Туа',
                    'Gambart': 'Гамбар',
                    'Giacobini': 'Джакобини',
                    'Gibbs': 'Гиббс',
                    'Hill': 'Хилл',
                    'Honda': 'Хонда',
                    'IRAS': 'IRAS',
                    'Klinkerfues': 'Клинкерфус',
                    'Kohoutek': 'Когоутек',
                    'Lovas': 'Ловас',
                    'Mauvais': 'Мовэ',
                    'Mellish': 'Меллиш',
                    'Petersen': 'Петерсон',
                    'Siding Spring': 'Сайдинг-Спринг',
                    'Skjellerup': 'Скьеллеруп',
                    'Swift': 'Свифт',
                    'Yanaka': 'Янака',
                    'Brooks': 'Брукс',
                    'Galle': 'Галле',
                    'Skiff': 'Скифф',
                    'Wilson': 'Уилсон',
                    'Herschel': 'Гершель',
                    'Perrine': 'Перрайн',
                    'Kowalski': 'Ковальский',
                    'Garradd': 'Гаррэдд',
                    'Beshore': 'Бешор',
                    'Cardinal': 'Кардинал',
                    'Denning': 'Деннинг',
                    'Finsler': 'Финслер',
                    'Harrington': 'Харрингтон',
                    'Hartwig': 'Хартвиг',
                    'Holvorcem': 'Ольворсем',
                    'Humason': 'Хьюмасон',
                    'Hyakutake': 'Хякутакэ',
                    'Lagerkvist': 'Лагерквист',
                    'Larsen': 'Ларсен',
                    'Pajdusakova': 'Пайдушакова',
                    'Palomar': 'Паломарская обсерватория',
                    'Schaumasse': 'Шомасс',
                    'Schaeberle': 'Шеберле',
                    'Schwartz': 'Шварц',
                    'Ikeya': 'Икэя',
                    'Austin': 'Остин',
                    'de Vico': 'де Вико',
                    'Donati': 'Донати',
                    'Elenin': 'Еленин',
                    'Ferris': 'Феррис',
                    'Johnson': 'Джонсон',
                    'Metcalf': 'Меткалф',
                    'Montani': 'Монтани',
                    'Peltier': 'Пельтье',
                    'Respighi': 'Респиги',
                    'Tabur': 'Табур',
                    'Torres': 'Торрес',
                    'Wilk': 'Уилк',
                    'Bester': 'Бестер',
                    'Larson': 'Ларсон',
                    'Meier': 'Майер',
                    'Schweizer': 'Швейцер',
                    'Wirtanen': 'Виртанен',
                    'Bruhns': 'Брунс',
                    'Coggia': 'Коджа',
                    'Levy': 'Леви',
                    'La Sagra': 'Ла Сагра',
                    'Mrkos': 'Мркос',
                    'Skotti': 'Скотти',
                    'SWAN': 'SWAN',
                }
                if name in tr_name:
                    return '{} ({})'.format(code, tr_name[name])
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
