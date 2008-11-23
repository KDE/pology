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
  - C{plural}: the message must be plural
  - C{maxchar}: messages must have no more than this number of characters
  - C{fexpr}: logical expression made out of any previous matching typs
  - C{or}: use OR- instead of AND-matching for text fields

If more than one of the matching parameters are given (e.g. both C{msgid} and
C{msgstr}), the message matches only if all of them match.
This can be changed for text fields (C{msgid}, C{msgstr}, etc.) such that
the message matches if any of text fields match, using the C{of} parameter.
In case of plural messages, C{msgid} is considered matched if either C{msgid}
or C{msgid_plural} fields match, and C{msgstr} if any of the C{msgstr}
fields match.

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

The C{replace} option must go together with the C{msgstr} match. As usual for regular expression replacement, the replacement string may contain C{\<number>} references to groups defined by C{msgstr} match.

Other sieve parameters:
  - C{accel:<chars>}: strip these characters as accelerator markers
  - C{case}: case-sensitive match (insensitive by default)
  - C{mark}: mark each matched message with a flag
  - C{filter:[<lang>:]<name>,...}: apply filters to msgstr prior to matching

If accelerator character is not given by C{accel} option, the sieve will try
to guess the accelerator; it may choose wrongly or decide that there are no
accelerators. E.g. an C{X-Accelerator-Marker} header field is checked for the
accelerator character.

Using the C{mark} option, C{pattern-match} flag will be added to each
matched message, in the PO file itself; the messages will not be sent to
standard output. The modified files can then be opened in an editor,
and messages looked up by this flag. This is for cases when the search is
performed in order to modify something in matched messages, but doing so
automatically using C{replace} option is not possible or safe enough.
Option C{-m} of C{posieve.py} is useful here to send the names of
modified POs to a separate file.

The C{filter} option specifies pure text hooks to apply to
msgstr before it is checked. The hooks are found in C{pology.hook}
and C{pology.l10n.<lang>.hook} modules, and are specified
as comma-separated list of C{[<lang>:]<name>[/<function>]};
language is stated when a hook is language-specific, and function
when it is not the default C{process()} within the hook module.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import sys
import os
import re

from pology.misc.report import report, error, warning
from pology.misc.msgreport import report_msg_content
from pology.misc.langdep import get_hook_lreq
from pology.misc.wrap import wrap_field, wrap_field_unwrap
from pology.file.message import MessageUnsafe
from pology.hook.remove_subs import remove_accel_msg


