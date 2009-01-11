# -*- coding: UTF-8 -*-

"""
Convert OpenOffice embedded context to Gettext context.

By default, the sieve will not issue request to sync the catalog files,
which means that the files will not be modified unless another sieve in
the chain requests sync. In this way, the sieve can be used to normalize
contexts for other non-syncing sieves, like L{stats<sieve.stats>} or
L{find-messages<sieve.find_messages>}. The normal sync-on-modify behavior
can be recovered by C{sync} option.

Sieve options:
  - C{sync}: do request syncing to disk of modified catalogs

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

from pology.misc.msgreport import warning_on_msg


class Sieve (object):

    def __init__ (self, options):

        self.nconv = 0

        # Sync catalogs?
        self.sync = False
        if "sync" in options:
            self.sync = True
            options.accept("sync")

        # Indicators to the caller.
        if not self.sync:
            # No monitor or syncing unless requested explicitly.
            self.caller_sync = False
            self.caller_monitored = False


    def process (self, msg, cat):

        # Skip messages already having Gettext context.
        if msg.msgctxt or msg.msgctxt_previous:
            return

        msrc = (cat.filename, msg.refline, msg.refentry)

        chead = "_:"
        ctail = "\n"

        if msg.msgid.startswith(chead):
            pos = msg.msgid.find(ctail)
            if pos < 0:
                warning_on_msg("malformed embedded context", msg, cat)
                return

            ctxt = msg.msgid[len(chead):pos]
            text = msg.msgid[pos+len(ctail):]

            if not ctxt or not text:
                warning_on_msg("empty context or text", msg, cat)
                return

            msg.msgctxt = ctxt
            msg.msgid = text

            self.nconv += 1


    def finalize (self):

        if self.nconv > 0:
            print "Total contexts converted: %d" % (self.nconv,)

