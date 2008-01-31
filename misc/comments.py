# -*- coding: UTF-8 -*-

"""
Parsing and composing message comments.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

def parse_list (comments, prefix, separator):
    """
    Extract elements of the list embedded in comments.

    An embedded list is identified by a prefix substring in the comment,
    followed by list of elements separated by a certain character sequence.
    If several comments start by the same identifier substring, they are
    considered continuation of the same list (even if there are non-list
    comments in between).

    Leading and trailing whitespace is stripped when matching for
    prefix substring, as well as from the parsed list elements.

    @param comments: comments to parse
    @type comments: sequence of strings
    @param prefix: list identifier substring
    @type prefix: string
    @param separator: sequence separating list elements
    @type separator: string

    @returns: parsed elements
    @rtype: list of strings
    """

    lst = []
    for cmnt in comments:
        if cmnt.strip().startswith(prefix):
            p = cmnt.find(prefix)
            els = cmnt[p + len(prefix):].split(separator)
            els = [x.strip() for x in els if x]
            lst.extend(els)

    return lst


def manc_parse_list (msg, prefix, separator=" "):
    """
    Extract elements of the list embedded in manual comments.

    List elements are extracted by calling L{parse_list()} on manual comments,
    passing along prefix and separtor as is.

    @param msg: message to parse
    @type msg: Message
    @param prefix: list identifier substring
    @type prefix: string
    @param separator: sequence separating list elements
    @type separator: string

    @returns: parsed elements
    @rtype: list of strings

    @see: L{parse_list}
    """

    return parse_list(msg.manual_comment, prefix, separator)


def autoc_parse_list (msg, prefix, separator=" "):
    """
    Extract elements of the list embedded in auto comments.

    List elements are extracted by calling L{parse_list()} on auto comments,
    passing along prefix and separtor as is.

    @param msg: message to parse
    @type msg: Message
    @param prefix: list identifier substring
    @type prefix: string
    @param separator: sequence separating list elements
    @type separator: string

    @returns: parsed elements
    @rtype: list of strings

    @see: L{parse_list}
    """

    return parse_list(msg.auto_comment, prefix, separator)


def manc_parse_flag_list (msg, prefix):
    """
    Extract custom flags embedded in manual comments.

    An embedded list of flags is of the form::

        # <prefix>, flag1, flag2, ...

    Custom flags are extracted by calling L{parse_list()}
    with C{<prefix>,} as prefix and C{,} as element separator.

    @param msg: message to parse
    @type msg: Message
    @param prefix: flag list identifier
    @type prefix: string

    @returns: parsed flags
    @rtype: list of strings

    @see: L{parse_list}
    """

    return parse_list(msg.manual_comment, prefix + ",", ",")

