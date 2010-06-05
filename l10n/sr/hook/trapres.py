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


def froments (name, args=(), kwargs={}, vfilter=None, testsub=False):
    """
    Resolve trapnakron references in translation using XML entity format
    [hook factory].

    If an entity cannot be resolved as trapnakron reference,
    warning is output and the entity is left unresolved.
    Instead of leaving the entity unresolved, an illustrative expansion
    for the property key given by the reference can be substituted
    by setting the C{testsub} parameter to C{True}.

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
    @param vfilter: format string (with single C{%s} directive) or function
        to apply to every resolved reference
    @type vfilter: string or (string)->string
    @param testsub: whether to substitute test forms in place of
        undefined references
    @type testsub: bool

    @return: type F3C hook
    @rtype: C{(msgstr, msg, cat) -> msgstr}
    """

    trapcon = _known_cons.get(name)
    if trapcon is None:
        raise KeyError(
            _("@info \"trapnakron\" is a shorthand for "
              "\"Transcriptions and Translations of Names and Acronyms\" "
              "in Serbian",
              "Unknown trapnakron constructor '%(name)s'.")
            % dict(name=name))

    tp = trapcon(*args, **kwargs)

    # Setup dummy replacement for undefined references.
    undefrepl = None
    if testsub:
        dkeysub1 = "__test1234a__"
        dkeysub2 = "__test1234b__"
        tp.import_string(u"""
        >%s/base/aff.sd
        %s: лопт|а, лопт|е+2, лопт|ин, лопта|сти
        %s: ваљ|ак, ваљ|ци+, ваљк|ов, ваљка|сти
        """ % (T.rootdir(), dkeysub1, dkeysub2))
        def undefrepl (ref):
            res = ref.rsplit("-", 1)
            if len(res) != 2:
                return None
            dkey, pkey = res
            if pkey == "":
                pkey = "n"
            dkeysub = dkeysub1
            if len(pkey) == 2 and pkey.endswith("k"):
                dkeysub = dkeysub2
            ckeysub = dkeysub + "-" + pkey
            return tp[ckeysub].upper()

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
                               srcname=srcstr, vfilter=vfilter,
                               undefrepl=undefrepl)
        msgstr, resolved, unknown = res

        return msgstr

    return hook


_froments_t1_hook = None

def froments_t1 (msgstr, msg, cat):
    """
    A testing specialization of L{froments}: C{name="ui"},
    C{vfilter="^%s"}, C{testsub=True} [type F3C hook].
    """

    global _froments_t1_hook
    if not _froments_t1_hook:
        _froments_t1_hook = froments("ui", vfilter=u"^%s", testsub=True)

    return _froments_t1_hook(msgstr, msg, cat)


def froments_t1db (msgstr, msg, cat):
    """
    A testing specialization of L{froments}: C{name="docbook4"},
    C{vfilter="^%s"}, C{testsub=True} [type F3C hook].
    """

    global _froments_t1_hook
    if not _froments_t1_hook:
        _froments_t1_hook = froments("docbook4", vfilter=u"^%s", testsub=True)

    return _froments_t1_hook(msgstr, msg, cat)

