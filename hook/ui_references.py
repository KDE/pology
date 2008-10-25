# -*- coding: UTF-8 -*-

"""
Resolve UI references in translation by following through original texts.

If PO files which are delivered are not the same PO files which
are actually being translated, but there is processing step involved to
get former from the latter, there is a possibility to automatically
resolve references to user interface strings mentioned through messages
(typical e.g. of documentation POs). Compared to hard-coding it,
this enables referenced UI text to always be in sync with actual UI,
without necessity for manual tracking of changes in the UI.

In the most basic form, a UI reference in a message may look like::

    msgid "By pressing the 'Install New Theme' button..."
    msgstr "Pritiskom dugmeta „Instaliraj novu temu“..."

where C{Install New Theme} is the original UI reference, and
C{Instaliraj novu temu} its hard-coded translated counterpart.
Instead, to have automatic resolution of translated UI reference,
the translation would be made as::

    msgid "By pressing the 'Install New Theme' button..."
    msgstr "Pritiskom dugmeta „~%/Install New Theme/“..."

The C{~%/Install New Theme/} is I{explicitly} marked UI reference, using
the C{<head>/<reference-text>/} directive, which is resolved into when
delivery POs are built out of the actually translated ones.
Slashes in the UI reference directive can be replaced with any other character consistenly (sed-style), while head of the directive can be chosen per project
(C{~%} is one of the defaults) and given as a parameter of hook factory.

There is also the possibility for C{implicit} UI references, not requiring
special directive, when UI text is natively separated out of the rest of
the text. This is the case e.g. in Docbook POs::

    msgid "By pressing the <guibutton>Install New Theme</guibutton>..."
    msgstr "Pritiskom dugmeta <guibutton>Install New Theme</guibutton>..."

Hook factories can be told which tags are known to contain UI references.
(Of course, explicit references can be used alongside implicit ones
whenever necessary.)

Linking to UI Catalogs
======================

In general, UI reference may not, and especially in case of documentation POs,
is not present in the same PO file as that where it is referenced.
Therefore hooks need to know two things: the list of all UI catalogs in the
project, and, for given PO which contains references, from which UI catalogs
it may possibly draw those references.

The list of UI catalogs can be given to hooks explicitly, as list of catalog
paths. This can, however, be inconvenient, as it causes either that
the hook client is called from a specific directory if paths are relative,
or setting up the client for a single machine in case of absolute paths.
Another way of specifying paths to UI catalogs is by an environment variable,
which contains colon-separated list of directory paths; hook factory will
search these paths for PO files, and collect them for UI referencing.
Both the explict list of paths and the environment variable which contains
the paths are given as parameters to hook factories.

By default, for a given PO file, the UI references in it are looked for only
in the catalog of the same name, assuming it is found within UI catalogs
(which may I{not} be the case for a documentation PO, in case its name
is different from the corresponding UI catalog name). Other than that,
the referencing catalog links possible UI catalogs through a header field,
which states just UI catalog names, not paths (as UI catalogs must be
unique by name)::

    msgid ""
    msgstr ""
    "Project-Id-Version: dolphin\\n"
    "..."
    "X-Associated-UI-Catalogs: dolphin libkonq filetypes "
    "desktop_kdebase kio4 kdelibs4\\n"

The order of catalog names is important, as in case a given reference exists
in two or more catalogs, the translation is taken from the first-most.
The following header fields, by name collecting order, are considered::

    X-KDE-Associated-UI-Catalogs-H
    X-KDE-Associated-UI-Catalogs
    X-KDE-Associated-UI-Catalogs-L
    X-Associated-UI-Catalogs-H
    X-Associated-UI-Catalogs
    X-Associated-UI-Catalogs-L

Format of UI References
=======================

If the UI text is unique by C{msgid} field in linked UI catalogs, then
it can be referenced simply as given above. But, if there are several
UI messages with same C{msgid}, differentiated by C{msgctxt}, then
the C{msgctxt} too has to be given explicitly in the reference, separated
by the pipe (C{|}) character. If the UI catalog has these two messages::

    msgctxt "@title:menu"
    msgid "Columns"
    msgid "Kolone"

    msgctxt "@action:inmenu View Mode"
    msgid "Columns"
    msgstr "kolone"

then, the proper C{"Columns"} can be implicitly referenced as::

    msgid ""...<guibutton>Columns</guibutton>..."
    msgstr "...<guibutton>@title:menu|Columns</guibutton>..."

In the unlikely case of C{|} character being part of the context string itself,
the "broken bar" C{¦} (C{U+00A6}) can be used instead.

If two messages with same C{msgid} are not in the same UI catalog, that
is not a conflict as one of those catalogs has priority. If one message
has context, but the other does not, the message without context is
selected by just preceeding the C{msgid} text with context separator
(i.e. as if the context is "empty").

Rarely it may happen that the referenced text is not statically complete,
but contains a format directive which is resolved at runtime. In such cases,
the reference is C{msgid} as it is, and the argument is substituted via
special syntax. If the UI message is::

    msgid "Configure %1..."
    msgstr "Podesi %1..."

then it is used as reference in the following way::

    msgid "...<guimenuitem>Configure Dolphin...</guimenuitem>..."
    msgstr "...<guimenuitem>Configure %1...^%1:Delfin</guimenuitem>..."

The argument follows after argument separator, the hat-character (C{^}),
and must state the argument text as well as the format directive it
replaces, separated by colon. In the unlikely case of C{^} being part
of the C{msgid} itself, the "feminine ordinal indicator" C{ª} (C{U+00AA})
can be used instead.

If there are several format directives in the referenced text,
they are by default considered "named", i.e. all character-wise equal
format directives will be replaced by the same argument. This is the
proper thing to do e.g. for C{python-format} or C{kde-format} messages,
but not for {c-format}, e.g. when there are two C{%s} in the text.
To replace just the first format directive with the argument, the directive
in the argument specification is preceeded with an exclamation mark
(C{!}): C{...^!%s:foo}.

Normalization of UI Text
========================

The exact text of UI message may contain some characters and substrings
which should not find their way into the text which references the message,
or should be modified. To facilitate this, UI catalogs are normalized
after being opened and before they are used to look for UI references.
In fact, UI references are written in this normalized form, rather than
using the original C{msgid} from the UI catalog (both for convenience and
as necessity).

One typical sequence to remove on normalization is the accelerator marker.
Hooks eliminate accelerator markers automatically, the only thing is that
they have to be to told what the accelerator marker character is. This
is not done through hook factories (since knowledge of accelerator marker
is of wider consequence when processing POs), but either by hook client
setting it explicitly (using
L{set_accelerator()<file.catalog.Catalog.set_accelerator>} method on catalogs),
or by giving it within C{X-Accelerator-Marker} header filed::

    msgid ""
    msgstr ""
    "Project-Id-Version: dolphin\\n"
    "..."
    "X-Accelerator-Marker: &\\n"

(This field may be set in catalogs throughout the project by applying the
L{set-header<sieve.set_header>} sieve with L{posieve<scripts.posieve>} script.)

Another is the problem of UI messages containing subsections which would
invalidate the target format being translated by the referencing PO, e.g.
malformed XML in Docbook catalogs. For example, literal ampersand (C{&})
must be represented by C{&amp;} in Docbook markup, thus this UI message::

    msgid "Scaled & Cropped"
    msgstr ""

would be referenced as::

    msgid "...<guimenuitem>Scaled &amp; Cropped</guimenuitem>..."
    msgstr "...<guimenuitem>Scaled &amp; Cropped</guimenuitem>..."

Hook factories have parameters for specifying type of escaping needed
for fetched UI texts by target format.

Notes
=====

If a UI reference cannot be resolved, for whatever reason (not existing,
context conflict, not translated, etc.), resolving hooks will output warnings
and fallback to English text. There are also checker hooks, to be able to
catch resolution problems, a sorf of "dry run" before building delivery POs.

@var default_headrefs: Default heads for explicit UI references.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

# NOTE: The implementation is tuned to look for and open as few as possible
# UI catalogs, and as lazily as possible.

import os
import re

from pology.misc.report import warning
from pology.misc.msgreport import warning_on_msg
from pology.misc.langdep import get_hook_lreq
from pology.misc.fsops import collect_catalogs_by_env
from pology.file.catalog import Catalog
from pology.hook.remove_subs import remove_accel_msg, remove_markup_msg


default_headrefs = ["~%"]


def resolve_ui (headrefs=default_headrefs, tagrefs=[],
                uicpaths=None, uicpathenv=None, xmlescape=False, pfhook=None,
                mkeyw=None, invmkeyw=False):
    """
    Resolve general UI references in translations [hook factory].

    If UI catalogs are collected through the environment variable,
    a warning is issued if the given variable has not been set.

    Resolved UI text can be postprocessed by an F1A hook (C{(text)->text}).
    It can be given either as the hook function itself, or as
    a L{language request<misc.langdep.get_hook_lreq>} string.

    If one or several markup keywords are given as C{mkeyw} parameter,
    UI reference resolution is skipped for catalogs which do not report one
    of the given keywords by their L{markup()<file.catalog.Catalog.markup>}
    method. This match may be inverted by C{invmkeyw} parameter, i.e.
    to skip resolution for catalogs reporting one of given keywords.

    @param headrefs: heads for explicit UI references
    @type headrefs: list of strings
    @param tagrefs: XML-like tags which define implicit UI references
    @type tagrefs: list of strings
    @param uicpaths: paths to UI catalogs in the project
    @type uicpaths: list of strings
    @param uicpathenv: environment variable defining directories
        where UI catalogs may be found (colon-separated directory paths)
    @type uicpathenv: string
    @param xmlescape: whether to normalize UI text for XML
    @type xmlescape: bool
    @param pfhook: F1A hook to postprocess resolved UI text
    @type pfhook: function or string
    @param mkeyw: markup keywords for taking catalogs into account
    @type mkeyw: string or list of strings
    @param invmkeyw: whether to invert the meaning of C{mkeyw} parameter
    @type invmkeyw: bool

    @return: type F3C hook
    @rtype: C{(msgstr, msg, cat) -> msgstr}
    """

    return _resolve_ui_w(headrefs, tagrefs, uicpaths, uicpathenv, xmlescape,
                         pfhook, mkeyw, invmkeyw,
                         modtext=True, spanrep=False)


def check_ui (headrefs=default_headrefs, tagrefs=[],
              uicpaths=None, uicpathenv=None, xmlescape=False,
              mkeyw=None, invmkeyw=False):
    """
    Check general UI references in translations [hook factory].

    See L{resolve_ui} for description of parameters.

    @return: type V3C hook
    @rtype: C{(msgstr, msg, cat) -> spans}
    """

    pfhook = None
    return _resolve_ui_w(headrefs, tagrefs, uicpaths, uicpathenv, xmlescape,
                         pfhook, mkeyw, invmkeyw,
                         modtext=False, spanrep=True)


_tagrefs_docbook4 = [
    "guilabel", "guibutton", "guiicon", "guimenu", "guisubmenu",
    "guimenuitem",
]

def resolve_ui_docbook4 (headrefs=default_headrefs,
                         uicpaths=None, uicpathenv=None, pfhook=None,
                         mkeyw=None):
    """
    Resolve UI references in Docbook 4.x translations [hook factory].

    A convenience hook which fixes some of the parameters to L{resolve_ui}
    to match implicit UI references and formatting needs for Docbook POs.

    @return: type F3C hook
    @rtype: C{(msgstr, msg, cat) -> msgstr}
    """

    tagrefs = _tagrefs_docbook4
    xmlescape = True
    invmkeyw = False
    return _resolve_ui_w(headrefs, tagrefs, uicpaths, uicpathenv, xmlescape,
                         pfhook, mkeyw, invmkeyw,
                         modtext=True, spanrep=False)


def check_ui_docbook4 (headrefs=default_headrefs,
                       uicpaths=None, uicpathenv=None, mkeyw=None):
    """
    Check UI references in Docbook 4.x translations [hook factory].

    A convenience hook which fixes some of the parameters to L{check_ui}
    to match implicit UI references and formatting needs for Docbook POs.

    @return: type V3C hook
    @rtype: C{(msgstr, msg, cat) -> spans}
    """

    tagrefs = _tagrefs_docbook4
    xmlescape = True
    invmkeyw = False
    pfhook = None
    return _resolve_ui_w(headrefs, tagrefs, uicpaths, uicpathenv, xmlescape,
                         pfhook, mkeyw, invmkeyw,
                         modtext=False, spanrep=True)


_tagrefs_kde4 = [
    "interface",
]

def resolve_ui_kde4 (headrefs=default_headrefs,
                     uicpaths=None, uicpathenv=None, pfhook=None,
                     mkeyw=None):
    """
    Resolve UI references in KDE4 UI translations [hook factory].

    A convenience hook which fixes some of the parameters to L{resolve_ui}
    to match implicit UI references and formatting needs for KDE4 UI POs.

    @return: type F3C hook
    @rtype: C{(msgstr, msg, cat) -> msgstr}
    """

    tagrefs = _tagrefs_kde4
    xmlescape = True
    invmkeyw = False
    return _resolve_ui_w(headrefs, tagrefs, uicpaths, uicpathenv, xmlescape,
                         pfhook, mkeyw, invmkeyw,
                         modtext=True, spanrep=False)


def check_ui_kde4 (headrefs=default_headrefs,
                   uicpaths=None, uicpathenv=None, mkeyw=None):
    """
    Check UI references in KDE4 UI translations [hook factory].

    A convenience hook which fixes some of the parameters to L{check_ui}
    to match implicit UI references and formatting needs for KDE4 UI POs.

    @return: type V3C hook
    @rtype: C{(msgstr, msg, cat) -> spans}
    """

    tagrefs = _tagrefs_kde4
    xmlescape = True
    invmkeyw = False
    pfhook = None
    return _resolve_ui_w(headrefs, tagrefs, uicpaths, uicpathenv, xmlescape,
                         pfhook, mkeyw, invmkeyw,
                         modtext=False, spanrep=True)


def _resolve_ui_w (headrefs, tagrefs, uicpaths, uicpathenv, xmlescape,
                   pfhook, mkeyw, invmkeyw, modtext, spanrep):
    """
    Worker for hook factories.
    """

    # Convert sequences into sets, for fast membership checks.
    if not isinstance(tagrefs, set):
        tagrefs = set(tagrefs)
    if not isinstance(headrefs, set):
        headrefs = set(headrefs)

    # Markup keywords should remain None if not a sequence or string.
    if mkeyw is not None:
        if isinstance(mkeyw, basestring):
            mkeyw = [mkeyw]
        mkeyw = set(mkeyw)

    # Resolve post-filtering hook.
    if pfhook is None:
        pfhook = lambda x: x
    elif isinstance(pfhook, basestring):
        pfhook = get_hook_lreq(pfhook)
    # ...else assume it is already a callable.

    # Regular expressions for finding and extracting UI references.
    # Add a never-match expression to start regexes for all reference types,
    # so that it can be applied even if the category has no entries.
    rxflags = re.U|re.I
    # - by tags
    rxstr = r"<\s*(%s)\b.*?>" % "|".join(list(tagrefs) + ["\x04"])
    uiref_start_tag_rx = re.compile(rxstr, rxflags)
    uiref_extract_tag_rx = {}
    for tag in tagrefs:
        rxstr = r"<\s*(%s)\b.*?>(.*?)(<\s*/\s*\1\s*>)" % tag
        uiref_extract_tag_rx[tag] = re.compile(rxstr, rxflags)
    # - by heads
    rxstr = r"(%s)" % "|".join(list(headrefs) + ["\x04"])
    uiref_start_head_rx = re.compile(rxstr, rxflags)
    uiref_extract_head_rx = {}
    for head in headrefs:
        rxstr = r"%s(.)(.*?)\1" % head
        uiref_extract_head_rx[head] = re.compile(rxstr, rxflags)

    # Lazy-evaluated data.
    ldata = {}

    # Function to split text by UI references, into list of tuples with
    # the text segment preceeding the reference as first element,
    # the reference as second element, and span indices of the reference
    # against complete text as the third and fourth elements;
    # trailing text segment has None as reference, and invalid span.
    # "Blah <ui>foo</ui> blah ~%/bar/ blah." ->
    # [("Blah <ui>", "foo", 9, 12), ("</ui> blah ", "bar", 26, 29),
    #  (" blah.", None, -1, -1)]
    def split_by_uiref (text, msg, cat, errspans):

        rsplit = []

        ltext = len(text)
        p = 0
        while True:
            mt = uiref_start_tag_rx.search(text, p)
            if mt: pt = mt.start()
            else: pt = ltext
            mh = uiref_start_head_rx.search(text, p)
            if mh: ph = mh.start()
            else: ph = ltext

            if pt < ph:
                # Tagged UI reference.
                tag = mt.group(1)
                m = uiref_extract_tag_rx[tag].search(text, pt)
                if not m:
                    errmsg = "non-terminated UI reference by tag '%s'" % tag
                    errspans.append(mt.span() + (errmsg,))
                    if not spanrep:
                        warning_on_msg(errmsg, msg, cat)
                    break

                uiref = m.group(2)
                pe = m.end() - len(m.group(3))
                ps = pe - len(uiref)

                rsplit.append((text[p:ps], uiref, ps, pe))
                p = pe

            elif ph < pt:
                # Headed UI reference.
                head = mh.group(1)
                m = uiref_extract_head_rx[head].search(text, ph)
                if not m:
                    errmsg = "non-terminated UI reference by head '%s'" % head
                    errspans.append(mh.span() + (errmsg,))
                    if not spanrep:
                        warning_on_msg(errmsg, msg, cat)
                    break

                uiref = m.group(2)
                ps, pe = m.span()

                rsplit.append((text[p:ps], uiref, ps, pe))
                p = pe

            else:
                # Both positions equal, meaning end of text.
                break

        # Trailing segment (or everything after an error).
        rsplit.append((text[p:], None, -1, -1))

        return rsplit


    # Function to resolve given UI reference
    # (part that needs to be under closure).
    def resolve_single_uiref(uiref, msg, cat):

        if ldata.get("uicpaths") is None:
            ldata["uicpaths"] = _collect_ui_catpaths(uicpaths, uicpathenv)
        if ldata.get("actcatfile") != cat.filename:
            ldata["actcatfile"] = cat.filename
            ldata["normcats"] = _load_norm_ui_cats(cat, ldata["uicpaths"],
                                                   xmlescape)
        normcats = ldata["normcats"]

        uiref_res, errmsgs = _resolve_single_uiref(uiref, normcats)
        uiref_res = pfhook(uiref_res)

        return uiref_res, errmsgs


    # The hook itself.
    def hook (msgstr, msg, cat):

        errspans = []
        tsegs = []

        if (   mkeyw is None
            or (not invmkeyw and mkeyw.intersection(cat.markup() or set()))
            or (invmkeyw and not mkeyw.intersection(cat.markup() or set()))
        ):
            rsplit = split_by_uiref(msgstr, msg, cat, errspans)

            for ptext, uiref, start, end in rsplit:
                tsegs.append(ptext)
                if uiref is not None:
                    uiref_res, errmsgs = resolve_single_uiref(uiref, msg, cat)
                    tsegs.append(uiref_res)
                    errspans.extend([(start, end, x) for x in errmsgs])
                    if not spanrep:
                        for errmsg in errmsgs:
                            warning_on_msg(errmsg, msg, cat)

        else:
            tsegs.append(msgstr)

        if modtext: # F3C hook
            return "".join(tsegs)
        elif spanrep: # V3C hook
            return errspans
        else: # S3C hook
            return len(errspans)

    return hook


def _collect_ui_catpaths (uicpaths, uicpathenv):

    all_uicpaths = []
    if uicpathenv is not None:
        all_uicpaths.extend(collect_catalogs_by_env(uicpathenv))
    if uicpaths is not None:
        all_uicpaths.extend(uicpaths)

    # Convert into dictionary by catalog name.
    # If there are several catalogs with the same name among paths,
    # the result is undefined (UI catalogs should be unique!)
    uicpath_dict = {}
    for uicpath in all_uicpaths:
        catname = os.path.basename(uicpath)
        p = catname.rfind(".")
        if p >= 0:
            catname = catname[:p]
        uicpath_dict[catname] = uicpath

    return uicpath_dict


# Cache for normalized UI catalogs.
# Mapping by normalization options, followed by catalog name:
# cache[normkey][catname]
_norm_cats_cache = {}

def _load_norm_ui_cats (cat, uicpaths, xmlescape):

    # Update cache for normalization key.
    normkey = (xmlescape,)
    if normkey not in _norm_cats_cache:
        _norm_cats_cache[normkey] = {}

    # Construct list of catalogs, by catalog name, from which this
    # catalog may draw UI strings.
    # The list should be ordered by decreasing priority,
    # used to resolve references in face of duplicates over catalogs.
    catnames = []

    # - the catalog itself, if among UI catalogs paths
    if cat.name in uicpaths:
        catnames.append(cat.name)

    # - catalogs listed in some header fields
    # NOTE: Mention in module docustring when adding/removing fields.
    afnames = (
        "X-KDE-Associated-UI-Catalogs-H",
        "X-KDE-Associated-UI-Catalogs",
        "X-KDE-Associated-UI-Catalogs-L",
        "X-Associated-UI-Catalogs-H",
        "X-Associated-UI-Catalogs",
        "X-Associated-UI-Catalogs-L",
    )
    for afname in afnames:
        for field in cat.header.select_fields(afname):
            # Field value is a list of catalog names.
            lststr = field[1]
            # Remove any summit-merging comments.
            p = lststr.find("~~")
            if p >= 0:
                lststr = lststr[:p]
            catnames.extend(lststr.split())

    # Open and normalize UI catalogs.
    # Cache catalogs for performance.
    uicats = []
    for catname in set(catnames):
        catpath = uicpaths.get(catname)
        if catpath is None:
            warning("UI catalog '%s' associated to '%s' "
                    "not among known catalog paths" % (catname, cat.name))
            continue
        normcatpath = catpath + "~norm"
        uicat = _norm_cats_cache[normkey].get(normcatpath)
        if uicat is None:
            print "Loading UI catalog '%s'..." % catpath
            uicat_raw = Catalog(catpath, monitored=False)
            uicat = _norm_ui_cat(uicat_raw, normcatpath, xmlescape)
            uicat.filename = normcatpath
            _norm_cats_cache[normkey][normcatpath] = uicat
        uicats.append(uicat)

    return uicats


def _norm_ui_cat (cat, normpath, xmlescape):

    norm_cat = Catalog("", create=True, monitored=False)

    for msg in cat:
        remove_markup_msg(msg, cat) # before accelerator removal
        remove_accel_msg(msg, cat) # after markup removal

        if xmlescape: # after markup removal
            msg.msgid = _escape_to_xml(msg.msgid)
            msg.msgid_plural = _escape_to_xml(msg.msgid_plural)
            for i in range(len(msg.msgstr)):
                msg.msgstr[i] = _escape_to_xml(msg.msgstr[i])

        # If the message as modified is still valid,
        # and not already present in the normalized catalog, append it.
        if msg.msgid and msg not in norm_cat:
            norm_cat.add(msg, -1) # O(1) when position -1

    return norm_cat


def _escape_to_xml (text):

    text = text.replace("&", "&amp;") # must be first
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")

    return text


_ts_fence = "|/|"

def _resolve_single_uiref (uitext, uicats):

    errmsgs = []

    # Determine context separator in the reference.
    # If the arcane one is not present, use normal.
    ctxsep = _uiref_ctxsep2
    if ctxsep not in uitext:
        ctxsep = _uiref_ctxsep

    # Return verbatim if requested (starts with two context separators).
    if uitext.startswith(ctxsep * 2):
        return uitext[len(ctxsep) * 2:], errmsgs

    # Split into msgctxt and msgid.
    has_msgctxt = False
    msgctxt = ""
    msgid = uitext
    if ctxsep in uitext:
        lst = uitext.split(ctxsep)
        if len(lst) > 2:
            rep = "..." + ctxsep + ctxsep.join(lst[2:])
            errmsgs.append("superfluous tail '%s' in UI reference '%s'"
                           % (rep, uitext))
        msgctxt, msgid = lst[:2]
        has_msgctxt = True
        # msgctxt may be empty while has_msgctxt is True.
        # This distinction is important when deciding between two msgids,
        # one having no context and one having a context.

    # Split any arguments from msgid.
    args = []
    argsep = _uiref_argsep2
    if _uiref_argsep2 not in msgid:
        argsep = _uiref_argsep
    if argsep in msgid:
        lst = msgid.split(argsep)
        msgid = lst[0]
        args_raw = lst[1:]
        for arg_raw in args_raw:
            alst = arg_raw.split(_uiref_argplsep)
            if len(alst) == 2:
                single = False
                if alst[0].startswith(_uiref_argsrepl):
                    alst[0] = alst[0][1:]
                    single = True
                alst.append(single)
                args.append(alst)
            else:
                errmsgs.append("invalid argument specification '%s' in "
                               "UI reference '%s'" % (arg_raw, uitext))

    # Try to find unambiguous match to msgctxt/msgid.
    rmsg = None
    rcat = None
    for uicat in uicats:
        if has_msgctxt:
            msgs = uicat.select_by_key(msgctxt, msgid)
        else:
            msgs = uicat.select_by_msgid(msgid)
        if len(msgs) == 1:
            rmsg = msgs[0]
            rcat = uicat
            break

    # If unambiguous match found.
    if rmsg is not None:
        # If the message is translated, use its translation,
        # otherwise use original and report.
        if rmsg.translated:
            ruitext = rmsg.msgstr[0]
        else:
            ruitext = msgid
            errmsgs.append("UI reference '%s' not translated at %s:%s(#%s)"
                           % (uitext,
                              rcat.filename, rmsg.refline, rmsg.refentry))

    # If no unambiguous match found, collect all the approximate ones,
    # report and use the original UI text.
    else:
        ruitext = msgid
        approx = []
        for uicat in uicats:
            nmsgs = uicat.select_by_msgid_fuzzy(msgid)
            for nmsg in nmsgs:
                approx.append("{{%s}} at %s:%s(#%s)"
                              % (_to_uiref(nmsg),
                                 uicat.filename, nmsg.refline, nmsg.refentry))
        if approx:
            errmsgs.append("UI reference '%s' cannot be resolved; "
                           "close matches:\n"
                           "%s" % (uitext, "\n".join(approx)))
        else:
            errmsgs.append("UI reference '%s' cannot be resolved" % uitext)

    # Strip scripted part if any.
    p = ruitext.find(_ts_fence)
    if p >= 0:
        ruitext = ruitext[:p]

    # Replace any provided arguments.
    for plhold, value, single in args:
        if plhold in ruitext:
            if single:
                ruitext = ruitext.replace(plhold, value, 1)
            else:
                ruitext = ruitext.replace(plhold, value)
        else:
            errmsgs.append("placeholder '%s' not found in resolved "
                           "UI reference text '%s' to reference '%s'"
                           % (plhold, ruitext, uitext))

    return ruitext, errmsgs


# Special tokens used in UI references.
_uiref_ctxsep = u"|" # normal context separator
_uiref_ctxsep2 = u"¦" # arcane context separator (fallback)
_uiref_argsep = u"^" # normal argument separator
_uiref_argsep2 = u"ª" # arcane argument separator (fallback)
_uiref_argplsep = u":" # placeholder separator in arguments
_uiref_argsrepl = u"!" # placeholder start to indicate single replacement

# Present message from a normalized catalog in reference format,
# suitable for inserting as a reference.
def _to_uiref (nmsg):

    uiref = nmsg.msgid

    if nmsg.msgctxt:
        # Use arcane separator if the msgid or msgctxt contain normal one.
        ctxsep = _uiref_ctxsep
        if ctxsep in uiref or ctxsep in nmsg.msgctxt:
            ctxsep = _uiref_ctxsep2
        uiref = nmsg.msgctxt + ctxsep + uiref
    elif _uiref_ctxsep in nmsg.msgid:
        # If the msgid contains normal separator, add one arcane separator
        # in front of it to indicate empty context.
        uiref = _uiref_ctxsep * 2 + uiref

    # TODO: Analyze format directives to add dummy arguments?

    return uiref

