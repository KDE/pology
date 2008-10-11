# -*- coding: UTF-8 -*-

"""
Check validity of text markup.
"""

import os
import glob

from pology.misc.comments import manc_parse_flag_list
from pology.misc.markup import check_xml_kde4_l1
from pology.sieve.check_xml_kde4 import flag_no_check_xml
from pology.misc.resolve import read_entities
from pology.misc.report import warning


def check_xml_kde4 (strict=False, entities={}, entpathenv=None, fcap=True):
    """
    Check XML markup in translations of KDE4 UI catalogs.

    Markup errors are reported to stdout.

    If the check is not strict, C{msgstr} is checked only if C{msgid} itself
    is valid XML markup in KDE4 UI.

    A dictionary of external XML entities (name, value) may be provided
    if such appear in the translation, for the check not to warn about
    unknown entities.
    Entities may also be automatically collected, by parsing all C{*.entities}
    files in directory paths given by the environment variable C{entpathenv};
    entity files are taken only from the roots of directory paths,
    and not recursively searched for.
    If an entity with the first letter in uppercase is encountered and not
    among the defined ones, it may be allowed to pass the check by setting
    the C{fcap} parameter to C{True}.

    If the message has L{pipe flag<pology.misc.comments.manc_parse_flag_list>}
    C{no-check-xml}, the check is skipped.

    @param strict: whether to require valid C{msgstr} even if C{msgid} is not
    @type strict: bool
    @param entities: additional entities to consider as known
    @type entities: dict
    @param entpathenv: environment variable with paths to entity definitions
    @type entpathenv: string
    @param fcap: whether to allow first-uppercase entities
    @type fcap: bool

    @note: Hook type factory: C{(cat, msg, text) -> None}
    """

    return _check_xml_kde4_w(strict, entities, entpathenv, fcap, False)


def check_xml_kde4_sp (strict=False, entities={}, entpathenv=None, fcap=False):
    """
    Like L{check_xml_kde4}, except that erroneous spans are returned
    instead of reporting problems to stdout.

    @note: Hook type factory: C{(cat, msg, text) -> spans}
    """

    return _check_xml_kde4_w(strict, entities, entpathenv, fcap, True)


def _check_xml_kde4_w (strict, entities, entpathenv, fcap, spanrep):
    """
    Worker for C{check_xml_kde4*} hook factories.
    """

    if entpathenv is not None:
        entpath = os.getenv(entpathenv)
        if entpath is None:
            warning("expected environment variable %s not set" % entpathenv)
        else:
            entities_by_arg = entities # add in the end, has higher priority
            entities = {}
            for path in entpath.split(":"):
                pattern = os.path.join(path, "*.entities")
                entities.update(read_entities(*glob.glob(pattern)))
            entities.update(entities_by_arg)
    if fcap:
        fcap_entities = {}
        for name, value in entities.iteritems():
            cname = name[:1].upper() + name[1:]
            fcap_entities[cname] = value
        entities.update(fcap_entities)

    if strict:
        def hook (cat, msg, msgstr):
            if flag_no_check_xml in manc_parse_flag_list(msg, "|"):
                if spanrep: return ([],)
                else: return
            spans = check_xml_kde4_l1(msgstr, ents=entities)
            if spanrep:
                return (spans,)
    else:
        def hook (cat, msg, msgstr):
            if (   flag_no_check_xml in manc_parse_flag_list(msg, "|")
                or check_xml_kde4_l1(msg.msgid, ents=entities)
                or check_xml_kde4_l1(msg.msgid_plural, ents=entities)
            ):
                if spanrep: return ([],)
                else: return
            spans = check_xml_kde4_l1(msgstr, ents=entities)
            if spanrep:
                return (spans,)

    return hook

