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

from pology.misc.report import report


def setup_sieve (p):

    p.set_desc(
    "Remove previous fields (#| ...) from messages."
    )

    p.add_param("all", bool,
                desc=
    "Remove previous fields from all messages "
    "(by default fields are not removed from messages with fuzzy flag)."
    )


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
            report("Total cleared of previous fields: %d" % self.ncleared)

