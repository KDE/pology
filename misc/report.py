# -*- coding: UTF-8 -*-

"""
Report info, warning and error messages.

Functions for Pology tools to issue reports to the user at runtime.
May colorize some output.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import os
import sys
import locale

import pology.misc.colors as C


_prev_text_cr = [None, None]

def encwrite (file, text):
    """
    Write unicode text to file using best encoding guess.

    If the file has been opened with explicit encoding, that encoding is used.
    Otherwise a guess is made based on the environment locale.

    @param file: file to write to
    @type file: C{file}
    @param text: text to write
    @type text: string or unicode
    """

    enc = getattr(file, "encoding", None) or locale.getpreferredencoding()
    text = text.encode(enc, "replace")

    # If last output was returning to line start with CR, clean up the line.
    if _prev_text_cr[0] is not None and not _prev_text_cr[1].closed:
        cstr = "\r%s\r" % (" " * len(_prev_text_cr[0]))
        _prev_text_cr[0] = None
        _prev_text_cr[1].write(cstr)
        _prev_text_cr[1] = None

    # If current output is returning to line start with CR, record it.
    if text.endswith("\r"):
        cstr = text
        if "\n" in cstr:
            cstr = cstr[cstr.rfind("\n") + 1:]
        _prev_text_cr[0] = cstr
        _prev_text_cr[1] = file

    file.write(text)


def report (text, showcmd=False, subsrc=None, file=sys.stdout):
    """
    Generic report.

    Text is output to the file descriptor, with one newline appended.

    @param text: text to report
    @type text: string
    @param showcmd: whether to show the command name
    @type showcmd: bool
    @param subsrc: more detailed source of the text
    @type subsrc: C{None} or string
    @param file: send output to this file descriptor
    @type file: C{file}
    """

    cmdname = None
    if showcmd:
        cmdname = os.path.basename(sys.argv[0])

    lines = text.split("\n")
    for i in range(len(lines)):
        if i == 0:
            if cmdname and subsrc:
                head = "%s (%s): " % (cmdname, subsrc)
            elif cmdname:
                head = "%s: " % cmdname
            elif subsrc:
                head = "(%s): " % subsrc
            else:
                head = ""
            lhead = len(head)
        else:
            if lhead:
                head = "... "
            else:
                head = ""
        lines[i] = head + lines[i]

    text = "\n".join(lines) + "\n"
    encwrite(file, text)


def warning (text, showcmd=True, subsrc=None, file=sys.stderr):
    """
    Generic warning.

    @param text: text to report
    @type text: string
    @param showcmd: whether to show the command name
    @type showcmd: bool
    @param subsrc: more detailed source of the text
    @type subsrc: C{None} or string
    @param file: send output to this file descriptor
    @type file: C{file}
    """

    pref = "warning"
    if file.isatty():
        np = _nonws_after_colreset(text)
        text = text[:np] + C.ORANGE + text[np:] + C.RESET
        pref = C.BOLD + pref + C.RESET
    report("%s: %s" % (pref, text), showcmd=showcmd, subsrc=subsrc, file=file)


def error (text, code=1, showcmd=True, subsrc=None, file=sys.stderr):
    """
    Generic error (aborts the execution).

    Exits with the given code.

    @param text: text to report
    @type text: string
    @param code: the exit code
    @type code: int
    @param showcmd: whether to show the command name
    @type showcmd: bool
    @param file: send output to this file descriptor
    @type file: C{file}
    """

    pref = "error"
    if file.isatty():
        np = _nonws_after_colreset(text)
        text = text[:np] + C.RED + text[np:] + C.RESET
        pref = C.BOLD + pref + C.RESET
    report("%s: %s" % (pref, text), showcmd=showcmd, subsrc=subsrc, file=file)
    sys.exit(code)


# Position in text of first non-whitespace after first whitespace sequence
# after last shell color reset.
# 0 if no color reset, len(text) if no conforming non-whitespace after reset.
def _nonws_after_colreset (text):

    p = text.rfind(C.RESET)
    if p >= 0:
        p += len(C.RESET)
        while p < len(text) and text[p].isspace():
            p += 1
        while p < len(text) and not text[p].isspace():
            p += 1
        return p
    else:
        return 0