def setup_sieve (p):

    p.set_desc(
    "Find and display messages."
    "\n\n"
    "Each message is matched according to one or several criteria, "
    "and if it matches as whole, its content is displayed to output device, "
    "along with originating catalog and referent line and entry number."
    "\n\n"
    "When several matching parameters are given, by default a message "
    "is matched if all of them match (AND-semantics). "
    "This can be changed to OR-semantics in a limited sense, "
    "for pattern matching in text fields (msgid, msgstr, etc.) "
    "using the '%(par1)s' parameter. "
    "Any matching parameter can be repeated if it makes sense (e.g. two "
    "matches on msgid)."
    "\n\n"
    "See documentation to pology.sieve.find_messages for details."
    % dict(par1="or")
    )

    # NOTE: Do not add default values for matchers,
    # we need None to see if they were issued or not.
    p.add_param("msgid", unicode, multival=True,
                metavar="REGEX",
                desc=
    "Matches if the msgid field matches the regular expression."
    )
    p.add_param("nmsgid", unicode, multival=True,
                metavar="REGEX",
                desc=
    "Matches if the msgid field does not match the regular expression."
    )
    p.add_param("msgstr", unicode, multival=True,
                metavar="REGEX",
                desc=
    "Matches if the msgstr field matches the regular expression."
    )
    p.add_param("nmsgstr", unicode, multival=True,
                metavar="REGEX",
                desc=
    "Matches if the msgstr field does not match the regular expression."
    )
    p.add_param("msgctxt", unicode, multival=True,
                metavar="REGEX",
                desc=
    "Matches if the msgctxt field matches the regular expression."
    )
    p.add_param("nmsgctxt", unicode, multival=True,
                metavar="REGEX",
                desc=
    "Matches if the msgctxt field does not match the regular expression."
    )
    p.add_param("comment", unicode, multival=True,
                metavar="REGEX",
                desc=
    "Matches if a comment line (extracted or translator) "
    "matches the regular expression."
    )
    p.add_param("ncomment", unicode, multival=True,
                metavar="REGEX",
                desc=
    "Matches if a comment line (extracted or translator) "
    "does not match the regular expression."
    )
    p.add_param("transl", bool,
                desc=
    "Matches if the message is translated."
    )
    p.add_param("ntransl", bool,
                desc=
    "Matches if the message is not translated."
    )
    p.add_param("plural", bool,
                desc=
    "Matches if the message is plural."
    )
    p.add_param("nplural", bool,
                desc=
    "Matches if the message is not plural."
    )
    p.add_param("maxchar", int,
                metavar="NUM",
                desc=
    "Matches if both the msgid and msgstr field have at most this many "
    "characters (0 or less means any number of characters)."
    )
    p.add_param("nmaxchar", int,
                metavar="NUM",
                desc=
    "Matches if either the msgid or msgstr field have more than this many "
    "characters (0 or less means any number of characters)."
    )
    p.add_param("fexpr", unicode,
                metavar="EXPRESSION",
                desc=
    "Matches if the logical expression matches. "
    "The expression is composed of direct matchers (not starting with n*), "
    "explicitly linked with AND, OR, and NOT operators, and parenthesis. "
    "Base matchers taking parameters are given as MATCHER/VALUE/, "
    "where slash can be replaced with another character sed-style. "
    "Global matching modifiers can be overriden using MATCHER/VALUE/MODS, or "
    "MATCHER/MODS for parameterless matchers "
    "(currently available: c/i for case-sensitive/insensitive). "
    "Examples:"
    "\n\n"
    "fexpr:'(msgctxt/foo/ or comment/foo/) and msgid/bar/'"
    "\n\n"
    "fexpr:'msgid/quuk/ and msgstr/Qaak/c'"
    )
    p.add_param("nfexpr", unicode,
                metavar="EXPRESSION",
                desc=
    "Matches if the logical expression does not match."
    )
    p.add_param("or", bool, defval=False, attrname="or_match",
                desc=
    "Use OR-semantics for matching text fields: if any of "
    "the patterns matches, the message is matched as whole."
    )
    p.add_param("case", bool, defval=False,
                desc=
    "Use case-sensitive text matching."
    )
    p.add_param("accel", unicode, multival=True,
                metavar="CHAR",
                desc=
    "Character which is used as UI accelerator marker in text fields, "
    "to ignore it on matching. "
    "If a catalog defines accelerator marker in the header, "
    "this value overrides it."
    )
    p.add_param("mark", bool, defval=False,
                desc=
    "Add '%(flag)s' flag to each matched message."
    % dict(flag=_flag_mark)
    )
    p.add_param("filter", unicode, multival=True, seplist=True,
                metavar="HOOKSPEC,...",
                desc=
    "F1A hook specification, to filter the msgstr fields through "
    "before matching them. "
    "Several hooks can be specified either as a comma-separated list, "
    "or by repeating the parameter."
    )
    p.add_param("replace", unicode,
                metavar="REPLSTR",
                desc=
    "Replace all substrings matched by msgstr pattern with REPLSTR. "
    "It can include back-references to matched groups (\\1, \\2, etc.)"
    )


_flag_mark = u"pattern-match"


# Matchers taking a value.
_op_matchers = set(["msgctxt", "msgid", "msgstr", "comment"])
# Matchers not taking a value.
_nop_matchers = set(["transl", "plural"])

# Matchers which produce a regular expression out of their value.
_rx_matchers = set(["msgctxt", "msgid", "msgstr", "comment"])

# All matchers together.
_all_matchers = set()
_all_matchers.update(_op_matchers)
_all_matchers.update(_nop_matchers)


