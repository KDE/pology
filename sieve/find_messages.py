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
        to matching (see L{misc.langdep.get_hook_lreq} for the format
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

import sys
import os
import re
import locale

from pology.sieve import SieveError
from pology.misc.report import report, error, warning
from pology.misc.msgreport import report_msg_content
from pology.misc.msgreport import report_msg_to_lokalize
from pology.misc.langdep import get_hook_lreq
from pology.misc.stdsvpar import add_param_poeditors
from pology.file.message import MessageUnsafe
from pology.hook.remove_subs import remove_accel_msg
from pology.misc.comments import parse_summit_branches


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
    "This can be changed to OR-semantics for matching in text fields "
    "(msgctxt, msgid, msgstr, comment) "
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
    p.add_param("obsol", bool,
                desc=
    "Matches if the message is obsolete."
    )
    p.add_param("nobsol", bool,
                desc=
    "Matches if the message is not obsolete."
    )
    p.add_param("active", bool,
                desc=
    "Matches if the message is active (translated and not obsolete)."
    )
    p.add_param("nactive", bool,
                desc=
    "Matches if the message is not active (not translated or obsolete)."
    )
    p.add_param("flag", unicode, multival=True,
                metavar="REGEX",
                desc=
    "Matches if one of the flags matches the regular expression."
    )
    p.add_param("nflag", unicode, multival=True,
                metavar="REGEX",
                desc=
    "Matches if none of the flags matches the regular expression."
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
    p.add_param("lspan", unicode,
                metavar="START:END",
                desc=
    "Matches if the message line number is in the given range "
    "(including starting line, excluding ending line)."
    )
    p.add_param("nlspan", unicode,
                metavar="START:END",
                desc=
    "Matches if the message line number is not in the given range "
    "(including starting line, excluding ending line)."
    )
    p.add_param("espan", unicode,
                metavar="START:END",
                desc=
    "Matches if the message entry number is in the given range "
    "(including starting entry, excluding ending entry)."
    )
    p.add_param("nespan", unicode,
                metavar="START:END",
                desc=
    "Matches if the message entry number is not in the given range "
    "(including starting entry, excluding ending entry)."
    )
    p.add_param("branch", unicode, seplist=True,
                metavar="BRANCH",
                desc=
    "In summited catalogs, match only messages belonging to given branch. "
    "Several branches can be given as comma-separated list."
    )
    p.add_param("nbranch", unicode, seplist=True,
                metavar="BRANCH",
                desc=
    "Match only messages not belonging to given branch."
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
    p.add_param("invert", bool, defval=False,
                desc=
    "Invert the condition: report messages which do not match."
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
    p.add_param("filter", unicode, multival=True,
                metavar="HOOKSPEC",
                desc=
    "F1A hook specification, to filter the msgstr fields through "
    "before matching them. "
    "Several hooks can be specified either by repeating the parameter."
    )
    p.add_param("replace", unicode,
                metavar="REPLSTR",
                desc=
    "Replace all substrings matched by msgstr pattern with REPLSTR. "
    "It can include back-references to matched groups (\\1, \\2, etc.)"
    )
    p.add_param("nomsg", bool, defval=False,
                desc=
    "Do not report message to standard output "
    "(when only the number of matches is wanted)."
    )
    add_param_poeditors(p)


_flag_mark = u"match"


# Matchers taking a value.
_op_matchers = set(["msgctxt", "msgid", "msgstr", "comment", "flag", "branch"])
# Matchers not taking a value.
_nop_matchers = set(["transl", "obsol", "active", "plural"])

# Matchers which produce a regular expression out of their value.
_rx_matchers = set(["msgctxt", "msgid", "msgstr", "comment", "flag"])

# All matchers together.
_all_matchers = set()
_all_matchers.update(_op_matchers)
_all_matchers.update(_nop_matchers)


class Sieve (object):


    def __init__ (self, params):

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
                    try:
                        if name == "fexpr":
                            m = build_msg_matcher(value, params)
                        else:
                            m = _create_matcher(name, value, [], params, neg)
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
        expr_and = create_match_group([
            "transl", "obsol", "active", "plural", "maxchar", "lspan", "espan",
            "flag", "branch",
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
                raise SieveError("cannot replace if no msgstr pattern given")
            rxflags = re.U
            if not self.p.case:
                rxflags |= re.I
            for rxstr in self.p.msgstr:
                self.replrxs.append(re.compile(rxstr, rxflags))

        # Resolve filtering hooks.
        self.pfilters = []
        for hreq in self.p.filter or []:
            self.pfilters.append(get_hook_lreq(hreq, abort=True))

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
        msgf = _prepare_filtered_msg(msg, cat, filters=self.pfilters)

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
            report("Total matching: %d" % self.nmatch)


_all_ops = set()
_unary_ops = set(["not"])
_all_ops.update(_unary_ops)
_binary_ops = set(["and", "or"])
_all_ops.update(_binary_ops)


class ExprError (Exception):
    """
    Exception for errors in message matching expressions.
    """

    def __init__ (self, expr=None, msg=None, start=None, end=None):
        """
        Constructor.

        All the parameters are made available as instance variables.

        @param expr: the complete expression that caused the problem
        @type expr: string or None
        @param msg: the description of the problem
        @type msg: string or None
        @param start: start position of the problem into the expression string
        @type start: int or None
        @param end: end position of the problem
        @type end: int or None
        """

        self.expr = expr
        self.msg = msg
        self.start = start
        self.end = end


    def __unicode__ (self):

        if self.expr is not None and self.start is not None:
            start = self.start
            if self.end is not None:
                end = self.end
            else:
                end = self.start + 10
            subexpr = self.expr[start:end]
            if start > 0:
                subexpr = "..." + subexpr
            if end < len(self.expr):
                subexpr = subexpr + "..."
        else:
            subexpr = None

        if self.msg is not None and subexpr is not None:
            repstr = ("invalid expression at %d [%s]: %s"
                      % (self.start, subexpr, self.msg))
        elif self.msg is not None:
            repstr = "invalid expression: %s" % self.msg
        elif subexpr is not None:
            repstr = ("invalid expression at %d [%s]" % (self.start, subexpr))
        else:
            repstr = "invalid expression"

        return unicode(repstr)


    def __str__ (self):

        return self.__unicode__().encode(locale.getpreferredencoding())



def build_msg_matcher (exprstr, mopts=None, abort=False):
    """
    Build expression matcher for messages.

    For expression syntax, see this module documentation on C{fexpr}
    sieve parameter.

    The C{mopts} parameter, if given, defines global matching options.
    It can be either a dictionary or an object with data attributes,
    and can contain the following keys/attributes (in parenthesis:
    type and default value in case the key is not present):

      - C{case} (C{bool}, C{False}): C{True} for case-sensitive matching

    The built matcher function takes up to four parameters, in order:

      - C{msgf}: filtered message (to really match against)
      - C{msg}: raw message (to properly report matched spans)
      - C{cat}: catalog in which the message resides
      - C{hl}: L{highlight specification<misc.msgreport.report_msg_content>}
        (to be filled with matched spans, can be omitted from the call)

    Matcher function returns C{True} if the message is matched,
    C{False} otherwise.

    In case an error in expression is encountered while building the matcher,
    either L{ExprError} exception may be thrown or execution aborted,
    depending on the parameter C{abort}.

    @param exprstr: expression string
    @type exprstr: string
    @param mopts: global matching options
    @type mopts: dict or attribute object
    @param abort: on errors in expression, abort execution if C{True},
        raise L{ExprError} if C{False}
    @type abort: bool

    @return: matcher function
    @rtype: (msgf, msg, cat, hl=[])->bool
    """

    mopts = _prep_attrobj(mopts, dict(
        case=False,
    ))

    try:
        expr, p = _build_expr_r(exprstr, 0, len(exprstr), mopts)
        if p < len(exprstr):
            raise ExprError(exprstr, "premature end of expression")
    except ExprError, e:
        if abort:
            error(unicode(e))
        else:
            raise
    return expr


def build_msg_fmatcher (exprstr, mopts=None,
                        accels=None, filters=[], abort=False):
    """
    Build expression matcher for messages, with filtering.

    Like L{build_msg_matcher}, except that matchers built by this function
    do their own filtering, and so omit the first argument.

    For semantics of C{accels} and C{filters}, see this module documentation
    on C{accel} and C{filter} sieve parameters.

    @param exprstr: expression string
    @type exprstr: string
    @param mopts: global matching options
    @type mopts: attribute object
    @param accels: possible accelerator markers
    @type accels: sequence of strings or C{None}
    @param filters: filters to apply to text fields [F1A hooks]
    @type filters: (text)->text
    @param abort: on errors, abort execution if C{True},
        raise exception if C{False}
    @type abort: bool

    @return: matcher function
    @rtype: (msg, cat, hl=[])->bool
    """

    raw_matcher = build_msg_matcher(exprstr, mopts=mopts, abort=abort)

    def matcher (msg, cat, hl=[]):
        msgf = _prepare_filtered_msg(msg, cat, accels, filters)
        return raw_matcher(msgf, msg, cat, hl)

    return matcher


def _prep_attrobj (aobj, dctdef=None):

    if aobj is None or isinstance(aobj, dict):
        dct = aobj or {}
        class _Data: pass
        aobj = _Data()
        for key, value in dct.items():
            setattr(aobj, key, value)

    for key, val in (dctdef or {}).items():
        if not hasattr(aobj, key):
            setattr(aobj, key, val)

    return aobj


def _prepare_filtered_msg (msg, cat, accels=None, filters=[]):

    # Must not modify contents of real message.
    msgf = MessageUnsafe(msg)

    # - remove accelerators
    if accels is not None:
        old_accels = cat.accelerator()
        cat.set_accelerator(accels)
    remove_accel_msg(msgf, cat)
    if accels is not None:
        cat.set_accelerator(old_accels)
    # - apply msgstr filters
    for filtr in filters:
        for i in range(len(msgf.msgstr)):
            msgf.msgstr[i] = filtr(msgf.msgstr[i])

    return msgf


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
                raise ExprError(exprstr, "expected operator", p)
            expr, p = _build_expr_r(exprstr, p + 1, end, params)
            if p == end or exprstr[p] != ")":
                raise ExprError(exprstr, "no closing parenthesis", p)
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
                    raise ExprError(exprstr, "unexpected unary operator", pp)
                if tok in _binary_ops and not can_binary:
                    raise ExprError(exprstr, "unexpected binary operator", pp)
                can_operand = True
                can_unary = True
                can_binary = False
                tstack.append(tok)
            else:
                if not can_operand:
                    raise ExprError(exprstr, "expected an operator", pp)
                expr, p = _build_expr_matcher(tok, exprstr, p, end, params)
                tstack.append(expr)
                can_operand = False
                can_unary = False
                can_binary = True
        else:
            raise ExprError(exprstr,
                            "expected token starting with a letter", p + 1)

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
                        raise ExprError(exprstr,
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
                        raise ExprError(exprstr,
                                        "unknown binary operator '%s'" % op)
                    return cexpr
                tstack.append(closure())
                updated = True

    if len(tstack) >= 2:
        raise ExprError(exprstr, "premature end of expression", end)
    if len(tstack) == 0:
        raise ExprError(exprstr, "expected subexpression", start)

    return tstack[0], p


def _build_expr_matcher (mname, exprstr, start, end, params):

    if mname not in _all_matchers:
        raise ExprError(exprstr, "unknown matcher '%s'" % mname,
                        start - len(mname))

    # Get matcher value, if any.
    mval = None
    p = start
    if mname in _op_matchers:
        c = exprstr[p:p + 1]
        if p == end or c.isspace() or c.isalnum() or c in ("(", ")"):
            raise ExprError(exprstr, "expected parameter delimiter", p)
        delim = exprstr[p]
        pp = p + 1
        p = exprstr.find(delim, p + 1, end)
        if p < 0:
            raise ExprError(exprstr, "expected closing delimiter", end - 1)
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
        raise ExprError(None,
                        "unknown modifiers to '%s' matcher: %s"
                        % (name, " ".join(bad_mods)))

    if name in _rx_matchers:
        rxflags = re.U
        if "i" in mods or (not params.case and "c" not in mods):
            rxflags |= re.I
        try:
            regex = re.compile(value, rxflags)
        except:
            raise ExprError(None,
                            "cannot compile regular expression '%s'" % value)

    if 0: pass

    elif name == "msgctxt":
        def matcher (msgf, msg, cat, hl=[]):
            texts = []
            if msgf.msgctxt is not None:
                texts += [(msgf.msgctxt, "msgctxt", 0)]
            return _rx_in_any_text(regex, texts, hl)

    elif name == "msgid":
        def matcher (msgf, msg, cat, hl=[]):
            texts = [(msgf.msgid, "msgid", 0)]
            if msgf.msgid_plural is not None:
                texts += [(msgf.msgid_plural, "msgid_plural", 0)]
            return _rx_in_any_text(regex, texts, hl)

    elif name == "msgstr":
        def matcher (msgf, msg, cat, hl=[]):
            texts = [(msgf.msgstr[i], "msgstr", i)
                     for i in range(len(msgf.msgstr))]
            return _rx_in_any_text(regex, texts, hl)

    elif name == "comment":
        def matcher (msgf, msg, cat, hl=[]):
            texts = []
            texts.extend([(msgf.manual_comment[i], "manual_comment", i)
                          for i in range(len(msgf.manual_comment))])
            texts.extend([(msgf.auto_comment[i], "auto_comment", i)
                          for i in range(len(msgf.auto_comment))])
            texts.extend([(msgf.source[i][0], "source", i)
                          for i in range(len(msgf.source))])
            #FIXME: How to search flags? Mind highlighting.
            #texts.append((", ".join(msgf.flag), "flag", 0))
            return _rx_in_any_text(regex, texts, hl)

    elif name == "transl":
        def matcher (msgf, msg, cat, hl=[]):
            if value is None or value:
                return msg.translated
            else:
                return not msg.translated

    elif name == "obsol":
        def matcher (msgf, msg, cat, hl=[]):
            if value is None or value:
                return msg.obsolete
            else:
                return not msg.obsolete

    elif name == "active":
        def matcher (msgf, msg, cat, hl=[]):
            if value is None or value:
                return msg.translated and not msg.obsolete
            else:
                return not msg.translated or msg.obsolete

    elif name == "plural":
        def matcher (msgf, msg, cat, hl=[]):
            if value is None or value:
                return msg.msgid_plural is not None
            else:
                return msg.msgid_plural is None

    elif name == "maxchar":
        def matcher (msgf, msg, cat, hl=[]):
            otexts = [msgf.msgid]
            if msgf.msgid_plural is not None:
                otexts.append(msgf.msgid_plural)
            ttexts = msgf.msgstr
            onchar = sum([len(x) for x in otexts]) // len(otexts)
            tnchar = sum([len(x) for x in ttexts]) // len(ttexts)
            return onchar <= value and tnchar <= value

    elif name == "lspan":
        def matcher (msgf, msg, cat, hl=[]):
            try:
                start, end = value.split(":", 1)
                start = int(start) if start else 0
                end = int(end) if end else (cat[-1].refline + 1)
            except:
                raise ExprError("Invalid line span specification '%s'."
                                % value)
            return msg.refline >= start and msg.refline < end

    elif name == "espan":
        def matcher (msgf, msg, cat, hl=[]):
            try:
                start, end = value.split(":", 1)
                start = int(start) if start else 0
                end = int(end) if end else (cat[-1].refentry + 1)
            except:
                raise ExprError("Invalid entry span specification '%s'."
                                % value)
            return msg.refentry >= start and msg.refentry < end

    elif name == "branch":
        def matcher (msgf, msg, cat, hl=[]):
            return value in parse_summit_branches(msg)

    elif name == "flag":
        def matcher (msgf, msg, cat, hl=[]):
            #FIXME: How to highlight flags? (then use _rx_in_any_text)
            for flag in msgf.flag:
                if regex.search(flag):
                    return True
            return False

    else:
        raise ExprError(None, "unknown matcher '%s'" % name)

    if neg:
        return lambda *a: not matcher(*a)
    else:
        return matcher


def _rx_in_any_text (regex, texts, hl):

    match = False
    hl_dct = {}
    for text, hl_name, hl_item in texts:
        # Go through all matches, to highlight them all.
        for m in regex.finditer(text):
            hl_key = (hl_name, hl_item)
            if hl_key not in hl_dct:
                hl_dct[hl_key] = ([], text)
            hl_dct[hl_key][0].append(m.span())
            match = True

    hl.extend([x + y for x, y in hl_dct.items()])

    return match

