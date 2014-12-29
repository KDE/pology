# -*- coding: UTF-8 -*

"""
Various specific translation checks.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

from pology import _


def check_keyword_list (strict=False):
    """
    Verify that the translated keyword list has proper syntax according
    to the type of keyword message [hook factory].

    The following types of keyword messages are currently detected:
      - With context "Keywords" (or starts with "Keywords|"),
        indicates .desktop keyword list.
      - With context "X-KDE-Keywords" (or starts with "X-KDE-Keywords|"),
        indicates KDE-specific .desktop keyword list.

    The C{strict} parameter determines whether the C{msgstr} is checked
    only if the C{msgid} itself is valid (C{False}), or regardless
    of the validity of C{msgid} (C{True}).

    The checks may limit the actual valid syntax for the list type,
    such that some valid corner cases are not allowed.
    This is done when respecting a corner case would result in
    not catching frequently observed semantic errors.

    @param strict: whether to require valid C{msgstr} even if C{msgid} is not
    @type strict: bool

    @return: type V3C hook
    @rtype: C{(msgstr, msg, cat) -> spans}
    """

    def checkf (msgstr, msg, cat):

        if not strict:
            orig_spans = _check_keyword_list_text(msg.msgid, msg, cat)
            do_check = (len(orig_spans) == 0)
        else:
            do_check = True

        if do_check:
            spans = _check_keyword_list_text(msgstr, msg, cat)
        else:
            spans = []

        return spans

    return checkf


def _check_keyword_list_text (text, msg, cat):

    spans = []

    ctxt = msg.msgctxt or ""

    if ctxt == "Keywords" or ctxt.startswith("Keywords|"):
        pos = text.find(",")
        if pos >= 0:
            spans.append((pos, pos + 1,
                          _("@info",
                            "Keyword list with context '%(ident)s' "
                            "must not contain commas.",
                            ident="Keywords")))
        if not text.endswith(";"):
            spans.append((len(text), len(text),
                          _("@info",
                            "Keyword list with context '%(ident)s' "
                            "must end in semi-colon.",
                            ident="Keywords")))

    elif ctxt == "X-KDE-Keywords" or ctxt.startswith("X-KDE-Keywords|"):
        pos = text.find(";")
        if pos >= 0:
            spans.append((pos, pos + 1,
                          _("@info",
                            "Keyword list with context '%(ident)s' "
                            "must not contain semi-colons.",
                            ident="X-KDE-Keywords")))

    return spans


