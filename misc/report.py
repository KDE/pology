# -*- coding: UTF-8 -*-

"""
Report info, warning and error messages.

Functions for Pology tools to report messages to the user at runtime,
in different contexts and scenario. May colorize some output.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import os, re, sys, locale
from copy import deepcopy

import pology.misc.colors as C
from pology.file.message import Message
from pology.misc.colors import highlight_spans
from pology.misc.wrap import wrap_field
from pology.misc.diff import adapt_spans
from pology.misc.escape import escape


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


def report_on_msg (text, msg, cat, subsrc=None, file=sys.stdout):
    """
    Report on a PO message.

    Outputs the message reference (catalog name and message position),
    along with the report text.

    @param text: text to report
    @type text: string
    @param msg: the message for which the text is reported
    @type msg: L{Message_base}
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

    Outputs the message reference (catalog name and the message position),
    along with the warning text.

    @param text: text to report
    @type text: string
    @param msg: the message for which the text is reported
    @type msg: L{Message_base}
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

    Outputs the message reference (catalog name and message position),
    along with the error text. Aborts execution with the given code.

    @param text: text to report
    @type text: string
    @param msg: the message for which the text is reported
    @type msg: L{Message_base}
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


def report_on_msg_hl (highlight, msg, cat, fmsg=None,
                      subsrc=None, file=sys.stdout):
    """
    Report on parts of a PO message.

    For each of the spans found in the L{highlight<report_msg_content>}
    specification which have a note attached, outputs the position reference
    (catalog name, message position, spanned segment) and the span note.
    The highlight can be relative to a somewhat modified, filtered message
    instead of the original one.

    @param highlight: highlight specification
    @type highlight: L{highlight<report_msg_content>}
    @param msg: the message for which the text is reported
    @type msg: L{Message_base}
    @param cat: the catalog where the message lives
    @type cat: L{Catalog}
    @param fmsg: filtered message to which the highlight corresponds
    @type fmsg: L{Message_base}
    @param subsrc: more detailed source of the message
    @type subsrc: C{None} or string
    @param file: send output to this file descriptor
    @type file: C{file}
    """

    tfmt = _msg_ref_fmtstr(file)

    if not fmsg: # use original message as filtered if not given
        fmsg = msg

    for hspec in highlight:
        name, item, spans = hspec[:3]

        if name == "msgctxt":
            text = msg.msgctxt
            ftext = fmsg.msgctxt
        elif name == "msgid":
            text = msg.msgid
            ftext = fmsg.msgid
        elif name == "msgid_plural":
            text = msg.msgid_plural
            ftext = fmsg.msgid_plural
        elif name == "msgstr":
            text = msg.msgstr[item]
            ftext = fmsg.msgstr[item]
        # TODO: Add more fields.
        else:
            warning("unknown field '%s' in highlight specification" % name)
            continue

        if len(hspec) > 3:
            # Override filtered text from filtered message
            # by filtered text from the highlight spec.
            ftext = hspec[3]

        spans = adapt_spans(text, ftext, spans, merge=False)

        if msg.msgid_plural and name == "msgstr":
            name = "%s_%d" % (name, item)

        for span in spans:
            if len(span) < 3:
                continue
            start, end, snote = span
            seglen = end - start
            if seglen > 0:
                segtext = text[start:end]
                if len(segtext) > 30:
                    segtext = segtext[:27] + "..."
                posinfo = "%s:%d:\"%s\"" % (name, start, escape(segtext))
            else:
                posinfo = "%s:%d" % (name, start)
            posinfo = C.GREEN + posinfo + C.RESET

            refstr = tfmt % (cat.filename, msg.refline, msg.refentry)
            rtext = "%s[%s]: %s" % (refstr, posinfo, snote)
            report(rtext, subsrc=subsrc, showcmd=False)


