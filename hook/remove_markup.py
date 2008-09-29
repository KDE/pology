# -*- coding: UTF-8 -*-

"""
Remove markup from parts of the message.

Expected markup types are determined from the catalog, by calling its
L{markup()<pology.file.catalog.Catalog.markup>} method.
Use L{set_markup()<pology.file.catalog.Catalog.set_markup>}
to set expected markup types after the catalog has been opened,
in case it does not specify any on its own.

The following markup types are recognized at the moment, by keyword strings
(case insensitive): C{html}, C{kuit}, C{htmlkuit}, C{docbook}, C{xml}.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import pology.misc.markup as M


def _rem_in_text (text, mtypes):

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


def _rem_in_msg (msg, mtypes):

    msg.msgid = _rem_in_text(msg.msgid, mtypes)
    msg.msgid_plural = _rem_in_text(msg.msgid_plural, mtypes)
    for i in range(len(msg.msgstr)):
        msg.msgstr[i] = _rem_in_text(msg.msgstr[i], mtypes)

    msg.msgid_previous = _rem_in_text(msg.msgid_previous, mtypes)
    msg.msgid_plural_previous = _rem_in_text(msg.msgid_plural_previous, mtypes)


def remove_markup_text (cat, msg, text):
    """
    Remove markup from one of the text fields of the message.

    If catalog reports C{None} for markup types, text is not touched.

    @note: Hook type: C{(cat, msg, text) -> text}
    """

    mtypes = cat.markup()
    return _rem_in_text(text, mtypes)


def remove_markup_msg (cat, msg):
    """
    Remove markup from all applicable text fields in the message.

    If catalog reports C{None} for markup types, text is not touched.

    @note: Hook type: C{(cat, msg) -> None}, modifies C{msg}
    """

    mtypes = cat.markup()
    _rem_in_msg(msg, mtypes)

