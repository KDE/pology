# -*- coding: UTF-8 -*-

"""
Report info, warning and error messages.

Functions for Pology tools to report messages to the user at runtime,
in different contexts and scenario. May colorize some output.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import os, re, sys, locale
import pology.misc.colors as C
from copy import deepcopy


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
                        file=sys.stdout, highlight=None):
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
    @param file: output stream. Default is sys.stdout
    @type file: file
    @param highlight: regular expression pattern used to colorize text. Default is None
    @type highlight: re.compile regular expression
    """

    local_encoding=locale.getdefaultlocale()[1]
    
    tfmt = _msg_ref_fmtstr(file) + "\n"
    text = tfmt % (cat.filename, msg.refline, msg.refentry)
    text += msg.to_string(force=force).rstrip() + "\n"
    if highlight and file.isatty():
        colors=[]
        for match in highlight.finditer(text):
            colors.append(match.span())
        offset=0
        for color in colors:
            text=text[:color[0]+offset]+C.RED+text[color[0]+offset:color[1]+offset]+C.RESET+text[color[1]+offset:]
            offset+=len(C.RED)+len(C.RESET)
    if delim:
        text += delim + "\n"
    text=text.encode(local_encoding, "replace")
    file.write(text)


def rule_error(msg, cat, rule, pluralId=0):
    """Print formated rule error message on screen
    @param msg: pology.file.message.Message object
    @param cat: pology.file.catalog.Catalog object
    @param rule: pology.misc.rules.Rule object
    @param pluralId: msgstr count in case of plural form. Default to 0"""
    C = _colors_for_file(sys.stdout)

    msg = deepcopy(msg)

    if rule.onmsgid:
        text = msg.msgid
    else:
        text = msg.msgstr[pluralId]

    textc = (  text[0:rule.span[0]]
             + C.BOLD + C.RED + text[rule.span[0]:rule.span[1]] + C.RESET
             + text[rule.span[1]:])

    if rule.onmsgid:
        msg.msgid = textc
    else:
        msg.msgstr[pluralId] = textc

    # Some info on the rule.
    rinfo = (  "(" + rule.rawPattern + ")"
             + C.BOLD + C.RED + " ==> " + C.RESET
             + C.BOLD + rule.hint + C.RESET)

    # Must force reformat, as we don't know if the message is monitored.
    report_msg_content(msg, cat, delim=rinfo+"\n"+("-"*40), force=True)


def rule_xml_error(msg, cat, rule, pluralId=0):
    """Create and returns rule error message in XML format
    @param msg: pology.file.message.Message object
    @param cat: pology.file.catalog.Catalog object
    @param rule: pology.misc.rules.Rule object
    @param pluralId: msgstr count in case of plural form. Default to 0
    @return: XML message as a list of unicode string"""
    xmlError=[]
    xmlError.append("\t<error>\n")
    xmlError.append("\t\t<line>%s</line>\n" % msg.refline)
    xmlError.append("\t\t<refentry>%s</refentry>\n" % msg.refentry)
    xmlError.append("\t\t<msgctxt><![CDATA[%s]]></msgctxt>\n" % _escapeCDATA(msg.msgctxt))
    xmlError.append("\t\t<msgid><![CDATA[%s]]></msgid>\n" % _escapeCDATA(msg.msgid))
    xmlError.append("\t\t<msgstr><![CDATA[%s]]></msgstr>\n" % _escapeCDATA(msg.msgstr[pluralId]))
    xmlError.append("\t\t<start>%s</start>\n" % rule.span[0])
    xmlError.append("\t\t<end>%s</end>\n" % rule.span[1])
    xmlError.append("\t\t<pattern><![CDATA[%s]]></pattern>\n" % rule.rawPattern)
    xmlError.append("\t\t<hint><![CDATA[%s]]></hint>\n" % rule.hint)
    xmlError.append("\t</error>\n")
    return xmlError

def spell_error(msg, cat, faultyWord, suggestions):
    """Print formated rule error message on screen
    @param msg: pology.file.message.Message object
    @param cat: pology.file.catalog.Catalog object
    @param faultyWord: badly spelled word
    @param suggestions : list of correct words to suggest"""
    C = _colors_for_file(sys.stdout)
    print "-"*40
    print C.BOLD+"%s:%d(%d)" % (cat.filename, msg.refline, msg.refentry)+C.RESET
    #TODO: color in red part of context that make the mistake
    print C.BOLD+"Faulty word: "+C.RESET+C.RED+faultyWord+C.RESET
    if suggestions:
        print C.BOLD+"Suggestion(s): "+C.RESET+", ".join(suggestions) 
    print
    
def spell_xml_error(msg, cat, faultyWord, suggestions, pluralId=0):
    """Create and returns spell error message in XML format
    @param msg: pology.file.message.Message object
    @param cat: pology.file.catalog.Catalog object
    @param faultyWord: badly spelled word
    @param suggestions : list of correct words to suggest
    @param pluralId: msgstr count in case of plural form. Default to 0
    @return: XML message as a list of unicode string"""
    xmlError=[]
    xmlError.append("\t<error>\n")
    xmlError.append("\t\t<line>%s</line>\n" % msg.refline)
    xmlError.append("\t\t<refentry>%s</refentry>\n" % msg.refentry)
    xmlError.append("\t\t<msgctxt><![CDATA[%s]]></msgctxt>\n" % _escapeCDATA(msg.msgctxt))
    xmlError.append("\t\t<msgid><![CDATA[%s]]></msgid>\n" % _escapeCDATA(msg.msgid))
    xmlError.append("\t\t<msgstr><![CDATA[%s]]></msgstr>\n" % _escapeCDATA(msg.msgstr[pluralId]))
    xmlError.append("\t\t<faulty>%s</faulty>\n" % faultyWord)
    for suggestion in suggestions:
        xmlError.append("\t\t<suggestion>%s</suggestion>\n" % suggestion)
    xmlError.append("\t</error>\n")
    return xmlError
    
# Format string for message reference, based on the file descriptor.
def _msg_ref_fmtstr (file=sys.stdout):

    C = _colors_for_file(file)
    fmt = ""
    fmt += C.CYAN + "%s" + C.RESET + ":" # file name
    fmt += C.PURPLE + "%d" + C.RESET # line number
    fmt += "(" + C.PURPLE + "#%d" + C.RESET + ")" # entry number

    return fmt

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

# Return appropriate color sequences for file descriptor.
class _NoopColors (object):
    def __init__ (self):
        for color in dir(C):
            if not color.startswith("_"):
                self.__dict__[color] = ""
_noopColors = _NoopColors()
def _colors_for_file (file):
    if file.isatty():
        return C
    else:
        return _noopColors

def _escapeCDATA(text):
    """Escape CDATA tags to allow inclusion into CDATA
    @param text: text to convert
    @type text: str or unicode
    @return: modified string"""
    text=text.replace("<![CDATA[", "<_!_[CDATA[")
    text=text.replace("]]>", "]_]_>")
    return text