class Sieve (object):


    def __init__ (self, params, options):

        self.nmatch = 0

        self.p = params

        # Build matching function.
        # It takes as arguments: filtered message, message, catalog,
        # and highlight specification (which is filled on matches).

        def create_match_group (names, negatable=False, orlinked=False):

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
                    if name == "fexpr":
                        m = _build_expr(value, params)
                    else:
                        m = _create_matcher(name, value, [], params, neg)
                    matchers.append(m)

            if orlinked:
                expr = lambda *a: reduce(lambda s, m: s or m(*a),
                                         matchers, False)
            else:
                expr = lambda *a: reduce(lambda s, m: s and m(*a),
                                         matchers, True)
            return expr

        # - first matchers which are always AND
        expr_and = create_match_group([
            "transl", "plural", "maxchar",
        ], negatable=True, orlinked=False)

        # - then matchers which can be AND or OR
        expr_andor = create_match_group([
            "msgctxt", "msgid", "msgstr", "comment",
            "fexpr",
        ], negatable=True, orlinked=self.p.or_match)

        # - all together
        self.matcher = lambda *a: expr_and(*a) and expr_andor(*a)

        # Prepare replacement.
        self.replrxs = []
        if self.p.replace is not None:
            if not self.p.msgstr:
                error("cannot replace if no msgstr pattern given")
            rxflags = re.U
            if not self.p.case:
                rxflags |= re.I
            for rxstr in self.p.msgstr:
                self.replrxs.append(re.compile(rxstr, rxflags))

        # Resolve filtering hooks.
        self.pfilters = []
        for hreq in self.p.filter or []:
            self.pfilters.append(get_hook_lreq(x, abort=True))

        # Unless replacement or marking requested, no need to monitor/sync.
        if self.p.replace is None and not self.p.mark:
            self.caller_sync = False
            self.caller_monitored = False

        # Select wrapping for reporting messages.
        if options.do_wrap:
            self.wrapf = wrap_field
        else:
            self.wrapf = wrap_field_unwrap


    def process_header (self, hdr, cat):

        # Force explicitly given accelerators.
        if self.p.accel is not None:
            cat.set_accelerator(self.p.accel)


    def process (self, msg, cat):

        if msg.obsolete:
            return

        # Prepare filtered message for matching.
        msgf = MessageUnsafe(msg)
        # - remove accelerators
        remove_accel_msg(msgf, cat)
        # - apply msgstr filters
        for pfilter in self.pfilters:
            for i in range(len(msgf.msgstr)):
                msgf.msgstr[i] = pfilter(msgf.msgstr[i])

        # Match the message.
        hl_spec = {}
        match = self.matcher(msgf, msg, cat, hl_spec)

        if match:
            self.nmatch += 1

            # Do the replacement in translation if requested.
            # NOTE: Use the real, not the filtered message.
            for regex in self.replrxs:
                for i in range(len(msg.msgstr)):
                    msg.msgstr[i] = regex.sub(self.p.replace, msg.msgstr[i])

            if not self.p.mark:
                delim = "-" * 20
                if self.nmatch == 1:
                    report(delim)
                highlight = [x + y for x, y in hl_spec.items()]
                report_msg_content(msg, cat, wrapf=self.wrapf, force=True,
                                   delim=delim, highlight=highlight)
            else:
                msg.flag.add(_flag_mark)

        elif self.p.mark and _flag_mark in msg.flag:
            # Remove the flag if present but the message does not match.
            msg.flag.remove(_flag_mark)


    def finalize (self):

        if self.nmatch:
            report("Total matching: %d" % self.nmatch)


_all_ops = set()
_unary_ops = set(["not"])
_all_ops.update(_unary_ops)
_binary_ops = set(["and", "or"])
_all_ops.update(_binary_ops)


def _build_expr (exprstr, params):

    expr, p = _build_expr_r(exprstr, 0, len(exprstr), params)
    if p < len(exprstr):
        error("invalid search expression: "
              "premature end of expression after '%s'" % exprstr[:p])
    return expr


