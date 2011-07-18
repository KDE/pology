# -*- coding: UTF-8 -*-

"""
Matchers and matcher helpers for various objects.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import re

from pology import _, n_
from pology.comments import parse_summit_branches
from pology.message import MessageUnsafe
from pology.remove import remove_accel_msg
from pology.report import error


_all_ops = set()
_unary_ops = set(["not"])
_all_ops.update(_unary_ops)
_binary_ops = set(["and", "or"])
_all_ops.update(_binary_ops)

class ExprError (Exception):
    """
    Exception for errors in matching expressions.
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
            repstr = _("@info",
                       "Invalid expression at %(col)d [%(snippet)s]: "
                       "%(reason)s.",
                       col=self.start, snippet=subexpr, reason=self.msg)
        elif self.msg is not None:
            repstr = _("@info",
                       "Invalid expression: %(reason)s.",
                       reason=self.msg)
        elif subexpr is not None:
            repstr = _("@info",
                       "Invalid expression at %(col)d [%(snippet)s].",
                       col=self.start, snippet=subexpr)
        else:
            repstr = _("@info", "Invalid expression.")

        return unicode(repstr)


    def __str__ (self):

        return self.__unicode__().encode(locale.getpreferredencoding())


def make_filtered_msg (msg, cat, accels=None, filters=[]):
    """
    TODO: Write documentation.
    """

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


def make_msg_matcher (exprstr, mopts=None, abort=False):
    """
    Build expression matcher for messages.

    For expression syntax, check C{find-messages} sieve documentation
    for C{fexpr} parameter.
    TODO: Put this instruction here.

    The C{mopts} parameter, if given, defines global matching options.
    It can be either a dictionary or an object with data attributes,
    and can contain the following keys/attributes (in parenthesis:
    type and default value in case the key is not present):

      - C{case} (C{bool}, C{False}): C{True} for case-sensitive matching

    The built matcher function takes up to four parameters, in order:

      - C{msgf}: filtered message (to really match against)
      - C{msg}: raw message (to properly report matched spans)
      - C{cat}: catalog in which the message resides
      - C{hl}: L{highlight specification<msgreport.report_msg_content>}
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
            raise ExprError(exprstr, _("@item:intext",
                                       "premature end of expression"))
    except ExprError, e:
        if abort:
            error(unicode(e))
        else:
            raise
    return expr


def make_msg_fmatcher (exprstr, mopts=None,
                       accels=None, filters=[], abort=False):
    """
    Build expression matcher for messages, with filtering.

    Like L{make_msg_matcher}, except that matchers built by this function
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

    raw_matcher = make_msg_matcher(exprstr, mopts=mopts, abort=abort)

    def matcher (msg, cat, hl=[]):
        msgf = make_filtered_msg(msg, cat, accels, filters)
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
                raise ExprError(exprstr, _("@item:intext",
                                           "expected operator"), p)
            expr, p = _build_expr_r(exprstr, p + 1, end, params)
            if p == end or exprstr[p] != ")":
                raise ExprError(exprstr, _("@item:intext",
                                           "no closing parenthesis"), p)
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
                    raise ExprError(exprstr, _("@item:intext",
                                              "unexpected unary operator"), pp)
                if tok in _binary_ops and not can_binary:
                    raise ExprError(exprstr,
                                    _("@item:intext",
                                      "unexpected binary operator"), pp)
                can_operand = True
                can_unary = True
                can_binary = False
                tstack.append(tok)
            else:
                if not can_operand:
                    raise ExprError(exprstr, _("@item:intext",
                                               "expected an operator"), pp)
                expr, p = _build_expr_matcher(tok, exprstr, p, end, params)
                tstack.append(expr)
                can_operand = False
                can_unary = False
                can_binary = True
        else:
            raise ExprError(exprstr,
                            _("@item:intext",
                              "expected token starting with a letter"), p + 1)

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
                                        _("@item:intext",
                                          "unknown unary operator '%(op)s'",
                                          op=op))
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
                                        _("@item:intext",
                                          "unknown binary operator '%(op)s'",
                                          op=op))
                    return cexpr
                tstack.append(closure())
                updated = True

    if len(tstack) >= 2:
        raise ExprError(exprstr, _("@item:intext",
                                   "premature end of expression"), end)
    if len(tstack) == 0:
        raise ExprError(exprstr, _("@item:intext",
                                   "expected subexpression"), start)

    return tstack[0], p


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

def _build_expr_matcher (mname, exprstr, start, end, params):

    if mname not in _all_matchers:
        raise ExprError(exprstr, _("@item:intext",
                                   "unknown matcher '%(match)s'",
                                   match=mname),
                        start - len(mname))

    # Get matcher value, if any.
    mval = None
    p = start
    if mname in _op_matchers:
        c = exprstr[p:p + 1]
        if p == end or c.isspace() or c.isalnum() or c in ("(", ")"):
            raise ExprError(exprstr, _("@item:intext",
                                       "expected parameter delimiter"), p)
        delim = exprstr[p]
        pp = p + 1
        p = exprstr.find(delim, p + 1, end)
        if p < 0:
            raise ExprError(exprstr, _("@item:intext",
                                       "expected closing delimiter"), end - 1)
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
    return make_matcher(mname, mval, mmods, params), p


_matcher_mods = {
    "msgctxt": ["c", "i"],
    "msgid": ["c", "i"],
    "msgstr": ["c", "i"],
    "comment": ["c", "i"],
}

def make_matcher (name, value, mods, params, neg=False):
    """
    TODO: Write documentation.
    """

    known_mods = _matcher_mods.get(name, [])
    bad_mods = set(mods).difference(known_mods)
    if bad_mods:
        raise ExprError(None,
                        _("@item:intext",
                          "unknown modifiers %(modlist)s "
                          "to matcher '%(match)s'",
                          modlist=format_item_list(bad_mods), match=name))

    if name in _rx_matchers:
        rxflags = re.U
        if "i" in mods or (not params.case and "c" not in mods):
            rxflags |= re.I
        try:
            regex = re.compile(value, rxflags)
        except:
            raise ExprError(None, _("@item:intext",
                                    "invalid regular expression '%(regex)s'",
                                    regex=value))

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
        try:
            start, end = value.split(":", 1)
            start = int(start) if start else 0
            end = int(end) if end else None
        except:
            raise ExprError(value, _("@item:intext", "invalid line span"), 0)
        def matcher (msgf, msg, cat, hl=[]):
            cend = end
            if cend is None:
                cend = cat[-1].refline + 1
            return msg.refline >= start and msg.refline < cend

    elif name == "espan":
        try:
            start, end = value.split(":", 1)
            start = int(start) if start else 0
            end = int(end) if end else None
        except:
            raise ExprError(value, _("@item:intext", "invalid entry span"), 0)
        def matcher (msgf, msg, cat, hl=[]):
            cend = end
            if cend is None:
                cend = cat[-1].refentry + 1
            return msg.refentry >= start and msg.refentry < cend

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
        raise ExprError(name, _("@item:intext", "unknown matcher"), 0)

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

