# -*- coding: utf-8 -*-

"""
Report info, warning and error messages.

Functions for Pology tools to report PO messages to the user at runtime,
in different contexts and scenario. May colorize some output.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

# NOTE: These functions are not in pology.misc.report module,
# as that would cause circular module dependencies.

import sys
import os
import re
from copy import deepcopy

try: import dbus
except: print "please, install python-dbus package (for communication with Lokalize)"

from pology.misc.report import report, warning, error
from pology.misc.colors import colors_for_file
from pology.file.message import Message
from pology.misc.wrap import wrap_field_fine
from pology.misc.diff import adapt_spans
from pology.misc.escape import escape_c as escape
from pology.misc.monitored import Monpair


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
                      subsrc=None, file=sys.stdout, lokalize=False):
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

    C = colors_for_file(file)
    tfmt = _msg_ref_fmtstr(file)

    if not fmsg: # use original message as filtered if not given
        fmsg = msg

    for hspec in highlight:
        name, item, spans = hspec[:3]

        if name == "msgctxt":
            text = msg.msgctxt or u""
            ftext = fmsg.msgctxt or u""
        elif name == "msgid":
            text = msg.msgid
            ftext = fmsg.msgid
        elif name == "msgid_plural":
            text = msg.msgid_plural or u""
            ftext = fmsg.msgid_plural or u""
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

        if msg.msgid_plural is not None and name == "msgstr":
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


    if not lokalize: return

    if msg.obsolete: return

    try:
        try: globals()['lokalizeobj']
        except:
            bus = dbus.SessionBus()
            lokalize_dbus_instances=lambda:filter(lambda name: name.startswith('org.kde.lokalize'),bus.list_names())
            try:
                globals()['lokalizeinst']=lokalize_dbus_instances()[0]
                globals()['lokalizeobj']=bus.get_object(globals()['lokalizeinst'],'/ThisIsWhatYouWant')
                globals()['openFileInEditor']=globals()['lokalizeobj'].get_dbus_method('openFileInEditor','org.kde.Lokalize.MainWindow')
                globals()['visitedcats']={}
            except: return

        index=globals()['openFileInEditor'](os.path.abspath(cat.filename))
        editorobj=dbus.SessionBus().get_object(globals()['lokalizeinst'],'/ThisIsWhatYouWant/Editor/%d' % index)

        if cat.filename not in globals()['visitedcats']:
            globals()['visitedcats'][cat.filename]=1

            gotoEntry=editorobj.get_dbus_method('gotoEntry','org.kde.Lokalize.Editor')
            gotoEntry(msg.refentry-1)

            setEntriesFilteredOut=editorobj.get_dbus_method('setEntriesFilteredOut','org.kde.Lokalize.Editor')    
            setEntriesFilteredOut(True)

        setEntryFilteredOut=editorobj.get_dbus_method('setEntryFilteredOut','org.kde.Lokalize.Editor')    
        setEntryFilteredOut(msg.refentry-1,False)

    except:
        return



def report_msg_content (msg, cat,
                        wrapf=wrap_field_fine, force=False,
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
    C{"msgid"}, C{"msgid_plural"}, C{"msgstr"}, C{"manual_comment"},
    C{"auto_comment"}, C{"source"}, C{"flag"}.
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

    C = colors_for_file(file)
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
                text = _highlight_spans(text, spans, C.RED, C.RESET,
                                        ftext=ftext)
                return text

            if name == "msgctxt":
                if msg.msgctxt or ffmsg.msgctxt:
                    msg.msgctxt = hl(msg.msgctxt or u"", ffmsg.msgctxt or u"")
            elif name == "msgid":
                msg.msgid = hl(msg.msgid, ffmsg.msgid)
            elif name == "msgid_plural":
                msg.msgid_plural = hl(msg.msgid_plural or u"",
                                      ffmsg.msgid_plural or u"")
            elif name == "msgstr":
                msg.msgstr[item] = hl(msg.msgstr[item], ffmsg.msgstr[item])
            elif name == "manual_comment":
                msg.manual_comment[item] = hl(msg.manual_comment[item],
                                              ffmsg.manual_comment[item])
            elif name == "auto_comment":
                msg.auto_comment[item] = hl(msg.auto_comment[item],
                                            ffmsg.auto_comment[item])
            elif name == "source":
                msg.source[item] = Monpair((hl(msg.source[item][0],
                                              ffmsg.source[item][0]),
                                            msg.source[item][1]))
            elif name == "flag":
                pass # FIXME: How to do this?
            else:
                warning("unknown field '%s' in highlight specification" % name)

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
            if msg.msgid_plural is not None and name == "msgstr":
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
                rsegs.append("[%s]: %s" % (posinfo, snote))
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


def rule_error(msg, cat, rule, highlight=None, fmsg=None, showmsg=True):
    """
    Print formated rule error message on screen.

    @param msg: pology.file.message.Message object
    @param cat: pology.file.catalog.Catalog object
    @param rule: pology.misc.rules.Rule object
    @param highlight: highlight specification (see L{report_msg_content})
    @param fmsg: filtered message which the rule really matched
    @param showmsg: whether to show contents of message (either filtered or original)
    """

    C = colors_for_file(sys.stdout)

    # Some info on the rule.
    rinfo = (  ""
             + "rule %s" % rule.displayName + " "
             + C.BOLD + C.RED + " ==> " + C.RESET
             + C.BOLD + rule.hint + C.RESET)

    if showmsg:
        report_msg_content(msg, cat,
                           highlight=highlight,
                           fmsg=fmsg, showfmsg=(fmsg is not None),
                           note=rinfo, delim=("-" * 40))
    else:
        report_on_msg(rinfo, msg, cat)
        report_on_msg_hl(highlight, msg, cat, fmsg)


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
    xmlError.append("\t\t<msgctxt><![CDATA[%s]]></msgctxt>\n" % _escapeCDATA(msg.msgctxt or u""))
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
    C = colors_for_file(sys.stdout)
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
    xmlError.append("\t\t<msgctxt><![CDATA[%s]]></msgctxt>\n" % _escapeCDATA(msg.msgctxt or u""))
    xmlError.append("\t\t<msgid><![CDATA[%s]]></msgid>\n" % _escapeCDATA(msg.msgid))
    xmlError.append("\t\t<msgstr><![CDATA[%s]]></msgstr>\n" % _escapeCDATA(msg.msgstr[pluralId]))
    xmlError.append("\t\t<faulty>%s</faulty>\n" % faultyWord)
    for suggestion in suggestions:
        xmlError.append("\t\t<suggestion>%s</suggestion>\n" % suggestion)
    xmlError.append("\t</error>\n")
    return xmlError
    
# Format string for message reference, based on the file descriptor.
def _msg_ref_fmtstr (file=sys.stdout):

    C = colors_for_file(file)
    fmt = ""
    fmt += C.CYAN + "%s" + C.RESET + ":" # file name
    fmt += C.PURPLE + "%d" + C.RESET # line number
    fmt += "(" + C.PURPLE + "#%d" + C.RESET + ")" # entry number

    return fmt


def _escapeCDATA(text):
    """Escape CDATA tags to allow inclusion into CDATA
    @param text: text to convert
    @type text: str or unicode
    @return: modified string"""
    text=text.replace("<![CDATA[", "<_!_[CDATA[")
    text=text.replace("]]>", "]_]_>")
    return text


def _highlight_spans (text, spans, color_s, color_e, ftext=None):
    """
    Highlight spans in text.

    Adds shell colors around defined spans in the text.
    Spans are given as list of index tuples C{[(start1, end1), ...]} where
    start and end index have standard Python semantics.
    Span tuples can have more than two elements, with indices followed by
    additional elements, which are ignored by this function.

    If C{ftext} is not C{None} spans are understood as relative to it,
    and the function will try to adapt them to the main text
    (see L{pology.misc.diff.adapt_spans}).

    @param text: text to be highlighted
    @type text: string
    @param spans: spans to highlight
    @type spans: list of tuples
    @param color_s: starting color sequence
    @type color_s: string
    @param color_e: ending color sequence
    @type color_e: string
    @param ftext: text to which spans are actually relative
    @type ftext: string

    @returns: highlighted text
    @rtype: string
    """

    if not spans or (not color_s and not color_e):
        return text

    # Adapt spans regardless if filtered text has been given or not,
    # to fix any overlapping and put into expected ordering.
    if ftext is None:
        ftext = text
    spans = adapt_spans(text, ftext, spans, merge=True)
    if not spans:
        return text

    ctext = ""
    cstart = 0
    for span in spans:
        ctext += text[cstart:span[0]]
        ctext += color_s + text[span[0]:span[1]] + color_e
        cstart = span[1]
    ctext += text[span[1]:]

    return ctext