def _build_expr_r (exprstr, start, end, params):

    p = start
    tstack = []
    can_unary = True
    can_binary = False
    can_operand = True
    while p < end:
        while p < end and exprstr[p].isspace() and exprstr[p] != ")":
            p += 1
        if p == end or exprstr[p] == ")":
            break

        # Parse current subexpression, matcher, or operator.
        if exprstr[p] == "(":
            if not can_operand:
                error("invalid search expression: "
                      "expected operator after '%s'" % exprstr[:p])
            expr, p = _build_expr_r(exprstr, p + 1, end, params)
            if p == end or exprstr[p] != ")":
                error("invalid search expression: "
                      "no closing parenthesis after '%s'" % exprstr[:p])
            tstack.append(expr)
            can_operand = False
            can_unary = False
            can_binary = True
            p += 1
        elif exprstr[p].isalpha():
            pp = p
            while p < end and exprstr[p].isalnum():
                p += 1
            tok = exprstr[pp:p].lower()
            if tok in _all_ops:
                if tok in _unary_ops and not can_unary:
                    error("invalid search expression: "
                          "unexpected unary operator after '%s'"
                          % exprstr[:pp])
                if tok in _binary_ops and not can_binary:
                    error("invalid search expression: "
                          "unexpected binary operator after '%s'"
                          % exprstr[:pp])
                can_operand = True
                can_unary = True
                can_binary = False
                tstack.append(tok)
            else:
                if not can_operand:
                    error("invalid search expression: "
                          "expected operator after '%s'" % exprstr[:pp])
                expr, p = _build_expr_matcher(tok, exprstr, p, end, params)
                tstack.append(expr)
                can_operand = False
                can_unary = False
                can_binary = True
        else:
            error("invalid search expression: "
                  "expected token starting with letter after '%s'"
                  % exprstr[:p + 1])

        # Update expression as possible.
        updated = True
        while updated:
            updated = False
            if (    len(tstack) >= 2
                and tstack[-2] in _unary_ops
                and tstack[-1] not in _all_ops
            ):
                def closure (): # for closure over cexpr*
                    cexpr1 = tstack.pop()
                    op = tstack.pop()
                    if op == "not":
                        cexpr = lambda *a: not cexpr1(*a)
                    else: # cannot happen
                        error("invalid search expression: "
                              "unknown unary operator '%s'" % op)
                    return cexpr
                tstack.append(closure())
                updated = True
            if (    len(tstack) >= 3
                and tstack[-3] not in _all_ops
                and tstack[-2] in _binary_ops
                and tstack[-1] not in _all_ops
            ):
                def closure (): # for closure over cexpr*
                    cexpr2 = tstack.pop()
                    op = tstack.pop()
                    cexpr1 = tstack.pop()
                    if op == "and":
                        cexpr = lambda *a: cexpr1(*a) and cexpr2(*a)
                    elif op == "or":
                        cexpr = lambda *a: cexpr1(*a) or cexpr2(*a)
                    else: # cannot happen
                        error("invalid search expression: "
                              "unknown binary operator '%s'" % op)
                    return cexpr
                tstack.append(closure())
                updated = True

    if len(tstack) >= 2:
        error("invalid search expression: "
              "premature end of expression after '%s'" % exprstr[:end])
    if len(tstack) == 0:
        error("invalid search expression: "
              "expected subexpression after '%s'" % exprstr[:start])

    return tstack[0], p


def _build_expr_matcher (mname, exprstr, start, end, params):

    if mname not in _all_matchers:
        error("invalid search expression: "
              "unknown matcher '%s' after '%s'" % (mname, exprstr[:start]))

    # Get matcher value, if any.
    mval = None
    p = start
    if mname in _op_matchers:
        c = exprstr[p:p + 1]
        if p == end or c.isspace() or c.isalnum() or c in ("(", ")"):
            error("invalid search expression: "
                  "expected parameter delimiter after '%s'" % exprstr[:p])
        delim = exprstr[p]
        pp = p + 1
        p = exprstr.find(delim, p + 1, end)
        if p < 0:
            error("invalid search expression: "
                  "expected closing delimiter after '%s'" % exprstr[:end - 1])
        mval = exprstr[pp:p]
    # Get match modifiers, if any.
    mmods = []
    c = exprstr[p:p + 1]
    if p < end and not c.isspace() and not c.isalnum() and c not in ("(", ")"):
        p += 1
        pp = p
        while p < end and exprstr[p].isalnum():
            p += 1
        mmods = list(exprstr[pp:p])

    #print "{%s}{%s}{%s}" % (mname, mval, mmods)
    return _create_matcher(mname, mval, mmods, params), p


