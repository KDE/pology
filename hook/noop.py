# -*- coding: UTF-8 -*-

"""
Hook which do nothing.

Noop hooks may be useful in situations where application of a hook
is necessary, or when a previously set hook needs to be canceled.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

def text (text):
    """
    Return text as given [type F1A hook].
    """

    return text


def textm (text, msg, cat):
    """
    Return text as given [type F3A hook].
    """

    return text


def msg (msg, cat):
    """
    Do nothing on the message [type F4A hook].
    """

    return 0


def hdr (hdr, cat):
    """
    Do nothing on the header [type F4B hook].
    """

    return 0


def cat (cat):
    """
    Do nothing on the catalog [type F5A hook].
    """

    return 0


def path (path):
    """
    Do nothing on the path [type F6A hook].
    """

    return 0

