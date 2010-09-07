# -*- coding: UTF-8 -*-

"""
Unfuzzy messages fuzzied only due to some tags being closed in-place
(like C{<br>} to C{<br/>}).

Documented in C{doc/user/sieving.docbook}.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import re

from pology import _, n_
from pology.report import report


def setup_sieve (p):

    p.set_desc(_("@info sieve discription",
    "Unfuzzy messages fuzzied only due to some tags being closed in-place "
    "(like '%(tag1)s' to '%(tag2)s')."
    "\n\n"
    "Possible only if catalogs were merged with --previous option.",
    tag1="<br>", tag2="<br/>"))


_tags_inpl = r"(br|hr|nl)"
_open_inpl_rx = re.compile(r"<\s*" + _tags_inpl + r"\s*>", re.U)
_close_inpl_rx = re.compile(r"<\s*/\s*" + _tags_inpl + r"\s*>", re.U)
_openclose_inpl_rx = re.compile(r"<\s*" + _tags_inpl + r"\s*/\s*>", re.U)

# Replace any needed <...> with <.../> in the text.
def _norm_inpl (text):
    text = _open_inpl_rx.sub(r"<\1/>", text)
    text = _openclose_inpl_rx.sub(r"<\1/>", text) # to normalize <br />, etc.
    return text


class Sieve (object):

    def __init__ (self, params):

        self.caller_monitored = True

        self.nunfuzz = 0
        self.nmodinpl = 0


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
                msg.unfuzzy()
                self.nunfuzz += 1

        # Replace any <...> with <.../> in the msgstr.
        for i in range(len(msg.msgstr)):
            if _open_inpl_rx.search(msg.msgstr[i]):
                msg.msgstr[i] = _open_inpl_rx.sub(r"<\1/>", msg.msgstr[i])
                self.nmodinpl += 1


    def finalize (self):

        if self.nunfuzz > 0:
            msg = n_("@info:progress",
                     "Unfuzzied %(num)d message due to "
                     "closing tags in-place.",
                     "Unfuzzied %(num)d messages due to "
                     "closing tags in-place.",
                     num=self.nunfuzz)
            report("===== " + msg)
        if self.nmodinpl > 0:
            msg = n_("@info:progress",
                     "Modified %(num)d translations by "
                     "closing tags in-place.",
                     "Modified %(num)d translations by "
                     "closing tags in-place.",
                     num=self.nmodinpl)
            report("===== " + msg)

