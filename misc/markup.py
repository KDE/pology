# -*- coding: UTF-8 -*-

"""
Process text markup.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import os
import re
import codecs
import xml.parsers.expat

from pology.misc.report import error
from pology import rootdir
from pology.misc.diff import adapt_spans
from pology.misc.entities import read_entities


_nlgr_rx = re.compile(r"\n{2,}")
_wsgr_rx = re.compile(r"\s+")

def plain_to_unwrapped (text):
    """
    Convert wrapped plain text to unwrapped.

    Two or more newlines are considered as paragraph boundaries and left in,
    while all other newlines are removed.
    Whitespace in the text is simplified throughout.

    @param text: text to unwrap
    @type text: string

    @returns: unwrapped text
    @rtype: string
    """

    # Strip leading and trailing whitespace.
    text = text.strip()

    # Strip leading and trailing whitespace in all lines.
    text = "\n".join([x.strip() for x in text.split("\n")])

    # Mask all paragraph breaks.
    pbmask = "\x04\x04"
    text = _nlgr_rx.sub(pbmask, text)

    # Replace all whitespace groups with single space.
    text = _wsgr_rx.sub(" ", text)

    # Unmask paragraph breaks.
    text = text.replace(pbmask, "\n\n")

    return text


xml_entities = {
    "lt": "<",
    "gt": ">",
    "apos": "'",
    "quot": "\"",
    "amp": "&",
}

WS_SPACE = "\x04~sp"
WS_TAB = "\x04~tb"
WS_NEWLINE = "\x04~nl"
_ws_masks = {
    WS_SPACE: " ",
    WS_TAB: "\t",
    WS_NEWLINE: "\n",
}
_ws_unmasks = dict([(y, x) for x, y in _ws_masks.items()])

def xml_to_plain (text, tags=None, subs={}, ents={}, keepws=set(),
                  ignels=set()):
    """
    Convert any XML-like markup to plain text.

    By default, all tags in the text are replaced with a single space;
    entities, unless one of the XML default (C{&lt;}, C{&gt;}, C{&amp;},
    C{&quot;}, C{&apos;}), are left untouched;
    all whitespace groups are simplified to single space and leading and
    trailing removed.

    If only a particular subset of tags should be taken into account, it can
    be specified by the C{tags} parameter, as a sequence of tag names
    (the sequence is internally converted to set before processing).

    If a tag should be replaced with a special sequence of characters
    (either opening or closing tag), or the text wrapped by it replaced too,
    this can be specified by the C{subs} parameter. It is a dictionary of
    3-tuples by tag name, which tells what to replace with the opening tag,
    the closing tag, and the wrapped text. For example, to replace
    C{<i>foobar</i>} with C{/foobar/}, the dictionary entry would be
    C{{"i": ("/", "/", None)}} (where final C{None} states not to touch
    the wrapped text); to replace C{<code>...</code>} with C{@@@}
    (i.e. remove code segment completely but leave in a marker that there
    was something), the entry is C{{"code": ("", "", "@@@")}}.
    Note that whitespace is automatically simplified, so if whitespace
    given by the replacements should be exactly preserved, use C{WS_*}
    string constants in place of corresponding whitespace characters.

    To have some entities other than the XML default replaced with proper
    values, a dictionary of known entities with values may be provided using
    the C{ents} parameter.

    Whitespace can be preserved within some elements, as given by
    their tags in the C{keepws} sequence.

    Some elements may be completely removed, as given by the C{ignels} sequence.
    Each element of the sequence should either be a tag, or a (tag, type) tuple,
    where type is the value of the C{type} argument to element, if any.

    It is assumed that the markup is well-formed, and if it is not
    the result is undefined; but best attempt at conversion is made.

    There are several other functions in this module which deal with well known
    markups, such that it is not necessary to use this function with
    C{tags}, C{subs}, or C{ents} manually specified.

    If you only want to resolve entities from a known set, instead of
    calling this function with empty C{tags} and entities given in C{ents},
    consider using the more powerfull L{pology.misc.resolve.resolve_entities}.

    @param text: markup text to convert to plain
    @type text: string
    @param tags: known tags
    @type tags: sequence of strings
    @param subs: replacement specification
    @type subs: dictionary of 3-tuples
    @param ents: known entities and their values
    @type ents: dictionary
    @param keepws: tags of elements in which to preserve whitespace
    @type keepws: sequence of strings
    @param ignels: tags or tag/types or elements to completely remove
    @type ignels: sequence of strings and (string, string) tuples

    @returns: plain text version
    @rtype: string
    """

    # Convert some sequences to sets, for faster membership checks.
    if tags is not None and not isinstance(tags, set):
        tags = set(tags)
    if not isinstance(keepws, set):
        keepws = set(keepws)
    if not isinstance(ignels, set):
        ignels = set(ignels)

    # Resolve user-supplied entities before tags,
    # as they may contain more markup.
    # (Resolve default entities after tags,
    # because the default entities can introduce invalid markup.)
    text = _resolve_ents(text, ents, xml_entities)

    # Build element tree, trying to work around badly formed XML
    # (but do note when the closing element is missing).
    # Element tree is constructed as list of tuples:
    # (tag, opening_tag_literal, closing_tag_literal, atype, content)
    # where atype is the value of type attribute (if any),
    # and content is a sublist for given element;
    # tag may be #text, when the content is string.
    eltree = []
    curel = eltree
    parent = []
    any_tag = False
    p = 0
    while True:
        pp = p
        p = text.find("<", p)
        if p < 0:
            break
        curel.append(("#text", None, None, None, text[pp:p]))
        tag_literal, tag, atype, opening, p = _parse_tag(text, p)
        if p < 0:
            break
        if opening: # opening tag
            any_tag = True
            curel.append([tag, tag_literal, None, atype, []])
            parent.append(curel)
            curel = curel[-1][-1]
        else: # closing tag
            if parent:
                curel = parent.pop()
                curel[-1][2] = tag_literal # record closing tag literal
            else: # faulty markup, move top element
                eltree = [[tag, None, tag_literal, None, curel]]
                curel = eltree
    curel.append(("#text", None, None, None, text[pp:]))

    # Replace tags.
    text = _resolve_tags(eltree, tags, subs, keepws, ignels)

    # Resolve default entities.
    text = _resolve_ents(text, xml_entities)

    return text


def _parse_tag (text, p):
    # text[p] must be "<"

    tag = ""
    atype = None
    opening = True

    tlen = len(text)
    pp = p
    in_str = False
    in_tag = False
    in_attr = False
    in_lead = True
    in_afterslash = False
    in_aftereq = False
    in_aftertag = False
    in_afterattr = False
    ntag = ""
    nattr = ""
    while True:
        p += 1
        if p >= tlen:
            break

        if in_lead and not text[p].isspace():
            in_lead = False
            opening = text[p] != "/"
            if opening:
                in_tag = True
                p_tag = p
            else:
                in_afterslash = True
        elif in_afterslash and not text[p].isspace():
            in_afterslash = False
            in_tag = True
            p_tag = p
        elif in_tag and (text[p].isspace() or text[p] == ">"):
            in_tag = False
            in_aftertag = True
            tag = text[p_tag:p]
            ntag = tag.lower()
        elif in_aftertag and not (text[p].isspace() or text[p] == ">"):
            in_aftertag = False
            in_attr = True
            p_attr = p
        elif in_attr and (text[p].isspace() or text[p] in ("=", ">")):
            in_attr = False
            if text[p] != "=":
                in_afterattr = True
            else:
                in_aftereq = True
            attr = text[p_attr:p]
            nattr = attr.lower()
        elif in_aftereq and text[p] in ('"', "'"):
            in_aftereq = False
            in_str = True
            quote_char = text[p]
            p_str = p + 1
        elif in_str and text[p] == quote_char:
            in_str = False
            s = text[p_str:p].strip().replace(" ", "")
            if nattr == "type":
                atype = s
        elif in_afterattr and text[p] == "=":
            in_afterattr = False
            in_aftereq = True

        if not in_str and text[p] == ">":
            break

    p += 1
    tag_literal = text[pp:p]

    return tag_literal, tag, atype, opening, p


_entity_rx = re.compile(r"&([\w_:][\w\d._:-]*);")

def _resolve_ents (text, ents={}, ignents={}):
    """
    Resolve XML entities as described in L{xml_to_plain}, ignoring some.
    """

    # There may be entities within entities, so replace entities in each
    # entity value too before substituting in the main text.
    ntext = []
    p = 0
    while True:
        pp = p
        p = text.find("&", p)
        if p < 0:
            break
        ntext.append(text[pp:p])
        m = _entity_rx.match(text, p)
        if m:
            name = m.group(1)
            if name not in ignents:
                value = ents.get(name)
                if value is not None:
                    # FIXME: Endless recursion if the entity repeats itself.
                    value = _resolve_ents(value, ents, ignents)
                    ntext.append(value)
                else:
                    # Put entity back as-is.
                    ntext.append(m.group(0))
            else: # ignored entity, do not touch
                ntext.append(text[p:m.span()[1]])
            p = m.span()[1]
        else:
            ntext.append(text[p]) # the ampersand
            p += 1
    ntext.append(text[pp:])
    text = "".join(ntext)

    return text


# Ordinary around masked whitespace.
_wsgr_premask_rx = re.compile(r"\s+(\x04~\w\w)")
_wsgr_postmask_rx = re.compile(r"(\x04~\w\w)\s+")

def _resolve_tags (elseq, tags=None, subs={}, keepws=set(), ignels=set()):
    """
    Replace XML tags as described in L{xml_to_plain}, given the parsed tree.
    Split into top and recursive part.
    """

    # Text with masked whitespace where significant.
    text = _resolve_tags_r(elseq, tags, subs, keepws, ignels)

    # Simplify whitespace.
    text = _wsgr_rx.sub(" ", text)
    text = _wsgr_premask_rx.sub(r"\1", text)
    text = _wsgr_postmask_rx.sub(r"\1", text)
    text = text.strip()

    # Unmask significant whitespace.
    text = _unmask_ws(text)

    # Remove excess newlines even if supposedly significant.
    text = text.strip("\n")
    text = _nlgr_rx.sub("\n\n", text)

    return text


def _resolve_tags_r (elseq, tags=None, subs={}, keepws=set(), ignels=set()):

    segs = []
    for el in elseq:
        if el[0] in ignels or (el[0], el[3]) in ignels:
            # Complete element is ignored (by tag, or tag/type).
            continue

        if el[0] == "#text":
            segs.append(el[-1])
        elif tags is None or el[0] in tags:
            repl_pre, repl_post, repl_cont = subs.get(el[0], [" ", " ", None])
            if repl_pre is None:
                repl_pre = ""
            if repl_post is None:
                repl_post = ""
            if repl_cont is None:
                repl_cont = _resolve_tags_r(el[-1], tags, subs, keepws, ignels)
                if el[0] in keepws:
                    # Mask whitespace in wrapped text.
                    repl_cont = _mask_ws(repl_cont)
            # If space not significant,
            # find first non-whitespace characters in wrapped text
            # and shift them before surrounding replacements.
            if el[0] not in keepws:
                lcont = len(repl_cont)
                p1 = 0
                while p1 < lcont and repl_cont[p1].isspace():
                    p1 += 1
                p2 = lcont - 1
                while p2 > 0 and repl_cont[p2].isspace():
                    p2 -= 1
                repl_pre = repl_cont[:p1] + repl_pre
                repl_post = repl_post + repl_cont[p2+1:]
                repl_cont = repl_cont[p1:p2+1]
            segs.append(repl_pre + repl_cont + repl_post)
        else:
            # Ignored tag, put back verbatim.
            repl_pre = el[1]
            if repl_pre is None:
                repl_pre = ""
            repl_post = el[2]
            if repl_post is None:
                repl_post = ""
            repl_cont = _resolve_tags_r(el[-1], tags, subs, keepws, ignels)
            segs.append(repl_pre + repl_cont + repl_post)

    return "".join(segs)


def _mask_ws (text):

    for mask, ws in _ws_masks.items():
        text = text.replace(ws, mask)
    return text


def _unmask_ws (text):

    for mask, ws in _ws_masks.items():
        text = text.replace(mask, ws)
    return text


_html_tags = set("""
    qt html
    a b big blockquote body br center cite code dd dl dt em font
    h1 h2 h3 h4 h5 h6 head hr i img li meta nobr ol p pre
    s span strong style sub sup table td th tr tt u ul var
