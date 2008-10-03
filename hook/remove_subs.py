# -*- coding: UTF-8 -*-

"""
Remove special substrings from parts of the message.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import re

from pology.misc.resolve import remove_accelerator as _rm_accel_in_text
from pology.misc.resolve import remove_fmtdirs as _rm_fmtd_in_text_single
from pology.misc.resolve import remove_literals as _rm_lit_in_text_single
import pology.misc.markup as M
from pology.misc.comments import manc_parse_field_values
from pology.misc.report import warning_on_msg


def _rm_accel_in_msg (msg, accels, greedy=False):

    msg.msgid = _rm_accel_in_text(msg.msgid, accels, greedy)
    msg.msgid_plural = _rm_accel_in_text(msg.msgid_plural, accels, greedy)
    for i in range(len(msg.msgstr)):
        msg.msgstr[i] = _rm_accel_in_text(msg.msgstr[i], accels, greedy)

    msg.msgid_previous = _rm_accel_in_text(msg.msgid_previous, accels, greedy)
    msg.msgid_plural_previous = _rm_accel_in_text(msg.msgid_plural_previous,
                                                  accels, greedy)


def remove_accel_text (cat, msg, text):
    """
    Remove accelerator marker from one of the text fields of the message.

    Accelerator marker is determined from the catalog, by calling its
    L{accelerator()<pology.file.catalog.Catalog.accelerator>} method.
    Use L{set_accelerator()<pology.file.catalog.Catalog.set_accelerator>}
    to set possible accelerator markers after the catalog has been opened,
    in case it does not specify any on its own.
    If catalog reports C{None} for accelerators, text is not touched.

    @note: Hook type: C{(cat, msg, text) -> text}
    @see: L{pology.misc.resolve.remove_accelerator}
    """

    accels = cat.accelerator()
    return _rm_accel_in_text(text, accels)


def remove_accel_text_greedy (cat, msg, text):
    """
    Like L{remove_accel_text}, except that if catalog reports C{None}
    for accelerators, some frequent marker characters are removed.

    @note: Hook type: C{(cat, msg, text) -> text}
    @see: L{pology.misc.resolve.remove_accelerator}
    """

    accels = cat.accelerator()
    return _rm_accel_in_text(text, accels, greedy=True)


def remove_accel_msg (cat, msg):
    """
    Remove accelerator marker from all applicable text fields in the message,
    as if L{remove_accel_text} was applied to each.

    @note: Hook type: C{(cat, msg) -> None}, modifies C{msg}
    @see: L{pology.misc.resolve.remove_accelerator}
    """

    accels = cat.accelerator()
    _rm_accel_in_msg(msg, accels)


def remove_accel_msg_greedy (cat, msg):
    """
    Like L{remove_accel_msg}, except that if catalog reports C{None}
    for accelerators, some frequent marker characters are removed.

    @note: Hook type: C{(cat, msg) -> None}, modifies C{msg}
    @see: L{pology.misc.resolve.remove_accelerator}
    """

    accels = cat.accelerator()
    _rm_accel_in_msg(msg, accels, greedy=True)


def _rm_markup_in_text (text, mtypes):

    if mtypes is None:
        return text

    for mtype in mtypes:
        mtype = mtype.lower()
        if 0: pass
        elif mtype == "htmlkuit":
            text = M.htmlkuit_to_plain(text)
        elif mtype == "html":
            text = M.html_to_plain(text)
        elif mtype == "kuit":
            text = M.kuit_to_plain(text)
        elif mtype == "docbook":
            # No special conversion at the moment.
            text = M.xml_to_plain(text)
        elif mtype == "xml":
            text = M.xml_to_plain(text)

    return text


def _rm_markup_in_msg (msg, mtypes):

    msg.msgid = _rm_markup_in_text(msg.msgid, mtypes)
    msg.msgid_plural = _rm_markup_in_text(msg.msgid_plural, mtypes)
    for i in range(len(msg.msgstr)):
        msg.msgstr[i] = _rm_markup_in_text(msg.msgstr[i], mtypes)

    msg.msgid_previous = _rm_markup_in_text(msg.msgid_previous, mtypes)
    msg.msgid_plural_previous = _rm_markup_in_text(msg.msgid_plural_previous,
                                                   mtypes)


def remove_markup_text (cat, msg, text):
    """
    Remove markup from one of the text fields of the message.

    Expected markup types are determined from the catalog, by calling its
    L{markup()<pology.file.catalog.Catalog.markup>} method.
    Use L{set_markup()<pology.file.catalog.Catalog.set_markup>}
    to set expected markup types after the catalog has been opened,
    in case it does not specify any on its own.
    If catalog reports C{None} for markup types, text is not touched.

    The following markup types are recognized at the moment, by keyword strings
    (case insensitive): C{html}, C{kuit}, C{htmlkuit}, C{docbook}, C{xml}.

    @note: Hook type: C{(cat, msg, text) -> text}
    """

    mtypes = cat.markup()
    return _rm_markup_in_text(text, mtypes)


def remove_markup_msg (cat, msg):
    """
    Remove markup from all applicable text fields in the message,
    as if L{remove_markup_text} was applied to each.

    @note: Hook type: C{(cat, msg) -> None}, modifies C{msg}
    """

    mtypes = cat.markup()
    _rm_markup_in_msg(msg, mtypes)


def _format_flags (msg):

    return [x for x in msg.flag if x.endswith("-format")]


def _rm_fmtd_in_text (text, formats, subs=""):

    for format in formats:
        text = _rm_fmtd_in_text_single(text, format, subs=subs)

    return text


def _rm_fmtd_in_msg (msg, subs=""):

    formats = _format_flags(msg)

    msg.msgid = _rm_fmtd_in_text(msg.msgid, formats, subs)
    msg.msgid_plural = _rm_fmtd_in_text(msg.msgid_plural, formats, subs)
    for i in range(len(msg.msgstr)):
        msg.msgstr[i] = _rm_fmtd_in_text(msg.msgstr[i], formats, subs)

    msg.msgid_previous = _rm_fmtd_in_text(msg.msgid_previous, formats, subs)
    msg.msgid_plural_previous = _rm_fmtd_in_text(msg.msgid_plural_previous,
                                                 formats, subs)


def remove_fmtdirs_text (cat, msg, text):
    """
    Remove format directives from one of the text fields of the message.

    The type of format directives is determined from message format flags.

    @note: Hook type: C{(cat, msg, text) -> text}
    @see: L{pology.misc.resolve.remove_fmtdirs}
    """

    return _rm_fmtd_in_text(text, _format_flags(msg))


def remove_fmtdirs_text_tick (tick):
    """
    Like L{remove_fmtdirs_text}, except that each format directive is
    replaced by a non-whitespace "tick" instead of plainly removed.

    @param tick: the tick sequence
    @type tick: string

    @note: Hook type factory: C{(cat, msg, text) -> text}
    """

    def hook (cat, msg, text):
        return _rm_fmtd_in_text(text, _format_flags(msg), tick)

    return hook


def remove_fmtdirs_msg (cat, msg):
    """
    Remove format directives from all applicable text fields in the message,
    as if L{remove_fmtdirs_text} was applied to each.

    @note: Hook type: C{(cat, msg) -> None}, modifies C{msg}
    """

    _rm_fmtd_in_msg(msg)


def remove_fmtdirs_msg_tick (tick):
    """
    Remove format directives from all applicable text fields in the message,
    as if L{remove_fmtdirs_text_tick} was applied to each.

    @param tick: the tick sequence
    @type tick: string

    @note: Hook type factory: C{(cat, msg) -> None}, modifies C{msg}
    """

    def hook (cat, msg):
        _rm_fmtd_in_msg(msg, tick)

    return hook


def _literals_spec (cat, msg):

    fname = "literal-segment"
    rx_strs = manc_parse_field_values(msg, fname)

    # Compile regexes.
    # Empty regex indicates not to do any heuristic removal.
    rxs = []
    heuristic = True
    for rx_str in rx_strs:
        if rx_str:
            try:
                rxs.append(re.compile(rx_str, re.U))
            except:
                warning_on_msg("field %s states malformed regex: %s"
                               % (fname, rx_str), msg, cat)
        else:
            heuristic = False

    return [], rxs, heuristic


def _rm_lit_in_text (text, substrs, regexes, heuristic, subs=""):

    return _rm_lit_in_text_single(text, subs=subs, substrs=substrs,
                                  regexes=regexes, heuristic=heuristic)


def _rm_lit_in_msg (cat, msg, subs=""):

    strs, rxs, heu = _literals_spec(cat, msg)

    msg.msgid = _rm_lit_in_text(msg.msgid, strs, rxs, heu, subs)
    msg.msgid_plural = _rm_lit_in_text(msg.msgid_plural, strs, rxs, heu, subs)
    for i in range(len(msg.msgstr)):
        msg.msgstr[i] = _rm_lit_in_text(msg.msgstr[i], strs, rxs, heu, subs)

    msg.msgid_previous = _rm_lit_in_text(msg.msgid_previous,
                                          strs, rxs, heu, subs)
    msg.msgid_plural_previous = _rm_lit_in_text(msg.msgid_plural_previous,
                                                 strs, rxs, heu, subs)


def remove_literals_text (cat, msg, text):
    """
    Remove literal segments from one of the text fields of the message.

    Literal segments are URLs, email addresses, command line options, etc.
    anything symbolic that the machine, rather than human alone, should parse.
    Note format directives are excluded here, see L{remove_fmtdirs_text}
    for removing them.

    By default, literals are removed heuristically, but this can be influenced
    by embedded C{literal-segment} fields in manual comments. For example::

        # literal-segment: foobar

    states that all C{foobar} segments are literals. The field value is
    actually a regular expression, and there may be several such fields::

        # literal-segment: \w+bar
        # literal-segment: foo[&=] ### a sub comment

    To prevent any heuristic removal of literals, add a C{literal-segment}
    field with empty value.

    @note: Hook type: C{(cat, msg, text) -> text}
    @see: L{pology.misc.resolve.remove_literals}
    """

    strs, rxs, heu = _literals_spec(cat, msg)
    return _rm_lit_in_text(text, strs, rxs, heu)


def remove_literals_text_tick (tick):
    """
    Like L{remove_literals_text}, except that each literal segment is
    replaced by a non-whitespace "tick" instead of plainly removed.

    @param tick: the tick sequence
    @type tick: string

    @note: Hook type factory: C{(cat, msg, text) -> text}
    """

    def hook (cat, msg, text):
        strs, rxs, heu = _literals_spec(cat, msg)
        return _rm_lit_in_text(text, strs, rxs, heu, tick)

    return hook


def remove_literals_msg (cat, msg):
    """
    Remove literal segments from all applicable text fields in the message,
    as if L{remove_literals_text} was applied to each.

    @note: Hook type: C{(cat, msg) -> None}, modifies C{msg}
    """

    _rm_lit_in_msg(cat, msg)


def remove_literals_msg_tick (tick):
    """
    Remove literal segments from all applicable text fields in the message,
    as if L{remove_literals_text_tick} was applied to each.

    @param tick: the tick sequence
    @type tick: string

    @note: Hook type factory: C{(cat, msg) -> None}, modifies C{msg}
    """

    def hook (cat, msg):
        _rm_lit_in_msg(cat, msg, tick)

    return hook

