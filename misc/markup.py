# -*- coding: UTF-8 -*-

"""
Process text markup.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import re
from pology.misc.report import error


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


_tag_split_rx = re.compile(r"<\s*(/?)\s*(\w*).*>")

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

def xml_to_plain (text, tags=None, subs={}, ents={}, keepws=set()):
    """
    Convert any XML-like markup to plain text.

    By default, all tags are removed from the text;
    entities, unless one of the XML default (C{&lt;}, C{&gt;}, C{&amp;},
    C{&quot;}, C{&apos;}), are left in stripped of ampersand and semicolon;
    all whitespace groups are simplified to single space and leading and
    trailing removed.

    If only a particular subset of tags should be taken into account, it can
    be specified by the C{tags} parameter, as a sequence of tag names
    (the sequence is internally converted to set before processing).

    If a tag should not be plain removed, but replaced with some characters
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

    Whitespace can be preserved within some tags, as given by the C{keepws}
    sequence.

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

    @returns: plain text version
    @rtype: string
    """

    # Convert some sequences to sets, for faster membership checks.
    if tags is not None and not isinstance(tags, set):
        tags = set(tags)
    if not isinstance(keepws, set):
        keepws = set(keepws)

    # Resolve user-supplied entities before tags,
    # as they may contain more markup.
    # (Resolve default entities after tags,
    # because the default entities can introduce invalid markup.)
    text = _resolve_ents(text, ents, _ents_xml)

    # Build element tree, trying to work around badly formed XML
    # (but do note when the closing element is missing).
    # Element tree is constructed as list of tuples:
    # (tag, opening_tag_literal, closing_tag_literal, content)
    # where content is a sublist for given element;
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
        curel.append(("#text", None, None, text[pp:p]))
        pp = p
        p = text.find(">", p + 1)
        if p < 0:
            break
        p += 1
        tag_literal = text[pp:p]
        m = _tag_split_rx.match(tag_literal) # must match
        if not m:
            error("xml_to_plain: internal 10")
        tag = m.group(2)
        if m.group(1) != "/": # opening tag
            any_tag = True
            curel.append([tag, tag_literal, None, []])
            parent.append(curel)
            curel = curel[-1][-1]
        else: # closing tag
            if parent:
                curel = parent.pop()
                curel[-1][2] = tag_literal # record closing tag literal
            else: # faulty markup, move top element
                eltree = [[tag, None, tag_literal, curel]]
                curel = eltree
    curel.append(("#text", None, None, text[pp:]))

    # Replace tags.
    text = _resolve_tags(eltree, tags, subs)

    # Resolve default entities.
    text = _resolve_ents(text, _ents_xml)

    return text


_entity_rx = re.compile(r"&([\w_:][\w\d._:-]*);")

def _resolve_ents (text, ents={}, ignents={}):
    """
    Resolve XML entities as described in L{xml_to_plain}, ignoring some.
    """

    # There may be entities within entities, so reparse the text as long
    # as at least one known entity has been replaced in the previous pass.
    while True:
        n_replaced = 0
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
                        ntext.append(value)
                        n_replaced += 1
                    else:
                        ntext.append(name)
                else: # ignored entity, do not touch
                    ntext.append(text[p:m.span()[1]])
                p = m.span()[1]
            else:
                ntext.append(text[p]) # the ampersand
                p += 1
        ntext.append(text[pp:])
        text = "".join(ntext)
        if n_replaced == 0:
            break

    return text


# Ordinary around masked whitespace.
_wsgr_premask_rx = re.compile(r"\s+(\x04~\w\w)")
_wsgr_postmask_rx = re.compile(r"(\x04~\w\w)\s+")

def _resolve_tags (elseq, tags=None, subs={}, keepws=set()):
    """
    Replace XML tags as described in L{xml_to_plain}, given the parsed tree.
    Split into top and recursive part.
    """

    # Text with masked whitespace where significant.
    text = _resolve_tags_r(elseq, tags, subs, keepws)

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


def _resolve_tags_r (elseq, tags=None, subs={}, keepws=set()):

    segs = []
    for el in elseq:
        if el[0] == "#text":
            segs.append(el[-1])
        elif tags is None or el[0] in tags:
            repl_pre, repl_post, repl_cont = subs.get(el[0], [None] * 3)
            if repl_pre is None:
                repl_pre = ""
            if repl_post is None:
                repl_post = ""
            if repl_cont is None:
                repl_cont = _resolve_tags_r(el[-1], tags, subs)
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
            repl_cont = _resolve_tags_r(el[-1], tags, subs)
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