""".split())
_html_subs = {
    "_nows" : ("", "", None),
    "_parabr": (WS_NEWLINE*2, WS_NEWLINE*2, None),
}
_html_subs.update([(x, _html_subs["_nows"]) for x in _html_tags])
_html_subs.update([(x, _html_subs["_parabr"]) for x in
                   "br h1 h2 h3 h4 h5 h6 hr li p pre td th tr".split()])
_html_ents = { # in addition to default XML entities
    "nbsp": u"\xa0",
}
_html_keepws = set("""
    code pre
""".split())
_html_ignels = set([
    ("style", "text/css"),
])

def html_to_plain (text):
    """
    Convert HTML markup to plain text.

    @param text: HTML text to convert to plain
    @type text: string

    @returns: plain text version
    @rtype: string
    """

    return xml_to_plain(text, _html_tags, _html_subs, _html_ents,
                              _html_keepws, _html_ignels)


_kuit_tags = set("""
    kuit kuil title subtitle para list item note warning
    filename link application command resource icode bcode shortcut interface
    emphasis placeholder email envar message numid nl
""".split())
_kuit_subs = {
    "_nows" : ("", "", None),
    "_parabr" : ("", WS_NEWLINE*2, None),
}
_kuit_subs.update([(x, _kuit_subs["_nows"]) for x in _kuit_tags])
_kuit_subs.update([(x, _kuit_subs["_parabr"]) for x in
                   "title subtitle para item".split()])
_kuit_ents = { # in addition to default XML entities
}
_kuit_keepws = set("""
    icode bcode
