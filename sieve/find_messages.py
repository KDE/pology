# -*- coding: UTF-8 -*-

"""
Find messages by regular expression matching.

Matches the regular expression against requested elements of the message,
and reports the message if the match exists. Every matched message is
reported to standard output, with the name of the file from which it comes,
and referent line and entry number within the file.

Sieve options for matching:
  - C{msgctxt:<regex>}: regular expression to match against the C{msgctxt}
  - C{msgid:<regex>}: regular expression to match against the C{msgid}
  - C{msgstr:<regex>}: regular expression to match against the C{msgstr}
  - C{comment:<regex>}: regular expression to match against comments
  - C{transl}: the message must be translated
  - C{plural}: the message must be plural

If more than one of the matching options are given (e.g. both C{msgid} and
C{msgstr}), the message matches only if all of them match. In case of plural
messages, C{msgid} is considered matched if either C{msgid} or C{msgid_plural}
fields match, and C{msgstr} if any of the C{msgstr} fields match.

Every matching option has a counterpart with prepended C{n*},
by which the meaning of the match is inverted; for example, if both
C{msgid:foo} and C{nmsgid:bar} are given, then the message matches
if its C{msgid} contains C{foo} but does not contain C{bar}.

Sieve options for replacement:
  - C{replace:<string>}: string to replace matched part of translation

The C{replace} option must go together with the C{msgstr} match. As usual for regular expression replacement, the replacement string may contain C{\<number>} references to groups defined by C{msgstr} match.

Other sieve options:
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

import sys, os, re
from pology.misc.report import error, report_msg_content
from pology.misc.langdep import get_hook_lreq
from pology.misc.wrap import wrap_field, wrap_field_unwrap
from pology.file.message import MessageUnsafe
from pology.hook.remove_subs import remove_accel_msg


_flag_mark = u"pattern-match"


class Sieve (object):

    def __init__ (self, options, global_options):

        self.nmatch = 0

        self.accels = None
        if "accel" in options:
            options.accept("accel")
            self.accels = list(options["accel"])

        self.rxflags = re.U
        if "case" in options:
            options.accept("case")
        else:
            self.rxflags |= re.I

        self.field_matches = []
        has_msgstr_match = False
        for field in ("msgctxt", "msgid", "msgstr", "comment"):
            rxstr = None
            if field in options:
                options.accept(field)
                regex = re.compile(options[field], self.rxflags)
                self.field_matches.append((field, regex, False))
                if field == "msgstr":
                    has_msgstr_match = True
            nfield = "n%s" % field
            if nfield in options:
                options.accept(nfield)
                rxstr = options[nfield]
                regex = re.compile(options[nfield], self.rxflags)
                self.field_matches.append((field, regex, True))

        if not self.field_matches:
            error("no search pattern for a message field given")

        self.replace = None
        if "replace" in options:
            if not has_msgstr_match:
                error("no msgstr search pattern provided for replacement")
            options.accept("replace")
            self.replace = options["replace"]

        self.mark = False
        if "mark" in options:
            options.accept("mark")
            self.mark = True

        self.pfilters = []
        if "filter" in options:
            options.accept("filter")
            freqs = options["filter"].split(",")
            self.pfilters = [get_hook_lreq(x, abort=True) for x in freqs]

        self.transl = False
        if "transl" in options:
            options.accept("transl")
            self.transl = True
        self.untran = False
        if "ntransl" in options:
            options.accept("ntransl")
            self.untran = True

        self.plural = False
        if "plural" in options:
            options.accept("plural")
            self.plural = True
        self.nonplural = False
        if "nplural" in options:
            options.accept("nplural")
            self.nonplural = True

        self.maxchar = None
        if "maxchar" in options:
            options.accept("maxchar")
            self.maxchar = int(options["maxchar"])

        # Unless replacement or marking requested, no need to monitor/sync.
        if self.replace is None and not self.mark:
            self.caller_sync = False
            self.caller_monitored = False

        # Select wrapping for reporting messages.
        if global_options.do_wrap:
            self.wrapf = wrap_field
        else:
            self.wrapf = wrap_field_unwrap


    def process_header (self, hdr, cat):

        # Force explicitly given accelerators.
        if self.accels is not None:
            cat.set_accelerator(self.accels)


    def process (self, msg, cat):

        if msg.obsolete:
            return
        if self.transl and not msg.translated:
            return
        if self.untran and msg.translated:
            return
        if self.plural and not msg.msgid_plural:
            return
        if self.nonplural and msg.msgid_plural:
            return

        # Prepare filtered message for matching.
        msgf = MessageUnsafe(msg)

        # - remove accelerators
        remove_accel_msg(cat, msgf)

        # - apply msgstr filters
        for pfilter in self.pfilters:
            for i in range(len(msgf.msgstr)):
                msgf.msgstr[i] = pfilter(msgf.msgstr[i])

        # Match requested fields.
        match = True
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

            if self.maxchar is not None and field in ("msgid", "msgstr"):
                nchar = sum([len(x[0]) for x in texts]) // len(texts)
                if nchar > self.maxchar:
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

            # Check for global match (global match is AND).
            if not local_match:
                match = False
                break

            # Do the replacement in translation if requested.
            # NOTE: Use the real, not the filtered message.
            if field == "msgstr" and self.replace is not None:
                for i in range(len(msg.msgstr)):
                    msg.msgstr[i] = regex.sub(self.replace, msg.msgstr[i])

        if match:
            self.nmatch += 1
            if not self.mark:
                delim = "-" * 20
                if self.nmatch == 1:
                    print delim
                highlight = [x + y for x, y in hl_spec.items()]
                report_msg_content(msg, cat, wrapf=self.wrapf, force=True,
                                   delim=delim, highlight=highlight)
            else:
                msg.flag.add(_flag_mark)

        elif self.mark and _flag_mark in msg.flag:
            # Remove the flag if present but the message does not match.
            msg.flag.remove(_flag_mark)


    def finalize (self):

        if self.nmatch:
            print "Total matching: %d" % (self.nmatch,)

