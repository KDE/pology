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

See C{doc/user/lingo.docbook#sec-lguirefs} for details.

@var default_headrefs: Default heads for explicit UI references.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

# NOTE: The implementation is tuned to look for and open as few as possible
# UI catalogs, and as lazily as possible.

import hashlib
import os
import re

from pology import _, n_
from pology.catalog import Catalog
from pology.remove import remove_accel_msg, remove_markup_msg
from pology.colors import cjoin
from pology.fsops import collect_catalogs, collect_catalogs_by_env
from pology.getfunc import get_hook_ireq
from pology.msgreport import warning_on_msg
from pology.report import warning


default_headrefs = ["~%"]


def resolve_ui (headrefs=default_headrefs, tagrefs=[], uipathseps=[],
                uicpaths=None, uicpathenv=None, xmlescape=False, pfhook=None,
                mkeyw=None, invmkeyw=False, quiet=False, fdirsplit=None):
    """
    Resolve general UI references in translations [hook factory].

    If UI catalogs are collected through the environment variable,
    a warning is issued if the given variable has not been set.

    Resolved UI text can be postprocessed by an F1A hook (C{(text)->text}).
    It can be given either as the hook function itself, or as
    a L{language request<getfunc.get_hook_ireq>} string.

    If one or several markup keywords are given as C{mkeyw} parameter,
    UI reference resolution is skipped for catalogs which do not report one
    of the given keywords by their L{markup()<catalog.Catalog.markup>}
    method. This match may be inverted by C{invmkeyw} parameter, i.e.
    to skip resolution for catalogs reporting one of given keywords.

    The list of UI path separators given by the C{uipathseps} parameter
    is ordered by priority, such that the first one found in the composite
    reference text is used to split it into componental UI references.

    If the UI reference contains a formatting directive/argument placeholder,
    and the UI reference is found in a message of the same format
    (e.g. a tooltip referencing another part of UI), then using the argument
    substitution syntax may make the message invalid for the C{msgfmt -c}
    check. In that case, a splitter string specified by C{fdirsplit} parameter
    can be inserted somewhere between the first and the last character of
    the formatting directive, thus masking it from C{msgfmt -c}.

    @param headrefs: heads for explicit UI references
    @type headrefs: list of strings
    @param tagrefs: XML-like tags which define implicit UI references
    @type tagrefs: list of strings
    @param uipathseps: separators in composited UI references
    @type uipathseps: list of strings
    @param uicpaths: paths to UI catalogs in the project
        (both files and directories can be given)
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
    @param quiet: whether to output warnings of failed resolutions
    @type quiet: bool
    @param fdirsplit: splitter string for masking formatting directives
    @type fdirsplit: string

    @return: type F3C hook
    @rtype: C{(msgstr, msg, cat) -> msgstr}
    """

    return _resolve_ui_w(headrefs, tagrefs, uipathseps, uicpaths, uicpathenv,
                         xmlescape, pfhook, mkeyw, invmkeyw, quiet, fdirsplit,
                         modtext=True, spanrep=False)


def check_ui (headrefs=default_headrefs, tagrefs=[], uipathseps=[],
              uicpaths=None, uicpathenv=None, xmlescape=False,
              mkeyw=None, invmkeyw=False, fdirsplit=None):
    """
    Check general UI references in translations [hook factory].

    See L{resolve_ui} for description of parameters.

    @return: type V3C hook
    @rtype: C{(msgstr, msg, cat) -> spans}
    """

    pfhook = None
    quiet = True
    return _resolve_ui_w(headrefs, tagrefs, uipathseps, uicpaths, uicpathenv,
                         xmlescape, pfhook, mkeyw, invmkeyw, quiet, fdirsplit,
                         modtext=False, spanrep=True)


_tagrefs_docbook4 = [
    "guilabel", "guibutton", "guiicon", "guimenu", "guisubmenu",
    "guimenuitem",
]

def resolve_ui_docbook4 (headrefs=default_headrefs,
                         uicpaths=None, uicpathenv=None, pfhook=None,
                         mkeyw=None, quiet=False):
    """
    Resolve UI references in Docbook 4.x translations [hook factory].

    A convenience hook which fixes some of the parameters to L{resolve_ui}
    to match implicit UI references and formatting needs for Docbook POs.

    @return: type F3C hook
    @rtype: C{(msgstr, msg, cat) -> msgstr}
    """

    tagrefs = _tagrefs_docbook4
    uipathseps = []
    xmlescape = True
    invmkeyw = False
    fdirsplit = None
    return _resolve_ui_w(headrefs, tagrefs, uipathseps, uicpaths, uicpathenv,
                         xmlescape, pfhook, mkeyw, invmkeyw, quiet, fdirsplit,
                         modtext=True, spanrep=False)


def check_ui_docbook4 (headrefs=default_headrefs,
                       uicpaths=None, uicpathenv=None, mkeyw=None):
    """
    Check UI references in Docbook 4.x translations [hook factory].

    A convenience resolver which fixes some of the parameters to L{check_ui}
    to match implicit UI references and formatting needs for Docbook POs.

    @return: type V3C hook
    @rtype: C{(msgstr, msg, cat) -> spans}
    """

    tagrefs = _tagrefs_docbook4
    uipathseps = []
    xmlescape = True
    invmkeyw = False
    pfhook = None
    quiet = True
    fdirsplit = None
    return _resolve_ui_w(headrefs, tagrefs, uipathseps, uicpaths, uicpathenv,
                         xmlescape, pfhook, mkeyw, invmkeyw, quiet, fdirsplit,
                         modtext=False, spanrep=True)


_tagrefs_kde4 = [
    "interface",
]

def resolve_ui_kde4 (headrefs=default_headrefs, uipathseps=None,
                     uicpaths=None, uicpathenv=None, pfhook=None,
                     mkeyw=None, quiet=False):
    """
    Resolve UI references in KDE4 UI translations [hook factory].

    A convenience resolver which fixes some of the parameters to L{resolve_ui}
    to match implicit UI references and formatting needs for KDE4 UI POs.

    If C{uipathseps} is C{None}, separators known to KUIT C{<interface>} tag
    will be used automatically.

    C{fdirsplit} is set to C{"~"}.

    @return: type F3C hook
    @rtype: C{(msgstr, msg, cat) -> msgstr}
    """

    tagrefs = _tagrefs_kde4
    if uipathseps is None:
        uipathseps = ["->"]
    xmlescape = True
    invmkeyw = False
    fdirsplit = "~"
    return _resolve_ui_w(headrefs, tagrefs, uipathseps, uicpaths, uicpathenv,
                         xmlescape, pfhook, mkeyw, invmkeyw, quiet, fdirsplit,
                         modtext=True, spanrep=False)


def check_ui_kde4 (headrefs=default_headrefs, uipathseps=None,
                   uicpaths=None, uicpathenv=None, mkeyw=None):
    """
    Check UI references in KDE4 UI translations [hook factory].

    A convenience resolver which fixes some of the parameters to L{check_ui}
    to match implicit UI references and formatting needs for KDE4 UI POs.

    If C{uipathseps} is C{None}, separators known to KUIT C{<interface>} tag
    will be used automatically.

    C{fdirsplit} is set to C{"~"}.

    @return: type V3C hook
    @rtype: C{(msgstr, msg, cat) -> spans}
    """

    tagrefs = _tagrefs_kde4
    if uipathseps is None:
        uipathseps = ["->"]
    xmlescape = True
    invmkeyw = False
    pfhook = None
    quiet = True
    fdirsplit = "~"
    return _resolve_ui_w(headrefs, tagrefs, uipathseps, uicpaths, uicpathenv,
                         xmlescape, pfhook, mkeyw, invmkeyw, quiet, fdirsplit,
                         modtext=False, spanrep=True)


def _resolve_ui_w (headrefs, tagrefs, uipathseps, uicpaths, uicpathenv,
                   xmlescape, pfhook, mkeyw, invmkeyw, quiet, fdirsplit,
                   modtext, spanrep):
    """
    Worker for resolver factories.
    """

    # Convert sequences into sets, for fast membership checks.
    if not isinstance(tagrefs, set):
        tagrefs = set(tagrefs)
    if not isinstance(headrefs, set):
        headrefs = set(headrefs)
    if not isinstance(uipathseps, set):
        uipathseps = set(uipathseps)

    # Markup keywords should remain None if not a sequence or string.
    if mkeyw is not None:
        if isinstance(mkeyw, basestring):
            mkeyw = [mkeyw]
        mkeyw = set(mkeyw)

    # Construct post-filtering hook.
    if pfhook is None:
        pfhook = lambda x: x
    elif isinstance(pfhook, basestring):
        pfhook = get_hook_ireq(pfhook)
    # ...else assume it is already a hook function.

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
                    errmsg = _("@info \"tag\" is a tag in HTML/XML context",
                               "Non-terminated UI reference by tag '%(tag)s'.",
                               tag=tag)
                    errspans.append(mt.span() + (errmsg,))
                    if not spanrep and not quiet:
                        warning_on_msg(errmsg, msg, cat)
                    break

                uirefpath = m.group(2)
                pe = m.end() - len(m.group(3))
                ps = pe - len(uirefpath)

            elif ph < pt:
                # Headed UI reference.
                head = mh.group(1)
                m = uiref_extract_head_rx[head].search(text, ph)
                if not m:
                    errmsg = _("@info \"head\" is the leading part of "
                               "UI reference, e.g. '~%' in '~%/Save All/'",
                               "Non-terminated UI reference by "
                               "head '%(head)s'.",
                               head=head)
                    errspans.append(mh.span() + (errmsg,))
                    if not spanrep and not quiet:
                        warning_on_msg(errmsg, msg, cat)
                    break

                uirefpath = m.group(2)
                ps, pe = m.span()

            else:
                # Both positions equal, meaning end of text.
                break

            ptext_uiref = _split_uirefpath(text[p:ps], uirefpath, uipathseps)
            for ptext, uiref in ptext_uiref:
                rsplit.append((ptext, uiref, ps, pe))
            p = pe

        # Trailing segment (or everything after an error).
        rsplit.append((text[p:], None, -1, -1))

        return rsplit


    # Function to resolve given UI reference
    # (part that needs to be under closure).
    def resolve_single_uiref (uiref, msg, cat, resolver_helper):

        if ldata.get("uicpaths") is None:
            ldata["uicpaths"] = _collect_ui_catpaths(uicpaths, uicpathenv)
        if ldata.get("actcatfile") != cat.filename:
            ldata["actcatfile"] = cat.filename
            ldata["normcats"] = _load_norm_ui_cats(cat, ldata["uicpaths"],
                                                   xmlescape)
        normcats = ldata["normcats"]

        hookcl_f3c = lambda uiref: resolver_helper(uiref, msg, cat, True, False)
        hookcl_v3c = lambda uiref: resolver_helper(uiref, msg, cat, False, True)
        uiref_res, errmsgs = _resolve_single_uiref(uiref, normcats,
                                                   hookcl_f3c, hookcl_v3c,
                                                   fdirsplit)
        uiref_res = pfhook(uiref_res)

        return uiref_res, errmsgs


    # The resolver itself, in two parts.
    def resolver_helper (msgstr, msg, cat, modtext, spanrep):

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
                    uiref_res, errmsgs = resolve_single_uiref(uiref, msg, cat,
                                                              resolver_helper)
                    tsegs.append(uiref_res)
                    errspans.extend([(start, end, x) for x in errmsgs])
                    if not spanrep and not quiet:
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

    def resolver (msgstr, msg, cat):

        return resolver_helper(msgstr, msg, cat, modtext, spanrep)

    return resolver


def _collect_ui_catpaths (uicpaths, uicpathenv):

    all_uicpaths = []
    if uicpathenv is not None:
        all_uicpaths.extend(collect_catalogs_by_env(uicpathenv))
    if uicpaths is not None:
        all_uicpaths.extend(collect_catalogs(uicpaths))

    # Convert into dictionary by catalog name.
    # If there are several catalogs with the same name among paths,
    # store them under that name in undefined order.
    uicpath_dict = {}
    for uicpath in all_uicpaths:
        catname = os.path.basename(uicpath)
        p = catname.rfind(".")
        if p >= 0:
            catname = catname[:p]
        if catname not in uicpath_dict:
            uicpath_dict[catname] = []
        uicpath_dict[catname].append(uicpath)

    return uicpath_dict


# Cache for normalized UI catalogs.
# Mapping by normalization options and catalog name.
_norm_cats_cache = {}

def _load_norm_ui_cats (cat, uicpaths, xmlescape):

    # Construct list of catalogs, by catalog name, from which this
    # catalog may draw UI strings.
    # The list should be ordered by decreasing priority,
    # used to resolve references in face of duplicates over catalogs.
    catnames = []

    # - catalogs listed in some header fields
    # NOTE: Mention in module docustring when adding/removing fields.
    afnames = (
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

    # - the catalog itself, if among UI catalogs paths and not explicitly given
    if cat.name in uicpaths and not cat.name in catnames:
        catnames.insert(0, cat.name) # highest priority

    # Make catalog names unique, preserving order.
    uniq_catnames = []
    for catname in catnames:
        if catname not in uniq_catnames:
            uniq_catnames.append(catname)

    # Open and normalize UI catalogs.
    # Cache catalogs for performance.
    uicats = []
    chkeys = set()
    for catname in uniq_catnames:
        catpaths = uicpaths.get(catname)
        if not catpaths:
            warning(_("@info",
                      "UI catalog '%(catname1)s' associated to '%(catname2)s' "
                      "is not among known catalog paths.",
                      catname1=catname, catname2=cat.name))
            continue
        for catpath in catpaths:
            chkey = (xmlescape, catpath)
            chkeys.add(chkey)
            uicat = _norm_cats_cache.get(chkey)
            if uicat is None:
                uicat_raw = Catalog(catpath, monitored=False)
                uicat = _norm_ui_cat(uicat_raw, xmlescape)
                _norm_cats_cache[chkey] = uicat
            uicats.append(uicat)

    # Remove previous catalogs not reused by this call.
    # TODO: Better strategy for removing from cache.
    for chkey in set(_norm_cats_cache.keys()).difference(chkeys):
        #print "Removing normalized UI catalog '%s'..." % list(chkey)
        del _norm_cats_cache[chkey]

    return uicats


def _norm_ui_cat (cat, xmlescape):

    norm_cat = Catalog("", create=True, monitored=False)
    norm_cat.filename = cat.filename + "~norm"

    # Normalize messages and collect them by normalized keys.
    msgs_by_normkey = {}
    for msg in cat:
        if msg.obsolete:
            continue
        orig_msgkey = (msg.msgctxt, msg.msgid)
        remove_markup_msg(msg, cat) # before accelerator removal
        remove_accel_msg(msg, cat) # after markup removal
        normkey = (msg.msgctxt, msg.msgid)
        if normkey not in msgs_by_normkey:
            msgs_by_normkey[normkey] = []
        msgs_by_normkey[normkey].append((msg, orig_msgkey))

    for msgs in msgs_by_normkey.values():
        # If there are several messages with same normalized key and
        # different translations, add extra disambiguations to context.
        # These disambiguations must not depend on message ordering.
        if len(msgs) > 1:
            # Check equality of translations.
            msgstr0 = u""
            for msg, d1 in msgs:
                if msg.translated:
                    if not msgstr0:
                        msgstr0 = msg.msgstr[0]
                    elif msgstr0 != msg.msgstr[0]:
                        msgstr0 = None
                        break
            if msgstr0 is None: # disambiguation necessary
                tails = set()
                for msg, (octxt, omsgid) in msgs:
                    if msg.msgctxt is None:
                        msg.msgctxt = u""
                    tail = hashlib.md5(omsgid).hexdigest()
                    n = 4 # minimum size of the disambiguation tail
                    while tail[:n] in tails:
                        n += 1
                        if n > len(tail):
                            raise PologyError(
                                _("@info",
                                  "Hash function has returned same result "
                                  "for two different strings."))
                    tails.add(tail[:n])
                    msg.msgctxt += "~" + tail[:n]
            else: # all messages have same translation, use first
                msgs = msgs[:1]

        # Escape text fields.
        if xmlescape:
            for msg, d1 in msgs:
                if msg.msgctxt:
                    msg.msgctxt = _escape_to_xml(msg.msgctxt)
                msg.msgid = _escape_to_xml(msg.msgid)
                if msg.msgid_plural:
                    msg.msgid_plural = _escape_to_xml(msg.msgid_plural)
                for i in range(len(msg.msgstr)):
                    msg.msgstr[i] = _escape_to_xml(msg.msgstr[i])

        # Add normalized messages to normalized catalog.
        for msg, d1 in msgs:
            if msg.msgctxt or msg.msgid:
                norm_cat.add_last(msg)

    return norm_cat


def _escape_to_xml (text):

    text = text.replace("&", "&amp;") # must be first
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")

    return text


_ts_fence = "|/|"

def _resolve_single_uiref (uitext, uicats, hookcl_f3c, hookcl_v3c, fdirsplit):

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
    msgctxt = None
    msgid = uitext
    if ctxsep in uitext:
        lst = uitext.split(ctxsep)
        if len(lst) > 2:
            rep = "..." + ctxsep + ctxsep.join(lst[2:])
            errmsgs.append(_("@info \"tail\" is the trailing remainder of "
                             "a UI reference string after parsing",
                             "Superfluous tail '%(str)s' in "
                             "UI reference '%(ref)s'.",
                             str=rep, ref=uitext))
        msgctxt, msgid = lst[:2]
        if not msgctxt:
            # FIXME: What about context with existing, but empty context?
            msgctxt = None
        has_msgctxt = True
        # msgctxt may be None while has_msgctxt is True.
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
                if fdirsplit and fdirsplit in alst[0]:
                    plhold = alst[0].replace(fdirsplit, "", 1)
                    if single:
                        msgid = msgid.replace(alst[0], plhold, 1)
                    else:
                        msgid = msgid.replace(alst[0], plhold)
                    alst[0] = plhold
                # Argument itself may contain UI references.
                local_errspans = hookcl_v3c(alst[1])
                if local_errspans:
                    errmsgs.extend([x[-1] for x in local_errspans])
                else:
                    alst[1] = hookcl_f3c(alst[1])
                alst.append(single)
                args.append(alst)
            else:
                errmsgs.append(_("@info",
                                 "Invalid argument specification '%(arg)s' "
                                 "in UI reference '%(ref)s'.",
                                 arg=arg_raw, ref=uitext))

    # Try to find unambiguous match to msgctxt/msgid.
    rmsg = None
    rcat = None
    for uicat in uicats:
        if has_msgctxt:
            msgs = uicat.select_by_key(msgctxt, msgid)
            if not msgs:
                # Also try as if the context were regular expression.
                msgs = uicat.select_by_key_match(msgctxt, msgid,
                                                 exctxt=False, exid=True,
                                                 case=False)
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
            errmsgs.append(_("@info",
                             "UI reference '%(ref)s' not translated "
                             "at %(file)s:%(line)d(#%(entry)d).",
                             ref=uitext, file=rcat.filename,
                             line=rmsg.refline, entry=rmsg.refentry))

    # If no unambiguous match found, collect all the approximate ones,
    # report and use the original UI text.
    else:
        ruitext = msgid
        approx = []
        for uicat in uicats:
            nmsgs = uicat.select_by_msgid_fuzzy(msgid)
            for nmsg in nmsgs:
                if nmsg.translated:
                    approx1 = _("@item condensed display of text and "
                                "its translation; they should stand out "
                                "well, hence the {{...}} wrapping",
                                "{{%(text)s}}={{%(translation)s}} "
                                "at %(file)s:%(line)d(#%(entry)d)",
                                text=_to_uiref(nmsg),
                                translation=nmsg.msgstr[0],
                                file=uicat.filename,
                                line=nmsg.refline, entry=nmsg.refentry)
                else:
                    approx1 = _("@item condensed display of text without "
                                "translation; it should stand out "
                                "well, hence the {{...}} wrapping",
                                "{{%(text)s}}=(untranslated) "
                                "at %(file)s:%(line)d(#%(entry)d)",
                                text=_to_uiref(nmsg),
                                file=uicat.filename,
                                line=nmsg.refline, entry=nmsg.refentry)
                approx.append(approx1)
        if approx:
            errmsgs.append(_("@info",
                             "UI reference '%(ref)s' cannot be resolved; "
                             "close matches:\n"
                             "%(matches)s",
                             ref=uitext, matches=cjoin(approx, "\n")))
        else:
            errmsgs.append(_("@info",
                             "UI reference '%(ref)s' cannot be resolved.",
                             ref=uitext))

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
            errmsgs.append(_("@info",
                             "Placeholder '%(plhold)s' not found in resolved "
                             "UI reference text '%(text)s' "
                             "to reference '%(ref)s'.",
                             plhold=plhold, text=ruitext, ref=uitext))

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


# Split UI reference path as [(ptext, ref1), (sep, ref2), (sep, ref3), ...]
def _split_uirefpath (ptext, uirefpath, uipathseps):

    p = -1
    for sep in uipathseps:
        p = uirefpath.find(sep)
        if p >= 0:
            break
    if p < 0:
        return [(ptext, uirefpath)]
    else:
        rsplit = uirefpath.split(sep)
        return zip([ptext] + [sep] * (len(rsplit) - 1), rsplit)

