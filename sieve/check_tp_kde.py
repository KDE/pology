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
  - C{check}: select only one or few checks to be applied, instead of all
  - C{showmsg}: show content of the message, with errors highlighted
  - C{lokalize}: open catalogs at problematic messages in Lokalize

Sometimes the original text itself may not be valid against a certain check.
If this is the case, by default translation is not expected to be valid either,
so the check is skipped.
This behavior can be canceled by issuing the C{strict} sieve parameter,
when the translation is reported problematic even if the original is such.
If C{strict} is used, some checks can be ignored on a particular, irreparable
through translation only message, by adding to it an appropriate
L{sieve flag<sieve.parse_sieve_flags>}.

Parameter C{check} may be used to to apply only some instead of all checks.
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

  - Validity of translator credits (C{trcredits}).
    Catalogs may contain meta-messages to input translator credits;
    translations of these messages should be valid on on their own,
    but also have some congruence between them.

  - Query placeholders in Plasma runners (C{plrunq}).
    Messages in Plasma runners may contain special query placeholder C{:q:},
    which should be present in translation too.

  - Catalog-specific checking (C{catspec}).
    Certain messages in certain catalogs have special validity requirements,
    and this check activates all such catalog-specific checks.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import os
import re

from pology import _, n_
from pology.markup import flag_no_check_markup
from pology.escape import escape_c
from pology.markup import validate_kde4_l1
from pology.markup import validate_qtrich_l1
from pology.msgreport import report_on_msg_hl, report_msg_content
from pology.msgreport import report_msg_to_lokalize
from pology.report import report, format_item_list
from pology.sieve import add_param_poeditors
from pology.sieve import SieveError, SieveCatalogError, parse_sieve_flags
from pology.proj.kde.cattype import get_project_subdir
from pology.proj.kde.cattype import is_txt_cat, is_qt_cat, is_docbook_cat


def setup_sieve (p):

    p.set_desc(_("@info sieve discription",
    "Check validity of messages in catalogs within KDE Translation Project."
    ))
    p.add_param("strict", bool, defval=False,
                desc=_("@info sieve parameter discription",
    "Check translations strictly: report problems in translation regardless "
    "of whether original itself is valid (default is to check translation "
    "only if original passes checks)."
    ))
    chnames = _known_checks.keys()
    chnames.sort()
    p.add_param("check", unicode, seplist=True,
                metavar=_("@info sieve parameter value placeholder",
                          "KEYWORD,..."),
                desc=_("@info sieve parameter discription",
    "Run only this check instead of all (currently available: %(chklist)s). "
    "Several checks can be specified as a comma-separated list.",
    chklist=format_item_list(chnames)
    ))
    p.add_param("showmsg", bool, defval=False,
                desc=_("@info sieve parameter discription",
    "Also show the full message that had some problems."
    ))
    add_param_poeditors(p)


class Sieve (object):

    def __init__ (self, params):

        self.strict = params.strict
        self.showmsg = params.showmsg
        self.lokalize = params.lokalize

        self.selected_checks = None
        if params.check is not None:
            unknown_checks = []
            for chname in params.check:
                if chname not in _known_checks:
                    unknown_checks.append(chname)
            if unknown_checks:
                fmtchecks = format_item_list(unknown_checks)
                raise SieveError(
                    _("@info",
                      "Unknown checks selected: %(chklist)s.",
                      chklist=fmtchecks))
            self.selected_checks = set(params.check)

        # Indicators to the caller:
        self.caller_sync = False # no need to sync catalogs to the caller
        self.caller_monitored = False # no need for monitored messages

        self.nproblems = 0


    def process_header (self, hdr, cat):

        # Collect catalog data for determining type.
        cname = cat.name
        csubdir = get_project_subdir(cat.filename)
        if not csubdir:
            raise SieveCatalogError(
                _("@info",
                  "Cannot determine project subdirectory "
                  "of the catalog '%(file)s'.",
                  file=cat.filename))

        # Select checks applicable to current catalog.
        self.current_checks = []

        def add_checks (names):
            if self.selected_checks is not None:
                names = set(names).intersection(self.selected_checks)
            for name in names:
                self.current_checks.append(_known_checks[name])

        if is_txt_cat(cname, csubdir):
            add_checks(["nots"])
        elif is_qt_cat(cname, csubdir):
            add_checks(["qtmarkup", "qtdt", "nots"])
        elif is_docbook_cat(cname, csubdir):
            add_checks(["dbmarkup", "nots"])
        else: # default to native KDE4 catalog
            add_checks(["kde4markup", "qtdt", "trcredits", "plrunq"])
        add_checks(["catspec"]) # to all catalogs, will select internally

        # Reset catalog progress cache, available to checks.
        self.pcache = {
            "strict": self.strict,
        }


    def process (self, msg, cat):

        if not msg.translated:
            return

        highlight = []
        for check in self.current_checks:
            self.nproblems += check(msg, cat, self.pcache, highlight)

        if highlight:
            if self.showmsg:
                report_msg_content(msg, cat, highlight=highlight,
                                   delim=("-" * 20))
            else:
                report_on_msg_hl(highlight, msg, cat)
            if self.lokalize:
                report_msg_to_lokalize(msg, cat, highlight)


    def finalize (self):

        if self.nproblems > 0:
            if not self.strict:
                msg = n_("@info:progress TP stands for Translation Project",
                         "Found %(num)d problem in KDE TP translations.",
                         "Found %(num)d problems in KDE TP translations.",
                         num=self.nproblems)
            else:
                msg = n_("@info:progress",
                         "Found %(num)d problem in "
                         "KDE TP translations (strict mode).",
                         "Found %(num)d problems in "
                         "KDE TP translations (strict mode).",
                         num=self.nproblems)
            report("===== " + msg)


