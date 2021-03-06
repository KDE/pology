# -*- coding: UTF-8 -*-

"""
Various checks for translations into Serbian.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import re

from pology import _, n_
from pology.diff import adapt_spans
from pology.msgreport import warning_on_msg

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
    # - format directives
    re.compile(r"%(\(\w+\))? ?\d?\$?[\d.]*[a-z]+", re.U|re.I), # C-like
    re.compile(r"%\d+", re.U|re.I), # Qt-like, must come after C-like
    # - text within these tags
    re.compile(r"<\s*(%s)\b.*?\b\1\s*>" % "|".join("""
        bcode command envar filename icode shortcut placeholder style code tt
        literal screen option keycap userinput systemitem prompt function
        foreignphrase varname programlisting token markup parameter keysym
        methodname replaceable sgmltag arg classname type package errorcode
    """.split()), re.U|re.I|re.S),
    # - some tags are requested without attributes, as otherwise
    # Latin-content is allowed inside attributes only.
    re.compile(r"<\s*(%s)\s*>\b.*?\b\1\s*>" % "|".join("""
        email link
    """.split()), re.U|re.I|re.S),
    # - all tags (must come after the above text removed by tags)
    re.compile(r"<.*?>", re.U|re.I),
    # - entities
    re.compile(r"&[\w_:][\w\d._:-]*;", re.U|re.I),
    # - command line options
    re.compile(r"(?<!\w)--?\w[\w-]*", re.U|re.I),
    # - hex numbers
    re.compile(r"0x[\dabcdef]*", re.U|re.I),
    # - alternatives directives
    re.compile(r"~@(.)(.*?)\1(.*?)\1", re.U|re.I|re.S),
    # - extension filter, e.g. "*.png|PNG files"
    re.compile(r"^.*\*\..*\|", re.U|re.I),
    # - URLs and web links
    re.compile(r"\S+://\S*[\w&=]", re.U),
    re.compile(r"\w{3,}(\.[\w-]{2,})+", re.U),
    # - wiki stuff
    re.compile(r"\[\[[^\]]*(\||\])", re.U|re.I),
    re.compile(r"\[[^\s]*", re.U|re.I),
    re.compile(r"\{\{.*?(\||\}\})", re.U|re.I),
    # - double escapings
    re.compile(r"\\[nt]"),
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

# Messages to skip by tags in auto comments.
_auto_cmnt_tag_rx = re.compile(r"^\s*Tag:\s*(%s)\s*$" % "|".join("""
    filename envar programlisting screen command option userinput cmdsynopsis
    email errorcode
""".split()), re.U|re.I)

# The hook worker.
def _naked_latin_w (msgstr, msg, cat, origui=False, sideeffect=False):

    # Avoid meta-messages.
    if (   msg.msgctxt in ("EMAIL OF TRANSLATORS",)
        or (    cat.name.endswith(".desktop")
            and msg.msgctxt in ("Keywords", "Query"))
    ):
        if sideeffect:
            return 0
        else:
            return []

    # Avoid specially tagged messages.
    for auto_cmnt in msg.auto_comment:
        if _auto_cmnt_tag_rx.search(auto_cmnt):
            if sideeffect:
                return 0
            else:
                return []

    # Eliminate all no-check segments.
    stripped_msgstr = msgstr
    if origui: # must come before tag removal
        for rx in _no_check_lat_origui_rxs:
            stripped_msgstr = rx.sub("", stripped_msgstr)
    for rx in _no_check_lat_rxs:
        stripped_msgstr = rx.sub("", stripped_msgstr)

    matches = list(_naked_latin_rx.finditer(stripped_msgstr))
    if sideeffect:
        # Report if any Latin text remained in stripped msgstr.
        for m in matches:
            warning_on_msg(_("@info",
                             "Naked Latin segment '%(snippet)s'.",
                             snippet=m.group(0)), msg, cat)
        return len(matches)
    else:
        # Collect and adapt offending spans.
        spans = [m.span() for m in matches]
        spans = adapt_spans(msgstr, stripped_msgstr, spans, merge=False)
        return spans


def naked_latin (msgstr, msg, cat):
    """
    Report spans of Latin letters outside of sanctioned contexts
    [type V3C hook].

    Latin segments are allowed within:
      - some XML-like tags, e.g. C{tt}, C{code}, C{email}, C{envar}, etc.
      - XML-like entities, e.g. C{&foo;} or C{&#x00a0;}
      - format directives starting with %-character
      - command line options, e.g. C{-o} or C{--foo-bar}
      - hexadecimal number starting with C{0x}
      - extension filters, e.g. C{"*.png|ПНГ слике"}
      - alternative directives {~@/.../.../}, e.g. C{~@/Делфин/Dolphin/}
      - links in wiki markup, e.g. C{"...на [http://foo.org страни Фуа]"}
      - templates in wiki markup, e.g. C{"{{note|Обавезно проверите...}}"}
      - explicit wrapping C{~!/.../}, e.g. C{"...наредбом ~!/grep/..."}

    @return: annotated spans
    """

    return _naked_latin_w(msgstr, msg, cat)


def naked_latin_origui (msgstr, msg, cat):
    """
    Like C{naked_latin}, but allowing original UI references which are
    supposed to be automatically resolved [type V3C hook].

    Original UI references are given:
      - within XML-like tags: C{gui*} (C{guilabel}, C{guimenu}, etc.),
        C{interface};
        e.g. C{"...кликните на <guibutton>Scramble Reactor</guibutton> да..."}
      - manually wrapped by C{~%/.../},
        e.g. C{"...кликните на ~%/Scramble Reactor/ да..."}

    @return: annotated spans
    """

    return _naked_latin_w(msgstr, msg, cat, origui=True)


def naked_latin_se (msgstr, msg, cat):
    """
    Side-effect version of C{naked_latin}, issuing warnings to stderr
    [type S3C hook].

    @return: number of errors
    """

    return _naked_latin_w(msgstr, msg, cat, sideeffect=True)


def naked_latin_origui_se (msgstr, msg, cat):
    """
    Side-effect version of C{naked_latin_origui}, issuing warnings to stderr
    [type S3C hook].

    @return: number of errors
    """

    return _naked_latin_w(msgstr, msg, cat, origui=True, sideeffect=True)

