# -*- coding: UTF-8 -*-

"""
Convert separator-embedded context to Gettext context.

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
    "Convert separator-embedded context to Gettext context."
    ))

    p.add_param("sep", unicode, mandatory=True,
                metavar=_("@info sieve parameter value placeholder", "STRING"),
                desc=_("@info sieve parameter discription",
    "Separator between the context and the text in msgid field."
    ))


class Sieve (object):

    def __init__ (self, params):

        self.nconv = 0

        self.csep = unescape(params.sep)
        if not self.csep:
            raise SieveError(
                _("@info", "Context separator cannot be empty string."))


    def process (self, msg, cat):

        # Skip messages already having Gettext context.
        if msg.msgctxt or msg.msgctxt_previous:
            return

        pos = msg.msgid.find(self.csep)
        if pos >= 0:
            if msg.msgid.find(self.csep, pos + len(self.csep)) >= 0:
                # If more than one delimiter, probably not context.
                return
            ctxt = msg.msgid[:pos]
            text = msg.msgid[pos + len(self.csep):]
            if not ctxt or not text:
                # Something is strange, skip.
                return
            exmsgs = cat.select_by_key(ctxt, text, wobs=True)
            if exmsgs:
                exmsg = exmsgs[0]
                if not msg.obsolete and exmsg.obsolete:
                    cat.remove_on_sync(exmsg)
                elif msg.obsolete and not exmsg.obsolete:
                    cat.remove_on_sync(msg)
                    return
                else:
                    return
            msg.msgctxt = ctxt
            msg.msgid = text
            self.nconv += 1


    def finalize (self):

        if self.nconv > 0:
            msg = n_("@info:progress",
                     "Converted %(num)d separator-embedded context.",
                     "Converted %(num)d separator-embedded contexts.",
                     num=self.nconv)
            report("===== " + msg)

