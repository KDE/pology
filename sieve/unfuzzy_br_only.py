# -*- coding: UTF-8 -*-

import re

_open_br_rx = re.compile(r"<\s*br\s*>", re.U)
_close_br_rx = re.compile(r"<\s*/\s*br\s*>", re.U)
_openclose_br_rx = re.compile(r"<\s*br\s*/\s*>", re.U)

def _norm_br (text):
    """Replace any <br> with <br/> in the text."""
    text = _open_br_rx.sub("<br/>", text)
    text = _openclose_br_rx.sub("<br/>", text) # to normalize <br />, etc.
    return text

class Sieve (object):
    """Unfuzzy if the only differences are in-place closed <br> tags (<br/>).
    Unconditionally in-place close <br> tags in the msgstr's.
    """
    def __init__ (self, options, global_options):
        self.nunfuzz = 0
        self.nmodbr = 0
        # Indicators to the caller:
        # - monitor to avoid unnecessary reformatting when unfuzzied
        self.caller_monitored = True

    def process (self, msg, cat):
        # Skip checks if the msgid contains closing </br>, too odd.
        if _close_br_rx.search(msg.msgid): return

        # Unfuzzy message if closed <br/> are the only difference.
        if msg.fuzzy \
        and msg.msgctxt_previous == msg.msgctxt \
        and _open_br_rx.search(msg.msgid_previous):
            # Normalize <br> tags for checking.
            msgid_previous_n = _norm_br(msg.msgid_previous)
            msgid_plural_previous_n = _norm_br(msg.msgid_plural_previous)
            msgid_n = _norm_br(msg.msgid)
            msgid_plural_n = _norm_br(msg.msgid_plural)

            if msgid_n == msgid_previous_n \
            and msgid_plural_n == msgid_plural_previous_n:
                msg.fuzzy = False
                self.nunfuzz += 1
                msg.modcount = 1 # in case of non-monitored messages

        # Replace any <br> with <br/> in the msgstr.
        if not msg.obsolete:
            for i in range(len(msg.msgstr)):
                if _open_br_rx.search(msg.msgstr[i]):
                    msg.msgstr[i] = _open_br_rx.sub("<br/>", msg.msgstr[i])
                    self.nmodbr += 1
                    msg.modcount = 1 # in case of non-monitored messages

    def finalize (self):
        if self.nunfuzz > 0:
            print "Total unfuzzied due to closed <br> only: %d" % self.nunfuzz
        if self.nmodbr > 0:
            print "Total modified by closing <br>: %d" % self.nmodbr
