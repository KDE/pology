# -*- coding: UTF-8 -*-

"""
Various checks for translations into Serbian.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import re

from pology.misc.msgreport import warning_on_msg

# ----------------------------------------
# Checks for presence of naked Latin segments.

# Directive head for manual GUI references in docs.
_gui_man_dir = "~%"

# Directive head for explicit wrapping to ignore Latin.
_lat_wrap_dir = "~!"

# - segments not to be considered naked
_no_check_lat_rxs = (
    # - explicitly wrapped to ignore
    re.compile(_lat_wrap_dir + r"(.)(.*?)\1", re.U|re.I|re.S),
    # - entities
    re.compile(r"&[\w_:][\w\d._:-]*;", re.U|re.I),
    # - format directives
    re.compile(r"%(\d+| ?[\d.]*[a-z]+)", re.U|re.I),
    # - command line options
    re.compile(r"(?<!\S)--?\w[\w-]*", re.U|re.I),
    # - hex numbers
    re.compile(r"0x[\dabcdef]*", re.U|re.I),
    # - alternatives directives
    re.compile(r"~@(.)(.*?)\1(.*?)\1", re.U|re.I|re.S),
    # - extension filter, e.g. "*.png|PNG files"
    re.compile(r"^.*\*\..*\|", re.U|re.I),
    # - text within these tags
    # NOTE: Some tags are requested without attributes, as otherwise
    # Latin-content is allowed inside attribute only.
    re.compile(r"<\s*(bcode)\b.*?\b\1\s*>", re.U|re.I|re.S),
    re.compile(r"<\s*(command)\b.*?\b\1\s*>", re.U|re.I),
    re.compile(r"<\s*(email)\s*>\b.*?\b\1\s*>", re.U|re.I),
    re.compile(r"<\s*(envar)\b.*?\b\1\s*>", re.U|re.I),
    re.compile(r"<\s*(filename)\b.*?\b\1\s*>", re.U|re.I),
    re.compile(r"<\s*(icode)\b.*?\b\1\s*>", re.U|re.I),
    re.compile(r"<\s*(link)\s*>\b.*?\b\1\s*>", re.U|re.I),
    re.compile(r"<\s*(shortcut)\b.*?\b\1\s*>", re.U|re.I),
    re.compile(r"<\s*(placeholder)\b.*?\b\1\s*>", re.U|re.I),
    re.compile(r"<\s*(style)\b.*?\b\1\s*>", re.U|re.I|re.S), # for text/css
    re.compile(r"<\s*(code)\b.*?\b\1\s*>", re.U|re.I|re.S), # HTML code tag
    re.compile(r"<\s*(tt)\b.*?\b\1\s*>", re.U|re.I|re.S), # also HTML code tag
    re.compile(r"<\s*(literal)\b.*?\b\1\s*>", re.U|re.I|re.S), # Docbook
    re.compile(r"<\s*(screen)\b.*?\b\1\s*>", re.U|re.I|re.S), # Docbook
    re.compile(r"<\s*(option)\b.*?\b\1\s*>", re.U|re.I|re.S), # Docbook
    re.compile(r"<\s*(keycap)\b.*?\b\1\s*>", re.U|re.I|re.S), # Docbook
    re.compile(r"<\s*(userinput)\b.*?\b\1\s*>", re.U|re.I|re.S), # Docbook
    # - all tags (must come after the above text removed by tags)
    re.compile(r"<.*?>", re.U|re.I),
    # - wiki stuff
    re.compile(r"\[\[[^\]]*(\||\])", re.U|re.I),
    re.compile(r"\[[^\s]*", re.U|re.I),
    re.compile(r"\{\{.*?(\||\}\})", re.U|re.I),
)
_no_check_lat_origui_rxs = (
    # - automatic by tags
    re.compile(r"<\s*(gui[a-z]+)\b.*?\b\1\s*>", re.U|re.I|re.S), # Docbook
    re.compile(r"<\s*(interface)\b.*?\b\1\s*>", re.U|re.I|re.S), # KUIT
    # - manually wrapped
    re.compile(_gui_man_dir + r"(.)(.*?)\1", re.U|re.I|re.S),
)

# Warn on naked-Latin if this matches.
_naked_latin_rx = re.compile(r"[a-z][a-z\W]*", re.U|re.I)

# The hook worker.
def _naked_latin_w (cat, msg, msgstr, origui=False, passthrough=False):

    # Avoid meta-messages.
    if (   msg.msgctxt in ("EMAIL OF TRANSLATORS",)
        or (    cat.name.startswith("desktop_")
            and msg.msgctxt in ("Keywords", "Query"))
    ):
        if passthrough:
            return None
        else:
            return [], None

    # Eliminate all no-check segments.
    stripped_msgstr = msgstr
    if origui: # must come before tag removal
        for rx in _no_check_lat_origui_rxs:
            stripped_msgstr = rx.sub("", stripped_msgstr)
    for rx in _no_check_lat_rxs:
        stripped_msgstr = rx.sub("", stripped_msgstr)

    matches = _naked_latin_rx.finditer(stripped_msgstr)
    if passthrough:
        # Report if any Latin text remained in stripped msgstr.
        for m in matches:
            warning_on_msg("naked-Latin segment: %s" % m.group(0), msg, cat)
        return None
    else:
        # Collect offending spans.
        spans = [m.span() for m in matches]
        return spans, stripped_msgstr


def naked_latin (cat, msg, msgstr):
    """
    Report spans of Latin letters outside of sanctioned contexts.

    Latin segments are allowed within:
      - the following XML-like tags: C{bcode}, C{command}, C{email}, C{envar},
        C{filename}, C{icode}, C{link}, C{shortcut}, C{placeholder}, C{style},
        C{code}, C{tt}, C{literal}, C{screen}, C{option}, C{keycap},
        C{userinput}
      - XML-like entities, e.g. C{&foo;} or C{&#x00a0;}
      - format directives starting with %-character
      - command line options, e.g. C{-o} or C{--foo-bar}
      - hexadecimal number starting with C{0x}
      - extension filters, e.g. C{"*.png|ПНГ слике"}
      - alternative directives {~@/.../.../}, e.g. C{~@/Делфин/Dolphin/}
      - links in wiki markup, e.g. C{"...на [http://foo.org страни Фуа]"}
      - templates in wiki markup, e.g. C{"{{note|Обавезно проверите...}}"}
      - explicit wrapping C{~!/.../}, e.g. C{"...наредбом ~!/grep/..."}

    @note: Hook type: C{(cat, msg, msgstr) -> spans}
    """

    return _naked_latin_w(cat, msg, msgstr)


def naked_latin_origui (cat, msg, msgstr):
    """
    Like C{naked_latin}, but allowing original UI references which are
    supposed to be automatically resolved.

    Original UI references are given:
      - within XML-like tags: C{gui*} (C{guilabel}, C{guimenu}, etc.),
        C{interface};
        e.g. C{"...кликните на <guibutton>Scramble Reactor</guibutton> да..."}
      - manually wrapped by C{~%/.../},
        e.g. C{"...кликните на ~%/Scramble Reactor/ да..."}

    @note: Hook type: C{(cat, msg, msgstr) -> spans}
    """

    return _naked_latin_w(cat, msg, msgstr, origui=True)


def naked_latin_pt (cat, msg, msgstr):
    """
    Pass-through version of C{naked_latin}, issuing warnings to stderr.

    @note: Hook type: C{(cat, msg, msgstr) -> None}
    """

    return _naked_latin_w(cat, msg, msgstr, passthrough=True)


def naked_latin_origui_pt (cat, msg, msgstr):
    """
    Pass-through version of C{naked_latin_origui}, issuing warnings to stderr.

    @note: Hook type: C{(cat, msg, msgstr) -> None}
    """

    return _naked_latin_w(cat, msg, msgstr, origui=True, passthrough=True)

