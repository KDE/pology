# -*- coding: UTF-8 -*-

"""
Remove special substrings from parts of the message.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

from pology.misc.resolve import remove_accelerator as _rm_accel_in_text
import pology.misc.markup as M


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