# Map of checks by name,
# updated at point of definition of the check.
_known_checks = {}

# --------------------------------------
# Check for KDE4 markup.

_tsfence = "|/|"

def _check_kde4markup (msg, cat, pcache, hl):

    strict = pcache.get("strict", False)

    # Do not check markup if:
    # - the check is explicitly skipped for this message
    # - the original is bad and not running in strict mode
    if flag_no_check_markup in parse_sieve_flags(msg):
        return 0
    if not strict:
        if (   validate_kde4_l1(msg.msgid)
            or validate_kde4_l1(msg.msgid_plural or u"")
        ):
            return 0

    nproblems = 0
    for i in range(len(msg.msgstr)):
        msgstr = msg.msgstr[i]

        lst = msgstr.split(_tsfence, 1)
        msgstr = lst[0]
        msgscript = ""
        if len(lst) == 2:
            # FIXME: No point in checking the scripted part as it is,
            # since calls may be used to modify markup in special ways.
            # Perhaps it would work to remove calls and check what's left?
            #msgscript = lst[1]
            pass

        for text in (msgstr, msgscript):
            spans = validate_kde4_l1(text)
            if spans:
                nproblems += len(spans)
                hl.append(("msgstr", i, spans))

    return nproblems

_known_checks["kde4markup"] = _check_kde4markup

# --------------------------------------
# Check for Qt markup.

def _check_qtmarkup (msg, cat, pcache, hl):

    strict = pcache.get("strict", False)

    if flag_no_check_markup in parse_sieve_flags(msg):
        return 0
    if not strict:
        if (   validate_qtrich_l1(msg.msgid)
            or validate_qtrich_l1(msg.msgid_plural or u"")
        ):
            return 0

    nproblems = 0
    for i in range(len(msg.msgstr)):
        spans = validate_qtrich_l1(msg.msgstr[i])
        if spans:
            nproblems += len(spans)
            hl.append(("msgstr", i, spans))

    return nproblems

_known_checks["qtmarkup"] = _check_qtmarkup

# --------------------------------------
# Check for Docbook markup.

from pology.markup import check_docbook4_msg

def _check_dbmarkup (msg, cat, pcache, hl):

    check1 = pcache.get("check_dbmarkup_hook")
    if not check1:
        strict = pcache.get("strict", False)
        check1 = check_docbook4_msg(strict=strict, entities=None)
        pcache["check_dbmarkup_hook"] = check1

    hl1 = check1(msg, cat)
    hl.extend(hl1)
    nproblems = sum(len(x[2]) for x in hl1)

    return nproblems

_known_checks["dbmarkup"] = _check_dbmarkup

# --------------------------------------
# Check for no scripting in dumb messages.

def _check_nots (msg, cat, pcache, hl):

    nproblems = 0
    for i in range(len(msg.msgstr)):
        msgstr = msg.msgstr[i]
        p = msgstr.find(_tsfence)
        if p >= 0:
            nproblems += 1
            hl.append(("msgstr", i,
                       [(p, p + len(_tsfence),
                         _("@info",
                           "Dumb message, translation cannot be scripted."))]))

    return nproblems

_known_checks["nots"] = _check_nots

# --------------------------------------
# Qt datetime format messages.

_qtdt_flag = "qtdt-format"

_qtdt_clean_rx = re.compile(r"'.*?'")
_qtdt_split_rx = re.compile(r"\W+", re.U)

def _qtdt_parse (text):

    text = _qtdt_clean_rx.sub("", text)
    fields = [x for x in _qtdt_split_rx.split(text) if x]
    return fields


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
        errmsg = _("@info",
                   "Qt date-format mismatch: "
                   "original contains fields {%(fieldlist1)s} "
                   "while translation contains {%(fieldlist2)s}.",
                   fieldlist1=format_item_list(sorted(msgid_fmts)),
                   fieldlist2=format_item_list(sorted(msgstr_fmts)))
        spans.append((None, None, errmsg))

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
def _check_qtdt (msg, cat, pcache, hl):

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

_known_checks["qtdt"] = _check_qtdt

# --------------------------------------
# Check for runtime translator data.

