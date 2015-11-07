# -*- coding: UTF-8 -*-

"""
Reformat documentation update date for Catalan KDE Team.

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
    "Reformat documentation update date for Catalan KDE Team."
    ))


class Sieve (object):

    def __init__ (self, params):
        # Some dates have non-standard format, here is the workaround for them:
        self.pretranslated = {
            u'April 8, 2003': u'8 d\'abril de 2003',
            u'Jun 7, 2005': u'7 de juny de 2005',
            u'2007-31-03': u'31 de març de 2007',
            u'June 12, 2005': u'12 de juny de 2005',
            u'2009-11-8': u'08 de novembre de 2009',
            u'May 25, 2005': u'25 de maig de 2005',
            u'28/12/2007': u'28 de desembre de 2007',
            u'28/08/2009': u'28 d\'agost de 2009',
            u'February 1st, 2005': u'1 de febrer de 2005',
            u'June 07, 2005': u'7 de juny de 2005',
            u'May 22, 2011': u'22 de maig de 2011',
            u'August 3 2012': u'22 d\'agost de 2012',
            u'April 7, 2003': u'7 d\'abril de 2003',
        }	
    
        # Other dates should have the following format: (yyyy-mm-dd)
        self.date_re = re.compile("^[0-9][0-9][0-9][0-9]\-[0-9][0-9]\-[0-9][0-9]$")

    def format_date (self, date_en):
        if self.pretranslated.has_key(date_en):
            return self.pretranslated[date_en]
        elif self.date_re.match(date_en):
            date_result = os.popen("date '+%-d m%mm %Y' -d " + date_en).readlines()[0].decode('utf-8').rstrip() + u''

            # Translate name of months into Catalan
	    return date_result.\
                replace('m01m', u'de gener de').\
                replace('m02m', u'de febrer de').\
                replace('m03m', u'de març de').\
                replace('m04m', u'd\'abril de').\
                replace('m05m', u'de maig de').\
                replace('m06m', u'de juny de').\
                replace('m07m', u'de juliol de').\
                replace('m08m', u'd\'agost de').\
                replace('m09m', u'de setembre de').\
                replace('m10m', u'd\'octubre de').\
                replace('m11m', u'de novembre de').\
                replace('m12m', u'de desembre de')
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

