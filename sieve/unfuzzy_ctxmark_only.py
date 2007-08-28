# -*- coding: UTF-8 -*-

import re

_strip_rx = re.compile(r"^\s*@[^\s]+(.*)", re.U)
_norm_rx = re.compile(r"[^\w]", re.U)
def _stripped (ctxt):
    """Strip the KUIT context marker, and normalize rest of the string."""
    m = _strip_rx.search(ctxt)
    if m: stripped = m.group(1)
    else: stripped = ctxt
    return _norm_rx.sub("", stripped.lower())

class Sieve (object):
    """Unfuzzy when only a KUIT context mark difference to previous."""

    def __init__ (self, options, global_options):
        self.nmatch = 0
        # Indicators to the caller:
        # - monitor to avoid unnecessary reformatting when unfuzzied
        self.caller_monitored = True

    def process (self, msg, cat):
        if msg.fuzzy \
        and msg.msgid == msg.msgid_previous \
        and msg.msgid_plural == msg.msgid_plural_previous \
        and _stripped(msg.msgctxt) == _stripped(msg.msgctxt_previous):
            msg.fuzzy = False
            self.nmatch += 1
            msg.modcount = 1 # in case of non-monitored messages

    def finalize (self):
        if self.nmatch > 0:
            print "Total unfuzzied due to context marker: %d" % (self.nmatch,)
