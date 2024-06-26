# -*- coding: utf-8 -*-

"""
Remove special substrings from text.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import re

from pology import _, n_
from pology.comments import manc_parse_field_values, manc_parse_list
import pology.markup as M
from pology.msgreport import warning_on_msg
from pology.resolve import remove_accelerator as _rm_accel_in_text
from pology.resolve import remove_fmtdirs as _rm_fmtd_in_text_single
from pology.resolve import remove_literals as _rm_lit_in_text_single
from pology.resolve import resolve_entities_simple


def _rm_accel_in_msg (msg, accels, greedy=False):

    msg.msgid = _rm_accel_in_text(msg.msgid, accels, greedy)
    if msg.msgid_plural:
        msg.msgid_plural = _rm_accel_in_text(msg.msgid_plural, accels, greedy)
    for i in range(len(msg.msgstr)):
        msg.msgstr[i] = _rm_accel_in_text(msg.msgstr[i], accels, greedy)

    if msg.msgid_previous:
        msg.msgid_previous = _rm_accel_in_text(msg.msgid_previous,
                                               accels, greedy)
    if msg.msgid_plural_previous:
        msg.msgid_plural_previous = _rm_accel_in_text(msg.msgid_plural_previous,
                                                      accels, greedy)
    return 0


def _get_accel_marker (msg, cat):

    accels = manc_parse_field_values(msg, "accelerator-marker")
    if not accels:
        accels = cat.accelerator()
    return accels


def remove_accel_text (text, msg, cat):
    """
    Remove accelerator marker from one of the text fields of the message
    [type F3A hook].

    Accelerator marker is determined from the catalog, by calling its
    L{accelerator()<pology.catalog.Catalog.accelerator>} method.
    Use L{set_accelerator()<pology.catalog.Catalog.set_accelerator>}
    to set possible accelerator markers after the catalog has been opened,
    in case it does not specify any on its own.
    If catalog reports C{None} for accelerators, text is not touched.

    Accelerator marker can also be specified for a particular message,
    by embedded C{accelerator-marker} field in manual comments::

        # accelerator-marker: _

    This overrides accelerator marker reported by the catalog.

    @return: text

    @see: L{pology.resolve.remove_accelerator}
    """

    accels = _get_accel_marker(msg, cat)
    return _rm_accel_in_text(text, accels)


def remove_accel_text_greedy (text, msg, cat):
    """
    Like L{remove_accel_text}, except that if catalog reports C{None}
    for accelerators, some frequent marker characters are removed
    [type F3A hook].

    @return: text

    @see: L{pology.resolve.remove_accelerator}
    """

    accels = _get_accel_marker(msg, cat)
    return _rm_accel_in_text(text, accels, greedy=True)


def remove_accel_msg (msg, cat):
    """
    Remove accelerator marker from all applicable text fields in the message,
    as if L{remove_accel_text} was applied to each [type F4A hook].

    @return: number of errors

    @see: L{pology.resolve.remove_accelerator}
    """

    accels = _get_accel_marker(msg, cat)
    return _rm_accel_in_msg(msg, accels)


def remove_accel_msg_greedy (msg, cat):
    """
    Like L{remove_accel_msg}, except that if catalog reports C{None}
    for accelerators, some frequent marker characters are removed
    [type F4A hook].

    @return: number of errors

    @see: L{pology.resolve.remove_accelerator}
    """

    accels = _get_accel_marker(msg, cat)
    return _rm_accel_in_msg(msg, accels, greedy=True)


def _rm_markup_in_text (text, mtypes):

    if mtypes is None:
        return text

    for mtype in mtypes:
        mtype = mtype.lower()
        if 0: pass
        elif mtype == "html":
            text = M.html_to_plain(text)
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
        elif mtype == "xmlents":
            # FIXME: Only default XML entities can be handled as-is;
            # perhaps markup remover should also take entity mapping
            # as argument, and pass it here?
            text = resolve_entities_simple(text, M.xml_entities)

    return text


def _rm_markup_in_msg (msg, mtypes):

    msg.msgid = _rm_markup_in_text(msg.msgid, mtypes)
    if msg.msgid_plural:
        msg.msgid_plural = _rm_markup_in_text(msg.msgid_plural, mtypes)
    for i in range(len(msg.msgstr)):
        msg.msgstr[i] = _rm_markup_in_text(msg.msgstr[i], mtypes)

    if msg.msgid_previous:
        msg.msgid_previous = _rm_markup_in_text(msg.msgid_previous, mtypes)
    if msg.msgid_plural_previous:
        msg.msgid_plural_previous = _rm_markup_in_text(msg.msgid_plural_previous,
                                                       mtypes)
    return 0


def remove_markup_text (text, msg, cat):
    """
    Remove markup from one of the text fields of the message [type F3A hook].

    Expected markup types are determined from the catalog, by calling its
    L{markup()<pology.catalog.Catalog.markup>} method.
    Use L{set_markup()<catalog.Catalog.set_markup>}
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
    if msg.msgid_plural:
        msg.msgid_plural = _rm_fmtd_in_text(msg.msgid_plural, formats, subs)
    for i in range(len(msg.msgstr)):
        msg.msgstr[i] = _rm_fmtd_in_text(msg.msgstr[i], formats, subs)

    if msg.msgid_previous:
        msg.msgid_previous = _rm_fmtd_in_text(msg.msgid_previous, formats, subs)
    if msg.msgid_plural_previous:
        msg.msgid_plural_previous = _rm_fmtd_in_text(msg.msgid_plural_previous,
                                                     formats, subs)
    return 0


