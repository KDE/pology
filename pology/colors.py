# -*- coding: UTF-8 -*-
"""
Standard codes for terminal colors.

@author: Chusslove Illich <caslav.ilic@gmx.net>
@author: Sébastien Renard <sebastien.renard@digitalfox.org>
@license: GPLv3
"""

from optparse import OptionParser
import re
import sys

# NOTE: Must not import anything from Pology, as top __init__ includes this.


_xml_entities = {
    "lt": "<",
    "gt": ">",
    "apos": "'",
    "quot": "\"",
    "amp": "&",
}

def _resolve_xml_ents (text):

    segs = []
    p = 0
    while True:
        p1 = p
        p = text.find("&", p1)
        if p < 0:
            segs.append(text[p1:])
            break
        segs.append(text[p1:p])
        p2 = p
        p = text.find(";", p2)
        if p < 0:
            segs.append(text[p2:])
            break
        ent = text[p2 + 1:p]
        val = _xml_entities.get(ent)
        if val is None:
            segs.append(text[p2])
            p = p2 + 1
        else:
            segs.append(val)
            p += 1
    rtext = "".join(segs)
    return rtext


def _escape_xml_ents (text):

    rtext = text.replace("&", "&amp;")
    for ent, val in list(_xml_entities.items()):
        if val != "&":
            rtext = rtext.replace(val, "&" + ent + ";")
    return rtext


class ColorString (str):
    """
    Class for strings with color markup.

    This class provides automatic resolution of color XML markup
    in strings for various output formats.
    It automatically escapes any raw strings combined with it
    (e.g. when using the C{%} or C{+} operators)
    and returns objects of its own type from methods
    (e.g. from C{split()} or C{strip()}).
    Otherwise it should behave like a normal string.

    Note that usage of this class is expensive,
    given that arguments are constantly checked and strings escaped.
    It should be used only for user-visible output,
    i.e. where human reaction time is the limiting factor.
    """

    def _escape (self, v):
        if isinstance(v, str) and not isinstance(v, ColorString):
            v = str(v)
            v = _escape_xml_ents(v)

        return v


    def __add__ (self, other):

        return ColorString(str.__add__(self, self._escape(other)))


    def __radd__ (self, other):

        return ColorString(str.__add__(self._escape(other), self))


    def __mod__ (self, args):

        if isinstance(args, dict):
            rargs = dict((k, self._escape(v)) for k, v in list(args.items()))
        elif isinstance(args, tuple):
            rargs = tuple(self._escape(v) for v in args)
        else:
            rargs = self._escape(args)
        return ColorString(str.__mod__(self, rargs))


    def __repr__ (self):

        return "%s(%s)" % (self.__class__.__name__, str.__repr__(self))

    def __iter__(self):
        for c in str(self):
            yield self.__class__(c)


    def join (self, strings):
        rstrings = [self._escape(s) for s in strings]
        return ColorString(str.join(self, rstrings))


    def resolve (self, ctype=None, dest=None):
        """
        Resolve color markup according to given type and destination.

        Currently available coloring types (values of C{ctype} parameter):
          - C{"none"}: no coloring
          - C{"term"}: ANSI color escape sequences (for terminal output)
          - C{"html"}: HTML markup (for integration into HTML pages)
        If C{ctype} is C{None}, it is taken from global coloring options.

        Some coloring types may be applied conditionally, based on whether
        the intended output destination is a file or terminal.
        If this is desired, the file descriptor of the destination
        can be given by the C{dest} parameter.

        @param ctype: type of coloring
        @type ctype: string
        @param dest: destination file descriptor
        @type dest: file
        @returns: plain string with resolved markup
        @rtype: string
        """

        # Resolve coloring type, considering all things.
        if ctype is None:
            ctype = _cglobals.ctype
        if ctype in (None, "term"):
            if not _cglobals.outdep or (dest and dest.isatty()):
                ctype = "term"
            else:
                ctype = "none"

        color_pack = _color_packs.get(ctype)
        if color_pack is None:
            color_pack = _color_packs.get("none")
        colorf, escapef, finalf = color_pack
        text = str(self)
        rtext, epos = self._resolve_markup_w(text, len(text), 0, None, None,
                                             colorf, escapef)
        rtext = finalf(rtext)
        return rtext


    def _resolve_markup_w (self, text, tlen, pos, tag, ptag, colorf, escapef):

        rsegs = []
        p = pos
        valid = True
        closed = False
        while p < tlen:
            pp = p
            p = text.find("<", p)
            if p < 0:
                p = tlen
            seg = text[pp:p]
            rsegs.append(escapef(_resolve_xml_ents(seg)))
            if p == tlen:
                break
            pp = p
            stag, closed, p = self._parse_tag(text, tlen, p)
            if stag is not None:
                if not closed:
                    rseg, p = self._resolve_markup_w(text, tlen, p, stag, tag,
                                                     colorf, escapef)
                    rsegs.append(rseg)
                else:
                    if tag != stag:
                        # Wrong closed tag, declare this span not valid
                        # and reposition at the tag start.
                        valid = False
                        p = pp
                    break
            else:
                # Not a proper tag start, just take literal < and go on.
                rsegs.append("<")
                p = pp + 1
        if tag and not closed:
            valid = False

        rtext = "".join(rsegs)
        if tag:
            if valid:
                rtext = colorf(tag, rtext, ptag)
            else:
                # Not proper span, put back opening tag.
                rtext = "<%s>%s" % (tag, rtext)

        return rtext, p


    def _parse_tag (self, text, tlen, pos):

        # FIXME: No possibility of attributes at the moment.
        if tlen is None:
            tlen = len(text)
        p = pos
        tag = None
        closed = False
        if p < tlen and text[p] == "<":
            p += 1
            while p < tlen and text[p].isspace():
                p += 1
            if p < tlen:
                if text[p] == "/":
                    p += 1
                    closed = True
                pp = p
                p = text.find(">", p)
                if p < 0:
                    p = tlen
                else:
                    tag = text[pp:p].strip()
                    p += 1
        return tag, closed, p


    def visual_segment (self, pos):
        """
        Get visual representation of raw segment starting from position.

        This function checks whether the segment of the string starting
        at given position has the raw or another visual value,
        accounting for markup.
        If the visual and raw segments differ, the visual representation
        and length of the raw segment are returned.
        Otherwise, empty string and zero length are returned.

        @param pos: position where to check for visual segment
        @type pos: int
        @returns: visual segment and length of underlying raw segment
        @rtype: string, int
        """

        vis, rlen = "", 0

        c = self[pos:pos + 1]
        if c == "<":
            pos2 = self.find(">", pos)
            if pos2 > 0:
                vis, rlen = "", pos2 + 1 - pos
        elif c == "&":
            pos2 = self.find(";", pos)
            if pos2 > 0:
                ent = self[pos + 1:pos2]
                val = _xml_entities.get(ent)
                if val is not None:
                    vis, rlen = val, pos2 + 1 - pos

        return vis, rlen


