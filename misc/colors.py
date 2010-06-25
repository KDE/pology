# -*- coding: UTF-8 -*-
"""
Standard codes for terminal colors.

@author: Chusslove Illich <caslav.ilic@gmx.net>
@author: Sébastien Renard <sebastien.renard@digitalfox.org>
@license: GPLv3
"""


import re

from pology import PologyError, _, n_


coloring_types = (
    "none",
    "term",
    "html",
)


def _get_colors_none ():

    return {}


_colors_term = {}

def _get_colors_term ():

    if _colors_term:
        return _colors_term

    reset = "\033[0;0m"
    def makef (color):
        return lambda text: color + text + reset
    for name, color in (
        ("bold", "\033[01m"),
        ("underline", "\033[04m"),
        ("black", "\033[30m"),
        ("red", "\033[31m"),
        ("green", "\033[32m"),
        ("orange", "\033[33m"),
        ("blue", "\033[34m"),
        ("purple", "\033[35m"),
        ("cyan", "\033[36m"),
        ("grey", "\033[37m"),
    ):
        _colors_term[name] = makef(color)

    return _colors_term


_colors_html = {}

def _get_colors_html ():

    if _colors_html:
        return _colors_html

    _colors_html["bold"] = lambda text: "<b>%s</b>" % text
    _colors_html["underline"] = lambda text: "<u>%s</u>" % text

    def makef (color):
        return lambda text: "<font color='%s'>%s</font>" % (color, text)
    for name, color in (
        ("black", "#000000"),
        ("red", "#ff0000"),
        ("green", "#228b22"),
        ("orange", "#ff8040"),
        ("blue", "#0000ff"),
        ("purple", "#ff0080"),
        ("cyan", "#52F3FF"),
        ("grey", "#808080"),
    ):
        _colors_html[name] = makef(color)

    return _colors_html


class Colors:
    """
    Color applicator: methods for wrapping text snippets in color.
    """

    def __init__ (self, ctype):
        """
        Constructor.

        Parameter C{ctype} is specifies the type of coloring.
        Currently available are: C{"none"}, C{"term"}, C{"html"}.

        @param ctype: type of coloring
        @type ctype: string
        """

        if ctype == "none":
            self._colorfs = _get_colors_none()
            self._resolvef = _resolve_xml_ents
        elif ctype == "term":
            self._colorfs = _get_colors_term()
            self._resolvef = _resolve_xml_ents
        elif ctype == "html":
            self._colorfs = _get_colors_html()
            self._resolvef = lambda t: t
        else:
            raise PologyError(
                _("@info",
                  "Unknown type of coloring '%(type)s' requested.",
                  type=ctype))


    def unescape (self, text):
        """
        Resolve escapes in text which were used to mask what would be
        interpreted as a color tag for this type of coloring.
        """

        return self._resolvef(text)


    def _add_color (self, name, text):

        colorf = self._colorfs.get(name)
        if colorf is not None:
            return colorf(text)
        else:
            return text


    def bold (self, text):

        return self._add_color("bold", text)


    def underline (self, text):

        return self._add_color("underline", text)


    def red (self, text):

        return self._add_color("red", text)


    def green (self, text):

        return self._add_color("green", text)


    def orange (self, text):

        return self._add_color("orange", text)


    def blue (self, text):

        return self._add_color("blue", text)


    def purple (self, text):

        return self._add_color("purple", text)


    def cyan (self, text):

        return self._add_color("cyan", text)


    def grey (self, text):

        return self._add_color("grey", text)


# NOTE: Private function instead of misc.resolve.resolve_entities,
# because it needs to be lightweight and forgiving
# (and there could be an import loop too).
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


def colors_for_file (fd, ctype=None):
    """
    Appropriate color applicator for an output file descriptor.

    If C{ctype} is C{None}, it is taken from global coloring options.
    After this, the following happens:
      - if C{ctype} is C{"term"}, and the file descriptor given by C{fd}
            is linked to a terminal, the ANSI-escapes color applicator
            is be returned;
      - if C{ctype} is C{"term"} and the file descriptor is linked to a file,
            the no-op applicator is returned;
      - if C{ctype} is not C{"term"}, the color applicator according to it
            is returned regardless of the file descriptor.
    L{set_coloring_globals} may be used to override elements of this behavior.

    @param fd: file descriptor for which the colors are requested
    @type fd: file
    @param ctype: type of coloring (see L{Colors.__init__} for possibilities)
    @type ctype: string
    @returns: color applicator
    @rtype: L{Colors}
    """

    if ctype is None:
        ctype = _cglobals.ctype

    if ctype in (None, "term"):
        if not _cglobals.outdep or (fd and fd.isatty()):
            return Colors("term")
        else:
            return Colors("none")
    else:
        return Colors(ctype)


def resolve_color_markup (text, colors):
    """
    Resolve color markup in text according to given color applicator.

    Possible tags in text are those as coloring methods of L{Colors}.

    @param colors: color applicator
    @type colors: L{Colors}
    @returns: resolved text
    @rtype: string
    """

    return _resolve_color_markup_w(text, colors, 0)


_tag_rx = re.compile(r"<\s*([a-z]\w*)\s*>([^<]*)<\s*/\s*\1\s*>", re.U)

def _resolve_color_markup_w (text, colors, plnum):

    m = _tag_rx.search(text)
    plhold = "\x00%d" % plnum
    if m:
        tag, seg = m.groups()
        tagf = getattr(colors, tag, None)
        if tagf is not None:
            rseg = tagf(seg)
        else:
            rseg = "<%s>%s</%s>" % (tag, seg, tag)
        #rseg = colors.unescape(rseg)
        pre, aft = text[:m.start()], text[m.end():]
        rtext = _resolve_color_markup_w(pre + plhold + aft, colors, plnum + 1)
        rtext = rtext.replace(plhold, rseg)
    else:
        rtext = text
        #rtext = colors.unescape(rtext)
    return rtext


def set_coloring_globals (ctype="term", outdep=True):
    """
    Set global options for coloring.

    L{colors_for_file} will use type of coloring given by C{ctype}
    whenever its own C{ctype} is set to C{None}.

    If C{outdep} is set to C{False}, L{colors_for_file} will not check
    the file descriptor given to it, and always return color applicator
    according to C{ctype}.

    @param ctype: type of coloring (see L{Colors.__init__} for possibilities)
    @type ctype: string
    @param outdep: whether coloring depends on output file descriptor
    @type outdep: bool
    """

    _cglobals.outdep = outdep
    _cglobals.ctype = ctype


class _Data: pass
_cglobals = _Data()
set_coloring_globals()

