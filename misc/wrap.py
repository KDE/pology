# -*- coding: UTF-8 -*-

"""
Text wrapping, with special handling for typical texts in PO files.

Wrapping turns out to be quite a non-trivial matter.
Gettext itself implements an intricate wrapping algorithm from the Unicode
consortium, with its own tweaks, which is hard to beat in any simpler way.
Thus, do not be surprised if the wrapping quality offered by this module does
not meet your exact needs.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import re
import unicodedata

from pology import PologyError, _, n_


# Regex for splitting C{<...>} into tag name and few other elements.
_tag_split_rx = re.compile(r"^\s*<\s*(/?)\s*(\w+)[^/>]*(/?)\s*>\s*$")

# Characters for "natural" breaks where to wrap the text.
_natbr = u".,;/%-)]}"

# Strings at which the text should be wrapped before or after.
_prebr = ("|/|",)
_postbr = (("\\n", "\\\\n"), "|/|")
# |/| is the Transcript fence, should break both before and after.

# Tags for normal breaking (after the closed tag)
_tagbr_normal = (
    # HTML
    "p", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "li",
    "table", "th", "td", "tr", "center", "blockquote", "pre", "dd", "dl", "dt",
    # KUIT
    "title", "subtitle", "para", "list", "item",
    # Docbook
    "calloutlist", "glosslist", "itemizedlist", "orderedlist", "segmentedlist",
    "simplelist", "variablelist", "listitem", "seglistitem", "varlistentry",
)

# Tags usually closed in-place in strict XML, break before and after.
_tagbr_inplace = (
    # HTML
    "br", "hr",
    # KUIT
    "nl",
)


def _tag_split (tag):
    """
    Split tag statement into tag name and a state string.

    State is one of "open" (<foo>), "close" (</foo>), or "inplace" (<foo/>).

    @param tag: the tag proper, C{<...>}
    @type tag: string
    @returns: tag name and state
    @rtype: string, string
    """

    m = _tag_split_rx.match(tag)
    if m:
        if m.group(1):
            state = "close"
        elif m.group(3):
            state = "inplace"
        else:
            state = "open"
        return m.group(2), state
    else:
        return "", ""


def wrap_text (text, wcol=79, lead="", trail="", flead=None, femp=False,
               natbr="", prebr=(), postbr=(), tagbr=(), tagbr2=(),
               wcolmin=0, midbr=True, remtrws=False, addnl=True):
    """
    Wrap text into lines.

    Wrapping behavior and positions can be controlled by several parameters.
    Trailing and leading strings can be added to each wrapped line, including
    a special lead for the first line.

    If wrapping column is given as less or equal to zero, the lines are split
    only at unconditional breaks.

    This is a very general wrapping function, see the more specialized ones in
    this module for practical use with PO message elements.

    @param text: the text to wrap
    @type text: string
    @param wcol: column to wrap after
    @type wcol: int
    @param lead: prefix for each line
    @type lead: string
    @param trail: suffix for each line
    @type trail: string
    @param flead:
        special suffix for the first line. Normal suffix is used if this is
        given as C{None}
    @type flead: C{None} or string
    @param femp:
        C{True} to leave the first line empty if the complete text would not
        fit into it, C{False} for normal use of the first line
    @type femp: bool
    @param natbr: characters other than space to naturally break at
    @type natbr: string
    @param prebr: character sequences to unconditionally break before
    @type prebr: (string*)
    @param postbr: character sequences to unconditionally break after
    @type postbr: (string*)
    @param tagbr: tag names to break before opening and after closing
    @type tagbr: (string*)
    @param tagbr2: tag names to always break after (like <br>)
    @type tagbr2: (string*)
    @param wcolmin: minimal column to allow natural breaks after
    @type wcolmin: int
    @param midbr:
        C{True} to allow break in the middle of a word if no usual break
        found before C{wcol} has been exceeded
    @type midbr: bool
    @param remtrws:
        whether to strictly remove any trailing whitespace in wrapped lines
        (otherwise trailing whitespace may be left in under certain conditions)
    @type remtrws: bool
    @param addnl: whether to add newline to end of each line
    @type addnl: bool
    @returns: wrapped lines
    @rtype: [string*]
    """

    if flead is None:
        flead = lead

    rlentext = len(text)
    atoms = _atomize(text)[:-1] # strip sentry
    vlenlead = _atomize(lead)[-1][2]
    vlentrail = _atomize(trail)[-1][2]
    vlenflead = _atomize(flead)[-1][2]

    if wcol > 0 and vlenlead + vlentrail + 1 >= wcol:
        raise PologyError(
            _("@info",
              "Wrapping is too tight, cannot fit leading and trailing text."))

    lines = [] # list of lines
    nlines = 0
    lenatoms = len(atoms)
    p = 0 # position into original text by atoms
    vtext = "".join(x[0] for x in atoms)
    vposs = tuple(x[2] for x in atoms)
    while p < lenatoms:
        # Determine effective wrapping column for this line.
        ewcol = wcol - 1 - vlentrail # -1 for newline character
        if nlines == 0:
            clead = flead
            ewcol -= vlenflead
        else:
            clead = lead
            ewcol -= vlenlead

        # Find where to wrap.
        atbr = False # immediate break found
        pl = 0 # position into current line
        ple = 0 #b apparent position into current line
        pl_ok = 0 # last good position into current line (where wrap was fine)
        ple_ok = 0 # last good apparent position into current line
        pvseg, pvlen = "", 0
        while (    p + pl < lenatoms
               and (ple <= ewcol or wcol <= 0 or (not midbr and pl_ok == 0))
               and not atbr
        ):
            if pl > 0:
                pvseg, pvlen = atoms[p + pl - 1][:2]
            cvseg, cvlen = atoms[p + pl][:2]
            if postbr or tagbr or tagbr2: # condition for optimization
                backvtext = vtext[vposs[p]:vposs[p + pl]]
            if prebr or tagbr: # condition for optimization
                forevtext = vtext[vposs[p + pl]:]

            # Immediate breaks allowed only after
            # at least one visually non-empty atom.
            if vposs[p + pl] > vposs[p]:

                # Check for an immediate break by sequence.
                for br in postbr:
                    if not isinstance(br, tuple):
                        if backvtext.endswith(br):
                            atbr = True; break
                    else:
                        br1, br2 = br
                        if (    backvtext.endswith(br1)
                            and not backvtext.endswith(br2)
                        ):
                            atbr = True; break
                if atbr: break
                for br in prebr:
                    if forevtext.startswith(br):
                        atbr = True; break
                if atbr: break

                # Check for an immediate break by tag.
                if tagbr or tagbr2:
                    if backvtext.endswith(">"):
                        pt = backvtext.rfind("<", 0, -1)
                        if pt >= 0:
                            tag, state = _tag_split(backvtext[pt:])
                            if (   (tag in tagbr2)
                                or (    tag in tagbr
                                    and state in ("close", "inplace"))
                            ):
                                atbr = True; break
                if tagbr:
                    if forevtext.startswith("<"):
                        pt = forevtext.find(">", 1)
                        if pt >= 0:
                            tag, state = _tag_split(forevtext[:pt+1])
                            if tag in tagbr and state == "open":
                                atbr = True; break

            # Check for valid natural break.
            if (   pvseg in " "
                or (cvseg != " " and pvseg in natbr and cvseg not in natbr)
            ):
                pl_ok = pl
                ple_ok = ple

            ple += pvlen
            pl += 1

        # If not unconditional break, still enough text, and break possible.
        if not atbr and ple > ewcol and ewcol > 0:
            # Don't allow too short natural break.
            if ple_ok > wcolmin:
                pl = pl_ok
                ple = ple_ok
            # Backstep any segments still too much if mid-word break allowed.
            if midbr:
                while pl > 1 and ple > ewcol:
                    pl -= 1
                    ple -= atoms[pl][1]

        # Never break after non-final backslash.
        if p + pl < lenatoms:
            while pl > 1 and atoms[p + pl - 1][0] == "\\":
                pl -= 1
                ple -= atoms[p + pl][1]

        if (    nlines == 0
            and ((femp and p + pl < lenatoms) or (ewcol <= 0 and wcol > 0))
        ):
            # leaving first line empty
            lines.append(clead + trail)
            pl = 0
        else:
            p1 = atoms[p][4]
            p2 = atoms[p + pl][4] if p + pl < lenatoms else rlentext
            lines.append(clead + text[p1:p2] + trail)

        nlines += 1
        p += pl

    if lenatoms == 0: # in case no text given, main loop did not run
        lines.append(flead + trail)

    for i in range(len(lines)): # postprocess
        # Strip trailing whitespace if no trailing string or removal is forced.
        if not trail or remtrws:
            # Do not remove trailing whitespace which is part of leading string,
            # unless removal is forced.
            clead = ""
            if not remtrws:
                if i == 0: clead = flead
                else:      clead = lead
            tmp = lines[i][len(clead):]
            lines[i] = clead + tmp.rstrip()
        if addnl:
            lines[i] += "\n" # terminate with newline

    return lines


def _atomize (text):
    """
    Split text into atomic segments and compute their visual and raw widths.

    Returns list of tuples
    (visual segment, visual length, visual position, raw length, raw position).
    The list always ends with zero-visual length segment,
    so that it is not empty even if the text is empty,
    and that last atom's positions are visual and raw lengths of the string.
    """

    atoms = []
    isuc = isinstance(text, unicode)
    vsegf = getattr(text, "visual_segment", None)
    rpos = 0
    vpos = 0
    rlentext = len(text)
    while rpos < rlentext:
        rlen = 0
        if vsegf:
            vseg, rlen = vsegf(rpos)
        if rlen == 0:
            vseg, rlen = text[rpos], 1
        vlen = 1
        if isuc and vseg:
            width_class = unicodedata.east_asian_width(vseg)
            if width_class in ("W", "F"):
                vlen = 2
        atoms.append((vseg, vlen, vpos, rlen, rpos))
        vpos += vlen
        rpos += rlen
    atoms.append((type(text)(""), 0, vpos, 0, rpos))

    return atoms


def wrap_field (field, text, preseq=""):
    """
    Wrap fields in PO messages.

    This function can be sent as parameter to L{Message} and L{Catalog}
    methods and constructors.

    @param field: the field keyword (C{"msgctxt"}, C{"msgid"}, ...)
    @type field: string

    @param text: the text of the field
    @type text: string

    @param preseq:
        the prefix to field keyword, usually for previous-value (C{"#|"})
        and obsolete (C{"#~"}) fields
    @type preseq: string

    @returns: wrapped field lines (each ends with a newline)
    @rtype: list of strings
    """

    return wrap_text(text, 79,
                     flead=preseq+field+" \"",
                     lead=preseq+"\"",
                     trail="\"",
                     natbr=_natbr,
                     prebr=_prebr,
                     postbr=_postbr,
                     femp=True,
                     wcolmin=39)


def wrap_field_unwrap (field, text, preseq=""):
    """
    Wrap fields in PO messages at unconditional breaks (no column-wrapping).

    This function can be sent as parameter to L{Message} and L{Catalog}
    methods and constructors.

    The parameters and return values are as for L{wrap_field}.

    @see: L{wrap_field}
    """

    return wrap_text(text, 0,
                     flead=preseq+field+" \"",
                     lead=preseq+"\"",
                     trail="\"",
                     prebr=_prebr,
                     postbr=_postbr,
                     femp=True)


def wrap_comment (ctype, text):
    """
    Wrap comments in PO messages.

    @param ctype: the comment type (C{"# "}, C{"#:"}, C{"#."}, ...)
    @type ctype: string

    @param text: the text of the comment
    @type text: string

    @returns: wrapped comment lines (each ends with a newline)
    @rtype: list of strings
    """

    return wrap_text(text, 79,
                     lead="#"+ctype+" ",
                     femp=False,
                     midbr=False,
                     remtrws=True)
    # midbr is False in order to prevent e.g. very long source references
    # being forced split in the middle.
    # remtrws is True in order to remove the trailing space in empty comments.


def wrap_comment_unwrap (ctype, text):
    """
    Wrap comments in PO messages at unconditional breaks (no column-wrapping).

    The parameters and return values are as for L{wrap_comment}.

    @see: L{wrap_comment}
    """

    return wrap_text(text, 0,
                     lead="#"+ctype+" ",
                     femp=False,
                     remtrws=True)


def wrap_field_fine (field, text, preseq=""):
    """
    Wrap fields in PO messages, including breaks at selected markup elements.

    This function can be sent as parameter to L{Message} and L{Catalog}
    methods and constructors.

    The parameters and return values are as for L{wrap_field}.

    @see: L{wrap_field}
    """

    return wrap_text(text, 79,
                     flead=preseq+field+" \"",
                     lead=preseq+"\"",
                     trail="\"",
                     natbr=_natbr,
                     prebr=_prebr,
                     postbr=_postbr,
                     tagbr=_tagbr_normal,
                     tagbr2=_tagbr_inplace,
                     femp=True)


def wrap_field_fine_unwrap (field, text, preseq=""):
    """
    Wrap fields in PO messages, including breaks at selected markup elements,
    but only at unconditional breaks (no column-wrapping).

    This function can be sent as parameter to L{Message} and L{Catalog}
    methods and constructors.

    The parameters and return values are as for L{wrap_field}.

    @see: L{wrap_field}
    """

    return wrap_text(text, 0,
                     flead=preseq+field+" \"",
                     lead=preseq+"\"",
                     trail="\"",
                     prebr=_prebr,
                     postbr=_postbr,
                     tagbr=_tagbr_normal,
                     tagbr2=_tagbr_inplace,
                     femp=True)


def select_field_wrapper (wrapkw):
    """
    Select wrap function for PO message fields.

    Wrap function is selected by specifying a sequence of keywords,
    from the following set:
      - C{"basic"}: wrapping on column count
      - C{"fine"}: wrapping on logical breaks (such as C{<p>} or C{<para>} tags)
    Wrapping on newline characters is always engaged.
    If C{wrapkw} is given as C{None}, C{"basic"} only is assumed.

    @param wrapkw: wrapping keywords
    @type wrapkw: sequence of strings or C{None}

    @returns: wrapping function
    @rtype: (string, string, string?)->[string]

    @see: L{wrap_field}
    """

    if wrapkw is None:
        wrapkw = ["basic"]

    if "basic" in wrapkw:
        if "fine" in wrapkw:
            wrapf = wrap_field_fine
        else:
            wrapf = wrap_field
    else:
        if "fine" in wrapkw:
            wrapf = wrap_field_fine_unwrap
        else:
            wrapf = wrap_field_unwrap

    return wrapf

