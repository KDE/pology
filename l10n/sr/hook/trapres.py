# -*- coding: UTF-8 -*

"""
Resolve trapnakron references in translations.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

from pology.misc.markup import xml_entities, html_entities
from pology.misc.resolve import resolve_entities
from pology.misc.comments import manc_parse_list
import pology.l10n.sr.trapnakron as T


_known_cons = {}
def _get_names ():
    _known_cons[""] = T.trapnakron # base constructor
    for name in dir(T): # specialized constructors
        if name.startswith("trapnakron_"):
            _known_cons[name[len("trapnakron_"):]] = getattr(T, name)
_get_names()


def froments (name, args=(), kwargs={}, fmtref=None):
    """
    Resolve trapnakron references in translation using XML entity format
    [hook factory].

    If an entity cannot be resolved as trapnakron reference,
    warning is output and translation is not changed.

    Entities in a given message can be manually ignored through
    C{ignore-entity:} translation comment, which contains
    comma-separated list of entity names::

        # ignore-entity: foo, bar
        msgid "Blah, blah, &foo;, blah, blah, &bar;."
        msgstr "Бла, бла, &foo;, бла, бла, &bar;."

    Standard XML and HTML entities are ignored by default.

    @param name: suffix of trapnakron constructor,
        e.g. "ui" for L{trapnakron_ui<l10n.sr.trapnakron.trapnakron_ui>}
    @type name: string
    @param args: positional arguments to send to the constructor
    @type args: tuple
    @param kwargs: keyword arguments to send to the constructor
    @type kwargs: dict
    @param fmtref: format string (with single C{%s} directive) or function
        to apply to every resolved reference
    @type fmtref: string or (string)->string

    @return: type F3C hook
    @rtype: C{(msgstr, msg, cat) -> msgstr}
    """

    trapcon = _known_cons.get(name)
    if trapcon is None:
        raise KeyError("Unknown trapnakron constructor '%s'." % name)

    tp = trapcon(*args, **kwargs)

    # Entitites normally ignored on resolution.
    # FIXME: This should go by markup type advertised in catalog header.
    ignored_refs = {}
    ignored_refs.update(xml_entities)
    ignored_refs.update(html_entities)

    def hook (msgstr, msg, cat):

        srcstr = "%s:%d(%d)" % (cat.filename, msg.refline, msg.refentry)

        locally_ignored = manc_parse_list(msg, "ignore-entity:", ",")
        if locally_ignored:
            ignored_refs_mod = ignored_refs.copy()
            ignored_refs_mod.update([(x, None) for x in locally_ignored])
        else:
            ignored_refs_mod = ignored_refs

        res = resolve_entities(msgstr, tp, ignored_refs_mod,
                               srcname=srcstr, vfilter=fmtref)
        msgstr, resolved, unknown = res

        return msgstr

    return hook

