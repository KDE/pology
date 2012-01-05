# -*- coding: utf-8 -*-

"""
Report info, warning and error messages.

Functions for Pology tools to report PO messages to the user at runtime,
in different contexts and scenario. May colorize some output.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@author: Nick Shaforostoff (Николай Шафоростов) <shaforostoff@kde.ru>
@license: GPLv3
"""

# NOTE: These functions are not in pology.report module,
# as that would cause circular module dependencies.

from copy import deepcopy
import os
import re
import sys

from pology import _, n_
from pology.message import Message
from pology.colors import ColorString, cjoin, cinterp
from pology.diff import adapt_spans
from pology.escape import escape_c as escape
from pology.monitored import Monpair
from pology.report import report, warning, error, format_item_list


# FIXME: Make this a public function in getfunc module.
_modules_on_request = {}
def _get_module (name, cmsg=None):

    if name not in _modules_on_request:
        try:
            _modules_on_request[name] = __import__(name)
        except:
            if cmsg:
                warning(_("@info",
                          "Cannot import module '%(mod)s'; consequence:\n"
                          "%(msg)s",
                          mod=name, msg=cmsg))
            else:
                warning(_("@info",
                          "Cannot import module '%(mod)s'.",
                          mod=name))
            _modules_on_request[name] = None

    return _modules_on_request[name]


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

    posinfo = _msg_pos_fmt(cat.filename, msg.refline, msg.refentry)
    text = cinterp("%s: %s", posinfo, text)
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

    posinfo = _msg_pos_fmt(cat.filename, msg.refline, msg.refentry)
    text = cinterp("%s: %s", posinfo, text)
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

    posinfo = _msg_pos_fmt(cat.filename, msg.refline, msg.refentry)
    text = cinterp("%s: %s", posinfo, text)
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

    refpos = _msg_pos_fmt(cat.filename, msg.refline, msg.refentry)

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
            warning(_("@info",
                      "Unknown field '%(field)s' "
                      "in highlighting specification.",
                      field=name))
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
            if isinstance(start, int) and isinstance(end, int):
                seglen = end - start
                if seglen > 0:
                    segtext = text[start:end]
                    if len(segtext) > 30:
                        segtext = segtext[:27] + "..."
                    posinfo = "%s:%d:\"%s\"" % (name, start, escape(segtext))
                else:
                    posinfo = "%s:%d" % (name, start)
            else:
                posinfo = "%s" % name
            posinfo = ColorString("<green>%s</green>") % posinfo

            rtext = cinterp("%s[%s]: %s", refpos, posinfo, snote)
            report(rtext, subsrc=subsrc, showcmd=False)


def report_msg_to_lokalize (msg, cat, report=None):
    """
    Open catalog in Lokalize and jump to message.

    Lokalize is a CAT tool for KDE 4, U{http://userbase.kde.org/Lokalize}.
    This function opens the catalog in Lokalize (if not already open)
    and jumps to the given message within it.

    If the message is obsolete, it will be ignored.

    @param msg: the message which should be jumped to in Lokalize
    @type msg: L{Message_base}
    @param cat: the catalog in which the message resides
    @type cat: L{Catalog}
    @param report: simple text or highlight specification
    @type report: string or L{highlight<report_msg_content>}
    """

    dbus = _get_module("dbus",
                       _("@info",
                         "Communication with Lokalize not possible. "
                         "Try installing the '%(pkg)s' package.",
                         pkg="python-dbus"))
    if not dbus: return

    if msg.obsolete: return

    # If report is a highlight specification,
    # flatten it into lines of notes by spans.
    if isinstance(report, list):
        notes=[]
        for hspec in report:
            for span in hspec[2]:
                if len(span) > 2:
                    notes.append(span[2])
        report = cjoin(notes, "\n")

    try:
        try: globals()['lokalizeobj']
        except:
            bus = dbus.SessionBus()
            lokalize_dbus_instances=lambda:filter(lambda name: name.startswith('org.kde.lokalize'),bus.list_names())
            for lokalize_dbus_instance in lokalize_dbus_instances():
                try:
                    globals()['lokalizeinst']=lokalize_dbus_instance
                    globals()['lokalizeobj']=bus.get_object(globals()['lokalizeinst'],'/ThisIsWhatYouWant')
                    globals()['openFileInEditor']=globals()['lokalizeobj'].get_dbus_method('openFileInEditor','org.kde.Lokalize.MainWindow')
                    globals()['visitedcats']={}
                except:
                    pass
            if 'openFileInEditor' not in globals():
                return

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
        if report:
            addTemporaryEntryNote=editorobj.get_dbus_method('addTemporaryEntryNote','org.kde.Lokalize.Editor')
            addTemporaryEntryNote(msg.refentry-1,report.resolve(ctype="none"))

    except:
        return


