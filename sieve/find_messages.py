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

If more than one of the matching options are given (e.g. both C{msgid} and
C{msgstr}), the message matches only if all of them match. In case of plural
messages, C{msgid} is considered matched if either C{msgid} or C{msgid_plural}
fields match, and C{msgstr} if any of the C{msgstr} fields match.

Sieve options for replacement:
  - C{replace:<string>}: string to replace matched part of translation

The C{replace} option must go together with the C{msgstr} match. As usual for regular expression replacement, the replacement string may contain C{\<number>} references to groups defined by C{msgstr} match.

Other sieve options:
  - C{accel:<char>}: strip this character as an accelerator marker
  - C{case}: case-sensitive match (insensitive by default)
  - C{mark}: mark each matched message with a flag

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

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import sys, os, re
from pology.misc.report import error, report_msg_content


_flag_mark = u"pattern-match"


class Sieve (object):

    def __init__ (self, options, global_options):

        self.nmatch = 0

        self.accel_explicit = False
        self.accel = ""
        if "accel" in options:
            options.accept("accel")
            self.accel = options["accel"]
            self.accel_explicit = True

        self.rxflags = re.U
        if "case" in options:
            options.accept("case")
        else:
            self.rxflags |= re.I

        self.fields = []
        self.regexs = []
        for field in ("msgctxt", "msgid", "msgstr"):
            if field in options:
                options.accept(field)
                self.fields.append(field)
                self.regexs.append(re.compile(options[field], self.rxflags))

        if not self.fields:
            error("no search pattern given")

        self.replace = None
        if "replace" in options:
            if "msgstr" not in self.fields:
                error("no msgstr pattern provided for replacement")
            options.accept("replace")
            self.replace = options["replace"]

        self.mark = False
        if "mark" in options:
            options.accept("mark")
            self.mark = True

        # Unless replacement or marking requested, no need to monitor/sync.
        if self.replace is None and not self.mark:
            self.caller_sync = False
            self.caller_monitored = False


    def process_header (self, hdr, cat):

        # Check if the catalog itself states the accelerator character,
        # unless specified explicitly by the command line.
        if not self.accel_explicit:
            accel = cat.possible_accelerator()
            if accel is not None:
                self.accel = accel
            else:
                self.accel = ""


    def process (self, msg, cat):

        if msg.obsolete:
            return

        match = True

        for field, regex in zip(self.fields, self.regexs):

            if field == "msgctxt":
                texts = [msg.msgctxt]
            elif field == "msgid":
                texts = [msg.msgid, msg.msgid_plural]
            elif field == "msgstr":
                texts = msg.msgstr
            else:
                error("unknown search field '%s'" % field)

            local_match = False

            for text in texts:
                # Remove accelerator.
                if self.accel:
                    text = text.replace(self.accel, "")

                # Check for local match (local match is OR).
                if regex.search(text):
                    local_match = True
                    break

            # Check for global match (global match is AND).
            if not local_match:
                match = False
                break

            # Do the replacement in translation if requested.
            if field == "msgstr" and self.replace is not None:
                for i in range(len(msg.msgstr)):
                    msg.msgstr[i] = regex.sub(self.replace, msg.msgstr[i])

        if match:
            self.nmatch += 1
            if not self.mark:
                delim = "--------------------"
                if self.nmatch == 1:
                    print delim
                report_msg_content(msg, cat, delim=delim, highlight=regex)
            else:
                msg.flag.add(_flag_mark)

        elif self.mark and _flag_mark in msg.flag:
            # Remove the flag if present but the message does not match.
            msg.flag.remove(_flag_mark)


    def finalize (self):

        if self.nmatch:
            print "Total matching: %d" % (self.nmatch,)

