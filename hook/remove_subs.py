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
from pology.misc.msgreport import warning_on_msg


def _rm_accel_in_msg (msg, accels, greedy=False):

    msg.msgid = _rm_accel_in_text(msg.msgid, accels, greedy)
    msg.msgid_plural = _rm_accel_in_text(msg.msgid_plural, accels, greedy)
    for i in range(len(msg.msgstr)):
        msg.msgstr[i] = _rm_accel_in_text(msg.msgstr[i], accels, greedy)

    msg.msgid_previous = _rm_accel_in_text(msg.msgid_previous, accels, greedy)
    msg.msgid_plural_previous = _rm_accel_in_text(msg.msgid_plural_previous,
                                                  accels, greedy)
    return 0


def remove_accel_text (text, msg, cat):
    """
    Remove accelerator marker from one of the text fields of the message
    [type F3A hook].

    Accelerator marker is determined from the catalog, by calling its
    L{accelerator()<pology.file.catalog.Catalog.accelerator>} method.
    Use L{set_accelerator()<pology.file.catalog.Catalog.set_accelerator>}
    to set possible accelerator markers after the catalog has been opened,
    in case it does not specify any on its own.
    If catalog reports C{None} for accelerators, text is not touched.

    @return: text

    @see: L{pology.misc.resolve.remove_accelerator}
    """

    accels = cat.accelerator()
    return _rm_accel_in_text(text, accels)


def remove_accel_text_greedy (text, msg, cat):
    """
    Like L{remove_accel_text}, except that if catalog reports C{None}
    for accelerators, some frequent marker characters are removed
    [type F3A hook].

    @return: text

    @see: L{pology.misc.resolve.remove_accelerator}
    """

    accels = cat.accelerator()
    return _rm_accel_in_text(text, accels, greedy=True)


def remove_accel_msg (msg, cat):
    """
    Remove accelerator marker from all applicable text fields in the message,
    as if L{remove_accel_text} was applied to each [type F4A hook].

    @return: number of errors

    @see: L{pology.misc.resolve.remove_accelerator}
    """

    accels = cat.accelerator()
    return _rm_accel_in_msg(msg, accels)


def remove_accel_msg_greedy (msg, cat):
    """
    Like L{remove_accel_msg}, except that if catalog reports C{None}
    for accelerators, some frequent marker characters are removed
    [type F4A hook].

    @return: number of errors

    @see: L{pology.misc.resolve.remove_accelerator}
    """

    accels = cat.accelerator()
    return _rm_accel_in_msg(msg, accels, greedy=True)


def _rm_markup_in_text (text, mtypes):

    if mtypes is None:
        return text

    for mtype in mtypes:
        mtype = mtype.lower()
        if 0: pass
        elif mtype == "kde4":
            text = M.kde4_to_plain(text)
        elif mtype == "qtrich":
            text = M.qtrich_to_plain(text)
        elif mtype == "kuit":
            text = M.kuit_to_plain(text)
        elif mtype == "docbook4" or mtype == "docbook":
            text = M.docbook4_to_plain(text)
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
    return 0


def remove_markup_text (text, msg, cat):
    """
    Remove markup from one of the text fields of the message [type F3A hook].

    Expected markup types are determined from the catalog, by calling its
    L{markup()<pology.file.catalog.Catalog.markup>} method.
    Use L{set_markup()<file.catalog.Catalog.set_markup>}
    to set expected markup types after the catalog has been opened,
    in case it does not specify any on its own.
    If catalog reports C{None} for markup types, text is not touched.

    @return: text
    """

    mtypes = cat.markup()
    return _rm_markup_in_text(text, mtypes)


def remove_markup_msg (msg, cat):
    """
    Remove markup from all applicable text fields in the message,
    as if L{remove_markup_text} was applied to each [type F4A hook].

    @return: number of errors
    """

    mtypes = cat.markup()
    return _rm_markup_in_msg(msg, mtypes)


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
    return 0


