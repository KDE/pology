# -*- coding: UTF-8 -*-

"""
Process text markup.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import os
import re
import codecs
from pology.misc.report import error
from pology import rootdir


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


_ents_xml = {
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
    text = _resolve_ents(text, ents, _ents_xml)

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
    text = _resolve_ents(text, _ents_xml)

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

def htmlkuit_to_plain (text):
    """
    Convert mixed HTML and KUIT markup to plain text.

    Note that in general this is not the same as first converting HTML,
    and then KUIT, or vice versa. For example, if the text has C{&lt;}
    entity, after first conversion it will become plain C{<}, and interfere
    with second conversion. Thus, this function should be used whenever
    both HTML and KUIT may appear in the same text.

    @param text: HTML+KUIT text to convert to plain
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

def _prep_docbook_to_plain ():

    global _dbk_tags, _dbk_subs, _dbk_ents, _dbk_keepws, _dbk_ignels

    specpath = os.path.join(rootdir(), "misc",
                            "check_xml_docbook4-spec.txt")
    docbook_tagattrs = collect_xml_spec_l1(specpath)

    _dbk_tags = set(docbook_tagattrs.keys())

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

def docbook_to_plain (text):
    """
    Convert Docbook markup to plain text.

    @param text: Docbook text to convert to plain
    @type text: string

    @returns: plain text version
    @rtype: string
    """

    if _dbk_tags is None:
        _prep_docbook_to_plain()

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