def report_msg_content (msg, cat,
                        wrapf=None, force=False,
                        note=None, delim=None, highlight=None,
                        showmsg=True, fmsg=None, showfmsg=False,
                        subsrc=None, file=sys.stdout):
    """
    Report the content of a PO message.

    Provides the message reference, consisting of the catalog name and
    the message position within it, the message contents,
    and any notes on particular segments.

    Parts of the message can be highlighted using colors.
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
    If start or end index of a span is not an integer,
    then the note is taken as relating to the complete field.

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
        See L{to_lines()<message.Message_base.to_lines>} method
        of message classes for details.
        If not given, it will be taken from the catalog
        (see L{Catalog.wrapf<catalog.Catalog.wrapf>}).
    @type wrapf: (string)->[string...]
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

    rsegs = []

    wrapf = wrapf or cat.wrapf()

    notes_data = []
    if highlight:
        msg = Message(msg) # must work on copy, highlight modifies it
        ffmsg = fmsg or msg # use original message as filtered if not given

        # Unify spans for same parts, to have single coloring pass per part
        # (otherwise markup can get corrupted).
        highlightd = {}
        for hspec in highlight:
            name, item, spans = hspec[:3]
            pkey = (name, item)
            phspec = highlightd.get(pkey)
            if phspec is None:
                # Make needed copies in order not to modify
                # the original highlight when adding stuff later.
                highlightd[pkey] = list(hspec)
                highlightd[pkey][2] = list(spans)
            else:
                phspec[2].extend(spans)
                # Take filtered text if available and not already taken.
                if len(hspec) > 3 and len(phspec) <= 3:
                    phspec.append(hspec[3])
        highlight = highlightd.values()

        for hspec in highlight:
            name, item, spans = hspec[:3]

            def hl (text, ftext):
                if len(hspec) > 3:
                    # Override filtered text from filtered message
                    # by filtered text from the highlight spec.
                    ftext = hspec[3]
                aspans = adapt_spans(text, ftext, spans, merge=False)
                notes_data.append((text, name, item, aspans))
                text = _highlight_spans(text, spans, "red", ftext=ftext)
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
                warning(_("@info",
                          "Unknown field '%(field)s' "
                          "in highlighting specification.",
                          field=name))

    # Report the message.
    msegs = []
    if cat is not None:
        msegs += [_msg_pos_fmt(cat.filename, msg.refline, msg.refentry) + "\n"]
    if showmsg:
        msgstr = msg.to_string(wrapf=wrapf, force=force, colorize=1)
        msegs += [msgstr.rstrip() + "\n"]
    if msegs:
        rsegs.append(cjoin(msegs).rstrip())

    # Report notes.
    if note is not None: # global
        notestr = _("@info",
                    "<bold>[note]</bold> %(msg)s",
                    msg=note)
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
                if isinstance(start, int) and isinstance(end, int):
                    seglen = end - start
                    if seglen > 0:
                        segtext = text[start:end]
                        if len(segtext) > 30:
                            segtext = _("@item:intext shortened longer text",
                                        "%(snippet)s...",
                                        snippet=segtext[:27])
                        posinfo = "%s:%d:\"%s\"" % (name, start, escape(segtext))
                    else:
                        posinfo = "%s:%d" % (name, start)
                else:
                    posinfo = "%s" % name
                posinfo = ColorString("<green>%s</green>") % posinfo
                rsegs.append(_("@info",
                               "[%(pos)s]: %(msg)s",
                               pos=posinfo, msg=snote))
                note_ord += 1

    # Report the filtered message, if given and requested.
    if fmsg and showfmsg:
        fmtnote = (ColorString("<green>%s</green>")
                   % _("@info", ">>> Filtered message was:"))
        rsegs.append(fmtnote)
        fmsgstr = fmsg.to_string(wrapf=wrapf, force=force, colorize=1)
        mstr = fmsgstr.rstrip() + "\n"
        rsegs.append(mstr.rstrip())

    if delim:
        rsegs.append(delim)

    rtext = cjoin(rsegs, "\n").rstrip()
    report(rtext, subsrc=subsrc, file=file)


def rule_error(msg, cat, rule, highlight=None, fmsg=None, showmsg=True):
    """
    Print formated rule error message on screen.

    @param msg: pology.message.Message object
    @param cat: pology.catalog.Catalog object
    @param rule: pology.rules.Rule object
    @param highlight: highlight specification (see L{report_msg_content})
    @param fmsg: filtered message which the rule really matched
    @param showmsg: whether to show contents of message (either filtered or original)
    """

    # Some info on the rule.
    rinfo = _("@info",
              "rule %(rule)s <bold><red>==></red></bold> "
              "<bold>%(msg)s</bold>",
              rule=rule.displayName, msg=rule.hint)

    if showmsg:
        report_msg_content(msg, cat,
                           highlight=highlight,
                           fmsg=fmsg, showfmsg=(fmsg is not None),
                           note=rinfo, delim=("-" * 40))
    else:
        report_on_msg(rinfo, msg, cat)
        report_on_msg_hl(highlight, msg, cat, fmsg)


def multi_rule_error (msg, cat, rspec, showmsg=True):
    """
    Print formated rule error messages on screen.

    Like L{rule_error}, but reports multiple failed rules at once.
    Contents of the matched message is shown only once for all rules,
    with all highlights embedded, and all rule information following.
    This holds unless there are several different filtered messages,
    when rule failures are reported in groups by filtered message.

    @param msg: the message matched by rules
    @type msg: Message
    @param cat: the catalog in which the message resides
    @type cat: Catalog
    @param rspec: specification of failed rules. This is a list in which
        each element can be one of:
          - rule
          - tuple of rule and highlight specification (see
            L{report_msg_content} for details on highlight specifications).
            Highlight can be None.
          - tuple of rule, highlight, and filtered message which
            the rule really matched.
            Highlight and filtered message can be None.
    @type rspec: [(Rule|(Rule, highlight)|(Rule, highlight, Message))*]
    @param showmsg: whether to show contents of message
        (both original and filtered if given)
    @type showmsg: bool
    """

    # Expand elements in rule specification to full lengths.
    rspec_mod = []
    for el in rspec:
        if not isinstance(el, tuple):
            el = (el,)
        el_mod = el + tuple(None for i in range(3 - len(el)))
        rspec_mod.append(el_mod)
    rspec = rspec_mod

    # Split into groups by distinct filtered messages,
    # or make one dummy group if content display not requested.
    if showmsg:
        rspec_groups = []
        for rule, hl, fmsg in rspec:
            rlhls = None
            for ofmsg, rlhls in rspec_groups:
                if fmsg == ofmsg: # check for apparent equality
                    break
            if rlhls is None:
                rlhls = []
                rspec_groups.append((fmsg, rlhls))
            rlhls.append((rule, hl))
    else:
        rlhls = []
        rspec_groups = [(None, rlhls)]
        for rule, hl, fmsg in rspec:
            rlhls.append((rule, hl))

    # Report each rule group.
    for fmsg, rlhls in rspec_groups:
        rinfos = []
        highlight = []
        for rule, hl in rlhls:
            rinfos.append(_("@info",
                            "rule %(rule)s <bold><red>==></red></bold> "
                            "<bold>%(msg)s</bold>",
                            rule=rule.displayName, msg=rule.hint))
            highlight.extend(hl)
        if len(rinfos) > 1:
            note = cjoin([""] + rinfos, "\n")
        elif rinfos:
            note = rinfos[0]
        if showmsg:
            report_msg_content(msg, cat,
                               highlight=highlight,
                               fmsg=fmsg, showfmsg=(fmsg is not None),
                               note=note, delim=("-" * 40))
        else:
            report_on_msg(note, msg, cat)
            report_on_msg_hl(highlight, msg, cat, fmsg)


def rule_xml_error(msg, cat, rule, span, pluralId=0):
    """Create and returns rule error message in XML format
    @param msg: pology.message.Message object
    @param cat: pology.catalog.Catalog object
    @param span: list of 2-tuple (start, end) of offending spans
    @param rule: pology.rules.Rule object
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
        if isinstance(begin, int) and isinstance(end, int):
            xmlError.append("\t\t<highlight begin='%s' end='%s'/>\n" % (begin, end))
    #xmlError.append("\t\t<start>%s</start>\n" % span[0])
    #xmlError.append("\t\t<end>%s</end>\n" % span[1])
    xmlError.append("\t\t<pattern><![CDATA[%s]]></pattern>\n" % rule.rawPattern)
    xmlError.append("\t\t<hint><![CDATA[%s]]></hint>\n" % rule.hint)
    xmlError.append("\t</error>\n")
    return xmlError


