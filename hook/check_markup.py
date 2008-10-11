# -*- coding: UTF-8 -*-

"""
Check validity of text markup.
"""

import pology.misc.markup as M
from pology.misc.comments import manc_parse_flag_list
from pology.misc.entities import read_entities_by_env, fcap_entities
from pology.misc.report import warning


# Pipe flag used to manually prevent check for a particular message.
flag_no_check_xml = "no-check-xml"


def check_xml (strict=False, entities={}, entpathenv=None, fcap=True):
    """
    Check general XML markup in translations.

    Text is only checked to be well-formed XML, and possibly also whether
    encountered entities are defined. Markup errors are reported to stdout.

    C{msgstr} can be either checked only if the C{msgid} is valid itself,
    or regardless of the validity of the original. This is governed by the
    C{strict} parameter.

    A (name, value) dictionary of entities, in addition to XML's default
    (C{&lt;}, etc.), may be provided using the C{entities} parameter.
    If it is given as C{None}, entities are ignored by the check.

    Entities may also be automatically collected, by parsing all C{*.entities}
    files in directory paths given by the environment variable C{entpathenv};
    entity files are searched for recursively down each directory path.
    See L{parse_entities<misc.entities.parse_entities>} for the format of
    C{*.entities} files.

    If an entity with the first letter in uppercase is encountered and not
    among the defined ones, it may be allowed to pass the check by setting
    the C{fcap} parameter to C{True}.

    If the message has L{pipe flag<pology.misc.comments.manc_parse_flag_list>}
    C{no-check-xml}, the check is skipped.

    @param strict: whether to require valid C{msgstr} even if C{msgid} is not
    @type strict: bool
    @param entities: additional entities to consider as known
    @type entities: dict or C{None}
    @param entpathenv: environment variable with paths to entity definitions
    @type entpathenv: string
    @param fcap: whether to allow first-uppercase entities
    @type fcap: bool

    @note: Hook type factory: C{(cat, msg, text) -> None}
    """

    return _check_xml_w(M.check_xml_l1,
                        strict, entities, entpathenv, fcap, False)


def check_xml_sp (strict=False, entities=None, entpathenv=None, fcap=False):
    """
    Like L{check_xml_kde4}, except that erroneous spans are returned
    instead of reporting problems to stdout.

    @note: Hook type factory: C{(cat, msg, text) -> spans}
    """

    return _check_xml_w(M.check_xml_l1,
                        strict, entities, entpathenv, fcap, True)


def check_xml_kde4 (strict=False, entities={}, entpathenv=None, fcap=True):
    """
    Check XML markup in translations of KDE4 UI catalogs.

    See L{check_xml} for description of parameters.

    @note: Hook type factory: C{(cat, msg, text) -> None}
    """

    return _check_xml_w(M.check_xml_kde4_l1,
                        strict, entities, entpathenv, fcap, False)


def check_xml_kde4_sp (strict=False, entities={}, entpathenv=None, fcap=False):
    """
    Like L{check_xml_kde4}, except that erroneous spans are returned
    instead of reporting problems to stdout.

    @note: Hook type factory: C{(cat, msg, text) -> spans}
    """

    return _check_xml_w(M.check_xml_kde4_l1,
                        strict, entities, entpathenv, fcap, True)


def check_xml_docbook4 (strict=False, entities={}, entpathenv=None, fcap=True):
    """
    Check XML markup in translations of Docbook 4.x catalogs.

    See L{check_xml} for description of parameters.

    @note: Hook type factory: C{(cat, msg, text) -> None}
    """

    return _check_xml_w(M.check_xml_docbook4_l1,
                        strict, entities, entpathenv, fcap, False)


def check_xml_docbook4_sp (strict=False, entities={}, entpathenv=None, fcap=False):
    """
    Like L{check_xml_docbook4}, except that erroneous spans are returned
    instead of reporting problems to stdout.

    @note: Hook type factory: C{(cat, msg, text) -> spans}
    """

    return _check_xml_w(M.check_xml_docbook4_l1,
                        strict, entities, entpathenv, fcap, True)


def check_xml_qtrich (strict=False, entities={}, entpathenv=None, fcap=True):
    """
    Check Qt rich-text markup in translations.

    See L{check_xml} for description of parameters.
    See notes on checking Qt rich-text to
    L{check_xml_qtrich_l1<misc.markup.check_xml_qtrich_l1>}.

    @note: Hook type factory: C{(cat, msg, text) -> None}
    """

    return _check_xml_w(M.check_xml_qtrich_l1,
                        strict, entities, entpathenv, fcap, False)


def check_xml_qtrich_sp (strict=False, entities={}, entpathenv=None, fcap=False):
    """
    Like L{check_xml_qtrich}, except that erroneous spans are returned
    instead of reporting problems to stdout.

    @note: Hook type factory: C{(cat, msg, text) -> spans}
    """

    return _check_xml_w(M.check_xml_qtrich_l1,
                        strict, entities, entpathenv, fcap, True)


def _check_xml_w (check, strict, entities, entpathenv, fcap, spanrep):
    """
    Worker for C{check_xml*} hook factories.
    """

    entities = _read_combine_entities(entities, entpathenv, fcap)

    if strict:
        def hook (cat, msg, msgstr):
            if flag_no_check_xml in manc_parse_flag_list(msg, "|"):
                if spanrep: return ([],)
                else: return
            spans = check(msgstr, ents=entities)
            if spanrep:
                return (spans,)
    else:
        def hook (cat, msg, msgstr):
            if (   flag_no_check_xml in manc_parse_flag_list(msg, "|")
                or check(msg.msgid, ents=entities)
                or check(msg.msgid_plural, ents=entities)
            ):
                if spanrep: return ([],)
                else: return
            spans = check(msgstr, ents=entities)
            if spanrep:
                return (spans,)

    return hook


def _read_combine_entities (entities, entpathenv, fcap):

    if entpathenv is not None:
        tmp_entities = read_entities_by_env(entpathenv)
        # Give lower priority to read entities in case of conflicts.
        if entities is not None:
            tmp_entities.update(entities)
        entities = tmp_entities
    if fcap and entities is not None:
        tmp_entities = fcap_entities(entities)
        tmp_entities.update(entities)
        entities = tmp_entities

    return entities

