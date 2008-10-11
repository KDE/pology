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

    enc = file.encoding or locale.getpreferredencoding()
    text = text.encode(enc, "replace")
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