def spell_error(msg, cat, faultyWord, suggestions):
    """Print formated rule error message on screen
    @param msg: pology.message.Message object
    @param cat: pology.catalog.Catalog object
    @param faultyWord: badly spelled word
    @param suggestions : list of correct words to suggest"""
    report("-"*40)
    report(ColorString("<bold>%s:%d(%d)</bold>")
           % (cat.filename, msg.refline, msg.refentry))
    if msg.msgctxt:
        report(_("@info",
                 "<bold>Context:</bold> %(snippet)s",
                 snippet=msg.msgctxt))
    #TODO: color in red part of context that make the mistake
    report(_("@info",
             "<bold>Faulty word:</bold> <red>%(word)s</red>",
             word=faultyWord))
    if suggestions:
        report(_("@info",
                 "<bold>Suggestions:</bold> %(wordlist)s",
                 wordlist=format_item_list(suggestions)))


def spell_xml_error(msg, cat, faultyWord, suggestions, pluralId=0):
    """Create and returns spell error message in XML format
    @param msg: pology.message.Message object
    @param cat: pology.catalog.Catalog object
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
def _msg_pos_fmt (path, line, col):

    return (ColorString("<cyan>%s</cyan>:<purple>%d</purple>"
                        "(<purple>#%d</purple>)") % (path, line, col))


def _escapeCDATA(text):
    """Escape CDATA tags to allow inclusion into CDATA
    @param text: text to convert
    @type text: str or unicode
    @return: modified string"""
    text=text.replace("<![CDATA[", "<_!_[CDATA[")
    text=text.replace("]]>", "]_]_>")
    return text


def _highlight_spans (text, spans, color, ftext=None):
    """
    Adds colors around highlighted spans in text.

    Spans are given as list of index tuples C{[(start1, end1), ...]} where
    start and end index have standard Python semantics.
    Span tuples can have more than two elements, with indices followed by
    additional elements, which are ignored by this function.
    If start or end index in a span is not an integer, the span is ignored.

    The C{color} parameter is one of the color tags available in
    L{ColorString<colors.ColorString>} markup.

    If C{ftext} is not C{None}, spans are understood as relative to it,
    and the function will try to adapt them to the main text
    (see L{pology.diff.adapt_spans}).

    @param text: text to be highlighted
    @type text: string
    @param spans: spans to highlight
    @type spans: list of tuples
    @param color: color tag
    @type color: string
    @param ftext: text to which spans are actually relative
    @type ftext: string

    @returns: highlighted text
    @rtype: string
    """

    if not spans or color is None:
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
        if not isinstance(span[0], int) or not isinstance(span[1], int):
            continue
        ctext += text[cstart:span[0]]
        ctext += (ColorString("<%s>%%s</%s>" % (color, color))
                  % text[span[0]:span[1]]) # outside, to have auto-escaping
        cstart = span[1]
    ctext += text[span[1]:]

    return ctext

