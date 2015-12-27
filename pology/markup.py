# -*- coding: UTF-8 -*-

"""
Convert and validate markup in text.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import os
import re
import codecs
import xml.parsers.expat
import difflib

from pology import PologyError, datadir, _, n_
from pology.comments import manc_parse_flag_list
from pology.diff import adapt_spans
from pology.entities import read_entities
from pology.getfunc import get_result_ireq
from pology.msgreport import report_on_msg
from pology.multi import Multidict
from pology.report import format_item_list


# Pipe flag used to manually prevent check for a particular message.
flag_no_check_markup = "no-check-markup"


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
    The replacement for the wrapped text can also be a function,
    taking a string and returning a string.
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
    consider using the more powerfull L{pology.resolve.resolve_entities}.

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
        tag_literal, tag, atype, opening, closing, p = _parse_tag(text, p)
        if p < 0:
            break
        if opening: # opening tag
            any_tag = True
            curel.append([tag, tag_literal, None, atype, []])
            parent.append(curel)
            curel = curel[-1][-1]
        if closing: # closing tag (can be both opening and closing)
            if parent:
                curel = parent.pop()
                if not opening:
                    # Record closing tag literal if not opening as well.
                    curel[-1][2] = tag_literal 
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
    closing = False

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
        elif in_tag and (text[p].isspace() or text[p] in "/>"):
            in_tag = False
            in_aftertag = True
            tag = text[p_tag:p]
            ntag = tag.lower()
        elif in_aftertag and not (text[p].isspace() or text[p] in "/>"):
            in_aftertag = False
            in_attr = True
            p_attr = p
        elif in_attr and (text[p].isspace() or text[p] in "=/>"):
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

        if not in_str and text[p] == "/":
            closing = True
        if not in_str and text[p] == ">":
            break

    p += 1
    tag_literal = text[pp:p]

    return tag_literal, tag, atype, opening, closing, p


_entity_rx = re.compile(r"&([\w:][\w\d.:-]*);", re.U)

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
            repl_cont_orig = repl_cont
            if not isinstance(repl_cont, basestring):
                repl_cont = _resolve_tags_r(el[-1], tags, subs, keepws, ignels)
                if el[0] in keepws:
                    # Mask whitespace in wrapped text.
                    repl_cont = _mask_ws(repl_cont)
            if callable(repl_cont_orig):
                repl_cont = repl_cont_orig(repl_cont)
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
    a address applet area b base basefont big blockquote body br button
    caption center cite code col colgroup dd del dfn dir div dl dt
    em fieldset font form frame frameset h1 h2 h3 h4 h5 h6 head hr html
    i iframe img input ins isindex kbd label legend li link map menu meta
    noframes noscript ol option p param pre
    s samp script select small span strike strong style sub sup
    table tbody td textarea tfoot th thead title tr tt u ul var xmp
""".split())
_html_subs = {
    "_nows" : ("", "", None),
    "_parabr": (WS_NEWLINE*2, WS_NEWLINE*2, None),
}
_html_subs.update([(x, _html_subs["_nows"]) for x in _html_tags])
_html_subs.update([(x, _html_subs["_parabr"]) for x in
                   "br dd dl dt h1 h2 h3 h4 h5 h6 hr li p pre td th tr"
                   "".split()])
_html_ents = { # in addition to default XML entities
    "nbsp": u"\xa0",
}
_html_keepws = set("""
    code pre xmp
""".split())
_html_ignels = set([
    ("style", "text/css"),
])

def html_plain (text):
    """
    Convert HTML markup to plain text.

    @param text: HTML text to convert to plain
    @type text: string

    @returns: plain text version
    @rtype: string
    """

    return xml_to_plain(text, _html_tags, _html_subs, _html_ents,
                              _html_keepws, _html_ignels)


_qtrich_tags = set("""
    qt html
    a b big blockquote body br center cite code dd dl dt em font
    h1 h2 h3 h4 h5 h6 head hr i img li meta nobr ol p pre
    s span strong style sub sup table td th tr tt u ul var
""".split())
_qtrich_subs = {
    "_nows" : ("", "", None),
    "_parabr": (WS_NEWLINE*2, WS_NEWLINE*2, None),
}
_qtrich_subs.update([(x, _qtrich_subs["_nows"]) for x in _qtrich_tags])
_qtrich_subs.update([(x, _qtrich_subs["_parabr"]) for x in
                   "br dd dl dt h1 h2 h3 h4 h5 h6 hr li p pre td th tr"
                   "".split()])
_qtrich_ents = { # in addition to default XML entities
    "nbsp": u"\xa0",
}
_qtrich_keepws = set("""
    code pre
""".split())
_qtrich_ignels = set([
    ("style", "text/css"),
])

def qtrich_to_plain (text):
    """
    Convert Qt rich-text markup to plain text.

    @param text: Qt rich text to convert to plain
    @type text: string

    @returns: plain text version
    @rtype: string
    """

    return xml_to_plain(text, _qtrich_tags, _qtrich_subs, _qtrich_ents,
                              _qtrich_keepws, _qtrich_ignels)


_kuit_tags = set("""
    kuit kuil title subtitle para list item note warning
    filename link application command resource icode bcode shortcut interface
    emphasis placeholder email envar message numid nl
""".split())
_kuit_subs = {
    "_nows" : ("", "", None),
    "_parabr" : ("", WS_NEWLINE*2, None),
    "_ws" : (" ", " ", None),
    "_ui" : ("[", "]", None),
}
_kuit_subs.update([(x, _kuit_subs["_nows"]) for x in _kuit_tags])
_kuit_subs.update([(x, _kuit_subs["_ws"]) for x in
                   "placeholder".split()])
