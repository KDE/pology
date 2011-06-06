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
            u'April 8, 2003': u'8 апреля 2003 г.',
            u'Jun 7, 2005': u'7 июня 2005 г.',
            u'2007-31-03': u'31 марта 2007 г.',
            u'June 12, 2005': u'12 июня 2005 г.',
            u'2009-11-8': u'8 ноября 2009 г.',
            u'May 25, 2005': u'25 мая 2005 г.',
            u'28/12/2007': u'28 декабря 2007 г.',
            u'February 1st, 2005': u'1 февраля 2005 г.',
            u'June 07, 2005': u'7 июня 2005 г.',
            u'April 7, 2003': u'7 апреля 2003 г.',
        }	
    
        # Other dates should have the following format: (yyyy-mm-dd)
        self.date_re = re.compile("^[0-9][0-9][0-9][0-9]\-[0-9][0-9]\-[0-9][0-9]$")

    def format_date (self, date_en):
        if self.pretranslated.has_key(date_en):
            return self.pretranslated[date_en]
        elif self.date_re.match(date_en):
            date_result = os.popen("date '+%-d m%mm %Y' -d " + date_en).readlines()[0].decode('utf-8').rstrip() + u' г.'

            # Translate name of months into Russian
	    return date_result.\
                replace('m01m', u'января').\
                replace('m02m', u'февраля').\
                replace('m03m', u'марта').\
                replace('m04m', u'апреля').\
                replace('m05m', u'мая').\
                replace('m06m', u'июня').\
                replace('m07m', u'июля').\
                replace('m08m', u'августа').\
                replace('m09m', u'сентября').\
                replace('m10m', u'октября').\
                replace('m11m', u'ноября').\
                replace('m12m', u'декабря')
        else:
            print "This is not a valid date: " + date_en

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

