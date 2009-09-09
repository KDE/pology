# -*- coding: UTF-8 -*-

"""
Constructors of macro-declinators.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import os
import re

from pology.misc.macrodec import Declinator, Combinator
from pology.misc.normalize import identify, xentitize
from pology.l10n.sr.hook.cyr2lat import cyr2lat_stripped
from pology.l10n.sr.hook.nobr import to_nobr_hyphens
from pology.l10n.sr.hook.nobr import nobrhyp_char
from pology.misc.resolve import first_to_upper
from pology.misc.fsops import collect_files_by_ext


_suff_pltext = 10
_suff_tronly = 20
_suff_ltmarkup = 30

_markup_plain = "plain"
_markup_xml = "xml"
_markup_docbook4 = "docbook4"
_all_markups = (_markup_plain, _markup_xml, _markup_docbook4)


latin_modifier = "@latin"

autoalt_head = u"~@"
autoalt_sep = u"¦"


def build_declinator (mdfiles,
                      markup=_markup_plain, tagmap={},
                      ptsuff=None, tosuff=None, ltsuff=None,
                      pnfnend=None, pnodkey=None,
                      nobrhyp=False,
                      ndkeyto=None,
                      lmod=None):
    """
    Main declinator builder, covering all options.

    The declinator automatically sets and behaves as follows:

      - The entry and declination key separator is ASCII hyphen (C{-}).

      - All entry phrases are turned into entry keys by applying
        the L{identify()<misc.macrodec.identify>} function.
        Of particular note is that any non-ASCII characters will be
        eliminated from the key, therefore entries with such phrases
        should probably be given dummy additional pure-ASCII phrases.

      - All declination keys are transliterated into
        L{stripped-ASCII<l10n.sr.hook.cyr2lat.cyr2lat_stripped>} forms.

      - Conflict resolution is relaxed (see documentation on
        L{declinator construction<misc.macrodec.Declinator.__init__>}).

    Optional behavior includes:

      - Instead of plain text, declinations may be reported with some markup.
        The markup type is given by C{markup} parameter, and can be one of
        C{"plain"}, C{"xml"}, C{"docbook4"}.
        The C{tagmap} parameter contains mapping of base entry keys
        to tags which should equip declinations for these keys.

      - Entry keys can have several suffixes which effect how declinations
        are reported.
        Presence of the suffix given by C{ptsuff} parameter signals that
        declination should be forced to plain text, if another markup is
        in effect.
        Suffix given by C{tosuff} signals that declination should contain
        only translated/transliterated version, and not the original too,
        where these to would be returned by default (e.g. people names).
        Parameter C{ltsuff} states suffix which produces lighter version
        of the markup, where applicable (e.g. people names in Docbook).

      - Some macrodec files may contain names of people (e.g. authors,
        contributors of any kind), for which special processing may be desired:
        declinations by default to be returned with original name (or names)
        in parenthesis, and with automatic markup if applicable (e.g. Docbook).
        The C{pnfnend} parameter states the ending of the base filename
        (without extension) of macrodec files to be treated like this.
        It is assumed that the original name is the entry phrase,
        but another original name can be given by a declination
        (e.g. to show both real original name and English transliteration);
        the C{pnodkey} parameter is used to state the declination key which,
        if present, points to the second original name.

      - Ordinary hyphens may be converted into non-breaking hyphens
        by setting the C{nobrhyp} parameter to C{True}.
        Non-breaking hyphens are added heuristically, see
        the L{to_nobr_hyphens()<l10n.sr.hook.nobr.to_nobr_hyphens>} hook.
        Useful e.g. to avoid wrapping on hyphen-separated case endings.

      - Declination key normally cannot be empty, but C{ndkeyto} can
        be used to automatically substitute another declination key
        when empty key is encountered.
        In the lighter version, value of C{ndkeyto} is just a string
        of the key to substitute for empty.
        In the heavier version, the value is a tuple key to substitute,
        and list of two or more supplemental declination keys: empty key
        is replaced only if all declinations by supplemental keys exist and
        are equal (see e.g. L{build_declinator_ui} for usage of this).

      - If a macrodec file has version in Cyrillic and Latin script,
        such that both have same sets of entries by phrases,
        they can be united to produce combined declinations as
        L{alternative directives<misc.resolve.resolve_alternatives>}.
        The C{lmod} parameter is used to give the modifier to file name
        for Latin script (usually C{"@latin"}) which engages combining
        for each file that has counterpart with this modifier.
        If an entry phrase does not exist in both files, it is dropped
        (i.e. entry keys are produced as set intersection).

    @param mdfiles: list of paths of macrodec files
    @type mdfiles: list of strings
    @param markup: target markup
    @type markup: string
    @param tagmap: tags to assign to declinations by entry keys
    @type tagmap: dict string -> string
    @param ptsuff: entry key suffix to report "plain text" declinations
    @type ptsuff: string
    @param tosuff: entry key suffix to report "translation only" declinations
    @type tosuff: string
    @param ltsuff: entry key suffix to report "lighter markup" declinations
    @type ltsuff: string
    @param pnfnend: ending of macrodec base filename which contain people names
    @type pnfnend: string
    @param pnodkey: declination key of second original person's name
    @type pnodkey: string
    @param nobrhyp: whether to convert some ordinary into non-breaking hyphens
    @type nobrhyp: bool
    @param ndkeyto: declination key to substitute for empty key, when given
    @type ndkeyto: string or (string, [strings])
    @param lmod: modifier for Latin-version macrodec files, to engage combining
    @type lmod: string

    @returns: declinator
    @rtype: L{Declinator<misc.macrodec.Declinator>} or
            L{Combinator<misc.macrodec.Combinator>}
    """

    if markup not in _all_markups:
        raise StandardError("unknown markup '%s' for macro-declinator "
                            "(known markups: %s)"
                            % (markup, " ".join(_all_markups)))

    # Setup up requests by declination entry key ending.
    mvends = {}
    if ptsuff:
        mvends[ptsuff] = _suff_pltext
    if tosuff:
        mvends[tosuff] = _suff_tronly
    if ltsuff:
        mvends[ltsuff] = _suff_ltmarkup

    exdkeys = []
    if isinstance(ndkeyto, tuple):
        ndkeyto, exdkeys = ndkeyto

    # Check whether the source is containing tagged people names.
    _is_pn_rx = re.compile(pnfnend and (r"%s(\.\w+)?$" % pnfnend) or "$^")
    def is_pn_source (source):
        source_mod = lmod and source.replace(lmod, "") or source
        return bool(_is_pn_rx.search(source_mod))

    # Create transformators.
    ekeytf = _md_ekey_transf(mvends, tagmap)
    dkeytf = _md_dkey_transf(ndkeyto, exdkeys)
    dvaltf = _md_dval_transf(markup, nobrhyp, is_pn_source, pnodkey)

    # Build two declinators if dual script is in effect, otherwise single.
    pnodkeys = pnodkey and [pnodkey] or []
    mdecs = [Declinator(edsep="-",
                        ekeyitf=identify,
                        dkeyitf=cyr2lat_stripped,
                        ekeytf=ekeytf,
                        dkeytf=(dkeytf, False, False, False, exdkeys),
                        dvaltf=(dvaltf, True, True, True, True, pnodkeys))
             for x in range(lmod and 2 or 1)]

    # Import macrodec files into appropriate declinators.
    for mdfile in mdfiles:
        ekeyitf1, dvaltf1, phrasetf1 = [None] * 3
        if is_pn_source(mdfile):
            phrasetf1 = lambda x: _compose_person_name(x, markup=_markup_plain)
            ekeyitf1 = lambda x: _compose_person_name(x, markup=_markup_plain)
        mdec = (lmod and lmod in mdfile) and mdecs[1] or mdecs[0]
        mdec.import_file(mdfile, ekeyitf1=ekeyitf1, dvaltf1=dvaltf1,
                                 phrasetf1=phrasetf1)

    # Combine declinators if dual script in effect.
    if lmod:
        dvalcf = _md_dval_combf()
        mdec = Combinator(mdecs, dvalcf)
    else:
        mdec = mdecs[0]

    return mdec


def build_declinator_ui (mdfiles):
    """
    Builds a declinator suitable for application UI texts.

    Calls L{build_declinator} with the following setup:

      - Markup is plain text (C{plain}).

      - Suffixes: C{_sp} ("samo prevod") for translation-only declinations.

      - Macrodec files ending in C{_pn} are considered to contain people names,
        and by default declinations return with original in parenthesis.
        Declination key C{oo} is set to pick up secondary original name.

      - Non-breaking hyphens are heuristically replacing ordinary hyphens.

      - Empty declination key is converted into C{am} (accusative masculine
        descriptive adjective), providing that it is equal to C{gm}
        (genitive masculine descriptive adjective);
        i.e. if the descriptive adjective is invariable.

      - Files with C{@latin} modifier are picked up as Latin script variants
        of same-name ordinary file, and their declinations combined
        by alternative directives.

    @param mdfiles: macrodec file paths
    @type mdfiles: list of strings

    @returns: declinator
    """

    return build_declinator(
        mdfiles,
        markup="plain",
        tosuff="_sp", # for "samo prevod"
        pnfnend="_pn", # for "people names"
        pnodkey="oo",
        nobrhyp=True,
        ndkeyto=("am", ("am", "gm")),
        lmod=latin_modifier,
    )


def build_declinator_docbook4 (mdfiles, tagmap={}):
    """
    Builds a declinator suitable for Docbook texts.

    Calls L{build_declinator} with the following setup:

      - Markup is Docbook 4 (C{docbook4}).

      - Suffixes: C{_sp} ("samo prevod") for translation-only declinations,
        C{_ot} ("obican tekst") for plain-text declinations,
        C{_lv} ("laksa varijanta") for lighter version of markup.
        Lighter markup applied to people names, when outer C{<personname>}
        should be stripped (e.g. when it should not be present due to
        particular text segmentation of Docbook->PO extraction).

      - Macrodec files ending in C{_pn}, non-breaking hyphens,
        empty declination keys and C{@latin} files are treated same
        as in L{build_declinator_ui}

    @param mdfiles: macrodec file paths
    @type mdfiles: list of strings
    @param tagmap: tags to assign to declinations by entry keys
    @type tagmap: dict string -> string

    @returns: declinator
    """

    return build_declinator(
        mdfiles,
        markup="docbook4",
        tagmap=tagmap,
        ptsuff="_ot", # for "obican text"
        tosuff="_sp", # for "samo prevod"
        ltsuff="_lv", # for "laksa varijanta"
        pnfnend="_pn", # for "people names"
        pnodkey="oo",
        nobrhyp=True,
        ndkeyto=("am", ("am", "gm")),
        lmod=latin_modifier,
    )


def build_declinator_by_env (buildf, mdpathenv, recurse=True):
    """
    Build declinator by applying a function to macrodec files collected
    by environment variable.

    Instead of manually collecting files to send to a declinator builder,
    this function can be used to automatically collect them from
    directory paths given by environment variable (colon-separated),
    and send them to a builder function.

    @param buildf: function to apply to collected files
    @type buildf: callable
    @param mdpathenv: environment variable with colon-separated directory paths
    @type mdpathenv: string
    @param recurse: whether to search directories recursively
    @type recurse: bool

    @returns: declinator
    """

    mdpath = os.getenv(mdpathenv)
    if mdpath is None:
        warning("environment variable with macrodec directory paths '%s' "
                "not set" % mdpathenv)
        mdpath = ""

    mdfilepaths = collect_files_by_ext(mdpath.split(":"),
                                       ["frm", "md", "mdec"])
    return buildf(mdfilepaths)


def build_declinator_ui_by_env (mdpathenv, recurse=True):
    """
    Version of L{build_declinator_ui} that collects macrodec files
    by environment variable.

    See L{build_declinator_ui} for declinator building parameters,
    and L{build_declinator_by_env} for collecting files by environment.
    """

    buildf = lambda x: build_declinator_ui(x)
    return build_declinator_by_env(buildf, mdpathenv, recurse)


def build_declinator_docbook4_by_env (mdpathenv, recurse=True, tagmap={}):
    """
    Version of L{build_declinator_docbook4} that collects macrodec files
    by environment variable.

    See L{build_declinator_docbook4} for declinator building parameters,
    and L{build_declinator_by_env} for collecting files by environment.
    """

    buildf = lambda x: build_declinator_docbook4(x, tagmap)
    return build_declinator_by_env(buildf, mdpathenv, recurse)


# Transformation for entry keys of all declination entries (internal).
def _md_ekey_transf (endings, tagmap):

    def transf (name):

        # Should the value have first letter uppercased?
        fcap = name[0:1].isupper()
        if fcap:
            name = name[0].lower() + name[1:]

        # Collect and strip all known special endings.
        found_endings = set()
        while True:
            plen_endings = len(found_endings)
            for ending in endings:
                if name.endswith(ending):
                    name = name[:-len(ending)]
                    found_endings.add(ending)
            if len(found_endings) == plen_endings:
                break

        found_reqs = set([endings[x] for x in found_endings])

        # Tag to equip declinations of this entry with.
        # Do not equip if manually requested so.
        tagged = _suff_pltext not in found_reqs
        tag = tagged and tagmap.get(name) or None

        # Whether not to add original in parenthesis.
        noorig = _suff_tronly in found_reqs

        # Whether to use lighter markup variant.
        ltmarkup = _suff_ltmarkup in found_reqs

        return name, (fcap, tagged, tag, noorig, ltmarkup)

    return transf


# Transformation for all declination values:
# - capitalize on request from key processing
# - add tags on request from key processing
# - optionally replace ordinary with no-break hyphens
def _md_dval_transf (markup, nobrhyp, ispnsrcf, oodkey):

    to_nobr_hyph = to_nobr_hyphens(unsafe=True)

    tagsubs="%(v)s"
    vescape = None
    if markup in (_markup_xml, _markup_docbook4):
        tagsubs = "<%(t)s>%(v)s</%(t)s>"
        vescape = xentitize

    def transf (value, iscut, etfres, source, phrases, valmap):

        fcap, tagged, tag, noorig, ltmarkup = etfres[:5]

        ispnsrc = ispnsrcf(source)

        if ispnsrc and not iscut:
            otnames = []
            if oodkey and not noorig:
                otnames = filter(lambda x: x is not None,
                                # first real, then quasi original name
                                (valmap.get(oodkey), phrases[0]))
            rmarkup = tagged and markup or _markup_plain
            value = _compose_person_name(value, otnames, rmarkup, ltmarkup, fcap)

        else:
            if nobrhyp: # before tagging and escaping
                value = to_nobr_hyph(value)
            if fcap: # before tagging
                value = first_to_upper(value)
            if vescape: # before tagging
                value = vescape(value)
            if tag:
                value = tagsubs % dict(t=tag, v=value)

        return value

    return transf


# Transformation for declination values of person names (internal):
# - capitalize if requested
# - add quasi and real original name in parenthesis (unless requested otherwise)
# - add one of two variants of given markup (unless requested otherwise)
def _md_dval_transf_pn (markup, oodkey):

    return transf


# Transformation for all declination keys (query):
# - try to transform empty into non-empty key
def _md_dkey_transf (ndkeyto, ndkey_eqdkeys):

    def transf (dkey, valmap):

        # If key not empty, return it as-is.
        if dkey:
            return dkey

        # Empty ending allowed if all declinations requested
        # by supplementary keys are both existing and equal.
        # In that case, report the indicated key instead of empty.
        alleq = True
        ref_dval = None
        for tdkey in ndkey_eqdkeys:
            dval = valmap.get(tdkey)
            if dval is None:
                alleq = False
                break
            if ref_dval is None:
                ref_dval = dval
            elif ref_dval != dval:
                alleq = False
                break
        if alleq:
            return ndkeyto
        else:
            return dkey

    return transf


# Combining of Cyrillic and Latin declinations into alternative directives.
def _md_dval_combf ():

    def combf (values):

        return autoalt_head + autoalt_sep.join([""] + values + [""])

    return combf


_pn_tag_first = (u"i", u"и")
_pn_tag_last = (u"p", u"п")
_pn_tag_middle = (u"s", u"с")
_pn_tag_ignore = (u"x",)
_pn_all_tags = []
for tags in (_pn_tag_first, _pn_tag_last, _pn_tag_middle, _pn_tag_ignore):
    _pn_all_tags.extend(tags)

# Construct name composition out of tagged translated and
# real/quasi original names.
# May return None if some of the tagged names cannot be parsed.
def _compose_person_name (tname, otnames=[], markup=_markup_plain,
                          light=False, fcap=False):

    # Split name components from composite markup names.
    nsplit = _split_tagged_name(tname)
    if not nsplit: # translated name must be ok
        return None
    # Original names may be wrongly tagged, any such will be omitted.
    onsplits = filter(lambda x: x, map(_split_tagged_name, otnames))

    # Capitalize first letter of the first string of the composed name.
    if fcap:
        nsplit[0] = (nsplit[0][0], first_to_upper(nsplit[0][1]))

    if markup == _markup_docbook4:
        # Construct original names as ordinary text.
        names_o = []
        for onsplit in onsplits:
            name_o = " ".join([seg for tag, seg in onsplit])
            names_o.append(xentitize(name_o))

        # Add translated name with proper tagging.
        name_segs = []
        for tag, seg in nsplit:
            seg = xentitize(seg)
            if tag in _pn_tag_first:
                name_segs.append("<firstname>%s</firstname>" % seg)
            elif tag in _pn_tag_last:
                name_segs.append("<surname>%s</surname>" % seg)
            elif tag in _pn_tag_middle:
                name_segs.append("<othername>%s</othername>" % seg)
            else: # untagged
                name_segs.append("%s" % seg)
        name = "".join(name_segs)

        # Add original names.
        # There's just no other way to add original but inside one of
        # the other nodes of personname #*@^&%!
        if names_o:
            for kludge_tag in ("lineage", "surname", "othername", "firstname"):
                p = name.rfind("</" + kludge_tag)
                if p >= 0:
                    names_o_fmt = (" (%s)" % ", ".join(names_o))
                    name = name[:p] + names_o_fmt + name[p:]
                    break

        if not light:
            name = "<personname>%s</personname>" % name

        return name

    else:
        # Translated name.
        name = " ".join([seg for tag, seg in nsplit])

        # Add original names.
        names_o = []
        for onsplit in onsplits:
            name_o = " ".join([seg for tag, seg in onsplit])
            names_o.append(name_o)
        if names_o:
            name += " (%s)" % ", ".join(names_o)

        return name


# Split tagged person name into segments.
# See formdefs/contributors.frm for markup description.
# Return ordered list of 2-tuples, first element the tag, second the string.
# If the tagged name is not valid, return None.
def _split_tagged_name (tname):

    raw_els = tname.split("/")
    if len(raw_els) == 1:
        # Untagged name. Return as single empty-tagged element.
        return [("", raw_els[0])]
    nsplit = []
    ntag = raw_els[0]
    for i in range(1, len(raw_els) - 1):
        tag = ntag
        # Split the element into name segment and tag of next segment.
        tmp = raw_els[i].rsplit(" ", 1)
        if len(tmp) != 2:
            raise StandardError("invalid tagged person name '%s', "
                                "cannot split '%s'" % (tname, raw_els[i]))
            return None
        seg, ntag = tmp
        # Add current name segment.
        nsplit.append((tag.strip(), seg.strip()))
    # Final name segment.
    nsplit.append((ntag.strip(), raw_els[-1].strip()))

    # Check validity.
    for tag, seg in nsplit:
        if tag not in _pn_all_tags:
            raise StandardError("invalid tagged person name '%s', "
                                "unknown tag '%s'" % (tname, tag))
            return None
        elif tag in _pn_tag_ignore:
            # Name manually ignored.
            return None

    return nsplit

