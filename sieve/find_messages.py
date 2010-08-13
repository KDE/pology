# -*- coding: UTF-8 -*-

"""
Find messages in catalogs.

Matches patterns against elements of the message and examines its properties,
and reports the message if the match is complete. Matched messages are
reported to standard output, with the name of the file from which they come,
and referent line and entry number within the file.

Sieve parameters for matching:
  - C{msgctxt:<regex>}: regular expression to match against the C{msgctxt}
  - C{msgid:<regex>}: regular expression to match against the C{msgid}
  - C{msgstr:<regex>}: regular expression to match against the C{msgstr}
  - C{comment:<regex>}: regular expression to match against comments
  - C{transl}: the message must be translated
  - C{obsol}: the message must be obsolete
  - C{active}: the message must be active (translated and not obsolete)
  - C{flag:<regex>}: regular expression to match against flags
  - C{plural}: the message must be plural
  - C{maxchar}: messages must have no more than this number of characters
  - C{lspan:<start>:<end>}: the message line number must be in this range
  - C{espan:<start>:<end>}: the message entry number must be in this range
  - C{branch:<branch_id>}: match only messages from this branch (summit)
  - C{fexpr}: logical expression made out of any previous matching typs
  - C{or}: use OR- instead of AND-matching for text fields
  - C{invert}: report messages not matching the condition

If more than one of the matching parameters are given (e.g. both C{msgid} and
C{msgstr}), the message matches only if all of them match.
Using the C{or} parameter this can be changed for matching in text fields
(C{msgctxt}, C{msgid}, C{msgstr}, C{comment})
such that the message matches if any of text fields match.
In case of plural messages, C{msgid} is considered matched if either C{msgid}
or C{msgid_plural} fields match, and C{msgstr} if any of the C{msgstr}
fields match.
If C{invert} parameter is issued, messages are reported if they do not match
the condition assembled by other parameters.

Every matching option has a counterpart with prepended C{n*},
by which the meaning of the match is inverted; for example, if both
C{msgid:foo} and C{nmsgid:bar} are given, then the message matches
if its C{msgid} contains C{foo} but does not contain C{bar}.

When simple AND- or OR-matching is not enough, parameter C{fexpr} can
be used to specify full logical expressions, using any of the basic
matchers linked with AND, OR, NOT parameters, and parenthesis.
If a matcher needs a value (e.g. regular expressions), within expression
it is given as C{MATCHER/VALUE/}, where another nonalphanumeric character
can be used instead of slash if the value contains it.
If matchers is influenced by another global parameter (e.g. case sensitivity),
in the expression it may be able to take overriding modifiers as single
characters after matcher name, i.e. C{MATCHER/VALUE/MODS} (or C{MATCHER/MODS}
for parameterless matchers). Examples::

    # Either msgctxt or comment contain 'foo', and msgid contains 'bar'.
    fexpr:'(msgctxt/foo/ or comment/foo/) and msgid/bar/'

    # msgid contains 'quuk' in any casing and msgstr exactly 'Qaak'.
    fexpr:'msgid/quuk/ and msgstr/Qaak/c'

Available modifiers to matchers are:
  - C{c}: text matching pattern is case-sensitive
  - C{i}: text matching pattern is case-insensitive

Sieve parameters for replacement:
  - C{replace:<string>}: string to replace matched part of translation

The C{replace} option must go together with the C{msgstr} match. As usual for regular expression replacement, the replacement string may contain C{\\<number>} references to groups defined by C{msgstr} match.

Other sieve parameters:
  - C{accel:<chars>}: strip these characters as accelerator markers
  - C{case}: case-sensitive match (insensitive by default)
  - C{mark}: mark each matched message with C{match} flag
  - C{filter:<hookspec>}: apply F1A filtering hook to translation prior
        to matching (see L{getfunc.get_hook_ireq} for the format
        of hook specifications)
  - C{lokalize}: open catalogs at matched messages in Lokalize
  - C{nomsg}: do not report messages (to only count the number of matches)

If accelerator character is not given by C{accel} option, the sieve will try
to guess the accelerator; it may choose wrongly or decide that there are no
accelerators. E.g. an C{X-Accelerator-Marker} header field is checked for the
accelerator character.

Using the C{mark} option, C{match} flag will be added to each matched message,
modifying the PO file. Modified files can then be opened in an editor,
and messages looked up by this flag.
This is for cases when the search is performed in order to modify something
in matched messages, but doing so automatically using C{replace} option
is not possible or safe enough.
(Also useful here is the option C{-m} of C{posieve}, to write out
the paths of modified POs into a separate file.)

When used in a sieve chain, this sieve will stop further sieving of messages
which do not match. This makes it useful as a filter for selecting subsets
of messages on which other sieves should operate.
Parameter C{nomsg} can be used here to prevent reporting of
matched messages to standard output.

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
from pology.comments import parse_summit_branches
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
    "Find and display messages."
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

