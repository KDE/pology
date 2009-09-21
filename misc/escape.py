# -*- coding: UTF-8 -*-

"""
Escaping texts in various contexts.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import re

from pology.misc.report import warning

_escapes_c = {
    "\a" : "a",
    "\b" : "b",
    "\f" : "f",
    "\n" : "n",
    "\r" : "r",
    "\t" : "t",
    "\v" : "v",
    "\"" : "\"",
    "\\" : "\\",
}

_unescapes_c = dict([(y, x) for x, y in _escapes_c.items()])

def unescape_c (s):
    """
    Unescape text for C-style quoted strings.

    Octal and hex sequences (C{\\0OO}, C{\\xHH}) are converted into
    the corresponding ASCII characters if less than 128, or else
    thrown out (with a warning).

    Invalid escape sequences raise exception.

    @param s: text to unescape (without wrapping quotes)
    @type s: string

    @returns: unescaped text
    @rtype: string

    @see: L{escape_c}
    """

    segs = []
    p = 0
    while True:
        pp = p
        p = s.find("\\", p)
        if p < 0:
            segs.append(s[pp:])
            break
        segs.append(s[pp:p])
        p += 1
        c = s[p:p + 1]
        ec = None
        if c in ("x", "0"):
            dd = s[p + 1:p + 3]
            if len(dd) == 2:
                try:
                    ec = chr(int(dd, c == "x" and 16 or 8))
                    p += 3
                except:
                    pass
        else:
            ec = _unescapes_c.get(c)
            if ec is not None:
                p += 1
        if ec is None:
            raise StandardError("invalid C escape sequence after {{%s}}"
                                % s[:p])
        segs.append(ec)

    return type(s)().join(segs)


_escapes_c_wpref = dict([(x, "\\" + y) for x, y in _escapes_c.items()])

def escape_c (s):
    """
    Escape text for C-style quoted strings.

    @param s: text to escape
    @type s: string

    @returns: escaped text (without wrapping quotes)
    @rtype: string

    @see: L{unescape_c}
    """

    return type(s)().join([_escapes_c_wpref.get(c, c) for c in s])


_special_chars_sh = set(r" ~`#$&*()\|[]{};'\"<>?!")

def escape_sh (s):

    """
    Escape text for Unix sh-like shell.

    Escaped text may be used as a fixed argument in command line,
    i.e. the shell will not interpret any part of it in a special way.
    It is undefined which of the possible ways to escape are used
    (single quotes, double quotes, backslashes).

    @param s: text to escape
    @type s: string

    @returns: escaped text
    @rtype: string
    """

    if bool(set(s).intersection(_special_chars_sh)):
        quote = "'" if "'" not in s else '"'
        s = s.replace(quote, "\\" + quote)
        s = quote + s + quote

    return s


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

