# -*- coding: UTF-8 -*-

"""
Report info, warning and error messages.

Functions for Pology tools to report messages to the user at runtime,
in different contexts and scenario. May colorize some output.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import os, sys
import pology.misc.colors as C


def report (text, showcmd=False, subsrc=None, file=sys.stdout):
    """
    Generic report.

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

    if cmdname and subsrc:
        file.write("%s: (%s) %s\n" % (cmdname, subsrc, text))
    elif cmdname:
        file.write("%s: %s\n" % (cmdname, text))
    elif subsrc:
        file.write("(%s) %s\n" % (subsrc, text))
    else:
        file.write("%s\n" % text)


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
        text = C.ORANGE + text + C.RESET
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
        text = C.RED + text + C.RESET
        pref = C.BOLD + pref + C.RESET
    report("%s: %s" % (pref, text), showcmd=showcmd, subsrc=subsrc, file=file)
    sys.exit(code)


def report_on_msg (text, msg, cat, subsrc=None, file=sys.stdout):
    """
    Report on a PO message.

    Provides the message reference along with the report text,
    consisting of the catalog name and the message position within it.

    @param text: text to report
    @type text: string
    @param msg: the message for which the text is reported
    @type msg: instance of L{Message_base}
    @param cat: the catalog where the message lives
    @type cat: L{Catalog}
    @param subsrc: more detailed source of the message
    @type subsrc: C{None} or string
    @param file: send output to this file descriptor
    @type file: C{file}
    """

    tfmt = _msg_ref_fmtstr(file) + ": %s"
    text = tfmt % (cat.filename, msg.refline, msg.refentry, text)
    report(text, subsrc=subsrc, showcmd=False)


def warning_on_msg (text, msg, cat, subsrc=None, file=sys.stderr):
    """
    Warning on a PO message.

    Provides the message reference along with the warning text,
    consisting of the catalog name and the message position within it.

    @param text: text to report
    @type text: string
    @param msg: the message for which the text is reported
    @type msg: instance of L{Message_base}
    @param cat: the catalog where the message lives
    @type cat: L{Catalog}
    @param subsrc: more detailed source of the message
    @type subsrc: C{None} or string
    @param file: send output to this file descriptor
    @type file: C{file}
    """

    tfmt = _msg_ref_fmtstr(file) + ": %s"
    text = tfmt % (cat.filename, msg.refline, msg.refentry, text)
    warning(text, subsrc=subsrc, showcmd=False)


def error_on_msg (text, msg, cat, code=1, subsrc=None, file=sys.stderr):
    """
    Error on a PO message (aborts the execution).

    Provides the message reference along with the error text,
    consisting of the catalog name and the message position within it.
    Exits with the given code.

    @param text: text to report
    @type text: string
    @param msg: the message for which the text is reported
    @type msg: instance of L{Message_base}
    @param cat: the catalog where the message lives
    @type cat: L{Catalog}
    @param code: the exit code
    @type code: int
    @param subsrc: more detailed source of the message
    @type subsrc: C{None} or string
    @param file: send output to this file descriptor
    @type file: C{file}
    """

    tfmt = _msg_ref_fmtstr(file) + ": %s"
    text = tfmt % (cat.filename, msg.refline, msg.refentry, text)
    error(text, code=code, subsrc=subsrc, showcmd=True)


def report_msg_content (msg, cat, delim=None, force=False, subsrc=None,
                        file=sys.stdout):
    """
    Report the content of a PO message.

    Provides the message reference along with the message contents,
    consisting of the catalog name and the message position within it.

    @param msg: the message to report the content for
    @type msg: instance of L{Message_base}
    @param cat: the catalog where the message lives
    @type cat: L{Catalog}
    @param delim: text to print on line following the message
    @type delim: C{None} or string
    @param force: whether to force reformatting of cached message content
    @type force: bool
    @param subsrc: more detailed source of the message
    @type subsrc: C{None} or string
    """

    tfmt = _msg_ref_fmtstr(file) + "\n"
    text = tfmt % (cat.filename, msg.refline, msg.refentry)
    text += msg.to_string(force=force).rstrip() + "\n"
    if delim:
        text += delim + "\n"
    file.write(text)


# Format string for message reference, based on the file descriptor.
def _msg_ref_fmtstr (file=sys.stdout):

    if file.isatty():
        fmt = ""
        fmt += C.BLUE + "%s" + C.RESET + ":" # file name
        fmt += C.PURPLE + "%d" + C.RESET # line number
        fmt += "(" + C.PURPLE + "%d" + C.RESET + ")" # entry number
    else:
        fmt = "%s:%d(%d)"

    return fmt