def _fill_color_string_class ():

    def wrap_return_type (method):
        def wmethod (self, *args, **kwargs):
            res = method(self, *args, **kwargs)
            if isinstance(res, str):
                res = ColorString(res)
            elif isinstance(res, (tuple, list)):
                res2 = []
                for el in res:
                    if isinstance(el, str):
                        el = ColorString(el)
                    res2.append(el)
                res = type(res)(res2)
            return res
        return wmethod

    for attrname in (
        "__getitem__", "__mul__", "__rmul__",
        "capitalize", "center", "expandtabs", "ljust", "lower", "lstrip",
        "replace", "rjust", "rsplit", "rstrip", "split", "strip", "swapcase",
        "title", "translate", "upper", "zfill",
    ):
        method = getattr(str, attrname)
        setattr(ColorString, attrname, wrap_return_type(method))

_fill_color_string_class()


def cjoin (strings, joiner=""):
    """
    Join strings into a L{ColorString} if any of them are L{ColorString},
    otherwise into type of joiner.

    @param strings: strings to join
    @type strings: sequence of strings
    @param joiner: string to be inserted between each two strings
    @type joiner: string
    @returns: concatenation by joiner of all strings
    @rtype: type(joiner)/L{ColorString}
    """

    if not isinstance(joiner, ColorString):
        for s in strings:
            if isinstance(s, ColorString):
                joiner = ColorString(joiner)
                break
    return joiner.join(strings)


