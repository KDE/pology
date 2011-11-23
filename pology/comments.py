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

    Like L{manc_parse_list} but works on auto comments.

    @param msg: message to parse
    @type msg: Message
    @param prefix: list identifier substring
    @type prefix: string
    @param separator: sequence separating list elements
    @type separator: string

    @returns: parsed elements
    @rtype: list of strings
    """

    return parse_list(msg.auto_comment, prefix, separator)


def manc_parse_flag_list (msg, prefix):
    """
    Extract custom flags embedded in manual comments.

    An embedded list of flags is of the form::

        # <prefix>, flag1, flag2, ...

    Custom flags are extracted by calling L{parse_list()}
    with C{<prefix>,} as prefix and C{,} as element separator.

    Some types of custom flags used elsewhere in Pology, by prefixes:

      - pipe flags, with pipe character (C{|}) as prefix, used to
        influence behavior of L{sieves<pology.sieve>}

    @param msg: message to parse
    @type msg: Message
    @param prefix: flag list identifier
    @type prefix: string

    @returns: parsed flags
    @rtype: list of strings

    @see: L{parse_list}
    """

    return parse_list(msg.manual_comment, prefix + ",", ",")


def autoc_parse_flag_list (msg, prefix):
    """
    Extract custom flags embedded in auto comments.
    
    Like L{manc_parse_flag_list} but works on auto comments.

    @param msg: message to parse
    @type msg: Message
    @param prefix: flag list identifier
    @type prefix: string

    @returns: parsed flags
    @rtype: list of strings
    """

    return parse_list(msg.auto_comment, prefix + ",", ",")


def parse_field_values (comments, field):
    """
    Extract values of a field embedded in comments.

    And embedded field is of the form::

        <field>: <value> ### sub-comment

    There may be several fields of the same name, thus the values are
    returned in a list (empty if there were no appearances of the field).
    Values are stripped of leading and trailing whitespace.

    @param comments: comments to parse
    @type comments: sequence of strings
    @param field: field name
    @type field: string

    @returns: parsed values
    @rtype: list of strings
    """

    values = []
    for cmnt in comments:
        cmnt = cmnt.strip()
        p = cmnt.find("###")
        if p >= 0:
            cmnt = cmnt[:p]
        if cmnt.startswith(field):
            p = cmnt.find(field) + len(field)
            while p < len(cmnt) and cmnt[p].isspace():
                p += 1
            if p == len(cmnt) or cmnt[p] != ":":
                continue
            values.append(cmnt[p + 1:].strip())

    return values


def manc_parse_field_values (msg, field):
    """
    Extract values of a field embedded in manual comments.

    Applies L{parse_field_values} to manual comments of the message.

    @param msg: message to parse
    @type msg: Message
    @param field: field name
    @type field: string

    @returns: parsed values
    @rtype: list of strings
    """

    return parse_field_values(msg.manual_comment, field)


def autoc_parse_field_values (msg, field):
    """
    Extract values of a field embedded in auto comments.

    Like L{manc_parse_field_values} but works on auto comments.

    @param msg: message to parse
    @type msg: Message
    @param field: field name
    @type field: string

    @returns: parsed values
    @rtype: list of strings
    """

    return parse_field_values(msg.auto_comment, field)


def parse_summit_branches (msg):
    """
    Summit: Extract branch IDs from comments.

    Branch IDs are embedded as an auto comment of this form::

        #. +> branch_id_1 branch_id_2 ...

    Branch IDs should be unique.

    @param msg: message to parse
    @type msg: Message

    @returns: parsed branched IDs
    @rtype: set of strings
    """

    return set(parse_list(msg.auto_comment, "+>", " "))

