# -*- coding: UTF-8 -*-

"""
Various normalizations for strings.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import unicodedata
import re


_wsseq_rx = re.compile(r"[ \t\n]+", re.U)

def simplify (s):
    """
    Simplify ASCII whitespace in the string.

    All leading and trailing ASCII whitespace are removed,
    all inner ASCII whitespace sequences are replaced with space.

    @param s: string to normalize
    @type s: string

    @returns: normalized string
    @rtype: string
    """

    return _wsseq_rx.sub(" ", s.strip())


_uwsseq_rx = re.compile(r"\s+", re.U)

def usimplify (s):
    """
    Simplify whitespace in the string.

    Like L{simplify}, but takes into account all whitespace defined by Unicode.

    @param s: string to normalize
    @type s: string

    @returns: normalized string
    @rtype: string
    """

    return _uwsseq_rx.sub(" ", s.strip())


def shrink (s):
    """
    Remove all whitespace from the string.

    @param s: string to normalize
    @type s: string

    @returns: normalized string
    @rtype: string
    """

    return _uwsseq_rx.sub("", s)


def tighten (s):
    """
    Remove all whitespace and lowercase the string.

    @param s: string to normalize
    @type s: string

    @returns: normalized string
    @rtype: string
    """

    return _uwsseq_rx.sub("", s.lower())


_non_ascii_ident_rx = re.compile(r"[^a-z0-9_]", re.U|re.I)

def identify (s):
    """
    Construct an uniform-case ASCII-identifier out of the string.

    ASCII-identifier is constructed in the following order:
      - string is decomposed into Unicode NFKD
      - string is lowercased
      - every character that is not an ASCII alphanumeric is converted
        into underscore
      - if the string starts with a digit, underscore is prepended

    @param s: string to normalize
    @type s: string

    @returns: normalized string
    @rtype: string
    """

    ns = s

    # Decompose.
    ns = unicodedata.normalize("NFKD", ns)

    # Lowercase.
    ns = ns.lower()

    # Convert non-identifier chars into underscores.
    ns = _non_ascii_ident_rx.sub("_", ns) 

    # Prefix with underscore if first char is digit.
    if ns[0:1].isdigit():
        ns = "_" + ns

    return ns


def xentitize (s):
    """
    Replace characters having default XML entities with the entities.

    The replacements are:
      - C{&amp;} for ampersand
      - C{&lt} and C{&gt;} for less-than and greater-then signs
      - C{&apos;} and C{&quot;} for ASCII single and double quotes

    @param s: string to normalize
    @type s: string

    @returns: normalized string
    @rtype: string
    """

    ns = s
    ns = ns.replace("&", "&amp;") # must come first
    ns = ns.replace("<", "&lt;")
    ns = ns.replace(">", "&gt;")
    ns = ns.replace("'", "&apos;")
    ns = ns.replace('"', "&quot;")

    return ns

