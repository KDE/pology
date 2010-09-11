# -*- coding: UTF-8 -*-

"""
Find messages in catalogs.

Documented in C{doc/user/sieving.docbook}.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import locale
import os
import re
import sys

from pology import _, n_
from pology.message import MessageUnsafe
from pology.remove import remove_accel_msg
from pology.getfunc import get_hook_ireq
from pology.match import make_msg_matcher, make_matcher, make_filtered_msg
from pology.match import ExprError
from pology.msgreport import report_msg_content
from pology.msgreport import report_msg_to_lokalize
from pology.report import report, error, warning, format_item_list
from pology.sieve import SieveError
from pology.sieve import add_param_poeditors


def setup_sieve (p):

    p.set_desc(_("@info sieve discription",
    "Find messages in catalogs."
    "\n\n"
    "Each message is matched according to one or several criteria, "
    "and if it matches as whole, it is displayed to standard output, "
    "along with the catalog path and referent line and entry number."
    "\n\n"
    "When several matching parameters are given, by default a message "
    "is matched if all of them match (AND-relation). "
    "This can be changed to OR-relation for matching in text fields "
    "(%(fieldlist)s) using the '%(par)s' parameter. "
    "Any matching parameter can be repeated when it makes sense "
    "(e.g. two matches on msgid).",
    fieldlist=format_item_list(["msgctxt", "msgid", "msgstr", "comment"]),
    par="or"
    ))

    # NOTE: Do not add default values for matchers,
    # we need None to see if they were issued or not.
    p.add_param("msgid", unicode, multival=True,
                metavar=_("@info sieve parameter value placeholder", "REGEX"),
                desc=_("@info sieve parameter discription",
    "Matches if the '%(field)s' field matches the regular expression.",
    field="msgid"
    ))
    p.add_param("nmsgid", unicode, multival=True,
                metavar=_("@info sieve parameter value placeholder", "REGEX"),
                desc=_("@info sieve parameter discription",
    "Matches if the '%(field)s' field does not match the regular expression.",
    field="msgid"
    ))
    p.add_param("msgstr", unicode, multival=True,
                metavar=_("@info sieve parameter value placeholder", "REGEX"),
                desc=_("@info sieve parameter discription",
    "Matches if the '%(field)s' field matches the regular expression.",
    field="msgstr"
    ))
    p.add_param("nmsgstr", unicode, multival=True,
                metavar=_("@info sieve parameter value placeholder", "REGEX"),
                desc=_("@info sieve parameter discription",
    "Matches if the '%(field)s' field does not match the regular expression.",
    field="msgstr"
    ))
    p.add_param("msgctxt", unicode, multival=True,
                metavar=_("@info sieve parameter value placeholder", "REGEX"),
                desc=_("@info sieve parameter discription",
    "Matches if the '%(field)s' field matches the regular expression.",
    field="msgctxt"
    ))
    p.add_param("nmsgctxt", unicode, multival=True,
                metavar=_("@info sieve parameter value placeholder", "REGEX"),
                desc=_("@info sieve parameter discription",
    "Matches if the '%(field)s' field does not match the regular expression.",
    field="msgctxt"
    ))
    p.add_param("comment", unicode, multival=True,
                metavar=_("@info sieve parameter value placeholder", "REGEX"),
                desc=_("@info sieve parameter discription",
    "Matches if a comment line (extracted or translator) "
    "matches the regular expression."
    ))
    p.add_param("ncomment", unicode, multival=True,
                metavar=_("@info sieve parameter value placeholder", "REGEX"),
                desc=_("@info sieve parameter discription",
    "Matches if a comment line (extracted or translator) "
    "does not match the regular expression."
    ))
    p.add_param("transl", bool,
                desc=_("@info sieve parameter discription",
    "Matches if the message is translated."
    ))
    p.add_param("ntransl", bool,
                desc=_("@info sieve parameter discription",
    "Matches if the message is not translated."
    ))
    p.add_param("obsol", bool,
                desc=_("@info sieve parameter discription",
    "Matches if the message is obsolete."
    ))
    p.add_param("nobsol", bool,
                desc=_("@info sieve parameter discription",
    "Matches if the message is not obsolete."
    ))
    p.add_param("active", bool,
                desc=_("@info sieve parameter discription",
    "Matches if the message is active (translated and not obsolete)."
    ))
    p.add_param("nactive", bool,
                desc=_("@info sieve parameter discription",
    "Matches if the message is not active (not translated or obsolete)."
    ))
    p.add_param("flag", unicode, multival=True,
                metavar=_("@info sieve parameter value placeholder", "REGEX"),
                desc=_("@info sieve parameter discription",
    "Matches if one of the flags matches the regular expression."
    ))
    p.add_param("nflag", unicode, multival=True,
                metavar=_("@info sieve parameter value placeholder", "REGEX"),
                desc=_("@info sieve parameter discription",
    "Matches if none of the flags matches the regular expression."
    ))
    p.add_param("plural", bool,
                desc=_("@info sieve parameter discription",
    "Matches if the message is plural."
    ))
    p.add_param("nplural", bool,
                desc=_("@info sieve parameter discription",
    "Matches if the message is not plural."
    ))
    p.add_param("maxchar", int,
                metavar=_("@info sieve parameter value placeholder", "NUM"),
                desc=_("@info sieve parameter discription",
    "Matches if both the '%(field1)s' and '%(field2)s' field "
    "have at most this many characters "
    "(0 or less means any number of characters).",
    field1="msgid", field2="msgstr"
    ))
    p.add_param("nmaxchar", int,
                metavar=_("@info sieve parameter value placeholder", "NUM"),
                desc=_("@info sieve parameter discription",
    "Matches if either the '%(field1)s' or '%(field2)s' field "
    "have more than this many characters "
    "(0 or less means any number of characters).",
    field1="msgid", field2="msgstr"
    ))
    p.add_param("lspan", unicode,
                metavar=_("@info sieve parameter value placeholder",
                          "START:END"),
                desc=_("@info sieve parameter discription",
    "Matches if the message line number is in the given range "
    "(including starting line, excluding ending line)."
    ))
    p.add_param("nlspan", unicode,
                metavar=_("@info sieve parameter value placeholder",
                          "START:END"),
                desc=_("@info sieve parameter discription",
    "Matches if the message line number is not in the given range "
    "(including starting line, excluding ending line)."
    ))
    p.add_param("espan", unicode,
                metavar=_("@info sieve parameter value placeholder",
                          "START:END"),
                desc=_("@info sieve parameter discription",
    "Matches if the message entry number is in the given range "
    "(including starting entry, excluding ending entry)."
    ))
    p.add_param("nespan", unicode,
                metavar=_("@info sieve parameter value placeholder",
                          "START:END"),
                desc=_("@info sieve parameter discription",
    "Matches if the message entry number is not in the given range "
    "(including starting entry, excluding ending entry)."
    ))
    p.add_param("branch", unicode, seplist=True,
                metavar=_("@info sieve parameter value placeholder", "BRANCH"),
                desc=_("@info sieve parameter discription",
    "In summit catalogs, match only messages belonging to given branch. "
    "Several branches can be given as comma-separated list."
    ))
    p.add_param("nbranch", unicode, seplist=True,
                metavar=_("@info sieve parameter value placeholder", "BRANCH"),
                desc=_("@info sieve parameter discription",
    "Match only messages not belonging to given branch."
    ))
    p.add_param("fexpr", unicode,
                metavar=_("@info sieve parameter value placeholder",
                          "EXPRESSION"),
                desc=_("@info sieve parameter discription",
    "Matches if the logical expression matches. "
    "The expression is composed of direct matchers (not starting with n*), "
    "explicitly linked with AND, OR, and NOT operators, and parenthesis. "
    "Base matchers taking parameters are given as MATCHER/VALUE/, "
    "where slash can be replaced consistently with any other character. "
    "Global matching modifiers can be overriden using MATCHER/VALUE/MODS, or "
    "MATCHER/MODS for parameterless matchers "
    "(currently available: c/i for case-sensitive/insensitive). "
    "Examples:"
    "\n\n"
    "fexpr:'(msgctxt/foo/ or comment/foo/) and msgid/bar/'"
    "\n\n"
    "fexpr:'msgid/quuk/ and msgstr/Qaak/c'"
    ))
    p.add_param("nfexpr", unicode,
                metavar=_("@info sieve parameter value placeholder",
                          "EXPRESSION"),
                desc=_("@info sieve parameter discription",
    "Matches if the logical expression does not match."
    ))
    p.add_param("or", bool, defval=False, attrname="or_match",
                desc=_("@info sieve parameter discription",
    "Use OR-relation for matching text fields: if any of "
    "the patterns matches, the message is matched as whole."
    ))
    p.add_param("invert", bool, defval=False,
                desc=_("@info sieve parameter discription",
    "Invert the condition: report messages which do not match."
    ))
    p.add_param("case", bool, defval=False,
                desc=_("@info sieve parameter discription",
    "Case-sensitive text matching."
    ))
    p.add_param("accel", unicode, multival=True,
                metavar=_("@info sieve parameter value placeholder", "CHAR"),
                desc=_("@info sieve parameter discription",
    "Character which is used as UI accelerator marker in text fields, "
    "to ignore it on matching. "
    "If a catalog defines accelerator marker in the header, "
    "this value overrides it."
    ))
    p.add_param("mark", bool, defval=False,
                desc=_("@info sieve parameter discription",
    "Add '%(flag)s' flag to each matched message.",
    flag=_flag_mark
    ))
    p.add_param("filter", unicode, multival=True,
                metavar=_("@info sieve parameter value placeholder", "HOOK"),
                desc=_("@info sieve parameter discription",
    "F1A hook specification, to filter the msgstr fields through "
    "before matching them. "
    "Several hooks can be specified by repeating the parameter."
    ))
    p.add_param("replace", unicode,
                metavar=_("@info sieve parameter value placeholder",
                          "REPLSTR"),
                desc=_("@info sieve parameter discription",
    "Replace all substrings matched by msgstr pattern with REPLSTR. "
    "It can include back-references to matched groups (\\1, \\2, etc.)"
    ))
    p.add_param("nomsg", bool, defval=False,
                desc=_("@info sieve parameter discription",
    "Do not report message to standard output "
    "(when only the number of matches is wanted)."
    ))
    add_param_poeditors(p)


_flag_mark = u"match"


class Sieve (object):


    def __init__ (self, params):

        self.nmatch = 0

        self.p = params

        # Build matching function.
        # It takes as arguments: filtered message, message, catalog,
        # and highlight specification (which is filled on matches).

        def make_match_group (names, negatable=False, orlinked=False):

            names_negs = [(x, False) for x in names]
            if negatable:
                names_negs.extend([(x, True) for x in names])

            matchers = []
            for name, neg in names_negs:
                nname = name
                if neg:
                    nname = "n" + name
                values = getattr(params, nname)
                if values is None: # parameter not given
                    continue
                if not isinstance(values, list):
                    values = [values]
                for value in values:
                    try:
                        if name == "fexpr":
                            m = make_msg_matcher(value, params)
                        else:
                            m = make_matcher(name, value, [], params, neg)
                    except ExprError, e:
                        raise SieveError(unicode(e))
                    matchers.append(m)

            if orlinked:
                expr = lambda *a: reduce(lambda s, m: s or m(*a),
                                         matchers, False)
            else:
                expr = lambda *a: reduce(lambda s, m: s and m(*a),
                                         matchers, True)
            return expr

        # - first matchers which are always AND
        expr_and = make_match_group([
            "transl", "obsol", "active", "plural", "maxchar", "lspan", "espan",
            "flag", "branch",
        ], negatable=True, orlinked=False)

        # - then matchers which can be AND or OR
        expr_andor = make_match_group([
            "msgctxt", "msgid", "msgstr", "comment",
            "fexpr",
        ], negatable=True, orlinked=self.p.or_match)

        # - all together
        self.matcher = lambda *a: expr_and(*a) and expr_andor(*a)

        # Prepare replacement.
        self.replrxs = []
        if self.p.replace is not None:
            if not self.p.msgstr:
                raise SieveError(
                    _("@info",
                      "Cannot perform replacement if match "
                      "on '%(field)s' is not given.",
                      field="msgstr"))
            rxflags = re.U
            if not self.p.case:
                rxflags |= re.I
            for rxstr in self.p.msgstr:
                self.replrxs.append(re.compile(rxstr, rxflags))

        # Resolve filtering hooks.
        self.pfilters = []
        for hreq in self.p.filter or []:
            self.pfilters.append(get_hook_ireq(hreq, abort=True))

        # Unless replacement or marking requested, no need to monitor/sync.
        if self.p.replace is None and not self.p.mark:
            self.caller_sync = False
            self.caller_monitored = False


    def process_header (self, hdr, cat):

        # Force explicitly given accelerators.
        if self.p.accel is not None:
            cat.set_accelerator(self.p.accel)


    def process (self, msg, cat):
        """
        Returns 0 if the message is matched, 1 otherwise.
        """

        # Prepare filtered message for matching.
        msgf = make_filtered_msg(msg, cat, filters=self.pfilters)

        # Match the message.
        hl_spec = []
        match = self.matcher(msgf, msg, cat, hl_spec)
        if self.p.invert:
            match = not match

        if match:
            self.nmatch += 1

            # Do the replacement in translation if requested.
            # NOTE: Use the real, not the filtered message.
            for regex in self.replrxs:
                for i in range(len(msg.msgstr)):
                    msg.msgstr[i] = regex.sub(self.p.replace, msg.msgstr[i])

            if not self.p.nomsg:
                delim = "-" * 20
                if self.nmatch == 1:
                    report(delim)
                report_msg_content(msg, cat, wrapf=cat.wrapf(), force=True,
                                   delim=delim, highlight=hl_spec)

            if self.p.mark:
                msg.flag.add(_flag_mark)

            if self.p.lokalize:
                report_msg_to_lokalize(msg, cat)

        elif self.p.mark and _flag_mark in msg.flag:
            # Remove the flag if present but the message does not match.
            msg.flag.remove(_flag_mark)

        return 0 if match else 1


    def finalize (self):

        if self.nmatch:
            msg = n_("@info:progress",
                     "Found %(num)d message satisfying the conditions.",
                     "Found %(num)d messages satisfying the conditions.",
                     num=self.nmatch)
            report("===== " + msg)

