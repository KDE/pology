# -*- coding: UTF-8 -*-

"""
Check validity of special messages in KDE4 POs.

The items checked are:

  - Qt datetime format messages. A message is considered to be in this format
    if it contains "qtdt-format" in the context, or among flags.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import re
from pology.misc.report import report
from pology.misc.msgreport import report_on_msg

ts_fence = "|/|"


# --------------------------------------
# Qt datetime format messages.

_qtdt_flag = "qtdt-format"

_qtdt_clean_rx = re.compile(r"'.*?'")
_qtdt_split_rx = re.compile(r"\W+", re.U)

def _qtdt_parse (text):

    text = _qtdt_clean_rx.sub("", text)
    fields = [x for x in _qtdt_split_rx.split(text) if x]
    return fields


def _qtdt_fjoin (fields):

    lst = list(fields)
    lst.sort()
    return ", ".join(lst)


# Worker for check_qtdt* hooks.
def _check_qtdt_w (msgstr, msg, cat):

    # Check needed when used as summit hook.
    if (   (_qtdt_flag not in (msg.msgctxt or u"").lower())
       and (_qtdt_flag not in msg.flag)
    ):
        return

    # Get format fields from the msgid.
    msgid_fmts = _qtdt_parse(msg.msgid)

    # Expect the same format fields in msgstr.
    msgstr_fmts = _qtdt_parse(msgstr)
    spans = []
    if set(msgid_fmts) != set(msgstr_fmts):
        errmsg = ("Qt date-format mismatch, "
                  "msgid has fields (%s) while msgstr has (%s)"
                  % (_qtdt_fjoin(msgid_fmts), _qtdt_fjoin(msgstr_fmts)))
        spans.append((0, 0, errmsg))

    return spans


# Pass-through test hook.
def check_qtdt (msgstr, msg, cat):

    spans = _check_qtdt_w(msgstr, msg, cat)
    if spans:
        report_on_msg(spans[0][-1], msg, cat)
        return False
    else:
        return True


# Span-reporting test hook.
def check_qtdt_sp (msgstr, msg, cat):

    return _check_qtdt_w(msgstr, msg, cat)


# --------------------------------------

class Sieve (object):

    def __init__ (self, options):

        self.nbad = 0

        # Indicators to the caller:
        self.caller_sync = False # no need to sync catalogs to the caller
        self.caller_monitored = False # no need for monitored messages


    def process (self, msg, cat):

        # Check only translated messages.
        if not msg.translated:
            return

        for msgstr in msg.msgstr:

            # Split into ordinary and scripted part, if any.
            lst = msgstr.split(ts_fence, 1)
            msgstr = lst[0]
            msgscript = None
            if len(lst) == 2:
                msgscript = lst[1]

            # Check Qt datetime format.
            spans = check_qtdt_sp(cat, msg, msgstr)
            if spans:
                self.nbad += 1
                report_on_msg(spans[0][-1], msg, cat)


    def finalize (self):

        if self.nbad > 0:
            report("Total invalid translations of special messages: %d"
                   % self.nbad)

