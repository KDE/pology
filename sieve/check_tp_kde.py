# -*- coding: UTF-8 -*-

"""
Check validity of messages in catalogs within KDE Translation Project.

KDE Translation Project contains a great number of PO catalogs extracted
from various types of sources.
This results in that for each message, there are things that the translation
can, must or must not contain, for the translation to be technically valid.
When run over catalogs within KDE TP,
this sieve will first try to determine the type of each message
and then apply appropriate technical checks to it.
Message type is determined based on catalog location, catalog header,
message flags and contexts; even a particular message in a particular catalog
may be specifically checked, for some very special library code messages.

"Technical" issues are those which should be fixed regardless of
the language and style of translation, because they can lead to loss
of functionality, information or presentation to the user.
For example, a technical issue would be badly paired XML tags in translation,
when in the original they were well paired;
a non-technical issue (and thus not checked) would be when the original ends
with a certain punctuation, but translation does not -- whether such details
are errors or not, depends on the target language and translation style.

For the sieve to function properly, it needs to detect the project
subdirectory of each catalog up to topmost division within the branch,
e.g. C{messages/kdebase} or C{docmessages/kdegames}.
This means that the local working copy of the translation files needs
to follow the repository layout up to this point,
e.g. C{kde-trunk-ui/kdebase} and C{kde-trunk-doc/kdegames}
would not be valid local paths.

Sieve parameters:
  - C{strict}: require translation to be valid even if original is not
  - C{checks}: select only some checks to be applied, instead of all
  - C{lokalize}: open catalogs at problematic messages in Lokalize

Sometimes the original text itself may not be valid against a certain check.
If this is the case, by default translation is not expected to be valid either,
so the check is skipped.
This behavior can be canceled by issuing the C{strict} sieve parameter,
when the translation is reported problematic even if the original is such.
If C{strict} is used, some checks can be ignored on a particular, irreparable
through translation only message, by adding to it an appropriate
L{sieve flag<sieve.parse_sieve_flags>}.

To apply only one or a few, instead of all the checks, parameter C{check}
may be used.
It takes comma-separated list of check keywords, which are provided in
the list of checks that follows.

Currently available checks are:

  - KDE4 markup checking (C{kde4markup}).
    Skipped on a message by C{no-check-markup} sieve flag.

  - Qt markup checking (C{qtmarkup}).
    Skipped on a message by C{no-check-markup} sieve flag.

  - Docbook markup checking (C{dbmarkup}).
    Skipped on a message by C{no-check-markup} sieve flag.

  - No translation scripting in dumb messages (C{nots}).
    Message passing through KDE4 i18n at runtime may make use of
    U{translation scripting<http://techbase.kde.org/Localization/Concepts/Transcript>};
    this check will make sure that scripting is not attempted for
    other types of messages (those used by Qt-only code, etc.)

  - Qt datetime format messages (C{qtdt}).
    A message is considered to be in this format if
    it contains "qtdt-format" in C{msgctxt} or among flags.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import os
import re

from pology.misc.report import report
from pology.misc.msgreport import report_on_msg_hl
from pology.misc.msgreport import report_msg_to_lokalize
from pology.sieve import SieveError, SieveCatalogError
from pology.hook.check_markup import flag_no_check_markup
from pology.misc.markup import check_xml_kde4_l1
from pology.misc.markup import check_xml_qtrich_l1
from pology.misc.markup import check_xml_docbook4_l1, check_placeholder_els
from pology.sieve import parse_sieve_flags


def setup_sieve (p):

    p.set_desc(
    "Check validity of messages in catalogs within KDE Translation Project."
    )
    p.add_param("strict", bool, defval=False,
                desc=
    "Check translations strictly: report problems in translation regardless "
    "of whether original itself is valid (default is to check translation "
    "only if original passes checks)."
    )
    chnames = _known_checks.keys()
    chnames.sort()
    p.add_param("check", unicode, seplist=True,
                metavar="KEYWORD,...",
                desc=
    "Run only this check instead of all (currently available: %s). "
    "Several checks can be specified as a comma-separated list."
    % (", ".join(chnames))
    )
    p.add_param("lokalize", bool, defval=False,
                desc=
    "Open catalogs on problematic messages in Lokalize."
    )


class Sieve (object):

    def __init__ (self, params):

        self.strict = params.strict
        self.lokalize = params.lokalize

        self.selected_checks = None
        if params.check is not None:
            unknown_checks = []
            for chname in params.check:
                if chname not in _known_checks:
                    unknown_checks.append(chname)
            if unknown_checks:
                raise SieveError("unknown checks selected: %s"
                                 % ", ".join(unknown_checks))
            self.selected_checks = set(params.check)

        # Indicators to the caller:
        self.caller_sync = False # no need to sync catalogs to the caller
        self.caller_monitored = False # no need for monitored messages

        self.nproblems = 0


    def process_header (self, hdr, cat):

        # Collect catalog data for determining type.
        cname = cat.name
        csubdir = _get_catalog_project_subdir(cat.filename)
        if not csubdir:
            raise SieveCatalogError("%s: cannot determine project subdirectory "
                                    "of the catalog" % cat.filename)

        # Select applicable checks based on catalog type.
        def set_checks (names):
            self.current_checks = []
            if self.selected_checks is not None:
                names = set(names).intersection(self.selected_checks)
            for name in names:
                self.current_checks.append(_known_checks[name])

        if is_txt_cat(cname, csubdir):
            set_checks(["nots"])
        elif is_qt_cat(cname, csubdir):
            set_checks(["qtmarkup", "qtdt", "nots"])
        elif is_docbook_cat(cname, csubdir):
            set_checks(["dbmarkup", "nots"])
        else: # default to native KDE4 catalog
            set_checks(["kde4markup", "qtdt"])


    def process (self, msg, cat):

        if not msg.translated:
            return

        highlight = []
        for check in self.current_checks:
            self.nproblems += check(msg, cat, self.strict, highlight)

        if highlight:
            report_on_msg_hl(highlight, msg, cat)
            if self.lokalize:
                report_msg_to_lokalize(msg, cat, highlight)


    def finalize (self):

        if self.nproblems > 0:
            if self.strict:
                report("Total KDE TP problems in translation (strict): %d"
                       % self.nproblems)
            else:
                report("Total KDE TP problems in translation: %d"
                       % self.nproblems)


def _get_catalog_project_subdir (path):

    apath = os.path.abspath(path)
    up1dir = os.path.basename(os.path.dirname(apath))
    up2dir = os.path.basename(os.path.dirname(os.path.dirname(apath)))
    if (   not re.search(r"^(kde|koffice|extragear|playground|qt)", up1dir)
        or not re.search(r"^(|doc|wiki)messages$", up2dir)
    ):
        subdir = None
    else:
        subdir = os.path.join(up2dir, up1dir)

    return subdir


# --------------------------------------
# Catalog classification.

# - plain text
def is_txt_cat (name, subdir):

    return name.startswith("desktop_") or name.startswith("xml_")


# - pure Qt
_qt_catdirs = (
    "qt",
)
_qt_catnames = (
    "kdgantt1", "kdgantt",
)
_qt_catname_ends = (
    "_qt",
)
def is_qt_cat (name, subdir):

    up1dir = os.path.basename(subdir)
    if up1dir in _qt_catdirs:
        return True
    if name in _qt_catnames:
        return True
    for end in _qt_catname_ends:
        if name.endswith(end):
            return True
    return False


# - Docbook documentation
def is_docbook_cat (name, subdir):

    up2dir = os.path.basename(os.path.dirname(subdir))

    return (up2dir == "docmessages")


# --------------------------------------
# Check for KDE4 markup.

_tsfence = "|/|"

def _check_kde4markup (msg, cat, strict, hl):

    # Do not check markup if:
    # - the check is explicitly skipped for this message
    # - the original is bad and not running in strict mode
    if flag_no_check_markup in parse_sieve_flags(msg):
        return 0
    if not strict:
        if (   check_xml_kde4_l1(msg.msgid)
            or check_xml_kde4_l1(msg.msgid_plural or u"")
        ):
            return 0

    nproblems = 0
    for i in range(len(msg.msgstr)):
        msgstr = msg.msgstr[i]

        lst = msgstr.split(_tsfence, 1)
        msgstr = lst[0]
        msgscript = ""
        if len(lst) == 2:
            msgscript = lst[1]

        for text in (msgstr, msgscript):
            spans = check_xml_kde4_l1(text)
            if spans:
                nproblems += len(spans)
                hl.append(("msgstr", i, spans))

    return nproblems


# --------------------------------------
# Check for Qt markup.

def _check_qtmarkup (msg, cat, strict, hl):

    if flag_no_check_markup in parse_sieve_flags(msg):
        return 0
    if not strict:
        if (   check_xml_qtrich_l1(msg.msgid)
            or check_xml_qtrich_l1(msg.msgid_plural or u"")
        ):
            return 0

    nproblems = 0
    for i in range(len(msg.msgstr)):
        spans = check_xml_qtrich_l1(msg.msgstr[i])
        if spans:
            nproblems += len(spans)
            hl.append(("msgstr", i, spans))

    return nproblems


# --------------------------------------
# Check for Docbook markup.

from pology.sieve.check_xml_docbook4 import _check_dbmarkup


# --------------------------------------
# Check for no scripting in dumb messages.

def _check_nots (msg, cat, strict, hl):

    nproblems = 0
    for i in range(len(msg.msgstr)):
        msgstr = msg.msgstr[i]
        p = msgstr.find(_tsfence)
        if p >= 0:
            nproblems += 1
            hl.append(("msgstr", i,
                       [(p, p + len(_tsfence),
                         "dumb message, translation cannot be scripted")]))

    return nproblems


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


def _is_qtdt_msg (msg):

    return (   (_qtdt_flag in (msg.msgctxt or u"").lower())
            or (_qtdt_flag in msg.flag))


# Worker for check_qtdt* hooks.
def _check_qtdt_w (msgstr, msg, cat):

    if not _is_qtdt_msg(msg):
        return []

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


# Pass-through test hook (for external use).
def check_qtdt (msgstr, msg, cat):
    """
    Check validity of translation if the message is a Qt date-time format
    [type S3C hook].

    TODO: Document further.
    """

    spans = _check_qtdt_w(msgstr, msg, cat)
    if spans:
        report_on_msg(spans[0][-1], msg, cat)
        return False
    else:
        return True


# Span-reporting test hook (for external use).
def check_qtdt_sp (msgstr, msg, cat):
    """
    Check validity of translation if the message is a Qt date-time format
    [type V3C hook].

    Span reporting version of L{check_qtdt}.
    """

    return _check_qtdt_w(msgstr, msg, cat)


# Internal check for this sieve's use.
def _check_qtdt (msg, cat, strict, hl):

    if not _is_qtdt_msg(msg):
        return 0

    nproblems = 0
    for i in range(len(msg.msgstr)):
        msgstr = msg.msgstr[i]
        spans = _check_qtdt_w(msgstr, msg, cat)
        if spans:
            nproblems += 1
            hl.append(("msgstr", i, spans))

    return nproblems


# --------------------------------------
# Map of all existing checks.

_known_checks = {
    "kde4markup": _check_kde4markup,
    "qtmarkup": _check_qtmarkup,
    "dbmarkup": _check_dbmarkup,
    "nots": _check_nots,
    "qtdt": _check_qtdt,
}