_kuit_subs.update([(x, _kuit_subs["_parabr"]) for x in
                   "title subtitle para item nl"
                   "".split()])
_kuit_subs.update([(x, _kuit_subs["_ui"]) for x in
                   "interface".split()])
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


_htkt_tags = set(list(_qtrich_tags) + list(_kuit_tags))
_htkt_subs = dict(_qtrich_subs.items() + _kuit_subs.items())
_htkt_ents = dict(_qtrich_ents.items() + _kuit_ents.items())
_htkt_keepws = set(list(_qtrich_keepws) + list(_kuit_keepws))
_htkt_ignels = set(list(_qtrich_ignels) + list(_kuit_ignels))

def kde4_to_plain (text):
    """
    Convert KDE4 GUI markup to plain text.

    KDE4 GUI texts may contain both Qt rich-text and KUIT markup,
    even mixed in the same text.
    Note that the conversion cannot be achieved, in general, by first
    converting Qt rich-text, and then KUIT, or vice versa.
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

    specpath = os.path.join(datadir(), "spec", "docbook4.l1")
    docbook4_l1 = collect_xml_spec_l1(specpath)
    _dbk_tags = set(docbook4_l1.keys())

    _dbk_subs = {
        "_nows" : ("", "", None),
        "_parabr" : ("", WS_NEWLINE*2, None),
        "_ws" : (" ", " ", None),
        "_ui" : ("[", "]", None),
        "_uipath" : ("", "", lambda s: re.sub("\]\s*\[", "->", s, re.U)),
    }
    _dbk_subs.update([(x, _dbk_subs["_nows"]) for x in _dbk_tags])
    _dbk_subs.update([(x, _dbk_subs["_parabr"]) for x in
                      "para title".split()]) # FIXME: Add more.
    _dbk_subs.update([(x, _dbk_subs["_ws"]) for x in
                       "contrib address firstname placeholder surname "
                       "primary secondary "
                       "".split()])
    _dbk_subs.update([(x, _dbk_subs["_ui"]) for x in
                       "guilabel guibutton guiicon guimenu guisubmenu "
                       "guimenuitem "
                       "".split()])
    _dbk_subs.update([(x, _dbk_subs["_uipath"]) for x in
                       "menuchoice "
                       "".split()])

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
    Collect lightweight XML format specification, level 1.

    Level 1 specification is the dictionary of all known tags,
    with allowed attributes and subtags for each.

    File of the level 1 specification is in the following format::

        # A comment.
        # Tag with unconstrained attributes and subtags:
        tagA;
        # Tag with constrained attributes and unconstrained subtags:
        tagF : attr1 attr2 ...;
        # Tag with unconstrained attributes and constrained subtags:
        tagF > stag1 stag2 ...;
        # Tag with constrained attributes and subtags:
        tagF : attr1 attr2 ... > stag1 stag2 ...;
        # Tag with no attributes and unconstrained subtags:
        tagA :;
        # Tag with unconstrained attributes and no subtags:
        tagA >;
        # Tag with no attributes and no subtags:
        tagA :>;
        # Attribute value constrained by a regular expression:
        .... attr1=/^(val1|val2|val3)$/i ...
        # Reserved dummy tag specifying attributes common to all tags:
        pe-common-attrib : attrX attrY;

    The specification can contain a dummy tag named C{pe-common-attrib},
    stating attributes which are common to all tags, instead of having to
    list them with each and every tag.
    To make an attribute mandatory, it's name should be prefixed by
    exclamation sign (!).

    Specification file must be UTF-8 encoded.

    @param specpath: path to level 1 specification file
    @type specpath: string

    @return: level 1 specification
    @rtype: dict
    """

    ch_comm = "#"
    ch_attr = ":"
    ch_attre = "="
    ch_mattr = "!"
    ch_stag = ">"
    ch_end = ";"

    dtag_attr = "pe-common-attrib"

    valid_tag_rx = re.compile("^[\w-]+$")
    valid_attr_rx = re.compile("^[\w-]+$")

    c_tag, c_attr, c_attre, c_stag = range(4)

    ifs = codecs.open(specpath, "r", "UTF-8").read()
    lenifs = len(ifs)

    pos = [0, 1, 1]

    def signal (msg, bpos):

        emsg = _("@info \"L1-spec\" is shorthand for "
                 "\"level 1 specification\"",
                 "[L1-spec] %(file)s:%(line)d:%(col)d: %(msg)s",
                 file=specpath, line=bpos[0], col=bpos[1], msg=msg)
        raise PologyError(emsg)

    def advance (stoptest, cmnt=True):

        ind = pos[0]
        oind = ind
        substr = []
        sep = None
        while ind < lenifs and sep is None:
            if cmnt and ifs[ind] == ch_comm:
                ind = ifs.find("\n", ind)
                if ind < 0:
                    break
            else:
                sep = stoptest(ind)
                if sep is None:
                    substr.append(ifs[ind])
                    ind += 1
                else:
                    ind += len(sep)

        pos[0] = ind
        rawsubstr = ifs[oind:ind]
        p = rawsubstr.rfind("\n")
        if p >= 0:
            pos[1] += rawsubstr.count("\n")
            pos[2] = len(rawsubstr) - p
        else:
            pos[2] += len(rawsubstr)

        return "".join(substr), sep

    def make_rx_lint (rx_str, rx_flags, wch, lincol):
        try:
            rx = re.compile(rx_str, rx_flags)
        except:
            signal(_("@info the regex is already quoted when inserted",
                     "Cannot compile regular expression %(regex)s.",
                     regex=(wch + rx_str + wch)),
                     lincol)
        return lambda x: rx.search(x) is not None

    spec = {}
    ctx = c_tag
    entry = None
    while pos[0] < lenifs:
        if ctx == c_tag:
            t = lambda i: (    ifs[i] in (ch_attr, ch_stag, ch_end)
                           and ifs[i] or None)
            tag, sep = advance(t)
            tag = tag.strip()
            if tag:
                if sep is None:
                    signal(_("@info",
                             "Entry not terminated after the initial tag."),
                           lincol)
                if not valid_tag_rx.search(tag) and tag != dtag_attr:
                    signal(_("@info",
                             "Invalid tag name '%(tag)s'.", tag=tag),
                             lincol)
                entry = _L1Element(tag)
                spec[tag] = entry

            if sep == ch_attr:
                ctx = c_attr
            elif sep == ch_stag:
                ctx = c_stag
            elif sep == ch_end:
                ctx = c_tag
            else:
                break

        elif ctx == c_attr:
            if entry.attrs is None:
                entry.attrs = set()

            lincol = tuple(pos[1:])
            t = lambda i: (    (   ifs[i].isspace()
                                or ifs[i] in (ch_attre, ch_stag, ch_end))
                           and ifs[i] or [None])[0]
            attr, sep = advance(t)
            attr = attr.strip()
            if attr:
                if attr.startswith(ch_mattr):
                    attr = attr[len(ch_mattr):]
                    entry.mattrs.add(attr)
                if attr in entry.attrs:
                    signal(_("@info",
                             "Duplicate attribute '%(attr)s'.", attr=attr),
                             lincol)
                if not valid_attr_rx.search(attr):
                    signal(_("@info",
                             "Invalid attribute name '%(attr)s'.", attr=attr),
                             lincol)
                entry.attrs.add(attr)
                lastattr = attr

            if sep.isspace():
                ctx = c_attr
            elif sep == ch_attre:
                ctx = c_attre
            elif sep == ch_stag:
                ctx = c_stag
            elif sep == ch_end:
                ctx = c_tag
            else:
                signal(_("@info",
                         "Entry not terminated after the attribute list."),
                       lincol)

        elif ctx == c_attre:
            lincol = tuple(pos[1:])
            t = lambda i: not ifs[i].isspace() and ifs[i] or None
            sub, wch = advance(t)
            if wch is None:
                signal(_("@info",
                         "End of input inside the value constraint."),
                       lincol)
            t = lambda i: ifs[i] == wch and ifs[i] or None
            rx_str, sep = advance(t, cmnt=False)
            if sep is None:
                signal(_("@info",
                         "End of input inside the value constraint."),
                       lincol)
            t = lambda i: (not ifs[i].isalpha() and [""] or [None])[0]
            rx_flag_spec, sep = advance(t)
            rx_flags = re.U
            seen_flags = set()
            lincol = tuple(pos[1:])
            for c in rx_flag_spec:
                if c in seen_flags:
                    signal(_("@info",
                             "Regex flag '%(flag)s' is already issued.",
                             flag=c), lincol)
                if c == "i":
                    rx_flags |= re.I
                else:
                    signal(_("@info",
                             "Unknown regex flag '%(flag)s'.", flag=c),
                             lincol)
                seen_flags.add(c)
            entry.avlints[lastattr] = make_rx_lint(rx_str, rx_flags,
                                                   wch, lincol)
            ctx = c_attr

        elif ctx == c_stag:
            if entry.stags is None:
                entry.stags = set()

            lincol = tuple(pos[1:])
            t = lambda i: (    (ifs[i].isspace() or ifs[i] == ch_end)
                           and ifs[i] or [None])[0]
            stag, sep = advance(t)
            stag = stag.strip()
            if stag:
                if stag in entry.stags:
                    signal(_("@info",
                             "Repeated subtag '%(tag)s'.", tag=stag),
                             lincol)
                entry.stags.add(stag)

            if sep == ch_end:
                ctx = c_tag
            else:
                signal(_("@info",
                         "Entry not terminated after the subtag list."),
                       lincol)

    # Add common attributes to each tag.
    dentry_attr = spec.pop(dtag_attr, [])
    if dentry_attr:
        for attr in dentry_attr.attrs:
            attre = dentry_attr.avlints.get(attr)
            for entry in spec.values():
                if entry.attrs is None:
                    entry.attrs = set()
                if attr not in entry.attrs:
                    entry.attrs.add(attr)
                    if attre:
                        entry.avlints[attr] = attre

    return spec


