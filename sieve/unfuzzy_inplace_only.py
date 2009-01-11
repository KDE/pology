# -*- coding: UTF-8 -*-

import re

_tags_inpl = r"(br|hr|nl)"
_open_inpl_rx = re.compile(r"<\s*" + _tags_inpl + r"\s*>", re.U)
_close_inpl_rx = re.compile(r"<\s*/\s*" + _tags_inpl + r"\s*>", re.U)
_openclose_inpl_rx = re.compile(r"<\s*" + _tags_inpl + r"\s*/\s*>", re.U)

def _norm_inpl (text):
    """Replace any needed <...> with <.../> in the text."""
    text = _open_inpl_rx.sub(r"<\1/>", text)
    text = _openclose_inpl_rx.sub(r"<\1/>", text) # to normalize <br />, etc.
    return text


class Sieve (object):
    """
    Unfuzzy if the only differences are in-place closed tags (<br/>, etc.)
    Unconditionally in-place close such tags in the msgstr's.
    """

    def __init__ (self, options):

        self.nunfuzz = 0
        self.nmodinpl = 0
        # Indicators to the caller:
        # - monitor to avoid unnecessary reformatting when unfuzzied
        self.caller_monitored = True


    def process (self, msg, cat):

        # Skip checks if the msgid contains closing </...>, too odd.
        if _close_inpl_rx.search(msg.msgid):
            return

        # Unfuzzy message if closed <.../> are the only difference.
        if (    msg.fuzzy
            and msg.msgid_previous is not None
            and msg.msgctxt_previous == msg.msgctxt
            and _open_inpl_rx.search(msg.msgid_previous)
        ):
            # Normalize <...> tags for checking.
            msgid_previous_n = _norm_inpl(msg.msgid_previous)
            msgid_plural_previous_n = _norm_inpl(msg.msgid_plural_previous or u"")
            msgid_n = _norm_inpl(msg.msgid)
            msgid_plural_n = _norm_inpl(msg.msgid_plural or u"")

            if (    msgid_n == msgid_previous_n
                and msgid_plural_n == msgid_plural_previous_n
            ):
                msg.fuzzy = False
                self.nunfuzz += 1
                msg.modcount = 1 # in case of non-monitored messages

        # Replace any <...> with <.../> in the msgstr.
        if not msg.obsolete:
            for i in range(len(msg.msgstr)):
                if _open_inpl_rx.search(msg.msgstr[i]):
                    msg.msgstr[i] = _open_inpl_rx.sub(r"<\1/>", msg.msgstr[i])
                    self.nmodinpl += 1
                    msg.modcount = 1 # in case of non-monitored messages


    def finalize (self):

        if self.nunfuzz > 0:
            print "Total unfuzzied due to closing in-place: %d" % self.nunfuzz
        if self.nmodinpl > 0:
            print "Total modified by in-place closing: %d" % self.nmodinpl

