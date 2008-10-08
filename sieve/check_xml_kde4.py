# -*- coding: UTF-8 -*-

import sys, os, re
import locale
import xml.parsers.expat
from pology.misc.resolve import read_entities
from pology.misc.comments import manc_parse_flag_list
from pology.misc.report import report, report_on_msg

ts_fence = "|/|"

# ----------------------------------------
# Tags and attributes recognized by KDE4.

top_tag = "dummytop"

html_tags = """
qt html
a b big blockquote body br center cite code dd dl dt em font
h1 h2 h3 h4 h5 h6 head hr i img li meta nobr ol p pre
s span strong style sub sup table td th tr tt u ul var
""".split()

html_attrs = {
"a" : ["href", "title"],
"body" : ["style"],
"font" : ["color", "face", "size"],
"img" : ["src", "width", "height"],
"meta" : ["content", "name"],
"p" : ["align", "style"],
"span" : ["style"],
"style" : ["type"],
"table" : ["bgcolor", "border", "cellspacing", "cellpadding", "width"],
"big" : ["style"],
"em" : ["style"],
"b" : ["style", "title"], # really has title?
"td" : ["align", "width", "valign"],
}

kuit_tags = """
kuit kuil title subtitle para list item note warning
filename link application command resource icode bcode shortcut interface
emphasis placeholder email envar message numid nl
""".split()

kuit_attrs = {
"kuit" : ["ctx"],
"kuil" : ["ctx"],
"note" : ["label"],
"warning" : ["label"],
"link" : ["url"],
"command" : ["section"],
"email" : ["address"],
}

all_tags = [top_tag]
all_tags.extend(html_tags)
all_tags.extend(kuit_tags)

all_attrs = {}
all_attrs.update(html_attrs)
all_attrs.update(kuit_attrs)

# ----------------------------------------
# Default XML entities,
# and some rare HTML entities scattered around.

default_entities = {
    "lt" : u"<",
    "gt" : u">",
    "apos" : u"'",
    "quot" : u"\"",
    "amp" : u"&",
}

html_entities = {
    "nbsp" : u" ",
    "reg" : u"®",
    "tm" : u"™",
}

# ----------------------------------------
# Check well-formedness and existence of tags.

# Regex to mine the top tag.
_top_tag_rx = re.compile(r"^\s*<\s*(qt|html|kuil|kuit)\b", re.I|re.U)

# Regex for simplified matching of XML entity name (sans &...;).
_simple_ent_rx = re.compile(r"^([a-z0-9_-]+|#[0-9]+)$", re.I|re.U);

# Links to current state for the handlers.
_c_cat = None
_c_msg = None
_c_quiet = False
_c_errcnt = 0
_c_ents = {}
_c_spanrep = False
_c_errspans = []
_c_parser = None
_c_text = None
_c_enc = "UTF-8"

# Pipe flag used to manually prevent check for a particular message.
flag_no_check_xml = "no-check-xml"


# Heuristically escape &-accelerators by &amp; entities.
def _escape_amp_accel (text):

    ntext = ""
    while True:

        # Bracket possible entity reference.
        p1 = text.find("&")
        if p1 < 0:
            ntext += text
            break
        p2 = text.find(";", p1)
        if p2 < 0:
            # Escape all remaining ampersands.
            ntext += text.replace("&", "&amp;")
            break

        # See if it really looks like entity reference.
        seg = text[p1+1:p2]
        if not _simple_ent_rx.match(seg):
            # ...not, escape
            ntext += text[:p1] + "&amp;" + seg + ";"
        else:
            # ...yes, leave as is
            ntext += text[:p2+1]

        # Shorten original text.
        text = text[p2+1:]

    return ntext


# Handler to check existence of tags.
def _handler_start_element (name, attrs):

    global _c_errcnt

    # Normalize names to lower case.
    name = name.lower()
    attrs = [x.lower() for x in attrs]

    # Limit applicable tags for some catalogs.
    basename = os.path.basename(_c_cat.filename)
    if basename.startswith("desktop_") or basename.startswith("xml_"):
        applicable_tags = html_tags + [top_tag]
    elif basename in ("kdeqt.po",):
        applicable_tags = html_tags + [top_tag]
    else:
        applicable_tags = all_tags

    # Check existence of tag.
    if name not in applicable_tags:
        _c_errcnt += 1
        errmsg = "unrecognized XML tag: %s" % name
        if _c_spanrep:
            span = _make_span(_c_text, _c_parser.CurrentLineNumber,
                              _c_parser.CurrentColumnNumber + 1, errmsg)
            _c_errspans.append(span)
        elif not _c_quiet:
            report_on_msg(errmsg, _c_msg, _c_cat)
        return

    # Check applicability of attributes.
    for attr in attrs:
        if name not in all_attrs or attr not in all_attrs[name]:
            _c_errcnt += 1
            errmsg = "invalid attribute for tag <%s>: %s" % (name, attr)
            if _c_spanrep:
                span = _make_span(_c_text, _c_parser.CurrentLineNumber,
                                  _c_parser.CurrentColumnNumber + 1, errmsg)
                _c_errspans.append(span)
            elif not _c_quiet:
                report_on_msg(errmsg, _c_msg, _c_cat)


# Handler to check existance of entities.
def _handler_default (text):

    global _c_errcnt

    if text.startswith('&') and text.endswith(';'):
        ent = text[1:-1]
        if (    ent not in default_entities
            and ent not in html_entities
            and ent not in _c_ents):
            _c_errcnt += 1
            errmsg = "unknown entity: %s" % ent
            if _c_spanrep:
                span = _make_span(_c_text, _c_parser.CurrentLineNumber,
                                  _c_parser.CurrentColumnNumber + 1, errmsg)
                _c_errspans.append(span)
            elif not _c_quiet:
                report_on_msg(errmsg, _c_msg, _c_cat)