def report_msg_content (msg, cat,
                        wrapf=wrap_field, force=False,
                        note=None, delim=None, highlight=None,
                        showmsg=True, fmsg=None, showfmsg=False,
                        subsrc=None, file=sys.stdout):
    """
    Report the content of a PO message.

    Provides the message reference, consisting of the catalog name and
    the message position within it, the message contents,
    and any notes on particular segments.

    Parts of the message can be highlighted using shell colors.
    Parameter C{highlight} provides the highlighting specification, as
    list of tuples where each tuple consists of: name of the message element
    to highlight, element index (used when the element is a list of values),
    list of spans, and optionally the filtered text of the element value.
    For example, to highlight spans C{(5, 10)} and C{(15, 25)} in the C{msgid},
    and C{(30, 40)} in C{msgstr}, the highlighting specification would be::

        [("msgid", 0, [(5, 10), (15, 25)]), ("msgstr", 0, [(30, 40)])]

    Names of the elements that can presently be highlighted are: C{"msgctxt"},
    C{"msgid"}, C{"msgid_plural"}, C{"msgstr"}.
    For unique fields the element index is not used, but 0 should be given
    for consistency (may be enforced later).
    Span tuples can have a third element, following the indices, which is
    the note about why the particular span is highlighted;
    there may be more elements after the note, and these are all ignored.

    Sometimes the match to which the spans correspond has been made on a
    filtered value of the message field (e.g. after accelerator markers
    or tags have been removed). In that case, the filtered text can be
    given as the fourth element of the tuple, after the list of spans, and
    the function will try to fit spans from filtered onto original text.
    More globally, if the complete highlight is relative to a modified,
    filtered version of the message, this message can be given as
    C{fmsg} parameter.

    The display of content can be controlled by C{showmsg} parameter;
    if it is C{False}, only the message reference and span notes are shown.
    Similarly for the C{showfmsg} parameter, which controls the display
    of the content of filtered message (if given by C{fmsg}).
    To show the filtered message may be useful for debugging filtering
    in cases when it is not straightforward, or it is user-defined.

    @param msg: the message to report the content for
    @type msg: L{Message_base}
    @param cat: the catalog where the message lives
    @type cat: L{Catalog} or C{None}
    @param wrapf:
        the function used for wrapping message fields in output.
        See C{to_lines()} method of L{Message_base} for details.
    @type wrapf: string, string, string -> list of strings
    @param force: whether to force reformatting of cached message content
    @type force: bool
    @param note: note about why the content is being reported
    @type note: string
    @param delim: text to print on the line following the message
    @type delim: C{None} or string
    @param highlight: highlighting specification of message elements
    @type highlight: (see description)
    @param showmsg: show content of the message
    @type showmsg: bool
    @param fmsg: filtered message
    @type fmsg: L{Message_base}
    @param showfmsg: show content of the filtered message, if any
    @type showfmsg: bool
    @param subsrc: more detailed source of the message
    @type subsrc: C{None} or string
    @param file: output stream
    @type file: file
    """

    C = _colors_for_file(file)
    rsegs = []

    notes_data = []
    if highlight:
        msg = Message(msg) # must work on copy, highlight modifies it
        ffmsg = fmsg or msg # use original message as filtered if not given

        for hspec in highlight:
            name, item, spans = hspec[:3]

            def hl (text, ftext):
                if len(hspec) > 3:
                    # Override filtered text from filtered message
                    # by filtered text from the highlight spec.
                    ftext = hspec[3]
                aspans = adapt_spans(text, ftext, spans, merge=False)
                notes_data.append((text, name, item, aspans))
                if file.isatty():
                    text = highlight_spans(text, spans, ftext=ftext)
                return text

            if name == "msgctxt":
                msg.msgctxt = hl(msg.msgctxt, ffmsg.msgctxt)
            elif name == "msgid":
                msg.msgid = hl(msg.msgid, ffmsg.msgid)
            elif name == "msgid_plural":
                msg.msgid_plural = hl(msg.msgid_plural, ffmsg.msgid_plural)
            elif name == "msgstr":
                msg.msgstr[item] = hl(msg.msgstr[item], ffmsg.msgstr[item])
            else:
                warning("unknown field '%s' in highlight specification" % name)
            # TODO: Add more fields.

    # Report the message.
    mstr = ""
    if cat is not None:
        tfmt = _msg_ref_fmtstr(file)
        mstr += tfmt % (cat.filename, msg.refline, msg.refentry) + "\n"
    if showmsg:
        mstr += msg.to_string(wrapf=wrapf, force=force).rstrip() + "\n"
    if mstr:
        rsegs.append(mstr.rstrip())

    # Report notes.
    if note is not None: # global
        notestr = (C.BOLD + "note:" + C.RESET + " " + note)
        rsegs.append(notestr)
    if notes_data: # span notes
        note_ord = 1
        for text, name, item, spans in notes_data:
            if msg.msgid_plural and name == "msgstr":
                name = "%s%d" % (name, item)
            for span in spans:
                if len(span) < 3:
                    continue
                start, end, snote = span
                seglen = end - start
                if seglen > 0:
                    segtext = text[start:end]
                    if len(segtext) > 30:
                        segtext = segtext[:27] + "..."
                    posinfo = "%s:%d:\"%s\"" % (name, start, escape(segtext))
                else:
                    posinfo = "%s:%d" % (name, start)
                posinfo = C.GREEN + posinfo + C.RESET
                shead = C.BOLD + "span#%d" % note_ord + C.RESET
                rsegs.append("%s[%s]: %s" % (shead, posinfo, snote))
                note_ord += 1

    # Report the filtered message, if given and requested.
    if fmsg and showfmsg:
        fmtnote = C.GREEN + ">>> filtered message was:" + C.RESET
        rsegs.append(fmtnote)
        mstr = fmsg.to_string(wrapf=wrapf, force=force).rstrip() + "\n"
        rsegs.append(mstr.rstrip())

    if delim:
        rsegs.append(delim)

    rtext = "\n".join(rsegs).rstrip()
    report(rtext, subsrc=subsrc, file=file)


