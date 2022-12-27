# -*- coding: utf-8 -*-

"""
@author: Javier Viñal <fjvinal@gmail.com>
@license: GPLv3"""

import re

def setup_sieve (p):

    p.set_desc("Replace normal space by non-breaking space where needed.")


class Sieve (object):
    """Replace normal space by unbreakable space when needed"""

    def __init__ (self, params):

        self.nmatch = 0

        self.percent=re.compile("( %)(?=$| |\.|,)")

    def process (self, msg, cat):

        oldcount=msg.modcount

        for i in range(len(msg.msgstr)):
            msg.msgstr[i]=self.setUbsp(msg.msgstr[i])

        if oldcount<msg.modcount:
            self.nmatch+=1

    def finalize (self):

        if self.nmatch > 0:
            print "Total messages changed: %d" % (self.nmatch,)

    def setUbsp(self, text):
        """Set correctly unbreakable spaces"""
        text=text.replace(u"\xa0", u" ")
        text=text.replace(u"&nbsp;:", u"\xc2\xa0:")
        text=text.replace(u" :", u"\xa0:")
        text=text.replace(u" ;", u"\xa0;")
        text=text.replace(u" ?", u"\xa0?")
        text=text.replace(u" !", u"\xa0!")
        text=text.replace(u"« ", u"«\xa0")
        text=text.replace(u" »", u"\xa0»")
        text=text.replace(u" / ", u"\xa0/ ")
        text=self.percent.sub(u"\xa0%", text)
        
        return text