# Check current msgstr.
def check_xml (cat, msg, msgstr, quiet=False, ents={}, spanrep=False):

    # Link current state for handlers.
    global _c_cat; _c_cat = cat
    global _c_msg; _c_msg = msg
    global _c_quiet; _c_quiet = quiet
    global _c_ents; _c_ents = ents
    global _c_errcnt; _c_errcnt = 0
    global _c_spanrep; _c_spanrep = spanrep
    global _c_errspans; _c_errspans = []
    global _c_parser
    global _c_text

    # Split into possible ordinary and scripted parts.
    texts = msgstr.split(ts_fence, 1)

    # Replace &-accelerators with &amp;, to not confuse with entities.
    texts = [_escape_amp_accel(x) for x in texts]

    for text in texts:
        # Make sure the text has the top tag.
        if not _top_tag_rx.search(text):
            text = "<%s>%s</%s>" % (top_tag, text, top_tag)

        # Parse the text.
        p = xml.parsers.expat.ParserCreate(_c_enc)
        p.UseForeignDTD() # not to barf on non-default XML entities
        p.StartElementHandler = _handler_start_element
        p.DefaultHandler = _handler_default
        _c_parser = p

        _c_text = text
        try:
            p.Parse(text.encode(_c_enc), True)
        except xml.parsers.expat.ExpatError, e:
            _c_errcnt += 1
            if spanrep:
                span = _make_span(text, e.lineno, e.offset, e.message)
                _c_errspans.append(span)
                return (_c_errspans, _c_text)
            elif not quiet:
                report_on_msg("XML parsing: %s" % e, msg, cat)
                return False

    if not spanrep:
        return _c_errcnt == 0
    else:
        return (_c_errspans, _c_text)


_near_xml_error_rx = re.compile(r"\W*[\w:.-]*[^\w\s>]*(\s*>)?", re.U)

def _make_span (text, lno, col, errmsg):

    # Find problematic position.
    clno = 1
    p = 0
    while clno < lno:
        p = text.find("\n", p)
        if p < 0:
            break
        p += 1
        clno += 1
    if p < 0:
        return (0, len(text))

    # Scoop some reasonable nearby text.
    m = _near_xml_error_rx.match(text, p + col - 1)
    if not m:
        return (0, len(text))
    return (m.start(), m.end(), errmsg)


# ----------------------------------------
# Check for conformant Qt-date format msgstr.

_qtdt_clean_rx = re.compile(r"'.*?'")
_qtdt_split_rx = re.compile(r"\W+", re.U)

def _qtdt_parse (text):

    text = _qtdt_clean_rx.sub("", text)
    fields = [x for x in _qtdt_split_rx.split(text) if x]
    return fields


def _qtdt_fjoin (fields):

    lst = list(fields)
    lst.sort()
    return ", ".join(lst)


# NOTE: May be used as summit msgstr hook, must return None
def check_qtdt (cat, msg, msgstr):

    # Check needed when used as summit hook.
    if "qtdt-format" not in msg.msgctxt.lower():
        return

    # Get format fields from the msgid.
    msgid_fmts = _qtdt_parse(msg.msgid)

    # Expect the same format fields in msgstr.
    msgstr_fmts = _qtdt_parse(msgstr)
    if set(msgid_fmts) != set(msgstr_fmts):
        report_on_msg("Qt date-format mismatch: "
                      "msgid has fields (%s) while msgstr has (%s)"
                      % (_qtdt_fjoin(msgid_fmts), _qtdt_fjoin(msgstr_fmts)),
                      msg, cat)

# ----------------------------------------
# The checker sieve.

class Sieve (object):
    """Check validity of XML in KDE4 messages."""

    def __init__ (self, options, global_options):

        self.nbad = 0

        # Whether to strictly check translations:
        # if False, XML errors in translation are reported only if original
        # itself is valid XML, otherwise errors are reported unconditionally.
        self.strict = False
        if "strict" in options:
            options.accept("strict")
            self.strict = True

        # Files defining external entities.
        self.entity_files = []
        if "entdef" in options:
            options.accept("entdef")
            self.entity_files = options["entdef"].split(",")

        # Whether to check only non-XML issues.
        self.nonxml = False
        if "nonxml" in options:
            options.accept("nonxml")
            self.nonxml = True

        # Read definitions of external entities.
        self.entities = read_entities(*self.entity_files)

        # Indicators to the caller:
        self.caller_sync = False # no need to sync catalogs to the caller
        self.caller_monitored = False # no need for monitored messages


    def process (self, msg, cat):

        # Check only translated messages.
        if not msg.translated:
            return

        # Do not check messages when told so.
        if flag_no_check_xml in manc_parse_flag_list(msg, "|"):
            return

        # Check Qt-date format if the string is such.
        if "qtdt-format" in msg.msgctxt.lower():
            for msgstr in msg.msgstr:
                check_qtdt(cat, msg, msgstr)

        # Stop here if only check of non-XML issues requested.
        if self.nonxml:
            return

        # In in non-strict mode, check XML of translation only if the
        # original itself is valid XML.
        if not self.strict:
            if (   not check_xml(cat, msg, msg.msgid,
                                 quiet=True, ents=self.entities)
                or not check_xml(cat, msg, msg.msgid_plural,
                                 quiet=True, ents=self.entities)):
                return

        # Check XML in translation.
        for msgstr in msg.msgstr:
            if not check_xml(cat, msg, msgstr, ents=self.entities):
                self.nbad += 1


    def finalize (self):

        if self.nbad > 0:
            if self.strict:
                report("Total translations with invalid XML (strict): %d"
                       % self.nbad)
            else:
                report("Total translations with invalid XML: %d" % self.nbad)