""".split())
_kuit_ignels = set([
])

def kuit_to_plain (text):
    """
    Convert KUIT markup to plain text.

    @param text: KUIT text to convert to plain
    @type text: string

    @returns: plain text version
    @rtype: string
    """

    return xml_to_plain(text, _kuit_tags, _kuit_subs, _kuit_ents, 
                              _kuit_keepws, _kuit_ignels)


_htkt_tags = set(list(_html_tags) + list(_kuit_tags))
_htkt_subs = dict(_html_subs.items() + _kuit_subs.items())
_htkt_ents = dict(_html_ents.items() + _kuit_ents.items())
_htkt_keepws = set(list(_html_keepws) + list(_kuit_keepws))
_htkt_ignels = set(list(_html_ignels) + list(_kuit_ignels))

def kde4_to_plain (text):
    """
    Convert KDE4 GUI markup to plain text.

    KDE4 GUI texts may contain both (X)HTML and KUIT markup,
    even mixed in the same text.
    Note that the conversion cannot be achieved, in general, by first
    converting (X)HTML, and then KUIT, or vice versa.
    For example, if the text has C{&lt;} entity, after first conversion
    it will become plain C{<}, and interfere with second conversion.

    @param text: KDE4 text to convert to plain
    @type text: string

    @returns: plain text version
    @rtype: string
    """

    return xml_to_plain(text, _htkt_tags, _htkt_subs, _htkt_ents,
                              _htkt_keepws, _htkt_ignels)


# Assembled on first use.
_dbk_tags = None
_dbk_subs = None
_dbk_ents = None
_dbk_keepws = None
_dbk_ignels = None

def _prep_docbook4_to_plain ():

    global _dbk_tags, _dbk_subs, _dbk_ents, _dbk_keepws, _dbk_ignels

    specpath = os.path.join(rootdir(), "spec", "docbook4.l1")
    docbook4_tagattrs = collect_xml_spec_l1(specpath)

    _dbk_tags = set(docbook4_tagattrs.keys())

    _dbk_subs = {
        "_nows" : ("", "", None),
        "_parabr" : ("", WS_NEWLINE*2, None),
    }
    _dbk_subs.update([(x, _kuit_subs["_nows"]) for x in _dbk_tags])
    _dbk_subs.update([(x, _kuit_subs["_parabr"]) for x in
                      "para title".split()]) # FIXME: Add more.

    _dbk_ents = { # in addition to default XML entities
    }

    _dbk_keepws = set("""
        screen programlisting
    """.split()) # FIXME: Add more.

    _dbk_ignels = set([
    ])

def docbook4_to_plain (text):
    """
    Convert Docbook 4.x markup to plain text.

    @param text: Docbook text to convert to plain
    @type text: string

    @returns: plain text version
    @rtype: string
    """

    if _dbk_tags is None:
        _prep_docbook4_to_plain()

    return xml_to_plain(text, _dbk_tags, _dbk_subs, _dbk_ents,
                              _dbk_keepws, _dbk_ignels)


def collect_xml_spec_l1 (specpath):
    """
    Collect informal XML format specification, level 1.

    Level 1 specification is the dictionary of all known tags, with
    allowed attributes (by name only) for each.

    File of the level 1 specification is in the following format::

        # A comment.
        tagA;  # tag without any attributes
        tagB: attr1, attr2;  # tag having some attributes
        tagC: attr1, attr2, attr3, attr4,
              attr5, attr6;  # tag with many attributes, split over lines

    The specification can contain a dummy tag named C{pe-common-attributes},
    stating attributes which are common to all tags, instead of having to
    list them with each and every tag.

    Specification file must be UTF-8 encoded.

    @param specpath: path to level 1 specification file
    @type specpath: string

    @return: level 1 specification
    @rtype: dict
    """

    ifl = codecs.open(specpath, "r", "UTF-8")
    stripc_rx = re.compile(r"#.*")
    specstr = "".join([stripc_rx.sub('', x) for x in ifl.readlines()])
    ifl.close()
    tagattrs = {}
    for elspec in specstr.split(";"):
        lst = elspec.split(":")
        tag = lst.pop(0).strip()
        if not tag:
            continue
        tagattrs[tag] = {}
        if lst:
            attrs = lst[0].split()
            tagattrs[tag] = dict([(attr, True) for attr in attrs])

    # Add common attributes to each tag.
    cattrs = tagattrs.pop("pe-common-attrib", [])
    if cattrs:
        for attrs in tagattrs.itervalues():
            attrs.update(cattrs)

    return tagattrs


# Simplified matching of XML entity name (sans ampersand and semicolon).
_simple_ent_rx = re.compile(r"^([a-zA-Z0-9_.:-]+|#[0-9]+)$");

# Get line/column segment in error report.
_lin_col_rx = re.compile(r":\s*line\s*\d+,\s*column\s*\d+", re.I)

# Dummy top tag for topless texts.
_dummy_top = "_"

# Formatting for head of XML error messages.
_ehfmt = "(%s markup) "

# Global data for XML checking.
class _Global: pass
_g_xml_l1 = _Global()

def check_xml_l1 (text, spec=None, xmlfmt=None, ents=None,
                  casesens=True, accelamp=False):
    """
    Validate XML markup in text against L{level1<collect_xml_spec_l1>}
    specification.

    Text is not required to have a top tag; if it does not, a dummy one will
    be assigned to assure that the check passes.

    If C{spec} is C{None}, text is only checked to be well-formed.

    If C{ents} are C{None}, entities in the text are ignored by the check;
    otherwise, an entity not belonging to the known set is considered erroneous.
    Default XML entities (C{&lt;}, C{&gt;}, C{&amp;}, C{&quot;}, C{&apos;})
    are automatically added to the set of known entities.

    Tag and attribute names can be made case-insensitive by setting
    C{casesens} to C{False}.

    If text is a part of user interface, and the environment may use
    the literal ampersand as accelerator marker, it can be allowed to pass
    the check by setting C{accelamp} to C{True}.

    The result of the check is list of erroneous spans in the text,
    each given by start and end index (in Python standard semantics),
    and the error description, packed in a tuple.
    If there are no errors, empty list is returned.
    Reported spans need not be formally complete with respect to the error
    location, but are heuristically determined to be short and
    provide good visual indication of what triggers the error.

    @param text: text to check
    @type text: string
    @param spec: markup definition
    @type spec: L{level1<collect_xml_spec_l1>} specification
    @param xmlfmt: name of the particular XML format (for error messages)
    @type xmlfmt: string
    @param ents: set of known entities
    @type ents: sequence
    @param casesens: whether tag names are case-insensitive
    @type casesens: bool
    @param accelamp: whether to allow ampersand as accelerator marker
    @type accelamp: bool

    @returns: erroneous spans in the text
    @rtype: list of (int, int, string) tuples
    """

    # If ampersand accelerator marked allowed, replace one in non-entity
    # position with &amp;, to let the parser proceed.
    text_orig = text
    if accelamp:
        text = _escape_amp_accel(text)

    # Make sure the text has a top tag.
    text = "<%s>%s</%s>" % (_dummy_top, text, _dummy_top)

    # Prepare parser.
    xenc = "UTF-8"
    parser = xml.parsers.expat.ParserCreate(xenc)
    parser.UseForeignDTD() # not to barf on non-default XML entities
    parser.StartElementHandler = _handler_start_element
    parser.DefaultHandler = _handler_default

    # Link state for handlers.
    g = _g_xml_l1
    g.text = text
    g.spec = spec
    g.xmlfmt = xmlfmt or "XML"
    g.ents = ents
    g.casesens = casesens
    g.xenc = xenc
    g.parser = parser
    g.errcnt = 0
    g.spans = []

    # Parse and check.
    try:
        parser.Parse(text.encode(xenc), True)
    except xml.parsers.expat.ExpatError, e:
        errmsg = (_ehfmt + "%s") % (g.xmlfmt, e.message)
        span = _make_span(text, e.lineno, e.offset, errmsg)
        g.spans.append(span)

    # Adapt spans back to original text.
    pure_spans = [x[:2] for x in g.spans]
    pure_spans = adapt_spans(text_orig, text, pure_spans, merge=False)
    # Remove unhelpful line/column in error messages.
    errmsgs = []
    for errmsg, span in zip([x[2] for x in g.spans], pure_spans):
        m = _lin_col_rx.search(errmsg)
        if m:
            errmsg = errmsg[:m.start()] + errmsg[m.end():]
        errmsgs.append(errmsg)
    # Put spans back together.
    g.spans = [x + (y,) for x, y in zip(pure_spans, errmsgs)]

    return g.spans


def _escape_amp_accel (text):

    pos_amp = -1
    num_amp = 0

    p1 = 0
    while True:

        # Bracket possible entity reference.
        p1 = text.find("&", p1)
        if p1 < 0:
            break
        p2 = text.find(";", p1)

        # An accelerator marker if no semicolon in rest of the text
        # or the bracketed segment does not look like an entity,
        # and it is in front of an alphanumeric or itself
        # (or in front of tilde-directive, special in KDE4).
        nc = text[p1 + 1:p1 + 2]
        if (    (p2 < 0 or not _simple_ent_rx.match(text[p1 + 1:p2]))
            and ((nc.isalnum() or nc == "~") or nc == "&")
        ):
            pos_amp = p1
            num_amp = 1
            # Check if the next one is an ampersand too,
            # i.e. if it's an escaped accelerator markup.
            # FIXME: Or perhaps not let the other ampersand pass?
            if text[p1 + 1:p1 + 2] == "&":
                num_amp += 1

            break

        if p2 < 0:
            break

        p1 = p2

    if num_amp > 0:
        text = text[:pos_amp] + "&amp;" * num_amp + text[pos_amp + num_amp:]

    return text


def _handler_start_element (tag, attrs):

    g = _g_xml_l1

    if g.spec is None:
        return

    # Normalize names to lower case if allowed.
    if not g.casesens:
        tag = tag.lower()
        attrs = [x.lower() for x in attrs]

    # Check existence of the tag.
    if tag not in g.spec and tag != _dummy_top:
        errmsg = (_ehfmt + "unrecognized tag '%s'") % (g.xmlfmt, tag)
        span = _make_span(g.text, g.parser.CurrentLineNumber,
                          g.parser.CurrentColumnNumber + 1, errmsg)
        g.spans.append(span)
        return

    if tag == _dummy_top:
        return

    # Check applicability of attributes.
    known_attrs = g.spec[tag]
    for attr in attrs:
        if attr not in known_attrs:
            errmsg = ((_ehfmt + "invalid attribute '%s' to tag '%s'")
                      % (g.xmlfmt, attr, tag))
            span = _make_span(g.text, g.parser.CurrentLineNumber,
                              g.parser.CurrentColumnNumber + 1, errmsg)
            g.spans.append(span)


def _handler_default (text):

    g = _g_xml_l1

    if g.ents is not None and text.startswith('&') and text.endswith(';'):
        ent = text[1:-1]
        if ent not in g.ents and ent not in xml_entities:
            errmsg = (_ehfmt + "unknown entity '%s'") % (g.xmlfmt, ent)
            span = _make_span(g.text, g.parser.CurrentLineNumber,
                              g.parser.CurrentColumnNumber + 1, errmsg)
            g.spans.append(span)


# Text to fetch from the reported error position in XML stream.
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
        return (0, len(text), errmsg)
    start, end = m.span()
    while text[start].isalnum():
        if start == 0:
            break
        start -= 1

    return (start, end, errmsg)


_docbook4_l1 = None

def check_xml_docbook4_l1 (text, ents=None):
    """
    Validate Docbook 4.x markup in text against L{level1<collect_xml_spec_l1>}
    specification.

    Markup definition is extended to include C{<placeholder-N/>} elements,
    which C{xml2po} uses to segment text when extracting markup documents
    into PO templates.

    See L{check_xml_l1} for description of the C{ents} parameter
    and the return value.

    @param text: text to check
    @type text: string
    @param ents: set of known entities (in addition to default)
    @type ents: sequence

    @returns: erroneous spans in the text
    @rtype: list of (int, int, string) tuples
    """

    # FIXME: Freak message in konqueror_browser.po that puts
    # Python's difflib.ndiff() into infinite loop.
    if text.startswith("1, 7, 9, 11, 13, 15, 17, 19"):
        return []

    global _docbook4_l1
    if _docbook4_l1 is None:
        specpath = os.path.join(rootdir(), "spec", "docbook4.l1")
        _docbook4_l1 = collect_xml_spec_l1(specpath)

    return check_xml_l1(text, spec=_docbook4_l1, xmlfmt="Docbook4", ents=ents)


_placeholder_el_rx = re.compile(r"<\s*placeholder-(\d+)\s*/\s*>")

def check_placeholder_els (orig, trans):
    """
    Check if sets of C{<placeholder-N/>} elements are matching between
    original and translated text.

    C{<placeholder-N/>} elements are added into text by C{xml2po},
    for finer segmentation of markup documents extracted into PO templates.

    See L{check_xml_l1} for description of the return value.

    @param orig: original text
    @type orig: string
    @param trans: translated text
    @type trans: string

    @returns: erroneous spans in translation
    @rtype: list of (int, int, string) tuples
    """

    spans = []

    orig_plnums = set()
    for m in _placeholder_el_rx.finditer(orig):
        orig_plnums.add(m.group(1))
    trans_plnums = set()
    for m in _placeholder_el_rx.finditer(trans):
        trans_plnums.add(m.group(1))

    missing_plnums = list(orig_plnums.difference(trans_plnums))
    extra_plnums = list(trans_plnums.difference(orig_plnums))
    if missing_plnums:
        tags = "".join(["<placeholder-%s/>" % x for x in missing_plnums])
        errmsg = ("Missing placeholder tags in translation: %s" % tags)
        spans.append((0, 0, errmsg))
    elif extra_plnums: # do not report both, single glitch may cause them
        tags = "".join(["<placeholder-%s/>" % x for x in extra_plnums])
        errmsg = ("Extra placeholder tags in translation: %s" % tags)
        spans.append((0, 0, errmsg))

    return spans


# Class for making several dictionaries readable as one,
# without creating a single one with the union of keys from all other.
class _Multidict (object):

    def __init__ (self, dicts):
        # Order of dictionaries in the list matters,
        # firstmost has higher priority when looking for key.
        self.dicts = dicts

    def __contains__ (self, key):
        for d in self.dicts:
            if key in d:
                return True
        return False

    def __getitem__ (self, key):
        for d in self.dicts:
            if key in d:
                return d[key]
        raise KeyError, key

    def get (self, key, defval=None):
        for d in self.dicts:
            if key in d:
                return d[key]
        return defval


_entpath_html = os.path.join(rootdir(), "spec", "html.entities")
html_entities = read_entities(_entpath_html)

_html_l1 = None

def check_xml_html_l1 (text, ents=None):
    """
    Validate XHTML markup in text against L{level1<collect_xml_spec_l1>}
    specification.

    See L{check_xml_l1} for description of the C{ents} parameter
    and the return value.

    @param text: text to check
    @type text: string
    @param ents: set of known entities (in addition to default)
    @type ents: sequence

    @returns: erroneous spans in the text
    @rtype: list of (int, int, string) tuples
    """

    global _html_l1
    if _html_l1 is None:
        specpath = os.path.join(rootdir(), "spec", "html.l1")
        _html_l1 = collect_xml_spec_l1(specpath)

    if ents is not None:
        ents = _Multidict([ents, html_entities])

    return check_xml_l1(text, spec=_html_l1, xmlfmt="XHTML", ents=ents,
                        casesens=False)


_kuit_l1 = None

def check_xml_kuit_l1 (text, ents=None):
    """
    Validate KUIT markup in text against L{level1<collect_xml_spec_l1>}
    specification.

    KUIT is the semantic markup for user interface in KDE4.

    See L{check_xml_l1} for description of the C{ents} parameter
    and the return value.

    @param text: text to check
    @type text: string
    @param ents: set of known entities (in addition to default)
    @type ents: sequence

    @returns: erroneous spans in the text
    @rtype: list of (int, int, string) tuples
    """

    global _kuit_l1
    if _kuit_l1 is None:
        specpath = os.path.join(rootdir(), "spec", "html.l1")
        _kuit_l1 = collect_xml_spec_l1(specpath)

    return check_xml_l1(text, spec=_kuit_l1, xmlfmt="KUIT", ents=ents)


_kde4_l1 = None
_kde4_ents = None

def check_xml_kde4_l1 (text, ents=None):
    """
    Validate markup in texts used in KDE4 GUI.

    KDE4 GUI texts may contain both XHTML (Qt's subset of it, in fact)
    and KUIT markup, even mixed in the same text.

    See L{check_xml_l1} for description of the C{ents} parameter
    and the return value.

    @param text: text to check
    @type text: string
    @param ents: set of known entities (in addition to default)
    @type ents: sequence

    @returns: erroneous spans in the text
    @rtype: list of (int, int, string) tuples
    """

    global _kde4_l1, _kde4_ents
    if _kde4_l1 is None:
        _kde4_l1 = {}
        spath1 = os.path.join(rootdir(), "spec", "html.l1")
        _kde4_l1.update(collect_xml_spec_l1(spath1))
        spath2 = os.path.join(rootdir(), "spec", "kuit.l1")
        _kde4_l1.update(collect_xml_spec_l1(spath2))
        _kde4_ents = html_entities.copy()

    if ents is not None:
        ents = _Multidict([ents, _kde4_ents])

    return check_xml_l1(text, spec=_kde4_l1, xmlfmt="KDE4", ents=ents,
                        accelamp=True, casesens=False)