def remove_fmtdirs_text (text, msg, cat):
    """
    Remove format directives from one of the text fields of the message
    [type F3A hook].

    The type of format directives is determined from message format flags.

    @return: text

    @see: L{pology.misc.resolve.remove_fmtdirs}
    """

    return _rm_fmtd_in_text(text, _format_flags(msg))


def remove_fmtdirs_text_tick (tick):
    """
    Like L{remove_fmtdirs_text}, except that each format directive is
    replaced by a non-whitespace "tick" instead of plainly removed
    [hook factory].

    @param tick: the tick sequence
    @type tick: string

    @return: type F3A hook
    @rtype: C{(cat, msg, text) -> text}
    """

    def hook (text, msg, cat):
        return _rm_fmtd_in_text(text, _format_flags(msg), tick)

    return hook


def remove_fmtdirs_msg (msg, cat):
    """
    Remove format directives from all applicable text fields in the message,
    as if L{remove_fmtdirs_text} was applied to each [type F4A hook].

    @return: number of errors
    """

    return _rm_fmtd_in_msg(msg)


def remove_fmtdirs_msg_tick (tick):
    """
    Remove format directives from all applicable text fields in the message,
    as if L{remove_fmtdirs_text_tick} was applied to each [hook factory].

    @param tick: the tick sequence
    @type tick: string

    @return: type F4A hook
    @rtype: C{(cat, msg, text) -> numerr}
    """

    def hook (msg, cat):
        return _rm_fmtd_in_msg(msg, tick)

    return hook


def _literals_spec (msg, cat):

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


def _rm_lit_in_msg (msg, cat, subs=""):

    strs, rxs, heu = _literals_spec(msg, cat)

    msg.msgid = _rm_lit_in_text(msg.msgid, strs, rxs, heu, subs)
    msg.msgid_plural = _rm_lit_in_text(msg.msgid_plural, strs, rxs, heu, subs)
    for i in range(len(msg.msgstr)):
        msg.msgstr[i] = _rm_lit_in_text(msg.msgstr[i], strs, rxs, heu, subs)

    msg.msgid_previous = _rm_lit_in_text(msg.msgid_previous,
                                          strs, rxs, heu, subs)
    msg.msgid_plural_previous = _rm_lit_in_text(msg.msgid_plural_previous,
                                                 strs, rxs, heu, subs)
    return 0


def remove_literals_text (text, msg, cat):
    """
    Remove literal segments from one of the text fields of the message
    [type F3A hook].

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

    @return: text

    @see: L{pology.misc.resolve.remove_literals}
    """

    strs, rxs, heu = _literals_spec(msg, cat)
    return _rm_lit_in_text(text, strs, rxs, heu)


def remove_literals_text_tick (tick):
    """
    Like L{remove_literals_text}, except that each literal segment is
    replaced by a non-whitespace "tick" instead of plainly removed
    [hook factory].

    @param tick: the tick sequence
    @type tick: string

    @return: type F3A hook
    @rtype: C{(cat, msg, text) -> text}
    """

    def hook (text, msg, cat):
        strs, rxs, heu = _literals_spec(msg, cat)
        return _rm_lit_in_text(text, strs, rxs, heu, tick)

    return hook


def remove_literals_msg (msg, cat):
    """
    Remove literal segments from all applicable text fields in the message,
    as if L{remove_literals_text} was applied to each [type F4A hook].

    @return: number of errors
    """

    return _rm_lit_in_msg(msg, cat)


def remove_literals_msg_tick (tick):
    """
    Remove literal segments from all applicable text fields in the message,
    as if L{remove_literals_text_tick} was applied to each [hook factory].

    @param tick: the tick sequence
    @type tick: string

    @return: type F4A hook
    @rtype: C{(cat, msg, text) -> numerr}
    """

    def hook (msg, cat):
        return _rm_lit_in_msg(msg, cat, tick)

    return hook

