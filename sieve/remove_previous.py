# -*- coding: UTF-8 -*-

"""
Remove previous fields (C{#|...}) from messages.

By default, previous fields are removed only from messages not having
the C{fuzzy} flag. This can be changed by giving the C{all} parameter.

Sieve parameters:
  - C{all}: remove previous fields from all messages

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

from pology import _, n_
from pology.misc.report import report


def setup_sieve (p):

    p.set_desc(_("@info sieve discription",
    "Remove previous fields (#| ...) from messages."
    ))

    p.add_param("all", bool,
                desc=_("@info sieve parameter discription",
    "Remove previous fields from all messages "
    "(by default previous fields are not removed from fuzzy messages)."
    ))


class Sieve (object):

    def __init__ (self, params):

        self.p = params

        self.ncleared = 0


    def process (self, msg, cat):

        if self.p.all or "fuzzy" not in msg.flag: # also for obsolete
            modcount = msg.modcount
            msg.msgctxt_previous = None
            msg.msgid_previous = None
            msg.msgid_plural_previous = None
            if modcount < msg.modcount:
                self.ncleared += 1


    def finalize (self):

        if self.ncleared > 0:
            msg = n_("@info:progress",
                     "Cleared previous fields from %(num)d message.",
                     "Cleared previous fields from %(num)d messages.",
                     num=self.ncleared)
            report("===== %s" % msg)

