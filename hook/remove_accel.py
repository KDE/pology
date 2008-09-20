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

_usual_accels = list("_&~^")


def _rem_in_text (text, accels):

    if accels:
        for accel in accels:
            text = text.replace(accel, "", 1)

    return text


def _rem_in_msg (msg, accels):

    msg.msgid = _rem_in_text(msg.msgid, accels)
    msg.msgid_plural = _rem_in_text(msg.msgid_plural, accels)
    for i in range(len(msg.msgstr)):
        msg.msgstr[i] = _rem_in_text(msg.msgstr[i], accels)

    msg.msgid_previous = _rem_in_text(msg.msgid_previous, accels)
    msg.msgid_plural_previous = _rem_in_text(msg.msgid_plural_previous, accels)


def remove_accel_text (cat, msg, text):
    """
    Remove accelerator marker from one of the text fields of the message.

    If catalog reports C{None} for accelerators, text is not touched.

    @note: Hook type: C{(cat, msg, text) -> text}
    """

    accels = cat.accelerator()
    return _rem_in_text(text, accels)


def remove_accel_text_greedy (cat, msg, text):
    """
    Like L{remove_accel_text}, except that if catalog reports C{None}
    for accelerators, some frequent marker characters are removed.

    @note: Hook type: C{(cat, msg, text) -> text}
    """

    accels = cat.accelerator()
    if accels is None:
        accels = _usual_accels
    return _rem_in_text(text, accels)


def remove_accel_msg (cat, msg):
    """
    Remove accelerator marker from all applicable text fields in the message.

    If catalog reports C{None} for accelerators, text is not touched.

    @note: Hook type: C{(cat, msg) -> None}, modifies C{msg}
    """

    accels = cat.accelerator()
    _rem_in_msg(msg, accels)


def remove_accel_msg_greedy (cat, msg):
    """
    Like L{remove_accel_msg}, except that if catalog reports C{None}
    for accelerators, some frequent marker characters are removed.

    @note: Hook type: C{(cat, msg) -> None}, modifies C{msg}
    """

    accels = cat.accelerator()
    if accels is None:
        accels = _usual_accels
    _rem_in_msg(msg, accels)