def remove_fmtdirs_text (text, msg, cat):
    """
    Remove format directives from one of the text fields of the message
    [type F3A hook].

    The type of format directives is determined from message format flags.

    @return: text

    @see: L{pology.resolve.remove_fmtdirs}
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
                rxs.append(re.compile(rx_str, re.U|re.S))
            except:
                warning_on_msg(_("@info",
                                 "Field %(field)s states "
                                 "malformed regex '%(re)s'.",
                                 field=fname, re=rx_str),
                                 msg, cat)
        else:
            heuristic = False

    return [], rxs, heuristic


def _rm_lit_in_text (text, substrs, regexes, heuristic, subs=""):

    return _rm_lit_in_text_single(text, subs=subs, substrs=substrs,
                                  regexes=regexes, heuristic=heuristic)


def _rm_lit_in_msg (msg, cat, strs, rxs, heu, subs=""):

    msg.msgid = _rm_lit_in_text(msg.msgid, strs, rxs, heu, subs)
    if msg.msgid_plural:
        msg.msgid_plural = _rm_lit_in_text(msg.msgid_plural,
                                           strs, rxs, heu, subs)
    for i in range(len(msg.msgstr)):
        msg.msgstr[i] = _rm_lit_in_text(msg.msgstr[i], strs, rxs, heu, subs)

    if msg.msgid_previous:
        msg.msgid_previous = _rm_lit_in_text(msg.msgid_previous,
                                             strs, rxs, heu, subs)
    if msg.msgid_plural_previous:
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

    @see: L{pology.resolve.remove_literals}
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

    strs, rxs, heu = _literals_spec(msg, cat)
    return _rm_lit_in_msg(msg, cat, strs, rxs, heu)


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
        strs, rxs, heu = _literals_spec(msg, cat)
        return _rm_lit_in_msg(msg, cat, strs, rxs, heu, tick)

    return hook


def remove_marlits_text (text, msg, cat):
    """
    Remove literals by markup from one of the text fields of the message
    [type F3A hook].

    An "intersection" of L{remove_markup_text} and L{remove_literals_text},
    where literals segments are determined by markup, and both the segment text
    and its markup is removed. See documentation of these hooks for notes
    on what is considered literal and how markup type is determined.

    @return: text
    """

    strs, rxs, heu = [], _marlit_rxs(msg, cat), False
    return _rm_lit_in_text(text, strs, rxs, heu)


def remove_marlits_msg (msg, cat):
    """
    Remove literal segments by markup from all applicable text fields in
    the message, as if L{remove_marlits_text} was applied to each
    [type F4A hook].

    @return: number of errors
    """

    strs, rxs, heu = [], _marlit_rxs(msg, cat), False
    return _rm_lit_in_msg(msg, cat, strs, rxs, heu)


class _Cache: pass
_marlit_cache = _Cache()
_marlit_cache.mtypes = None
_marlit_cache.tags = set()
_marlit_cache.rxs = []
_marlit_cache.acmnt_tag_rx = re.compile(r"^\s*tag:\s*(\w+)\s*$", re.I)
_marlit_cache.rxs_all = [re.compile(r".*", re.S)]

def _marlit_rxs (msg, cat):

    # Update regex cache due to markup type.
    mtypes = cat.markup()
    if _marlit_cache.mtypes != mtypes:
        _marlit_cache.mtypes = mtypes
        _marlit_cache.tags = set()
        _marlit_cache.rxs = []
        for mtype in mtypes or []:
            _marlit_cache.tags.update(_marlit_tags(mtype))
            rx = _build_tagged_rx(_marlit_cache.tags)
            _marlit_cache.rxs.append(rx)

    # Check if the whole message is under a literal tag.
    for acmnt in msg.auto_comment:
        m = _marlit_cache.acmnt_tag_rx.search(acmnt)
        if m:
            tag = m.group(1).strip().lower()
            if tag in _marlit_cache.tags:
                return _marlit_cache.rxs_all

    return _marlit_cache.rxs


def _marlit_tags (mtype):

    tags = ""
    if 0: pass
    elif mtype == "html":
        tags = """
            tt code
        """
    elif mtype == "kde4":
        tags = """
            icode bcode filename envar command numid
            tt code
        """
    elif mtype == "qtrich":
        tags = """
            tt code
        """
    elif mtype == "kuit":
        tags = """
            icode bcode filename envar command numid
        """
    elif mtype == "docbook4" or mtype == "docbook":
        tags = """
            literal filename envar command option function markup varname
            screen programlisting userinput computeroutput
        """
    elif mtype == "xml":
        pass

    return set(tags.split())


def _build_tagged_rx (tags):

    if isinstance(tags, str):
        tags = tags.split()
    # For proper regex matching, tags that begin with a substring
    # equal to another full tag must come before that full tag.
    # So sort tags first by length, then by alphabet.
    tags = sorted(tags, key=lambda x: (-len(x), x))
    basetagged_rxsub = r"<\s*(%s)\b[^<]*>.*?<\s*/\s*\1\s*>"
    tagged_rx = re.compile(basetagged_rxsub % "|".join(tags), re.I|re.S)

    return tagged_rx


def remove_ignored_entities_msg (msg, cat):
    """
    Remove locally ignored entities from all applicable text fields in
    the message [type F4A hook].

    Entities are ignored by listing them in the embedded C{ignore-entities}
    fields in manual comments. For example::

        # ignore-entity: foobar, froobaz

    will remove entities C{&foobar;} and C{&froobaz;} from all text fields.

    @return: number of errors
    """

    locally_ignored = manc_parse_list(msg, "ignore-entity:", ",")
    if not locally_ignored:
        return 0

    msg.msgid = _rm_ent_in_text(msg.msgid, locally_ignored)
    if msg.msgid_plural:
        msg.msgid_plural = _rm_ent_in_text(msg.msgid_plural, locally_ignored)
    for i in range(len(msg.msgstr)):
        msg.msgstr[i] = _rm_ent_in_text(msg.msgstr[i], locally_ignored)

    return 0


def _rm_ent_in_text (text, entities):

    for entity in entities:
        text = text.replace("&%s;" % entity, "")

    return text


def rewrite_msgid (msg, cat):
    """
    Rewrite parts of C{msgid} based on translator comments [type F4A hook].

    Translator comments may issue C{rewrite-msgid} directives
    to modify parts of C{msgid} (as well as C{msgid_plural}) fields
    by applying a search regular expression and replace pattern.
    The search and replace pattern are wrapped and separated
    by any character consistently used, such as slashes.
    Examples::

        # rewrite-msgid: /foo/bar/
        # rewrite-msgid: /foo (\\w+) fam/bar \\1 bam/
        # rewrite-msgid: :foo/bar:foo/bam:

    If a search pattern is not valid, a warning on message is issued.

    Search pattern is case-sensitive.

    @return: number of errors
    """

    nerrors = 0

    # Collect and compile regular expressions.
    fname = "rewrite-msgid"
    rwspecs = manc_parse_field_values(msg, fname)
    rwrxs = []
    for rwspec in rwspecs:
        sep = rwspec[0:1]
        if not sep:
            warning_on_msg(_("@info",
                             "No patterns in rewrite directive."), msg, cat)
            nerrors += 1
            continue
        lst = rwspec.split(sep)
        if len(lst) != 4 or lst[0] or lst[3]:
            warning_on_msg(_("@info",
                             "Wrongly separated patterns in "
                             "rewrite directive '%(dir)s'.", dir=rwspec),
                             msg, cat)
            nerrors += 1
            continue
        srch, repl = lst[1], lst[2]
        try:
            rx = re.compile(srch, re.U)
        except:
            warning_on_msg(_("@info",
                             "Invalid search pattern in "
                             "rewrite directive '%(dir)s'.", dir=rwspec),
                             msg, cat)
            nerrors += 1
            continue
        rwrxs.append((rx, repl, rwspec))

    for rx, repl, rwspec in rwrxs:
        try:
            msg.msgid = rx.sub(repl, msg.msgid)
            if msg.msgid_plural is not None:
                msg.msgid_plural = rx.sub(repl, msg.msgid_plural)
        except:
            warning_on_msg(_("@info",
                             "Error in application of "
                             "rewrite directive '%(dir)s'.", dir=rwspec),
                             msg, cat)
            nerrors += 1

    return nerrors


def rewrite_inverse (msg, cat):
    """
    Rewrite message by replacing all its elements with that of another message
    which has the same C{msgstr[0]} [type F4A hook].

    Translator comments may issue C{rewrite-inverse} directives
    to replace all message parts with those from another message
    having the same C{msgstr[0]} field.
    The argument to the directive is a regular expression search pattern
    on C{msgid} and C{msgctxt} (leading and trailing whitespace get stripped)
    which is used to select the particular message if more than
    one other messages have same C{msgstr[0]}.
    Examples::

        # rewrite-inverse:
        # rewrite-inverse: Foo

    If the pattern does not match or it matches more than one other message,
    current message is not touched; also if the pattern
    is left empty and there is more than one other message.
    Search pattern is applied to C{msgctxt} and C{msgid} in turn,
    and the message is matched if any matches.
    Search pattern is case-sensitive.

    If more than one C{rewrite-inverse} directive is seen,
    or the search pattern is not valid, a warning on message is issued
    and current message is not touched.

    This hook is then executed again on the resulting message,
    in case the new translator comments contain another
    C{rewrite-inverse} directive.

    @return: number of errors
    """

    # Collect and compile regular expressions.
    fname = "rewrite-inverse"
    rwspecs = manc_parse_field_values(msg, fname)
    if not rwspecs:
        return 0
    if len(rwspecs) > 1:
        warning_on_msg(_("@info",
                         "More than one inverse rewrite directive "
                         "encountered."),
                       msg, cat)
        return 1

    srch = rwspecs[0]
    try:
        rx = re.compile(srch, re.U)
    except:
        warning_on_msg(_("@info",
                         "Invalid search pattern '%(pattern)s' in "
                         "inverse rewrite directive.", pattern=srch),
                       msg, cat)
        return 1

    msgs = cat.select_by_msgstr(msg.msgstr[0], lazy=True)
    msgs = [x for x in msgs if x.key != msg.key] # remove current
    if not msgs:
        warning_on_msg(_("@info",
                         "There are no other messages with same translation, "
                         "needed by inverse rewrite directive."),
                       msg, cat)
        return 1

    match = lambda x: (   (x.msgctxt is not None and rx.search(x.msgctxt))
                       or rx.search(x.msgid))
    sel_msgs = [x for x in msgs if match(x)] # remove non-matched
    if not sel_msgs:
        warning_on_msg(_("@info",
                         "Inverse rewrite directive matches none of "
                         "the other messages with same translation."),
                       msg, cat)
        return 1
    if len(sel_msgs) > 1:
        warning_on_msg(_("@info",
                         "Inverse rewrite directive matches more than "
                         "one other message with same translation."),
                       msg, cat)
        return 1

    # Copy all parts of the other message.
    omsg = sel_msgs[0]
    msg.msgid = omsg.msgid
    if msg.msgid_plural is not None and omsg.msgid_plural is not None:
        msg.msgid_plural = omsg.msgid_plural

    # Copy comments and recurse.
    msg.set(omsg)
    nerrors = rewrite_inverse(msg, cat)

    return nerrors


_ent_rx = re.compile(r"&[\w.:-]+;", re.U)

def remove_paired_ents (msg, cat):
    """
    Remove all XML-like entities from original, and from translation
    all that are also found in original [type F4A hook].

    To remove all entities from original, and all entitities from translation
    that also exist in original, may be useful prior to markup checks,
    when list of known entities is not available.

    @return: number of errors
    """

    return _rm_paired_ents(msg, cat)


def remove_paired_ents_tick (tick):
    """
    Like L{remove_paired_ents}, except that each XML-like entity is
    replaced by a non-whitespace "tick" instead of plainly removed
    [hook factory].

    @param tick: the tick sequence
    @type tick: string

    @return: type F3A hook
    @rtype: C{(cat, msg, text) -> text}
    """

    def hook (msg, cat):
        return _rm_paired_ents(msg, cat, tick)

    return hook


def _rm_paired_ents (msg, cat, tick=''):

    ents_orig = set()
    ents_orig.update(_ent_rx.findall(msg.msgid))
    for ent in ents_orig:
        msg.msgid = msg.msgid.replace(ent, tick)

    if msg.msgid_plural:
        ents_orig.update(_ent_rx.findall(msg.msgid_plural))
        for ent in ents_orig:
            msg.msgid_plural = msg.msgid_plural.replace(ent, tick)

    for i in range(len(msg.msgstr)):
        ents_trans = set(_ent_rx.findall(msg.msgstr[i]))
        for ent in ents_trans.intersection(ents_orig):
            msg.msgstr[i] = msg.msgstr[i].replace(ent, tick)

    return 0

