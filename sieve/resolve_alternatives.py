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


import os
import re
import sys

from pology import _, n_
from pology.misc.msgreport import warning_on_msg
from pology.misc.report import report
from pology.misc.resolve import resolve_alternatives
from pology.sieve import SieveError


def setup_sieve (p):

    p.set_desc(_("@info sieve discription",
    "Resolve alternative directives in translation."
    ))

    p.add_param("alt", unicode, mandatory=True,
                metavar=_("@info sieve parameter value placeholder", "N,Mt"),
                desc=_("@info sieve parameter discription",
    "N is index (1-based) of the alternative to take from each directive, "
    "and M the number of alternatives per directive. Example:\n"
    "\n"
    "alt:1,2t"
    ))


class Sieve (object):

    def __init__ (self, params):

        self.total = None
        self.select = None
        try:
            for spec in params.alt.split(","):
                if spec.endswith("t"):
                    self.total = int(spec[:-1])
                else:
                    self.select = int(spec)
        except:
            raise SieveError(
                _("@info",
                  "Malformed specification for "
                  "resolution of alternatives '%(spec)s'.",
                  spec=params.alt))
        if self.total is None:
            raise SieveError(
                _("@info",
                  "Number of alternatives per directive not given."))
        if self.select is None:
            raise SieveError(
                _("@info",
                  "Index of selected alternative not given."))
        if self.total < 1:
            raise SieveError(
                _("@info",
                  "Number of alternatives specified as %(num)d, "
                  "but must be greater than 1.",
                  num=self.total))
        if self.select < 1 or self.select > self.total:
            raise SieveError(
                _("@info",
                  "Selected alternative no. %(ord)d is out of range.",
                  ord=self.select))

        self.nresolved = 0


    def process (self, msg, cat):

        for i in range(len(msg.msgstr)):
            msg.msgstr[i], nresolved, valid = \
                resolve_alternatives(msg.msgstr[i], self.select, self.total,
                                     srcname=cat.filename)
            if valid:
                self.nresolved += nresolved
            else:
                warning_on_msg(_("@info",
                                 "Invalid alternatives directive "
                                 "in translation."), msg, cat)


    def finalize (self):

        if self.nresolved > 0:
            msg = n_("@info:progress",
                     "Resolved %(num)d alternative in translation.",
                     "Resolved %(num)d alternatives in translation.",
                     num=self.nresolved)
            report("===== " + msg)

