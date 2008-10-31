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

If more than one of the matching parameters are given (e.g. both C{msgid} and
C{msgstr}), the message matches only if all of them match. In case of plural
messages, C{msgid} is considered matched if either C{msgid} or C{msgid_plural}
fields match, and C{msgstr} if any of the C{msgstr} fields match.

Every matching option has a counterpart with prepended C{n*},
by which the meaning of the match is inverted; for example, if both
C{msgid:foo} and C{nmsgid:bar} are given, then the message matches
if its C{msgid} contains C{foo} but does not contain C{bar}.

Sieve parameters for replacement:
  - C{replace:<string>}: string to replace matched part of translation

The C{replace} option must go together with the C{msgstr} match. As usual for regular expression replacement, the replacement string may contain C{\<number>} references to groups defined by C{msgstr} match.

Other sieve parameters:
  - C{accel:<chars>}: strip these characters as accelerator markers
  - C{case}: case-sensitive match (insensitive by default)
  - C{mark}: mark each matched message with a flag
  - C{filter:[<lang>:]<name>,...}: apply filters to msgstr prior to matching
  - C{maxchar}: ignore messages with more than this number of characters

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

from pology.misc.report import error, warning
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
    p.add_param("maxchar", int, defval=0,
                metavar="NUM",
                desc=
    "Matches if the msgstr field has at most this many characters "
    "(0 or less means any number of characters)."
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


class Sieve (object):


    def __init__ (self, params, options):

        self.nmatch = 0

        self.p = params

        self.rxflags = re.U
        if not self.p.case:
            self.rxflags |= re.I

        self.field_matches = []
        has_msgstr_match = False
        for field in ("msgctxt", "msgid", "msgstr", "comment"):
            rxstr = None
            for value in getattr(params, field) or []:
                regex = re.compile(value, self.rxflags)
                self.field_matches.append((field, regex, False))
                if field == "msgstr":
                    has_msgstr_match = True
            nfield = "n%s" % field
            for value in getattr(params, nfield) or []:
                regex = re.compile(value, self.rxflags)
                self.field_matches.append((field, regex, True))

        if self.p.replace is not None:
            if not has_msgstr_match:
                error("no msgstr search pattern provided for replacement")

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
        if self.p.transl and not msg.translated:
            return
        if self.p.ntransl and msg.translated:
            return
        if self.p.plural and not msg.msgid_plural:
            return
        if self.p.nplural and msg.msgid_plural:
            return

        # Prepare filtered message for matching.
        msgf = MessageUnsafe(msg)

        # - remove accelerators
        remove_accel_msg(msgf, cat)

        # - apply msgstr filters
        for pfilter in self.pfilters:
            for i in range(len(msgf.msgstr)):
                msgf.msgstr[i] = pfilter(msgf.msgstr[i])

        # Match requested fields.
        match = not self.p.or_match
        hl_spec = {}
        for field, regex, invert in self.field_matches:

            # Select texts for matching, with highlight info.
            pfilters = []
            if field == "msgctxt":
                texts = [(msgf.msgctxt, "msgctxt", 0)]
            elif field == "msgid":
                texts = [(msgf.msgid, "msgid", 0),
                         (msgf.msgid_plural, "msgid_plural", 0)]
            elif field == "msgstr":
                texts = [(msgf.msgstr[i], "msgstr", i)
                         for i in range(len(msgf.msgstr))]
            elif field == "comment":
                texts = []
                texts.extend([(msgf.manual_comment[i], "cmanual", i)
                              for i in range(len(msgf.manual_comment))])
                texts.extend([(msgf.auto_comment[i], "cauto", i)
                              for i in range(len(msgf.auto_comment))])
                texts.append((", ".join(msgf.flag), "", 0))
                texts.append((" ".join(["%s:%s" % x for x in msgf.source]),
                              "", 0))
            else:
                error("unknown search field '%s'" % field)

            if self.p.maxchar > 0 and field in ("msgid", "msgstr"):
                nchar = sum([len(x[0]) for x in texts]) // len(texts)
                if nchar > self.p.maxchar:
                    match = False
                    break

            local_match = False

            for text, hl_name, hl_item in texts:

                # Check for local match (local match is OR).
                m = regex.search(text)
                if m:
                    local_match = True

                    hl_key = (hl_name, hl_item)
                    if hl_key not in hl_spec:
                        hl_spec[hl_key] = ([], text)
                    hl_spec[hl_key][0].append(m.span())

                    break

            # Invert meaning of the match if requested.
            if invert:
                local_match = not local_match

            # Check for global match.
            if self.p.or_match:
                match = match or local_match
            else:
                match = match and local_match
            if not match:
                break

            # Do the replacement in translation if requested.
            # NOTE: Use the real, not the filtered message.
            if field == "msgstr" and self.p.replace is not None:
                for i in range(len(msg.msgstr)):
                    msg.msgstr[i] = regex.sub(self.p.replace, msg.msgstr[i])

        if match:
            self.nmatch += 1
            if not self.p.mark:
                delim = "-" * 20
                if self.nmatch == 1:
                    print delim
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
            print "Total matching: %d" % (self.nmatch,)

