# -*- coding: UTF-8 -*-

"""
Remove accelerator marker from parts of the message.

Accelerator marker is determined from the catalog, by calling its
L{accelerator()<pology.file.catalog.Catalog.accelerator>} method.
Use L{set_accelerator()<pology.file.catalog.Catalog.set_accelerator>}
to set possible accelerator markers after the catalog has been opened,
in case it does not specify any on its own.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

from pology.misc.resolve import remove_accelerator as _rem_in_text


def _rem_in_msg (msg, accels, greedy=False):

    msg.msgid = _rem_in_text(msg.msgid, accels, greedy)
    msg.msgid_plural = _rem_in_text(msg.msgid_plural, accels, greedy)
    for i in range(len(msg.msgstr)):
        msg.msgstr[i] = _rem_in_text(msg.msgstr[i], accels, greedy)

    msg.msgid_previous = _rem_in_text(msg.msgid_previous, accels, greedy)
    msg.msgid_plural_previous = _rem_in_text(msg.msgid_plural_previous, accels,
                                             greedy)


def remove_accel_text (cat, msg, text):
    """
    Remove accelerator marker from one of the text fields of the message.

    If catalog reports C{None} for accelerators, text is not touched.

    @note: Hook type: C{(cat, msg, text) -> text}
    @see: L{pology.misc.resolve.remove_accelerator}
    """

    accels = cat.accelerator()
    return _rem_in_text(text, accels)


def remove_accel_text_greedy (cat, msg, text):
    """
    Like L{remove_accel_text}, except that if catalog reports C{None}
    for accelerators, some frequent marker characters are removed.

    @note: Hook type: C{(cat, msg, text) -> text}
    @see: L{pology.misc.resolve.remove_accelerator}
    """

    accels = cat.accelerator()
    return _rem_in_text(text, accels, greedy=True)


def remove_accel_msg (cat, msg):
    """
    Remove accelerator marker from all applicable text fields in the message.

    If catalog reports C{None} for accelerators, text is not touched.

    @note: Hook type: C{(cat, msg) -> None}, modifies C{msg}
    @see: L{pology.misc.resolve.remove_accelerator}
    """

    accels = cat.accelerator()
    _rem_in_msg(msg, accels)


def remove_accel_msg_greedy (cat, msg):
    """
    Like L{remove_accel_msg}, except that if catalog reports C{None}
    for accelerators, some frequent marker characters are removed.

    @note: Hook type: C{(cat, msg) -> None}, modifies C{msg}
    @see: L{pology.misc.resolve.remove_accelerator}
    """

    accels = cat.accelerator()
    _rem_in_msg(msg, accels, greedy=True)

