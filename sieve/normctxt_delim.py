# -*- coding: UTF-8 -*-

"""
Convert delimitor-embedded context to Gettext context.

Documented in C{doc/user/sieving.docbook}.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

from pology import _, n_
from pology.escape import unescape_c as unescape
from pology.msgreport import warning_on_msg
from pology.report import report
from pology.sieve import SieveError


def setup_sieve (p):

    p.set_desc(_("@info sieve discription",
    "Convert delimiter-embedded context to Gettext context."
    ))

    p.add_param("head", unicode, mandatory=True,
                metavar=_("@info sieve parameter value placeholder", "STRING"),
                desc=_("@info sieve parameter discription",
    "Start of the msgid field which indicates that the context follows."
    ))
    p.add_param("tail", unicode, mandatory=True,
                metavar=_("@info sieve parameter value placeholder", "STRING"),
                desc=_("@info sieve parameter discription",
    "End of context in msgid field, after which the text follows."
    ))


class Sieve (object):

    def __init__ (self, params):

        self.nconv = 0

        self.chead = unescape(params.head)
        if not self.chead:
            raise SieveError(
                _("@info", "Context head cannot be empty string."))
        self.ctail = unescape(params.tail)
        if not self.ctail:
            raise SieveError(
                _("@info", "Context tail cannot be empty string."))


    def process (self, msg, cat):

        # Skip messages already having Gettext context.
        if msg.msgctxt or msg.msgctxt_previous:
            return

        msrc = (cat.filename, msg.refline, msg.refentry)

        if msg.msgid.startswith(self.chead):
            pos = msg.msgid.find(self.ctail)
            if pos < 0:
                warning_on_msg(_("@info",
                                 "Malformed embedded context."), msg, cat)
                return

            ctxt = msg.msgid[len(self.chead):pos]
            text = msg.msgid[pos + len(self.ctail):]

            if not ctxt or not text:
                warning_on_msg(_("@info", "Empty context or text."), msg, cat)
                return

            msg.msgctxt = ctxt
            msg.msgid = text

            self.nconv += 1


    def finalize (self):

        if self.nconv > 0:
            msg = n_("@info:progress",
                     "Converted %(num)d delimiter-embedded context.",
                     "Converted %(num)d delimiter-embedded contexts.",
                     num=self.nconv)
            report("===== " + msg)