_trcredit_name_ctxt = "NAME OF TRANSLATORS"
_trcredit_email_ctxt = "EMAIL OF TRANSLATORS"

_trcredit_ctxts = set((
    _trcredit_name_ctxt,
    _trcredit_email_ctxt,
))

_valid_email_rx = re.compile(r"^\S+@\S+\.\S+$", re.U)

def _check_trcredits (msg, cat, pcache, hl):

    if not msg.active:
        return 0
    if msg.msgctxt not in _trcredit_ctxts:
        return 0

    errors = []

    if msg.msgctxt == _trcredit_name_ctxt:
        names = [x.strip() for x in msg.msgstr[0].split(",")]
        pcache["trnames"] = names

    elif msg.msgctxt == _trcredit_email_ctxt:
        emails = [x.strip() for x in msg.msgstr[0].split(",")]
        pcache["tremails"] = emails

        for email in emails:
            # Check minimal validity of address.
            if email and not _valid_email_rx.match(email):
                emsg = _("@info",
                         "Invalid email address '%(email)s'.",
                         email=escape_c(email))
                errors.append(emsg)

    # Check congruence between names and emails.
    names = pcache.get("trnames")
    emails = pcache.get("tremails")
    if emails and names:
        if len(names) != len(emails):
            emsg = _("@info",
                     "Different number of translator names (%(num1)d) "
                     "and email addresses (%(num2)d).",
                     num1=len(names), num2=len(emails))
            errors.append(emsg)
        else:
            for name, email, i in zip(names, emails, range(1, len(names) + 1)):
                if not name and not email:
                    emsg = _("@info",
                             "Both name and email address "
                             "of translator no. %(ord)d are empty.",
                             ord=i)
                    errors.append(emsg)

    if errors:
        hl.append(("msgstr", 0, [(None, None, x) for x in errors]))

    return len(errors)

_known_checks["trcredits"] = _check_trcredits

# --------------------------------------
# Check for query placeholders in Plasma runners.

def _check_plrunq (msg, cat, pcache, hl):

    if not msg.active:
        return 0

    nerrors = 0
    if ":q:" in msg.msgid and ":q:" not in msg.msgstr[0]:
        errmsg = _("@info",
                   "Plasma runner query placeholder '%(plhold)s' "
                   "is missing in translation.",
                   plhold=":q:")
        hl.append(("msgstr", 0, [(None, None, errmsg)]))
        nerrors += 1

    return nerrors

_known_checks["plrunq"] = _check_plrunq

# --------------------------------------
# Helpers for catalog-specific checks.

# Add a catalog-specific checks to one or more catalogs, selected by name.
# For example:
#   _add_cat_check(_check_cat_xyz, ["catfoo", "catbar"])
_known_checks_by_cat = {}
def _add_cat_check_hl (check, catspecs):
    for catspec in catspecs:
        if catspec not in _known_checks_by_cat:
            _known_checks_by_cat[catspec] = []
        if check not in _known_checks_by_cat[catspec]:
            _known_checks_by_cat[catspec].append(check)


# Like _add_cat_check_hl, except that instead of updating the highlight,
# check function returns a single error message or a list of error messages.
def _add_cat_check (check, catspecs):
    def check_mod (msg, cat, pcache, hl):
        errors = check(msg, cat, pcache)
        if errors:
            if isinstance(errors, basestring):
                errors = [errors]
            hl.append(("msgstr", 0, [(None, None, x) for x in errors]))
            return len(errors)
        else:
            return 0
    _add_cat_check_hl(check_mod, catspecs)


# Global check to apply appropriate catalog-specific checks.
def _check_catspec (msg, cat, pcache, hl):

    nproblems = 0
    for check in _known_checks_by_cat.get(cat.name, []):
        nproblems += check(msg, cat, pcache, hl)

    return nproblems

_known_checks["catspec"] = _check_catspec


# --------------------------------------
# Catalog-specific checks.

def _check_cat_libkleopatra (msg, cat, pcache):

    if "'yes' or 'no'" in (msg.msgctxt or ""):
        if msg.msgstr[0] not in ("yes", "no"):
            return _("@info",
                     "Translation must be exactly '%(text1)s' or '%(text2)s'.",
                     text1="yes", text2="no")

_add_cat_check(_check_cat_libkleopatra, ["libkleopatra"])


def _check_cat_kplatolibs (msg, cat, pcache):

    if "Letter(s) only" in (msg.msgctxt or ""):
        if not msg.msgstr[0].isalpha():
            return _("@info",
                     "Translation must contain only letters.")

_add_cat_check(_check_cat_kplatolibs, ["kplatolibs"])


def _check_cat_kdeqt (msg, cat, pcache):

    if msg.msgid == "QT_LAYOUT_DIRECTION":
        if msg.msgstr[0] not in ("LTR", "RTL"):
            return _("@info",
                     "Translation must be exactly '%(text1)s' or '%(text2)s'.",
                     text1="LTR", text2="RTL")

_add_cat_check(_check_cat_kdeqt, ["kdeqt"])

