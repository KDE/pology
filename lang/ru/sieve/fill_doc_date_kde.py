# -*- coding: UTF-8 -*-

"""
Reformat documentation update date for Russian KDE Team.

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
    "Reformat documentation update date for Russian KDE Team."
    ))


class Sieve (object):

    def __init__ (self, params):
        # Some dates have non-standard format, here is the workaround for them:
        self.pretranslated = {
            'April 8, 2003': '8 апреля 2003 г.',
            'April 7, 2003': '7 апреля 2003 г.',
            '28/08/2009': '28 августа 2009 г.',
            '22/05/2009': '22 мая 2009 г.',
            '07 January 2005': '7 января 2005 г.',
            'March 7, 2003': '7 марта 2003 г.',
            'March 8, 2003': '8 марта 2003 г.',
            'April 06, 2003': '6 апреля 2003 г.',
            'April 07, 2003': '7 апреля 2003 г.',
            'Month Daynumber, 4-Digit-Year': '2 февраля 2005 г.',
            'April 2018': 'апрель 2018 г.',
            '04/02/2007': '4 февраля 2007 г.',
        }
    
        # Other dates should have the following format: (yyyy-mm-dd)
        self.date_re = re.compile(r"^[0-9][0-9][0-9][0-9]\-[0-9][0-9]\-[0-9][0-9]$")

    def format_date (self, date_en):
        if date_en in self.pretranslated:
            return self.pretranslated[date_en]
        elif self.date_re.match(date_en):
            date_result = os.popen("date '+%-d m%mm %Y' -d " + date_en).readlines()[0].decode('utf-8').rstrip() + ' г.'

            # Translate name of months into Russian
            return date_result.\
                replace('m01m', 'января').\
                replace('m02m', 'февраля').\
                replace('m03m', 'марта').\
                replace('m04m', 'апреля').\
                replace('m05m', 'мая').\
                replace('m06m', 'июня').\
                replace('m07m', 'июля').\
                replace('m08m', 'августа').\
                replace('m09m', 'сентября').\
                replace('m10m', 'октября').\
                replace('m11m', 'ноября').\
                replace('m12m', 'декабря')
        else:
            print("\nThis is not a valid date: %s\n" % date_en)

    def process (self, msg, cat):
        # Detect documentation update date message
        if ("\n".join(msg.auto_comment) == "Tag: date"):
            new_msgstr = self.format_date(msg.msgid)
            if (msg.fuzzy or msg.msgstr[0] != new_msgstr):
                msg.msgstr[0] = new_msgstr
                msg.unfuzzy()
                report_msg_content(msg, cat)

    def finalize (self):
        ""