def rule_error(msg, cat, rule, highlight=None, fmsg=None):
    """
    Print formated rule error message on screen.

    @param msg: pology.file.message.Message object
    @param cat: pology.file.catalog.Catalog object
    @param rule: pology.misc.rules.Rule object
    @param highlight: highlight specification (see L{report_msg_content})
    @param fmsg: filtered message which the rule really matched
    """

    C = _colors_for_file(sys.stdout)

    # Some info on the rule.
    rinfo = (  ""
             + "rule %s" % rule.displayName + " "
             + C.BOLD + C.RED + " ==> " + C.RESET
             + C.BOLD + rule.hint + C.RESET)

    report_msg_content(msg, cat,
                       highlight=highlight,
                       fmsg=fmsg, showfmsg=(fmsg is not None),
                       note=rinfo, delim=("-" * 40))


def rule_xml_error(msg, cat, rule, span, pluralId=0):
    """Create and returns rule error message in XML format
    @param msg: pology.file.message.Message object
    @param cat: pology.file.catalog.Catalog object
    @param span: list of 2-tuple (start, end) of offending spans
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
    for begin, end in span:
        xmlError.append("\t\t<highlight begin='%s' end='%s'/>\n" % (begin, end))
    #xmlError.append("\t\t<start>%s</start>\n" % span[0])
    #xmlError.append("\t\t<end>%s</end>\n" % span[1])
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
    report("-"*40)
    report(C.BOLD+"%s:%d(%d)" % (cat.filename, msg.refline, msg.refentry)+C.RESET)
    if msg.msgctxt:
        report(C.BOLD+"Context: "+C.RESET+msg.msgctxt)
    #TODO: color in red part of context that make the mistake
    report(C.BOLD+"Faulty word: "+C.RESET+C.RED+faultyWord+C.RESET)
    if suggestions:
        report(C.BOLD+"Suggestions: "+C.RESET+", ".join(suggestions))
    
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
