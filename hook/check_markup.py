# -*- coding: UTF-8 -*-

"""
Check validity of text markup.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import pology.misc.markup as M
from pology.misc.comments import manc_parse_flag_list
from pology.misc.report import warning
from pology.misc.msgreport import report_on_msg
from pology.misc.langdep import get_result_lreq


# Pipe flag used to manually prevent check for a particular message.
flag_no_check_xml = "no-check-xml"


def check_xml (strict=False, entities={}, mkeyw=None):
    """
    Check general XML markup in translations [hook factory].

    Text is only checked to be well-formed XML, and possibly also whether
    encountered entities are defined. Markup errors are reported to stdout.

    C{msgstr} can be either checked only if the C{msgid} is valid itself,
    or regardless of the validity of the original. This is governed by the
    C{strict} parameter.

    Entities in addition to XML's default (C{&lt;}, etc.)
    may be provided using the C{entities} parameter.
    Several types of values with different semantic are possible:
      - if C{entities} is C{None}, unknown entities are ignored on checking
      - if string, it is understood as a general function evaluation
        L{request<misc.langdep.get_result_lreq>},
        and its result expected to be (name, value) dictionary-like object
      - otherwise, C{entities} is considered to be a
        (name, value) dictionary-like object as it is

    If a message has L{pipe flag<pology.misc.comments.manc_parse_flag_list>}
    C{no-check-xml}, the check is skipped for that message.
    If one or several markup keywords are given as C{mkeyw} parameter,
    check is skipped for all messages in a catalog which does not report
    one of the given keywords by its L{markup()<file.catalog.Catalog.markup>}
    method. See L{set_markup()<file.catalog.Catalog.set_markup>} for list of
    markup keywords recognized at the moment.

    @param strict: whether to require valid C{msgstr} even if C{msgid} is not
    @type strict: bool
    @param entities: additional entities to consider as known
    @type entities: C{None}, dict, or string
    @param mkeyw: markup keywords for taking catalogs into account
    @type mkeyw: string or list of strings

    @return: type S3C hook
    @rtype: C{(msgstr, msg, cat) -> numerr}
    """

    return _check_xml_w(M.check_xml_l1, strict, entities, mkeyw, False)


def check_xml_sp (strict=False, entities={}, mkeyw=None):
    """
    Like L{check_xml_kde4}, except that erroneous spans are returned
    instead of reporting problems to stdout [hook factory].

    @return: type V3C hook
    @rtype: C{(msgstr, msg, cat) -> spans}
    """

    return _check_xml_w(M.check_xml_l1, strict, entities, mkeyw, True)


def check_xml_kde4 (strict=False, entities={}, mkeyw=None):
    """
    Check XML markup in translations of KDE4 UI catalogs [hook factory].

    See L{check_xml} for description of parameters.

    @return: type S3C hook
    @rtype: C{(msgstr, msg, cat) -> numerr}
    """

    return _check_xml_w(M.check_xml_kde4_l1, strict, entities, mkeyw, False)


def check_xml_kde4_sp (strict=False, entities={}, mkeyw=None):
    """
    Like L{check_xml_kde4}, except that erroneous spans are returned
    instead of reporting problems to stdout [hook factory].

    @return: type V3C hook
    @rtype: C{(msgstr, msg, cat) -> spans}
    """

    return _check_xml_w(M.check_xml_kde4_l1, strict, entities, mkeyw, True)


def check_xml_docbook4 (strict=False, entities={}, mkeyw=None):
    """
    Check XML markup in translations of Docbook 4.x catalogs [hook factory].

    See L{check_xml} for description of parameters.

    @return: type S3C hook
    @rtype: C{(msgstr, msg, cat) -> numerr}
    """

    return _check_xml_w(M.check_xml_docbook4_l1, strict, entities, mkeyw, False)


def check_xml_docbook4_sp (strict=False, entities={}, mkeyw=None):
    """
    Like L{check_xml_docbook4}, except that erroneous spans are returned
    instead of reporting problems to stdout [hook factory].

    @return: type V3C hook
    @rtype: C{(msgstr, msg, cat) -> spans}
    """

    return _check_xml_w(M.check_xml_docbook4_l1, strict, entities, mkeyw, True)


def check_xml_html (strict=False, entities={}, mkeyw=None):
    """
    Check HTML markup in translations [hook factory].

    See L{check_xml} for description of parameters.
    See notes on checking HTML markup to
    L{check_xml_html_l1<misc.markup.check_xml_html_l1>}.

    @return: type S3C hook
    @rtype: C{(msgstr, msg, cat) -> numerr}
    """

    return _check_xml_w(M.check_xml_html_l1, strict, entities, mkeyw, False)


def check_xml_html_sp (strict=False, entities={}, mkeyw=None):
    """
    Like L{check_xml_html}, except that erroneous spans are returned
    instead of reporting problems to stdout [hook factory].

    @return: type V3C hook
    @rtype: C{(msgstr, msg, cat) -> spans}
    """

    return _check_xml_w(M.check_xml_html_l1, strict, entities, mkeyw, True)


def check_xml_qtrich (strict=False, entities={}, mkeyw=None):
    """
    Check Qt rich-text markup in translations [hook factory].

    See L{check_xml} for description of parameters.
    See notes on checking Qt rich-text to
    L{check_xml_qtrich_l1<misc.markup.check_xml_qtrich_l1>}.

    @return: type S3C hook
    @rtype: C{(msgstr, msg, cat) -> numerr}
    """

    return _check_xml_w(M.check_xml_qtrich_l1, strict, entities, mkeyw, False)


def check_xml_qtrich_sp (strict=False, entities={}, mkeyw=None):
    """
    Like L{check_xml_qtrich}, except that erroneous spans are returned
    instead of reporting problems to stdout [hook factory].

    @return: type V3C hook
    @rtype: C{(msgstr, msg, cat) -> spans}
    """

    return _check_xml_w(M.check_xml_qtrich_l1, strict, entities, mkeyw, True)


def check_xmlents (strict=False, entities={}, mkeyw=None, numeric=False):
    """
    Check existence of XML entities in translations [hook factory].

    See L{check_xml} for description of parameters.
    See notes on checking of entities to
    L{check_xmlents<misc.markup.check_xmlents>}.

    @return: type S3C hook
    @rtype: C{(msgstr, msg, cat) -> numerr}
    """

    return _check_xml_w(M.check_xmlents, strict, entities, mkeyw, False)


def check_xmlents_sp (strict=False, entities={}, mkeyw=None):
    """
    Like L{check_xmlents}, except that erroneous spans are returned
    instead of reporting problems to stdout [hook factory].

    @return: type V3C hook
    @rtype: C{(msgstr, msg, cat) -> spans}
    """

    return _check_xml_w(M.check_xmlents, strict, entities, mkeyw, True)


def _check_xml_w (check, strict, entities, mkeyw, spanrep):
    """
    Worker for C{check_xml*} hook factories.
    """

    if mkeyw is not None:
        if isinstance(mkeyw, basestring):
            mkeyw = [mkeyw]
        mkeyw = set(mkeyw)

    # Lazy-evaluated data.
    ldata = {}
    def eval_ldata ():
        ldata["entities"] = _get_entities(entities)

    def hook (msgstr, msg, cat):

        if (    mkeyw is not None
            and not mkeyw.intersection(cat.markup() or set())
        ):
            return (spanrep and [[]] or [0])[0]

        if not ldata:
            eval_ldata()
        entities = ldata["entities"]

        if (   flag_no_check_xml in manc_parse_flag_list(msg, "|")
            or (    not strict
                and (   check(msg.msgid, ents=entities)
                     or check(msg.msgid_plural or u"", ents=entities)))
        ):
            return (spanrep and [[]] or [0])[0]
        spans = check(msgstr, ents=entities)
        if spanrep:
            return spans
        else:
            for span in spans:
                if span[2:]:
                    report_on_msg(span[2], msg, cat)
            return len(spans)

    return hook


# Cache for loaded entities, by entity specification string,
# to speed up when several markup hooks are using the same setup.
_loaded_entities_cache = {}

def _get_entities (entspec):

    if not isinstance(entspec, basestring):
        return entspec

    entities = _loaded_entities_cache.get(entspec)
    if entities is not None:
        return entities

    entities = get_result_lreq(entspec)

    _loaded_entities_cache[entspec] = entities
    return entities