class _L1Element:

    def __init__ (self, tag=None, attrs=None, mattrs=set(), avlints={},
                  stags=None):

        # The tag of this element (string).
        self.tag = tag
        # Possible attributes (set, or None meaning any).
        self.attrs = attrs
        # Mandatory attributes (set).
        self.mattrs = mattrs
        # Validator functions for attribute values, per attribute (dict).
        # Validator does not have to be defined for each attribute.
        self.avlints = avlints
        # Possible subelements by tag (set, or None meaning any).
        self.stags = stags


# Simplified matching of XML entity name (sans ampersand and semicolon).
_simple_ent_rx = re.compile(r"^([\w.:-]+|#[0-9]+)$", re.U);

# Get line/column segment in error report.
_lin_col_rx = re.compile(r":\s*line\s*\d+,\s*column\s*\d+", re.I)

# Dummy top tag for topless texts.
_dummy_top = "_"


# Global data for XML checking.
class _Global: pass
_g_xml_l1 = _Global()

def validate_xml_l1 (text, spec=None, xmlfmt=None, ents=None,
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

    Text can be one or more entity definitions of the form C{<!ENTITY ...>},
    when special check is applied.

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

    if text.lstrip().startswith("<!ENTITY"):
        return _validate_xml_entdef(text, xmlfmt)

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
    g.tagstack = []

    # Parse and check.
    try:
        parser.Parse(text.encode(xenc), True)
    except xml.parsers.expat.ExpatError, e:
        errmsg = _("@info a problem in the given type of markup "
                   "(e.g. HTML, Docbook)",
                   "%(mtype)s markup: %(snippet)s.",
                   mtype=g.xmlfmt, snippet=e.args[0])
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


_ts_fence = "|/|"

def _escape_amp_accel (text):

    p_ts = text.find(_ts_fence)
    in_script = False

    p1 = 0
    found_accel = False
    while True:

        # Bracket possible entity reference.
        p1 = text.find("&", p1)
        if p1 < 0:
            break
        if not in_script and p_ts >= 0 and p1 > p_ts:
            in_script = True
            found_accel = False
        p2 = text.find(";", p1)

        # An accelerator marker if no semicolon in rest of the text
        # or the bracketed segment does not look like an entity,
        # and it is in front of an alphanumeric or itself.
        nc = text[p1 + 1:p1 + 2]
        if (    (p2 < 0 or not _simple_ent_rx.match(text[p1 + 1:p2]))
            and (nc.isalnum() or nc == "&")
        ):
            # Check if the next one is an ampersand too,
            # i.e. if it's a self-escaped accelerator marker.
            namp = 1
            if (    text[p1 + 1:p1 + 2] == "&"
                and not _simple_ent_rx.match(text[p1 + 2:p2])
            ):
                namp += 1

            # Escape the marker if first or self-escaped,
            # or currently in scripted part (in which there can be
            # any number of non-escaped markers).
            if not found_accel or namp > 1 or in_script:
                escseg = "&amp;" * namp
                text = text[:p1] + escseg + text[p1 + namp:]
                p1 += len(escseg)
                if namp == 1:
                    found_accel = True
            else:
                p1 += namp

        elif p2 > p1:
            p1 = p2
        else:
            break

    return text


def _handler_start_element (tag, attrs):

    g = _g_xml_l1

    if g.spec is None:
        return

    # Normalize names to lower case if allowed.
    if not g.casesens:
        tag = tag.lower()
        attrs = dict([(x.lower(), y) for x, y in attrs.items()])

    # Check existence of the tag.
    if tag not in g.spec and tag != _dummy_top:
        errmsg = _("@info",
                   "%(mtype)s markup: unrecognized tag '%(tag)s'.",
                   mtype=g.xmlfmt, tag=tag)
        span = _make_span(g.text, g.parser.CurrentLineNumber,
                          g.parser.CurrentColumnNumber + 1, errmsg)
        g.spans.append(span)
        return

    if tag == _dummy_top:
        return

    elspec = g.spec[tag]
    errmsgs = []

    # Check applicability of attributes and validity of their values.
    if elspec.attrs is not None:
        for attr, aval in attrs.items():
            if attr not in elspec.attrs:
                errmsgs.append(_("@info",
                                 "%(mtype)s markup: invalid attribute "
                                 "'%(attr)s' to tag '%(tag)s'.",
                                 mtype=g.xmlfmt, attr=attr, tag=tag))
            else:
                avlint = elspec.avlints.get(attr)
                if avlint and not avlint(aval):
                    errmsgs.append(_("@info",
                                     "%(mtype)s markup: invalid value "
                                     "'%(val)s' to attribute '%(attr)s'.",
                                     mtype=g.xmlfmt, val=aval, attr=attr))

    # Check proper parentage.
    if g.tagstack:
        ptag = g.tagstack[-1]
        pelspec = g.spec.get(ptag)
        if (    pelspec is not None and pelspec.stags is not None
            and tag not in pelspec.stags
        ):
            errmsgs.append(_("@info",
                             "%(mtype)s markup: tag '%(tag1)s' cannot be "
                             "a subtag of '%(tag2)s'.",
                             mtype=g.xmlfmt, tag1=tag, tag2=ptag))

    # Record element stack.
    g.tagstack.append(tag)

    for errmsg in errmsgs:
        span = _make_span(g.text, g.parser.CurrentLineNumber,
                          g.parser.CurrentColumnNumber + 1, errmsg)
        g.spans.append(span)


def _handler_default (text):

    g = _g_xml_l1

    if g.ents is not None and text.startswith('&') and text.endswith(';'):
        ent = text[1:-1]
        errmsg = None
        if ent.startswith("#"):
            if nument_to_char(ent) is None:
                errmsg = _("@info",
                           "%(mtype)s markup: invalid numeric "
                           "entity '%(ent)s'.",
                           mtype=g.xmlfmt, ent=ent)
        elif ent not in g.ents and ent not in xml_entities:
            nearents = [] #difflib.get_close_matches(ent, g.ents)
            if nearents:
                if len(nearents) > 5: # do not overwhelm message
                    fmtents = format_item_list(nearents[:5], incmp=True)
                else:
                    fmtents = format_item_list(nearents)
                errmsg = _("@info",
                           "%(mtype)s markup: unknown entity '%(ent)s' "
                           "(suggestions: %(entlist)s).",
                           mtype=g.xmlfmt, ent=ent, entlist=fmtents)
            else:
                errmsg = _("@info",
                           "%(mtype)s markup: unknown entity '%(ent)s'.",
                           mtype=g.xmlfmt, ent=ent)

        if errmsg is not None:
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


_entname_rx = re.compile(r"^([\w:][\w\d.:-]*)$", re.U)

def _validate_xml_entdef (text, xmlfmt):

    state = "void"
    pos = 0
    tlen = len(text)
    errmsg = None
    dhead = "!ENTITY"
    def next_nws (pos):
        while pos < tlen and text[pos].isspace():
            pos += 1
        return pos
    def next_ws (pos, ows=()):
        while pos < tlen and not text[pos].isspace() and text[pos] not in ows:
            pos += 1
        return pos
    errend = lambda: (_("@info",
                        "%(mtype)s markup: premature end of entity definition.",
                        mtype=xmlfmt),
                      tlen)
    while True:
        if state == "void":
            pos = next_nws(pos)
            if pos == tlen:
                break
            elif text[pos] != "<":
                errmsg = _("@info",
                           "%(mtype)s markup: expected opening angle bracket "
                           "in entity definition.",
                           mtype=xmlfmt)
                pos1 = pos + 1
            else:
                pos += 1
                state = "head"

        elif state == "head":
            pos = next_nws(pos)
            if pos == tlen:
                errmsg, pos1 = errend()
            else:
                pos1 = next_ws(pos)
                head = text[pos:pos1]
                if head != dhead:
                    errmsg = _("@info",
                               "%(mtype)s markup: expected '%(keyword)s' "
                               "in entity definition.",
                               mtype=xmlfmt, keyword=dhead)
                else:
                    pos = pos1
                    state = "name"

        elif state == "name":
            pos = next_nws(pos)
            pos1 = next_ws(pos, ("'", "\""))
            name = text[pos:pos1]
            if not _entname_rx.match(name):
                errmsg = _("@info",
                           "%(mtype)s markup: invalid entity name '%(name)s' "
                           "in entity definition.",
                           mtype=xmlfmt, name=name)
            else:
                pos = pos1
                state = "value"

        elif state == "value":
            pos = next_nws(pos)
            if pos == tlen:
                errmsg, pos1 = errend()
            elif text[pos] not in ("'", "\""):
                errmsg = _("@info",
                           "%(mtype)s markup: expected opening quote "
                           "(ASCII single or double) in entity definition.",
                           mtype=xmlfmt)
                pos1 = pos + 1
            else:
                quote = text[pos]
                pos1 = text.find(quote, pos + 1)
                if pos1 < 0:
                    errmsg = _("@info",
                               "%(mtype)s markup: unclosed entity value "
                               "in entity definition.",
                               mtype=xmlfmt)
                    pos1 = tlen
                else:
                    value = text[pos + 1:pos1]
                    # FIXME: Validate value? Does not have to be valid
                    # on its own, in principle.
                    pos = pos1 + 1
                    state = "tail"

        elif state == "tail":
            pos = next_nws(pos)
            if pos == tlen:
                errmsg, pos1 = errend()
            elif text[pos] != ">":
                errmsg = _("@info",
                           "%(mtype)s markup: expected closing angle bracket "
                           "in entity definition.",
                           mtype=xmlfmt)
                pos1 = pos + 1
            else:
                pos += 1
                state = "void"

        if errmsg:
            break

    spans = []
    if errmsg:
        if pos1 is None:
            pos1 = pos
        spans = [(pos, pos1, errmsg)]

    return spans


def check_xml (strict=False, entities={}, mkeyw=None):
    """
    Check general XML markup in translation [hook factory].

    Text is only checked to be well-formed XML, and possibly also whether
    encountered entities are defined. Markup errors are reported to stdout.

    C{msgstr} can be either checked only if the C{msgid} is valid itself,
    or regardless of the validity of the original. This is governed by the
    C{strict} parameter.

    Entities in addition to XML's default (C{&lt;}, etc.)
    may be provided using the C{entities} parameter.
    Several types of values with different semantic are possible:
      - if C{entities} is C{None}, unknown entities are ignored on checking
      - if string, it is understood as a general function evaluation
        L{request<getfunc.get_result_ireq>},
        and its result expected to be (name, value) dictionary-like object
      - otherwise, C{entities} is considered to be a (name, value) dictionary

    If a message has L{sieve flag<pology.sieve.parse_sieve_flags>}
    C{no-check-markup}, the check is skipped for that message.
    If one or several markup keywords are given as C{mkeyw} parameter,
    check is skipped for all messages in a catalog which does not report
    one of the given keywords by its L{markup()<catalog.Catalog.markup>}
    method. See L{set_markup()<catalog.Catalog.set_markup>} for list of
    markup keywords recognized at the moment.

    @param strict: whether to require valid C{msgstr} even if C{msgid} is not
    @type strict: bool
    @param entities: additional entities to consider as known
    @type entities: C{None}, dict, or string
    @param mkeyw: markup keywords for taking catalogs into account
    @type mkeyw: string or list of strings

    @return: type S3C hook
    @rtype: C{(msgstr, msg, cat) -> numerr}
    """

    return _check_xml_w(validate_xml_l1, strict, entities, mkeyw, False)


def check_xml_sp (strict=False, entities={}, mkeyw=None):
    """
    Like L{check_xml}, except that erroneous spans are returned
    instead of reporting problems to stdout [hook factory].

    @return: type V3C hook
    @rtype: C{(msgstr, msg, cat) -> spans}
    """

    return _check_xml_w(validate_xml_l1, strict, entities, mkeyw, True)


# Worker for C{check_xml*} hook factories.
def _check_xml_w (check, strict, entities, mkeyw, spanrep,
                  ignctxt=(), ignid=(), ignctxtsw=(), ignidsw=()):

    if mkeyw is not None:
        if isinstance(mkeyw, basestring):
            mkeyw = [mkeyw]
        mkeyw = set(mkeyw)

    # Lazy-evaluated data.
    ldata = {}
    def eval_ldata ():
        ldata["entities"] = _get_entities(entities)

    def checkf (msgstr, msg, cat):

        if (    mkeyw is not None
            and not mkeyw.intersection(cat.markup() or set())
        ):
            return [] if spanrep else 0

        if (   msg.msgctxt in ignctxt
            or msg.msgid in ignid
            or (msg.msgctxt is not None and msg.msgctxt.startswith(ignctxt))
            or msg.msgid.startswith(ignidsw)
        ):
            return [] if spanrep else 0

        if not ldata:
            eval_ldata()
        entities = ldata["entities"]

        if (   flag_no_check_markup in manc_parse_flag_list(msg, "|")
            or (    not strict
                and (   check(msg.msgid, ents=entities)
                     or check(msg.msgid_plural or u"", ents=entities)))
        ):
            return [] if spanrep else 0
        spans = check(msgstr, ents=entities)
        if spanrep:
            return spans
        else:
            for span in spans:
                if span[2:]:
                    report_on_msg(span[2], msg, cat)
            return len(spans)

    return checkf


# Cache for loaded entities, by entity specification string,
# to speed up when several markup hooks are using the same setup.
_loaded_entities_cache = {}

def _get_entities (entspec):

    if not isinstance(entspec, basestring):
        return entspec

    entities = _loaded_entities_cache.get(entspec)
    if entities is not None:
        return entities

    entities = get_result_ireq(entspec)

    _loaded_entities_cache[entspec] = entities
    return entities


_docbook4_l1 = None

def validate_docbook4_l1 (text, ents=None):
    """
    Validate Docbook 4.x markup in text against L{level1<collect_xml_spec_l1>}
    specification.

    Markup definition is extended to include C{<placeholder-N/>} elements,
    which C{xml2po} uses to segment text when extracting markup documents
    into PO templates.

    See L{validate_xml_l1} for description of the C{ents} parameter
    and the return value.

    @param text: text to check
    @type text: string
    @param ents: set of known entities (in addition to default)
    @type ents: sequence

    @returns: erroneous spans in the text
    @rtype: list of (int, int, string) tuples
    """

    global _docbook4_l1
    if _docbook4_l1 is None:
        specpath = os.path.join(datadir(), "spec", "docbook4.l1")
        _docbook4_l1 = collect_xml_spec_l1(specpath)

    xmlfmt = _("@item markup type", "Docbook4")
    return validate_xml_l1(text, spec=_docbook4_l1, xmlfmt=xmlfmt, ents=ents)


_db4_meta_msgctxt = set((
))
_db4_meta_msgid = set((
    "translator-credits",
))
_db4_meta_msgid_sw = (
    "@@image:",
)

def check_docbook4 (strict=False, entities={}, mkeyw=None):
    """
    Check XML markup in translations of Docbook 4.x catalogs [hook factory].

    See L{check_xml} for description of parameters.

    @return: type S3C hook
    @rtype: C{(msgstr, msg, cat) -> numerr}
    """

    return _check_xml_w(validate_docbook4_l1, strict, entities, mkeyw, False,
                        ignid=_db4_meta_msgid, ignctxt=_db4_meta_msgctxt,
                        ignidsw=_db4_meta_msgid_sw)


def check_docbook4_sp (strict=False, entities={}, mkeyw=None):
    """
    Like L{check_docbook4}, except that erroneous spans are returned
    instead of reporting problems to stdout [hook factory].

    @return: type V3C hook
    @rtype: C{(msgstr, msg, cat) -> spans}
    """

    return _check_xml_w(validate_docbook4_l1, strict, entities, mkeyw, True,
                        ignid=_db4_meta_msgid, ignctxt=_db4_meta_msgctxt,
                        ignidsw=_db4_meta_msgid_sw)


def check_docbook4_msg (strict=False, entities={}, mkeyw=None):
    """
    Check for any known problem in translation in messages
    in Docbook 4.x catalogs [hook factory].

    Currently performed checks:
      - Docbook markup
      - cross-message insertion placeholders

    See L{check_xml} for description of parameters.

    @return: type V4A hook
    @rtype: C{(msg, cat) -> parts}
    """

    check_markup = check_docbook4_sp(strict, entities, mkeyw)

    def checkf (msg, cat):

        hl = []
        for i in range(len(msg.msgstr)):
            spans = []
            spans.extend(check_markup(msg.msgstr[i], msg, cat))
            spans.extend(check_placeholder_els(msg.msgid, msg.msgstr[i]))
            if spans:
                hl.append(("msgstr", i, spans))
        return hl

    return checkf


_entpath_html = os.path.join(datadir(), "spec", "html.entities")
html_entities = read_entities(_entpath_html)

_html_l1 = None

def validate_html_l1 (text, ents=None):
    """
    Validate HTML markup in text against L{level1<collect_xml_spec_l1>}
    specification.

    At the moment, this function can only check HTML markup if well-formed
    in the XML sense, although HTML allows omission of some closing tags.

    See L{validate_xml_l1} for description of the C{ents} parameter
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
        specpath = os.path.join(datadir(), "spec", "html.l1")
        _html_l1 = collect_xml_spec_l1(specpath)

    if ents is not None:
        ents = Multidict([ents, html_entities])

    xmlfmt = _("@item markup type", "HTML")
    return validate_xml_l1(text, spec=_html_l1, xmlfmt=xmlfmt, ents=ents,
                           accelamp=True, casesens=False)


def check_html (strict=False, entities={}, mkeyw=None):
    """
    Check HTML markup in translations [hook factory].

    See L{check_xml} for description of parameters.
    See notes on checking HTML markup to L{validate_html_l1}.

    @return: type S3C hook
    @rtype: C{(msgstr, msg, cat) -> numerr}
    """

    return _check_xml_w(validate_html_l1, strict, entities, mkeyw, False)


def check_html_sp (strict=False, entities={}, mkeyw=None):
    """
    Like L{check_html}, except that erroneous spans are returned
    instead of reporting problems to stdout [hook factory].

    @return: type V3C hook
    @rtype: C{(msgstr, msg, cat) -> spans}
    """

    return _check_xml_w(validate_html_l1, strict, entities, mkeyw, True)


_qtrich_l1 = None

def validate_qtrich_l1 (text, ents=None):
    """
    Validate Qt rich-text markup in text against L{level1<collect_xml_spec_l1>}
    specification.

    At the moment, this function can only check Qt rich-text if well-formed
    in the XML sense, although Qt rich-text allows HTML-type omission of
    closing tags.

    See L{validate_xml_l1} for description of the C{ents} parameter
    and the return value.

    @param text: text to check
    @type text: string
    @param ents: set of known entities (in addition to default)
    @type ents: sequence

    @returns: erroneous spans in the text
    @rtype: list of (int, int, string) tuples
    """

    global _qtrich_l1
    if _qtrich_l1 is None:
        specpath = os.path.join(datadir(), "spec", "qtrich.l1")
        _qtrich_l1 = collect_xml_spec_l1(specpath)

    if ents is not None:
        ents = Multidict([ents, html_entities])

    xmlfmt = _("@item markup type", "Qt-rich")
    return validate_xml_l1(text, spec=_qtrich_l1, xmlfmt=xmlfmt, ents=ents,
                           accelamp=True, casesens=False)


def check_qtrich (strict=False, entities={}, mkeyw=None):
    """
    Check Qt rich-text markup in translations [hook factory].

    See L{check_xml} for description of parameters.
    See notes on checking Qt rich-text to L{validate_qtrich_l1}.

    @return: type S3C hook
    @rtype: C{(msgstr, msg, cat) -> numerr}
    """

    return _check_xml_w(validate_qtrich_l1, strict, entities, mkeyw, False)


def check_qtrich_sp (strict=False, entities={}, mkeyw=None):
    """
    Like L{check_qtrich}, except that erroneous spans are returned
    instead of reporting problems to stdout [hook factory].

    @return: type V3C hook
    @rtype: C{(msgstr, msg, cat) -> spans}
    """

    return _check_xml_w(validate_qtrich_l1, strict, entities, mkeyw, True)


_entpath_kuit = os.path.join(datadir(), "spec", "kuit.entities")
kuit_entities = read_entities(_entpath_kuit)

_kuit_l1 = None

def validate_kuit_l1 (text, ents=None):
    """
    Validate KUIT markup in text against L{level1<collect_xml_spec_l1>}
    specification.

    KUIT is the semantic markup for user interface in KDE4.

    See L{validate_xml_l1} for description of the C{ents} parameter
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
        specpath = os.path.join(datadir(), "spec", "kuit.l1")
        _kuit_l1 = collect_xml_spec_l1(specpath)

    if ents is not None:
        ents = Multidict([ents, kuit_entities])

    xmlfmt = _("@item markup type", "KUIT")
    return validate_xml_l1(text, spec=_kuit_l1, xmlfmt=xmlfmt, ents=ents,
                           accelamp=True)


_kde4_l1 = None
_kde4_ents = None

def validate_kde4_l1 (text, ents=None):
    """
    Validate markup in texts used in KDE4 GUI.

    KDE4 GUI texts may contain both Qt rich-text and KUIT markup,
    even mixed in the same text.

    See L{validate_xml_l1} for description of the C{ents} parameter
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
        spath1 = os.path.join(datadir(), "spec", "qtrich.l1")
        _kde4_l1.update(collect_xml_spec_l1(spath1))
        spath2 = os.path.join(datadir(), "spec", "kuit.l1")
        _kde4_l1.update(collect_xml_spec_l1(spath2))
        _kde4_ents = {}
        _kde4_ents.update(html_entities)
        _kde4_ents.update(kuit_entities)

    if ents is not None:
        ents = Multidict([ents, _kde4_ents])

    xmlfmt = _("@item markup type", "KDE4")
    return validate_xml_l1(text, spec=_kde4_l1, xmlfmt=xmlfmt, ents=ents,
                           accelamp=True, casesens=False)


def check_kde4 (strict=False, entities={}, mkeyw=None):
    """
    Check XML markup in translations of KDE4 UI catalogs [hook factory].

    See L{check_xml} for description of parameters.

    @return: type S3C hook
    @rtype: C{(msgstr, msg, cat) -> numerr}
    """

    return _check_xml_w(validate_kde4_l1, strict, entities, mkeyw, False)


def check_kde4_sp (strict=False, entities={}, mkeyw=None):
    """
    Like L{check_kde4}, except that erroneous spans are returned
    instead of reporting problems to stdout [hook factory].

    @return: type V3C hook
    @rtype: C{(msgstr, msg, cat) -> spans}
    """

    return _check_xml_w(validate_kde4_l1, strict, entities, mkeyw, True)


_pango_l1 = None

def validate_pango_l1 (text, ents=None):
    """
    Validate Pango markup in text against L{level1<collect_xml_spec_l1>}
    specification.

    See L{validate_xml_l1} for description of the C{ents} parameter
    and the return value.

    @param text: text to check
    @type text: string
    @param ents: set of known entities (in addition to default)
    @type ents: sequence

    @returns: erroneous spans in the text
    @rtype: list of (int, int, string) tuples
    """

    global _pango_l1
    if _pango_l1 is None:
        specpath = os.path.join(datadir(), "spec", "pango.l1")
        _pango_l1 = collect_xml_spec_l1(specpath)

    if ents is not None:
        ents = Multidict([ents, html_entities])

    xmlfmt = _("@item markup type", "Pango")
    return validate_xml_l1(text, spec=_pango_l1, xmlfmt=xmlfmt, ents=ents,
                           accelamp=True, casesens=False)


def check_pango (strict=False, entities={}, mkeyw=None):
    """
    Check XML markup in translations of Pango UI catalogs [hook factory].

    See L{check_xml} for description of parameters.

    @return: type S3C hook
    @rtype: C{(msgstr, msg, cat) -> numerr}
    """

    return _check_xml_w(validate_pango_l1, strict, entities, mkeyw, False)


def check_pango_sp (strict=False, entities={}, mkeyw=None):
    """
    Like L{check_pango}, except that erroneous spans are returned
    instead of reporting problems to stdout [hook factory].

    @return: type V3C hook
    @rtype: C{(msgstr, msg, cat) -> spans}
    """

    return _check_xml_w(validate_pango_l1, strict, entities, mkeyw, True)




_digits_dec = set("0123456789")
_digits_hex = set("0123456789abcdefABCDEF")

def nument_to_char (nument):
    """
    Convert numeric XML entity to character.

    Numeric XML entities can be decimal, C{&#DDDD;}, or hexadecimal,
    C{&#xHHHH;}, where C{D} and C{H} stand for number system's digits.
    4 digits is the maximum, but there can be less.

    If the entity cannot be converted to a character, for whatever reason,
    C{None} is reported.

    @param nument: numeric entity, with or without C{&} and C{;}
    @type nument: string

    @return: character represented by the entity
    @rtype: string or None
    """

    if nument[:1] == "&":
        nument = nument[1:-1]

    if nument[:1] != "#":
        return None

    if nument[1:2] == "x":
        known_digits = _digits_hex
        numstr = nument[2:]
        base = 16
    else:
        known_digits = _digits_dec
        numstr = nument[1:]
        base = 10

    if len(numstr) > 4 or len(numstr) < 1:
        return None

    unknown_digits = set(numstr).difference(known_digits)
    if unknown_digits:
        return None

    return unichr(int(numstr, base))


def validate_xmlents (text, ents={}, default=False, numeric=False):
    """
    Check whether XML-like entities in the text are among known.

    The text does not have to be XML markup as such.
    No XML parsing is performed, only the raw search for XML-like entities.

    @param text: text with entities to check
    @type text: string
    @param ents: known entities
    @type ents: sequence
    @param default: whether default XML entities are allowed (C{&amp;}, etc.)
    @type default: bool
    @param numeric: whether numeric character entities are allowed
    @type numeric: bool

    @returns: erroneous spans in the text
    @rtype: list of (int, int, string) tuples
    """

    spans = []

    p = 0
    while True:
        p = text.find("&", p)
        if p < 0:
            break
        pp = p
        m = _entity_rx.match(text, p)
        if m:
            p = m.end()
            ent = m.group(1)
            errmsg = None
            if numeric and ent.startswith("#"):
                if nument_to_char(ent) is None:
                    errmsg = _("@info",
                               "Invalid numeric entity '%(ent)s'.",
                               ent=ent)
            elif ent not in ents and (not default or ent not in xml_entities):
                nearents = [] #difflib.get_close_matches(ent, ents)
                if nearents:
                    if len(nearents) > 5: # do not overwhelm message
                        fmtents = format_item_list(nearents[:5], incmp=True)
                    else:
                        fmtents = format_item_list(nearents)
                    errmsg = _("@info",
                               "Unknown entity '%(ent)s' "
                               "(suggestions: %(entlist)s).",
                               ent=ent, entlist=fmtents)
                else:
                    errmsg = _("@info",
                               "Unknown entity '%(ent)s'.",
                               ent=ent)

            if errmsg is not None:
                spans.append((pp, p, errmsg))
        else:
            p += 1

    return spans


def check_xmlents (strict=False, entities={}, mkeyw=None,
                   default=False, numeric=False):
    """
    Check existence of XML entities in translations [hook factory].

    See L{check_xml} for description of parameters C{strict}, C{entities},
    and C{mkeyw}. See L{validate_xmlents} for parameters C{default} and
    C{numeric}, and for general notes on checking entities.

    @return: type S3C hook
    @rtype: C{(msgstr, msg, cat) -> numerr}
    """

    def check (text, ents):
        return validate_xmlents(text, ents, default=default, numeric=numeric)

    return _check_xml_w(check, strict, entities, mkeyw, False)


def check_xmlents_sp (strict=False, entities={}, mkeyw=None,
                      default=False, numeric=False):
    """
    Like L{check_xmlents}, except that erroneous spans are returned
    instead of reporting problems to stdout [hook factory].

    @return: type V3C hook
    @rtype: C{(msgstr, msg, cat) -> spans}
    """

    def check (text, ents):
        return validate_xmlents(text, ents, default=default, numeric=numeric)

    return _check_xml_w(check, strict, entities, mkeyw, True)


_placeholder_el_rx = re.compile(r"<\s*placeholder-(\d+)\s*/\s*>")

def check_placeholder_els (orig, trans):
    """
    Check if sets of C{<placeholder-N/>} elements are matching between
    original and translated text.

    C{<placeholder-N/>} elements are added into text by C{xml2po},
    for finer segmentation of markup documents extracted into PO templates.

    See L{validate_xml_l1} for description of the return value.

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
        errmsg = _("@info",
                   "Missing placeholder tags in translation: %(taglist)s.",
                   taglist=format_item_list(tags))
        spans.append((0, 0, errmsg))
    elif extra_plnums: # do not report both, single glitch may cause them
        tags = "".join(["<placeholder-%s/>" % x for x in extra_plnums])
        errmsg = _("@info",
                   "Superfluous placeholder tags in translation: %(taglist)s.",
                   taglist=format_item_list(tags))
        spans.append((0, 0, errmsg))

    return spans

