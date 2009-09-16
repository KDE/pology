# -*- coding: UTF-8 -*-

"""
Resolve alternative directives in translation.

See description of L{resolve_alternatives()<misc.resolve.resolve_alternatives>}
function for information on format and behavior of alternative directives.

Sieve parameters:
  - C{alt:N,Mt}: index (1-based) of alternative to take from each derictive,
        and total number of alternatives per directive (e.g. C{1,2t})

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""


import sys
import os
import re

from pology.misc.resolve import resolve_alternatives
from pology.misc.report import report
from pology.sieve import SieveError


def setup_sieve (p):

    p.set_desc(
    "Resolve alternative directives in translation."
    )

    p.add_param("alt", unicode, mandatory=True,
                metavar="N,Mt",
                desc=
    "N is index (1-based) of alternative to take from each directive, "
    "and M the number of alternatives per directive (e.g. '1,2t')."
    )


class Sieve (object):

    def __init__ (self, params):

        for spec in params.alt.split(","):
            if spec.endswith("t"):
                self.total = int(spec[:-1])
            else:
                self.select = int(spec)
        if not hasattr(self, "total"):
            raise SieveError("Number of alternatives per directive not given.")
        if not hasattr(self, "select"):
            raise SieveError("Index of selected alternative not given.")
        if self.total < 1:
            raise SieveError("Invalid number of alternatives: %d" % self.total)
        if self.select < 1 or self.select > self.total:
            raise SieveError("Selected alternative out of range: %d"
                             % self.select)

        self.nresolved = 0
        self.nmalformed = 0


    def process (self, msg, cat):

        for i in range(len(msg.msgstr)):
            msg.msgstr[i], nresolved, valid = \
                resolve_alternatives(msg.msgstr[i], self.select, self.total,
                                     srcname=cat.filename)
            if valid:
                self.nresolved += nresolved
            else:
                self.nmalformed += 1


    def finalize (self):

        if self.nresolved > 0:
            report("Total resolved alternatives: %d" % self.nresolved)
        if self.nmalformed > 0:
            report("Total malformed alternatives: %d" % self.nmalformed)