def cinterp (format, *args, **kwargs):
    """
    Interpolate arguments into the format string, producing L{ColorString}
    if any of the arguments is L{ColorString}, otherwise type of format string.

    The format string can use either positional format directives,
    in which case positional arguments are supplied after it,
    or it can use named format directives,
    in which case keyword arguments are supplied after it.
    If both positional and keyword arguments are following the format string,
    the behavior is undefined.

    @param format: string with formatting directives
    @type format: string
    @returns: interpolated strings
    @rtype: type(format)/L{ColorString}
    """

    iargs = args or kwargs
    if not isinstance(format, ColorString):
        for v in (list(iargs.values()) if isinstance(iargs, dict) else iargs):
            if isinstance(v, ColorString):
                format = ColorString(format)
                break
    return format % iargs


class ColorOptionParser (OptionParser):
    """
    Lightweight wrapper for C{OptionParser} from standard library C{optparse},
    to gracefully handle L{ColorString} arguments supplied to its methods.
    """

    def _cv (self, val):

        if isinstance(val, ColorString):
            val = val.resolve("term", sys.stdout)
        elif isinstance(val, (list, tuple)):
            val = list(map(self._cv, val))
        elif isinstance(val, dict):
            val = dict((k, self._cv(v)) for k, v in list(val.items()))
        return val


    def __init__ (self, *args, **kwargs):

        OptionParser.__init__(self, *self._cv(args), **self._cv(kwargs))


    def add_option (self, *args, **kwargs):

        OptionParser.add_option(self, *self._cv(args), **self._cv(kwargs))


    # FIXME: More overrides.


def get_coloring_types ():
    """
    List of keywords of all available coloring types.
    """

    return list(_color_packs.keys())


def set_coloring_globals (ctype="term", outdep=True):
    """
    Set global options for coloring.

    L{ColorString.resolve} will use the type of coloring given
    by C{ctype} here whenever its own C{ctype} is set to C{None}.

    If C{outdep} is set to C{False}, L{ColorString.resolve} will not
    check the file descriptor given to it, and always use coloring type
    according to C{ctype}.

    @param ctype: type of coloring
    @type ctype: string
    @param outdep: whether coloring depends on output file descriptor
    @type outdep: bool
    """

    _cglobals.outdep = outdep
    _cglobals.ctype = ctype


class _Data: pass
_cglobals = _Data()
set_coloring_globals()

# ========================================================================

_color_packs = {}

# ----------------------------------------
# No coloring, all markup elements are just removed.

_color_packs["none"] = (lambda c, s, p: s, lambda s: s, lambda r: r)


# ----------------------------------------
# ANSI terminal coloring.

_term_head = "\033["
_term_reset = "0;0m"
_term_colors = {
    "bold": "01m",
    "underline": "04m",
    "black": "30m",
    "red": "31m",
    "green": "32m",
    "orange": "33m",
    "blue": "34m",
    "purple": "35m",
    "cyan": "36m",
    "grey": "37m",
}

def _color_term (col, seg, pcol):

    eseq = _term_colors.get(col)
    if eseq is not None:
        # If this segment is within another colored section,
        # repeat the outer color sequence at end, otherwise reset.
        # If outer and current colors match, do nothing.
        eseq2 = _term_reset
        peseq = _term_colors.get(pcol)
        if peseq:
            eseq2 = _term_head + peseq
        if eseq != eseq2:
            seg = _term_head + eseq + seg + _term_head + eseq2
    return seg


_color_packs["term"] = (_color_term, lambda s: s, lambda r: r)


# ----------------------------------------
# HTML coloring.

_html_colors = {
    "black": "#000000",
    "red": "#ff0000",
    "green": "#228b22",
    "orange": "#ff8040",
    "blue": "#0000ff",
    "purple": "#ff0080",
    "cyan": "#52f3ff",
    "grey": "#808080",
}

def _color_term (col, seg, pcol):

    if col == "bold":
        seg = "<b>%s</b>" % seg
    elif col == "underline":
        seg = "<u>%s</u>" % seg
    else:
        rgb = _html_colors.get(col)
        if rgb is not None:
            seg = "<font color='%s'>%s</font>" % (rgb, seg)
    return seg


def _finalize_html (line):

    return line.replace("\n", "<br/>\n") + "<br/>"


_color_packs["html"] = (_color_term, _escape_xml_ents, _finalize_html)

