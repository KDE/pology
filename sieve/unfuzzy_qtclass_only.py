# -*- coding: UTF-8 -*-

"""
Unfuzzy messages fuzzied only due to changed Qt class name.

Documented in C{doc/user/sieving.docbook}.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import re

from pology import _, n_
from pology.report import report


def setup_sieve (p):

    p.set_desc(_("@info sieve discription",
    "Unfuzzy messages which got fuzzy only due to changed Qt class name."
    "\n\n"
    "Possible only if catalogs were merged with --previous option.",
    ))


_strip_rx = re.compile(r"^[a-z][\w:]*\|(.*)", re.U|re.I)

# Strip the Qt class.
def _stripped (ctxt):
    m = _strip_rx.search(ctxt)
    stripped = m.group(1) if m else ctxt
    return stripped


class Sieve (object):

    def __init__ (self, params):

        self.nmatch = 0


    def process (self, msg, cat):

        if (    msg.fuzzy
            and msg.msgid == msg.msgid_previous
            and msg.msgid_plural == msg.msgid_plural_previous
            and (   _stripped(msg.msgctxt or u"")
                 == _stripped(msg.msgctxt_previous or u""))
        ):
            msg.unfuzzy()
            self.nmatch += 1


    def finalize (self):

        if self.nmatch > 0:
            msg = n_("@info:progress",
                     "Unfuzzied %(num)d message fuzzy due to "
                     "difference in Qt class context only.",
                     "Unfuzzied %(num)d messages fuzzy due to "
                     "difference in Qt class context only.",
                     num=self.nmatch)
            report("===== " + msg)


