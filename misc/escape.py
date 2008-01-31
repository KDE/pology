# -*- coding: UTF-8 -*-

"""
Escaping texts in various contexts.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import re

_escape_seqs = {
    "\n" : "\\n",
    "\t" : "\\t",
    "\"" : "\\\"",
    # do not try to handle \\, ambiguous!
}

_unescp_seqs = dict([(_escape_seqs[x], x) for x in _escape_seqs.keys()])
_rx_unescp_g = re.compile(r"(.*?)(\\.)")
_rx_escapes_g = re.compile(r"(.*?)(" + r"|".join(_escape_seqs.keys()) + r")")

def unescape_strict (s):
    """
    Strictly unescape text for double-quoted strings.

    Exactly reverses result of L{escape_strict}.

    @param s: text to unescape (no wrapping double-quotes)
    @type s: string

    @returns: unescaped text
    @rtype: string

    @see: L{escape_strict}
    """

    ns = ""
    ie = 0
    for m in _rx_unescp_g.finditer(s):
        ie += len(m.group(1)) + len(m.group(2))
        ns += m.group(1)
        if _unescp_seqs.has_key(m.group(2)):
            ns += _unescp_seqs[m.group(2)]
        else:
            ns += m.group(2)
    ns += s[ie:]
    return ns


def unescape (s):
    """
    Non-strictly unescape text for double-quoted strings.

    This will do the wrong thing upon e.g. \\n, but much faster,
    and usually sufficient.

    Exactly reverses the result of L{escape}.

    @param s: text to unescape (no wrapping double-quotes)
    @type s: string

    @returns: unescaped text
    @rtype: string

    @see: L{escape}
    """

    ns = s;
    ns = ns.replace(r"\"", "\"")
    ns = ns.replace(r"\n", "\n")
    ns = ns.replace(r"\t", "\t")
    return ns;


def escape_strict (s):
    """
    Strictly escape text for double-quoted strings.

    Exactly reverses the result of L{unescape_strict}.

    @param s: text to escape
    @type s: string

    @returns: escaped text (no wrapping double-quotes)
    @rtype: string

    @see: L{unescape_strict}
    """

    ns = ""
    ie = 0
    for m in _rx_escapes_g.finditer(s):
        ie += len(m.group(1)) + len(m.group(2))
        ns += m.group(1) + _escape_seqs[m.group(2)]
    ns += s[ie:]
    return ns


def escape (s):
    """
    Non-strictly escape text for double-quoted strings.

    This will do the wrong thing upon e.g. \\n, but much faster,
    and usually sufficient.

    Exactly reverses the result of L{unescape}.

    @param s: text to escape
    @type s: string

    @returns: escaped text (no wrapping double-quotes)
    @rtype: string

    @see: L{unescape}
    """

    ns = s;
    ns = ns.replace("\"", r"\"")
    ns = ns.replace("\n", r"\n")
    ns = ns.replace("\t", r"\t")
    return ns;


def split_escaped (text, sep):
    """
    Like C{split()}, but double-separator is treated as an escape of itself.

    @param text: the text to split
    @type text: string

    @param sep: the separator
    @type sep: string

    @returns: parsed elements
    @rtype: list of strings
    """

    alakazoom = u"\u0004"
    tmp = text.replace(sep + sep, alakazoom).split(sep)
    return [x.replace(alakazoom, sep) for x in tmp]