_matcher_mods = {
    "msgctxt": ["c", "i"],
    "msgid": ["c", "i"],
    "msgstr": ["c", "i"],
    "comment": ["c", "i"],
}

def _create_matcher (name, value, mods, params, neg=False):

    known_mods = _matcher_mods.get(name, [])
    bad_mods = set(mods).difference(known_mods)
    if bad_mods:
        fmtmods = " ".join(bad_mods)
        error("unknown modifiers to '%s' matcher: %s" % (name, fmtmods))

    if name in _rx_matchers:
        rxflags = re.U
        if "i" in mods or (not params.case and "c" not in mods):
            rxflags |= re.I
        try:
            regex = re.compile(value, rxflags)
        except:
            error("cannot compile regular expression '%s'" % value)

    if 0: pass

    elif name == "msgctxt":
        def matcher (msgf, msg, cat, hl):
            texts = [(msgf.msgctxt, "msgctxt", 0)]
            return _rx_in_any_text(regex, texts, hl)

    elif name == "msgid":
        def matcher (msgf, msg, cat, hl):
            texts = [(msgf.msgid, "msgid", 0),
                     (msgf.msgid_plural, "msgid_plural", 0)]
            return _rx_in_any_text(regex, texts, hl)

    elif name == "msgstr":
        def matcher (msgf, msg, cat, hl):
            texts = [(msgf.msgstr[i], "msgstr", i)
                     for i in range(len(msgf.msgstr))]
            return _rx_in_any_text(regex, texts, hl)

    elif name == "comment":
        def matcher (msgf, msg, cat, hl):
            texts = []
            texts.extend([(msgf.manual_comment[i], "manual_comment", i)
                          for i in range(len(msgf.manual_comment))])
            texts.extend([(msgf.auto_comment[i], "auto_comment", i)
                          for i in range(len(msgf.auto_comment))])
            #FIXME: How to search flags and sources? Mind highlighting.
            #texts.append((", ".join(msgf.flag), "flag", 0))
            #texts.append((" ".join(["%s:%s" % x for x in msgf.source]),
                          #"source", 0))
            return _rx_in_any_text(regex, texts, hl)

    elif name == "transl":
        def matcher (msgf, msg, cat, hl):
            if value is None or value:
                return msg.translated
            else:
                return not msg.translated

    elif name == "plural":
        def matcher (msgf, msg, cat, hl):
            if value is None or value:
                return msg.msgid_plural != ""
            else:
                return msg.msgid_plural == ""

    elif name == "maxchar":
        def matcher (msgf, msg, cat, hl):
            otexts = [msgf.msgid]
            if msgf.msgid_plural:
                otexts.append(msgf.msgid_plural)
            ttexts = msgf.msgstr
            onchar = sum([len(x) for x in otexts]) // len(otexts)
            tnchar = sum([len(x) for x in ttexts]) // len(ttexts)
            return onchar <= value and tnchar <= value

    else:
        error("unknown matcher '%s'" % name)

    if neg:
        return lambda *a: not matcher(*a)
    else:
        return matcher


def _rx_in_any_text (regex, texts, hl):

    match = False
    for text, hl_name, hl_item in texts:
        # Go through all matches, to highlight them all.
        for m in regex.finditer(text):
            hl_key = (hl_name, hl_item)
            if hl_key not in hl:
                hl[hl_key] = ([], text)
            hl[hl_key][0].append(m.span())
            match = True

    return match

