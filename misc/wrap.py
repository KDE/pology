# -*- coding: UTF-8 -*-

import re
import unicodedata

_tag_split_rx = re.compile(r"^\s*<\s*(/?)\s*(\w+)[^/>]*(/?)\s*>\s*$")

def _tag_split (tag):
    """Split tag statement into tag name and a state string.

    State is one of "open" (<foo>), "close" (</foo>), or "inplace" (<foo/>).
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

def wrap_text (text, wcol=80, lead="", trail="", flead=None, femp=False,
               natbr="", prebr=(), postbr=(), tagbr=(), tagbr2=(),
               wcolmin=0, midbr=True):
    """Wrap text into lines, with added leading/trailing strings per line.

    Parameters:
      text    - text to wrap
      wcol    - column to wrap at
      lead    - leading string for each line
      trail   - trailing string for each line
      flead   - special leading for the first line, normal leading is used
                if not provided
      femp    - whether to leave the first line empty if complete text does not
                fit into it (leading and trailing strings are added in any case)
      natbr   - string of characters other than space to naturally break at
      prebr   - tuple of strings to unconditionally break before
      postbr  - tuple of strings to unconditionally break after
      tagbr   - tuple of tag names to break before opening and after closing
      tagbr2  - tuple of tag names to always break after (like <br>)
      wcolmin - minimal column to allow natural breaks at
      midbr   - allow mid-word break if no break found before wcol exceeded

    Return the list of lines (each line ends with a newline).

    Leading/trailing strings and \n itself are included into column counting.
    If wcol is 0 or negative, the lines are split only at unconditional breaks.
    """

    if flead is None:
        flead = lead

    lentext = len(text)
    lenlead = len(lead)
    lentrail = len(trail)
    lenflead = len(flead)

    # Compute apparent character widths on the display.
    cwidth = [1] * lentext
    if isinstance(text, unicode):
        for i in range(lentext):
            width_class = unicodedata.east_asian_width(text[i])
            if width_class in ("W", "F"):
                cwidth[i] = 2

    if wcol > 0 and lenlead + lentrail + 1 >= wcol:
        raise StandardError, "too tight wrapping, cannot fit lead and trail"

    lines = [] # list of lines
    nlines = 0
    p = 0 # position into original text
    while p < lentext:
        # Determine effective wrapping column for this line.
        ewcol = wcol - 1 - lentrail # -1 for newline character
        if nlines == 0:
            clead = flead
            ewcol -= lenflead
        else:
            clead = lead
            ewcol -= lenlead

        # Find where to wrap.
        atbr = False # immediate break found
        pl = 1 # position into current line
        # ...start from 1 to avoid immediate break on break-before sequence
        ple = cwidth[p] # apparent position into current line
        pl_ok = 0 # last good position into current line (where wrap was fine)
        ple_ok = 0 # last good apparent position into current line
        while p + pl < lentext \
        and (ple <= ewcol or wcol <= 0 or not midbr) \
        and not atbr:
            pchar = text[p + pl - 1]
            cchar = text[p + pl]
            backtext = text[:p+pl]
            foretext = text[p+pl:]

            # Check for an immediate break by sequence.
            for br in postbr:
                if backtext.endswith(br):
                    atbr = True; break
            if atbr: break
            for br in prebr:
                if foretext.startswith(br):
                    atbr = True; break
            if atbr: break

            # Check for an immediate break by tag.
            if tagbr or tagbr2:
                if backtext.endswith(">"):
                    pt = backtext.rfind("<", 0, -1)
                    if pt >= 0:
                        tag, state = _tag_split(backtext[pt:])
                        if (tag in tagbr2) \
                        or (tag in tagbr and state in ("close", "inplace")):
                            atbr = True; break
            if tagbr:
                if foretext.startswith("<"):
                    pt = foretext.find(">", 1)
                    if pt >= 0:
                        tag, state = _tag_split(foretext[:pt+1])
                        if tag in tagbr and state == "open":
                            atbr = True; break

            # Check for valid natural break.
            if pchar == " " \
            or (cchar != " " and pchar in natbr and cchar not in natbr):
                pl_ok = pl
                ple_ok = ple

            ple += cwidth[p + pl]
            pl += 1

        # If not unconditional break, still enough text, and break possible.
        if not atbr and ple > ewcol and ewcol > 0:
            # Don't allow too short natural break.
            if ple_ok > wcolmin:
                pl = pl_ok
                ple = ple_ok
            # Backstep any characters still too much if mid-word break allowed.
            if midbr:
                while pl > 1 and ple > ewcol:
                    pl -= 1
                    ple -= cwidth[p + pl]

        # Never break after a backslash.
        while pl > 1 and text[p + pl - 1] == "\\":
            pl -= 1
            ple -= cwidth[p + pl]

        if nlines == 0 \
        and ((femp and p + pl < lentext) or (ewcol <= 0 and wcol > 0)):
            # leaving first line empty
            lines.append(clead + trail)
            pl = 0
        else:
            lines.append(clead + text[p : p + pl] + trail)

        nlines += 1
        p += pl

    if lentext == 0: # in case no text given, main loop did not run
        lines.append(flead + trail)

    for i in range(len(lines)): # postprocess
        if not trail: # strip trailing whitespace if no trailing string
            # ...except for whitespace which is part of leading string
            if i == 0: clead = flead
            else:      clead = lead
            tmp = lines[i][len(clead):]
            lines[i] = clead + tmp.rstrip()
        lines[i] += "\n" # terminate with newline

    return lines


_natbr = u".,;/%-)]}"
_prebr = ("|/|",)
_postbr = ("\\n", "|/|")
# |/| is the Transcript fence, should break both before and after.

def wrap_field (field, text, preseq=""):
    return wrap_text(text, 80,
                     flead=preseq+field+" \"",
                     lead=preseq+"\"",
                     trail="\"",
                     natbr=_natbr,
                     prebr=_prebr,
                     postbr=_postbr,
                     femp=True,
                     wcolmin=40)

def wrap_field_unwrap (field, text, preseq=""):
    return wrap_text(text, 0,
                     flead=preseq+field+" \"",
                     lead=preseq+"\"",
                     trail="\"",
                     prebr=_prebr,
                     postbr=_postbr,
                     femp=True)

def wrap_comment (ctype, text):
    return wrap_text(text, 80,
                     lead="#"+ctype+" ",
                     femp=False,
                     midbr=False)
    # midbr is False in order to prevent e.g. very long source references
    # being forced split in the middle.

def wrap_comment_unwrap (ctype, text):
    return wrap_text(text, 0,
                     lead="#"+ctype+" ",
                     femp=False)

_tagbr_normal = (
    # HTML
    "p", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "li",
    "table", "th", "td", "tr", "center", "blockquote", "pre",
    # KUIT
    "title", "subtitle", "para", "list", "item",
)
_tagbr_inplace = (
    # HTML
    "br", "hr",
    # KUIT
    "nl",
)

def wrap_field_ontag (field, text, preseq=""):
    return wrap_text(text, 80,
                     flead=preseq+field+" \"",
                     lead=preseq+"\"",
                     trail="\"",
                     natbr=_natbr,
                     prebr=_prebr,
                     postbr=_postbr,
                     tagbr=_tagbr_normal,
                     tagbr2=_tagbr_inplace,
                     femp=True)

def wrap_field_ontag_unwrap (field, text, preseq=""):
    return wrap_text(text, 0,
                     flead=preseq+field+" \"",
                     lead=preseq+"\"",
                     trail="\"",
                     prebr=_prebr,
                     postbr=_postbr,
                     tagbr=_tagbr_normal,
                     tagbr2=_tagbr_inplace,
                     femp=True)
