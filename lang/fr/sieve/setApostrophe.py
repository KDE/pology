# -*- coding: UTF-8 -*-

"""
Replace apostrophe (’) with the ' according to the French rules.

Documented in C{doc/user/sieving.docbook}.

@author: Johnny Jazeix <jazeix@gmail.com>
@license: GPLv3"""

import re

from pology import _, n_
from pology.report import report


def setup_sieve (p):

    p.set_desc(_("@info sieve description",
                 "Replace apostrophe (’) with the ' symbol."))


class Sieve (object):
    """Replace ’ by ' when needed"""

    def __init__ (self, params):
        self.nmatch = 0

    def process (self, msg, cat):

        oldcount=msg.modcount

        for i in range(len(msg.msgstr)):
            msg.msgstr[i]=self.setApostrophe(msg.msgstr[i])

        if oldcount<msg.modcount:
            self.nmatch+=1

    def finalize (self):

        if self.nmatch > 0:
            report(n_("@info",
                      "Apostrophes updated in %(num)d message.",
                      "Apostrophes updated in %(num)d messages.",
                      num=self.nmatch))

    def setApostrophe(self, text):
        """Set correctly apostrophes"""
        text=text.replace("’", "'")
        
        return text
