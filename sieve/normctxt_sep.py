# -*- coding: UTF-8 -*-

"""
Convert separator-embedded context to Gettext context.

Context is embedded into C{msgid} field, as the initial part of the field
separated from the message text by a predefined substring.
For example, in::

    msgid "this-is-context|This is original text"
    msgstr "This is translated text"

the separator string is the pipe character (C{|}).

Sieve options:
  - C{sep} (mandatory): string used as context separator
  - C{nosync}: do not request to sync modified catalogs to disk

Parameter C{nosync} tells the sieve not to issue request to sync the catalogs,
which means that the files on disk will not be modified unless another sieve in
the chain requests syncing. In this way, the sieve can be used to normalize
contexts for other non-syncing sieves, like L{stats<sieve.stats>} or
L{find-messages<sieve.find_messages>}.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

from pology.sieve import SieveError
from pology.misc.msgreport import warning_on_msg
from pology.misc.escape import unescape


def setup_sieve (p):

    p.set_desc(
    "Convert separator-embedded context to Gettext context."
    )

    p.add_param("sep", unicode, mandatory=True,
                metavar="STRING",
                desc=
    "Separator between the context and the text in msgid field."
    )
    p.add_param("nosync", bool, defval=False,
                desc=
    "Do not request modified catalog to be synced to disk."
    )


class Sieve (object):

    def __init__ (self, params):

        self.nconv = 0

        self.csep = unescape(params.sep)
        if not self.csep:
            raise SieveError("context separator cannot be empty string")

        if params.nosync:
            self.caller_sync = False
            self.caller_monitored = False


    def process (self, msg, cat):

        # Skip messages already having Gettext context.
        if msg.msgctxt or msg.msgctxt_previous:
            return

        pos = msg.msgid.find(self.csep)
        if pos >= 0:
            if msg.msgid.find(self.csep, pos + 1) >= 0:
                # If more than one delimiter, probably not context.
                return
            ctxt = msg.msgid[:pos]
            text = msg.msgid[pos + 1:]
            if not ctxt or not text:
                # Something is strange, skip.
                return
            msg.msgctxt = ctxt
            msg.msgid = text
            self.nconv += 1


    def finalize (self):

        if self.nconv > 0:
            print "Total contexts converted: %d" % (self.nconv,)

