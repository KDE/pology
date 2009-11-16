# -*- coding: UTF-8 -*-

"""
Constructors of syntagma derivators for trapnakron.

Trapnakron -- transcriptions and translation of names and acronyms --
is a collection of syntagma derivator definitions residing in
C{pology/l10n/sr/trapnakron/}.
Its purpose is to support translation efforts in Serbian language,
where proper nouns and acronyms are frequently transcribed,
and sometimes translated.
For translators, it can be a manual reference, or even directly sourced
in translated material (see below).
For readers, it is a way to obtain original forms of transcribed and
translated phrases.

Trapnakron web pages are built based on trapnakron source in Pology.
This makes links between original and localized forms readily
available through internet search engines.
Adding C{trapnakron} or C{трапнакрон} keyword to the search phrase
causes the relevant trapnakron page to appear within top few hits,
and the desired other form will be shown already in the excerpt of the hit,
such that is not even necessary to follow it.
This frees translators from the burden of providing original forms
in parenthesis to the first mentioning (or some similar method),
and frees the text of the clutter caused by this.

While trapnakron definitions may be manually collected and imported into
a basic L{Synder<pology.misc.synder.Synder>} object, this module provides
wrappers which free the user of this manual work, as well as appropriate
transformation functions (C{*tf} parameters to C{Synder} constructor)
to produce various special behaviors on lookups.
Trapnakron constructors are defined by type of textual material,
e.g. for plain text or Docbook documentation.
Documentation of each constructor states what special lookup behaviors
will be available through C{Synder} objects created by it.

For a short demonstration, consider this derivation of a person's name::

    钱学森, Qián Xuésēn, Tsien Hsue-shen: Ћен| Сјуесен|

Suppose that a translator wants to source it directly in the text,
rather than to manually copy the transcription (e.g. to avoid having
to update the text should the transcription be modified in the future).
The translator therefore writes, using XML entity syntax::

    ...пројектовању ракета &qianxuesen-g; привукле су идеје...

where C{-g} denotes genitive case.
This text can be easily processed into the final form (before going out
to readers), using a script based on these few lines::

    >>> from pology.l10n.sr.trapnakron import trapnakron_plain
    >>> from pology.misc.resolve import resolve_entities_simple as resents
    >>> tp = trapnakron_plain()
    >>>
    >>> s = u"...пројектовању ракета &qianxuesen-g; привукле су идеје..."
    >>> print resents(s, tp)
    ...пројектовању ракета Ћена Сјуесена привукле су идеје...
    >>>


@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import os
import re

from pology.misc.synder import Synder
from pology.misc.normalize import identify, xentitize, simplify
from pology.l10n.sr.hook.wconv import ctol, cltoa
from pology.l10n.sr.hook.wconv import hctoc, hctol, hitoe, hitoi, hctocl
from pology.l10n.sr.hook.wconv import cltoh, eitoh
from pology.l10n.sr.hook.nobr import to_nobr_hyphens
from pology.l10n.sr.hook.nobr import nobrhyp_char
from pology.misc.resolve import first_to_upper
from pology.misc.fsops import collect_files_by_ext
import pology


# Allowed environment compositions, out of, in order:
# Ekavian Cyrillic, Ekavian Latin, Ijekavian Cyrillic, Ijekavian Latin.
# 1 indicates environment present, 0 absent.
_good_eicl_combos = set((
    "1000", "0100", "0010", "0001",
    "1100", "0011", "1010", "0101",
    "1111",
))

# Elements for composing alternatives directives.
_alt_sep_scr = u"¦|/"
_alt_sep_dlc = u"¦|/"

# Elements for composing hybridization directives.
_hyb_tag = u"›" # must match runtime
_hyb_head = u"~#" # must match runtime
_hyb_sep = u"⁝"

# Keywords of known target markups.
_known_markups = (
    "plain",
    "xml",
    "docbook4",
)

# Tags found within people names (groups of synonyms).
_pn_tag_first = (u"i", u"и")
_pn_tag_last = (u"p", u"п")
_pn_tag_middle = (u"s", u"с")
_pn_all_tags = set(sum((_pn_tag_first, _pn_tag_last, _pn_tag_middle), ()))

# Tag for derivations with unimportant keys.
_nokey_tag = "x"

# Disambiguation marker.
_disamb_marker = u"¤"

# Enumeration of known derivation key suffixes, for modifying derived values.
_suff_pltext = "_ot" # for "obican tekst"
_suff_pltext_id = 10
_suff_ltmarkup = "_lv" # for "laksa varijanta"
_suff_ltmarkup_id = 20
_suff_gematch_m = "_rm" # for "rod muski"
_suff_gematch_m_id = 30
_suff_gematch_z = "_rz" # for "rod zenski"
_suff_gematch_z_id = 31
_suff_gematch_s = "_rs" # for "rod srednji"
_suff_gematch_s_id = 32
_suff_gematch_u = "_ru" # for "rod muski zivi"
_suff_gematch_u_id = 33
_gematch_suffs = [_suff_gematch_m, _suff_gematch_z,
                  _suff_gematch_s, _suff_gematch_u]
_gematch_suff_ids = [_suff_gematch_m_id, _suff_gematch_z_id,
                     _suff_gematch_s_id, _suff_gematch_u_id]
_gematch_suff_ids_set = set(_gematch_suff_ids)
_gematch_suffs_genders = [
    (_suff_gematch_m_id, (u"м", u"m")),
    (_suff_gematch_z_id, (u"ж", u"ž")),
    (_suff_gematch_s_id, (u"с", u"s")),
    (_suff_gematch_u_id, (u"у", u"u")),
]
_suff_systr = "_s" # for "sistemska transkripcija"
_suff_systr_id = 40
_systr_ksuff_esuff = (_suff_systr, u"сист")
_suff_altdv1 = "_a" # for "alternativno izvodjenje"
_suff_altdv1_id = 50
_suff_altdv2 = "_a2" # second alternative
_suff_altdv2_id = 51
_suff_altdv3 = "_a3" # third alternative
_suff_altdv3_id = 52
_altdv_ksuffs_esuffs = [
    (_suff_altdv1, u"алт"),
    (_suff_altdv2, u"алт2"),
    (_suff_altdv3, u"алт3"),
]
_aenv_suff_ids = [_suff_systr_id, # order of elements significant
                  _suff_altdv1_id, _suff_altdv2_id, _suff_altdv3_id]
_aenv_suff_ids_set = set(_aenv_suff_ids)


def trapnakron (envec=u"", envel=u"л", envic=u"иј", envil=u"ијл",
                markup="plain", tagmap=None,
                ptsuff=None, ltsuff=None, gesuff=None,
                stsuff=None, adsuff=None,
                npkeyto=None, nobrhyp=False, disamb="",
                runtime=False):
    """
    Main trapnakron constructor, covering all options.

    The trapnakron constructor sets, either by default or optionally,
    various transformations to enhance queries to the resulting derivator.

    Default Behavior
    ================

    Property values are returned as alternatives/hybridized compositions of
    Ekavian Cyrillic, Ekavian Latin, Ijekavian Cyrillic, and Ijekavian Latin
    forms, as applicable.
    Any of these forms can be excluded from derivation by setting
    its C{env*} parameter to C{None}.
    C{env*} parameters can also be used to change the priority environment
    from which the particular form is derived.

    Derivation and property key separator in compound keys is
    the ASCII hyphen (C{-}).

    Derivation keys are derived from syntagmas by applying
    the L{identify()<misc.normalize.identify>} function.
    In derivations where this will result in strange keys,
    additional keys should be defined through hidden syntagmas.
    Property keys are transliterated into
    L{stripped-ASCII<l10n.sr.hook.wconv.cltoa>}.

    Conflict resolution for derivation keys is not strict
    (see L{derivator constructor<misc.synder.Synder.__init__>}).

    Optional behavior
    =================

    Instead of plain text, properties may be reported with some markup.
    The markup type is given by C{markup} parameter, and can be one of
    C{"plain"}, C{"xml"}, C{"docbook4"}.
    The C{tagmap} parameter contains mapping of derivation keys
    to tags which should wrap properties of these derivations.

    Derivation keys can have several suffixes which effect how
    the properties are reported:
      - Presence of the suffix given by C{ptsuff} parameter signals that
        properties should be forced to plain text, if another markup is
        globally in effect.
      - Parameter C{ltsuff} states the suffix which produces lighter version
        of the markup, where applicable (e.g. people names in Docbook).
      - When fetching a property within a sentence (with keys given e.g.
        as XML entities), sentence construction may require that
        the resolved value is of certain gender; parameter C{gesuff}
        can be used to provide a tuple of 4 gender suffixes,
        such that the property will resolve only if the value of gender
        matches the gender suffix.
      - Parameters C{stsuff} and C{adsuff} provide suffixes through
        which systematic transcription and alternative derivations
        are requested.
        They are actually tuples, where the first element is the key suffix,
        and the second element the suffix to primary environment
        which produces the systematic/alternative environment.
        C{adsuff} can also be a tuple of tuples, if several alternative
        derivations should be reachable.

    Ordinary hyphens may be converted into non-breaking hyphens
    by setting the C{nobrhyp} parameter to C{True}.
    Non-breaking hyphens are added heuristically, see
    the L{to_nobr_hyphens()<l10n.sr.hook.nobr.to_nobr_hyphens>} hook.
    Useful e.g. to avoid wrapping on hyphen-separated case endings.

    A property key normally cannot be empty, but C{npkeyto} parameter
    can be used to automatically substitute another property key
    when empty property key is seen in request for properties.
    In the simpler version, value of C{npkeyto} is just a string
    of the key to substitute for empty.
    In the more complex version, the value is a tuple containing
    the key to substitute and the list of two or more supplemental
    property keys: empty key is replaced only if all supplemental
    property values exist and are equal (see e.g. L{trapnakron_plain}
    for usage of this).

    Some property values may have been manually decorated with
    disambiguation markers (C{¤}), to differentiate them from
    property values of another derivation which would otherwise appear
    equal under a certain normalization.
    By default such markers are removed, but instead they
    can be substituted with a string given by C{disamb} parameter.

    Some derivations are defined only for purposes of obtaining
    their properties in scripted translations at runtime.
    They are by default not included, but can be by setting
    the C{runtime} parameter to C{True}.

    @param envec: primary environment for Ekavian Cyrillic derivation
    @type envec: string or C{None}
    @param envel: primary environment for Ekavian Latin derivation
    @type envel: string or C{None}
    @param envic: primary environment for Ijekavian Cyrillic derivation
    @type envic: string or C{None}
    @param envil: primary environment for Ijekavian Latin derivation
    @type envil: string or C{None}
    @param markup: target markup
    @type markup: string
    @param tagmap: tags to assign to properties by derivation keys
    @type tagmap: dict string -> string
    @param ptsuff: derivation key suffix to report plain text properties
    @type ptsuff: string
    @param ltsuff: derivation key suffix to report properties in lighter markup
    @type ltsuff: string
    @param gesuff: suffixes by gender, to have no resolution if gender is wrong
    @type gesuff: [(string, string)*]
    @param stsuff: derivation key and environment name suffixes
        to report systematic transcriptions
    @type stsuff: (string, string)
    @param adsuff: derivation key and environment name suffixes
        to report alternative derivations
    @type adsuff: (string, string) or ((string, string)*)
    @param npkeyto: property key to substitute for empty key, when given
    @type npkeyto: string or (string, [string*])
    @param nobrhyp: whether to convert some ordinary into non-breaking hyphens
    @type nobrhyp: bool
    @param disamb: string to replace each disambiguation marker with
    @type disamb: string
    @param runtime: whether to include runtime-only derivations
    @type runtime: bool

    @returns: trapnakron derivator
    @rtype: L{Synder<misc.synder.Synder>}
    """

    env0s = [envec, envel, envic, envil]
    combo =  "".join([(x is not None and "1" or "0") for x in env0s])
    if combo not in _good_eicl_combos:
        raise StandardError("Invalid combination of Ekavian/Ijekavian "
                            "Cyrillic/Latin environments "
                            "to trapnakron derivator.")

    if markup not in _known_markups:
        raise StandardError("Unknown markup '%s' to trapnakron derivator "
                            "(known markups: %s)."
                            % (markup, " ".join(_known_markups)))

    # Compose environment fallback chains.
    env = []
    envprops = [] # [(islatin, isije)*]
    vd = lambda e, d: e if e is not None else d
    if envec is not None:
        env.append((envec,))
        envprops.append((False, False))
    if envel is not None:
        env.append((envel, vd(envec, u"")))
        envprops.append((True, False))
    if envic is not None:
        env.append((envic, vd(envec, u"")))
        envprops.append((False, True))
    if envil is not None:
        env.append((envil, vd(envel, u"л"), vd(envic, u"иј"), vd(envec, u"")))
        envprops.append((True, True))

    # Setup up requests by derivation key suffix.
    mvends = {}
    if ptsuff:
        mvends[ptsuff] = _suff_pltext_id
    if ltsuff:
        mvends[ltsuff] = _suff_ltmarkup_id
    if gesuff:
        if len(gesuff) != 4:
            raise StandardError("Sequence of gender suffixes must have "
                                "exactly 4 elements.")
        mvends.update(zip(gesuff, _gematch_suff_ids))
    aenvs = {}
    if adsuff or stsuff:
        kesuffs = [] # must have same order as _aenv_suff_ids
        if stsuff is not None:
            kesuffs.append(stsuff)
        if not isinstance(adsuff[0], tuple):
            kesuffs.append(adsuff)
        else:
            kesuffs.extend(adsuff)
        for (ksuff, esuff), suff_id in zip(kesuffs, _aenv_suff_ids):
            mvends[ksuff] = suff_id
            # Compose environment fallback chain for this suffix.
            aenv = []
            for env1 in env:
                aenv1 = []
                for env0 in env1:
                    aenv1.extend((env0 + esuff, env0))
                aenv.append(tuple(aenv1))
            aenvs[suff_id] = tuple(aenv)

    # Setup substitution of empty property keys.
    expkeys = []
    if isinstance(npkeyto, tuple):
        npkeyto, expkeys = npkeyto

    # Create transformators.
    dkeytf = _sd_dkey_transf(mvends, tagmap)
    pkeytf = _sd_pkey_transf(npkeyto, expkeys)
    pvaltf = _sd_pval_transf(envprops, markup, nobrhyp, disamb)
    ksyntf = _sd_ksyn_transf(markup, False, disamb)
    envtf = _sd_env_transf(aenvs)

    # Build the derivator.
    sd = Synder(env=env,
                ckeysep="-",
                dkeytf=dkeytf, dkeyitf=identify,
                pkeytf=pkeytf, pkeyitf=norm_pkey,
                pvaltf=pvaltf, ksyntf=ksyntf,
                envtf=envtf,
                strictkey=False)

    # Collect synder files composing the trapnakron.
    sdfiles = _get_trapnakron_files(runtime)

    # Import into derivator.
    for sdfile in sdfiles:
        sd.import_file(sdfile)

    return sd


def rootdir ():
    """
    Get root directory to trapnakron derivation files.

    @returns: root directory path
    @rtype: string
    """

    return os.path.join(pology.rootdir(), "l10n", "sr", "trapnakron")


def _get_trapnakron_files (runtime=False):

    root = rootdir()
    files = collect_files_by_ext(root, ["sd"], recurse=False)
    if runtime:
        rtroot = os.path.join(root, "runtime")
        rtfiles = collect_files_by_ext(rtroot, ["sd"], recurse=False)
        files.extend(rtfiles)

    return files


def trapnakron_plain (envec=u"", envel=u"л", envic=u"иј", envil=u"ијл"):
    """
    Constructs trapnakron suitable for application to plain text.

    Calls L{trapnakron} with the following setup:

      - Markup is plain text (C{plain}).

      - Suffixes: C{_rm} ("rod muski") for resolving the property value only
        if it is of masculine gender, C{_rz} for feminine, C{_rs} for neuter;
        C{_s} for systematic transcription, C{_a}, C{_a2} and C{_a3} for
        other alternatives.

      - Non-breaking hyphens are heuristically replacing ordinary hyphens.

      - Empty property key is converted into C{am} (accusative masculine
        descriptive adjective), providing that it is equal to C{gm}
        (genitive masculine descriptive adjective);
        i.e. if the descriptive adjective is invariable.
    """

    return trapnakron(
        envec, envel, envic, envil,
        markup="plain",
        gesuff=_gematch_suffs,
        stsuff=_systr_ksuff_esuff,
        adsuff=_altdv_ksuffs_esuffs,
        npkeyto=("am", ("am", "gm")),
        nobrhyp=True,
    )


def trapnakron_ui (envec=u"", envel=u"л", envic=u"иј", envil=u"ијл"):
    """
    Constructs trapnakron suitable for application to UI texts.

    Like L{trapnakron_plain}, except that disambiguation markers
    are not removed but substituted with an invisible character,
    and runtime-only derivations are included too.

    Retaining disambiguation markers is useful when a normalized form
    (typically nominative) is used at runtime as key to fetch
    other properties of the derivation,
    and the normalization is such that it would fold two different
    derivations to same keys if the originating forms were left undecorated.
    """

    return trapnakron(
        envec, envel, envic, envil,
        markup="plain",
        gesuff=_gematch_suffs,
        stsuff=_systr_ksuff_esuff,
        adsuff=_altdv_ksuffs_esuffs,
        npkeyto=("am", ("am", "gm")),
        nobrhyp=True,
        disamb=u"\u2060",
        runtime=True,
    )


def trapnakron_docbook4 (envec=u"", envel=u"л", envic=u"иј", envil=u"ијл",
                         tagmap=None):
    """
    Constructs trapnakron suitable for application to Docbook 4 texts.

    Calls L{trapnakron} with the following setup:

      - Markup is Docbook 4 (C{docbook4}).

      - Suffixes: C{_ot} ("obican tekst") for plain-text properties,
        C{_lv} ("laksa varijanta") for lighter variant of the markup.
        Lighter markup currently applies to: people names
        (no outer C{<personname>}, e.g. when it should be elideded due to
        particular text segmentation on Docbook->PO extraction).
        Also the suffixes as for L{trapnakron_plain}.

      - Non-breaking hyphens and empty property keys
        are treated like in L{trapnakron_plain}.
    """

    return trapnakron(
        envec, envel, envic, envil,
        markup="docbook4",
        tagmap=tagmap,
        ptsuff=_suff_pltext,
        ltsuff=_suff_ltmarkup,
        gesuff=_gematch_suffs,
        stsuff=_systr_ksuff_esuff,
        adsuff=_altdv_ksuffs_esuffs,
        npkeyto=("am", ("am", "gm")),
        nobrhyp=True,
    )


# Transformation for derivation keys:
# - lowercase first letter if upper-case, and indicate value uppercasing
# - strip special suffixes and indicate value modifications based on them
def _sd_dkey_transf (suffspec, tagmap):

    def transf (dkey, sd):

        # Whether to uppercase the first letter of properties.
        fcap = dkey[0:1].isupper()
        if fcap:
            dkey = dkey[0].lower() + dkey[1:]

        # Collect and strip all known special suffixes.
        found_suff_ids = set()
        while True:
            plen_suff_ids = len(found_suff_ids)
            for suff, suff_id in suffspec.items():
                if dkey.endswith(suff):
                    dkey = dkey[:-len(suff)]
                    found_suff_ids.add(suff_id)
            if len(found_suff_ids) == plen_suff_ids:
                break

        # Tag which wraps the property values of this derivation.
        tag = tagmap.get(dkey) if tagmap else None

        # Whether to use plain text instead of markup, where applicable.
        pltext = _suff_pltext_id in found_suff_ids

        # Whether to use lighter variant of the markup, where applicable.
        ltmarkup = _suff_ltmarkup_id in found_suff_ids

        # Whether the gender is matching.
        if _gematch_suff_ids_set.intersection(found_suff_ids):
            gstr = sd.get2(dkey, "_rod")
            genders = list(set(map(ctol, hctocl(gstr)))) if gstr else []
            if (   not (len(genders) == 1)
                or not all([(x[0] not in found_suff_ids or genders[0] in x[1])
                            for x in _gematch_suffs_genders])
            ):
                dkey = None

        # Whether to use one of alternative environments.
        esuffid = None
        found_aenv_suff_ids = _aenv_suff_ids_set.intersection(found_suff_ids)
        if found_aenv_suff_ids:
            esuffid = tuple(found_aenv_suff_ids)[0]

        return dkey, fcap, tag, ltmarkup, pltext, esuffid

    return transf, "self"


# Transformation for property keys:
# - try to convert empty into non-empty key
def _sd_pkey_transf (npkeyto, npkey_eqpkeys):

    def transf (pkey, dkey, sd):

        # If key not empty, return it as-is.
        if pkey:
            return pkey

        # Empty ending allowed if all properties requested
        # by supplementary keys are both existing and equal.
        # In that case, report the indicated key instead of empty.
        alleq = True
        ref_pval = None
        for tpkey in npkey_eqpkeys:
            pval = sd.get2(dkey, tpkey)
            if pval is None:
                alleq = False
                break
            if ref_pval is None:
                ref_pval = pval
            elif ref_pval != pval:
                alleq = False
                break
        if alleq:
            return npkeyto
        else:
            return pkey

    return transf, "dkey", "self"


# Transformation for property values:
# - capitalize on request from key processing
# - add tags on request from key processing
# - optionally replace ordinary with no-break hyphens
# - resolve known taggings according to selected markup
# - add outer tags according to selected markup
# - replace disambiguation markers with invisible characters
# - construct hybridized forms out of multiple values
# If the property key starts with underscore, only hybridization is performed.
def _sd_pval_transf (envprops, markup, nobrhyp, disamb):

    def transf (mtsegs, pkey, dkrest, sd):

        fcap, tag, ltmarkup, pltext, d5 = dkrest
        if pkey.startswith("_"):
            fcap = False
            tag = None
            pltext = True

        pvals = []
        for tsegs, (islatin, isije) in zip(mtsegs, envprops):
            if tsegs is None:
                return None
            pval1 = _compose_text(tsegs, markup, nobrhyp, disamb,
                                  fcap, tag, ltmarkup, pltext, islatin)
            pvals.append(pval1)

        pval = _hybridize(envprops, pvals)

        return pval

    return transf, "pkey", "dkrest", "self"


# Transformation for derivation syntagmas.
# Like for property value transformation,
# except for alternatives/hybridization.
def _sd_ksyn_transf (markup, nobrhyp, disamb):

    def transf (tsegs, dkrest, sd):

        fcap, tag, ltmarkup, pltext, d5 = dkrest

        ksyn = _compose_text(tsegs, markup, nobrhyp, disamb,
                             fcap, tag, ltmarkup, pltext)

        return ksyn

    return transf, "dkrest", "self"


# Transformation for derivation environments.
# Returns a non-default environment on request from keys processing.
def _sd_env_transf (aenvs):

    def transf (env, dkrest):

        d1, d2, d3, d4, esuffid = dkrest

        if esuffid is not None:
            return aenvs[esuffid]
        else:
            return env

    return transf, "dkrest"


def _compose_text (tsegs, markup, nobrhyp, disamb,
                   fcap, tag, ltmarkup, pltext, tolatin=False):

    # Tagging and escaping.
    tagsubs="%(v)s"
    vescape = None
    if markup in ("xml", "docbook4"):
        tagsubs = "<%(t)s>%(v)s</%(t)s>"
        vescape = xentitize

    # All unique tags to current segments.
    atags = set(sum([x[1] for x in tsegs], []))

    if atags.intersection(_pn_all_tags):
        # A person name.
        markup_mod = markup if not pltext else "plain"
        text = _compose_person_name(tsegs, fcap, markup_mod, ltmarkup)
    else:
        # Ordinary derivations.
        text = simplify("".join([x[0] for x in tsegs]))
        if _nokey_tag in atags and " " in text: # before anything else
            text = text[text.find(" "):].lstrip()
        if fcap: # before adding outer tags
            text = first_to_upper(text)
        if vescape: # before adding outer tags
            text = vescape(text)
        if tag and not pltext:
            text = tagsubs % dict(t=tag, v=text)

    text = text.replace(_disamb_marker, disamb or "")
    if nobrhyp: # before conversion to Latin
        text = to_nobr_hyphens(unsafe=True)(text)
    if tolatin:
        text = ctol(text)

    return text


# Combine Ekavian/Ijekavian Cyrillic/Latin forms
# into hybrid Ijekavian Cyrillic text.
def _hybridize (envprops, pvals):

    if len(envprops) == 4: # different scripts and dialects
        cvalc = eitoh(pvals[0], pvals[2], delims=_alt_sep_dlc)
        cvall = eitoh(pvals[1], pvals[3], delims=_alt_sep_dlc)
        if ctol(cvalc) != cvall:
            cval = cltoh(cvalc, cvall, delims=_alt_sep_scr, full=True)
        else:
            cval = cvalc
    elif len(envprops) == 2:
        if envprops[0][0] == envprops[1][0]: # different dialects
            cval = eitoh(pvals[0], pvals[1], delims=_alt_sep_dlc)
        else: # different scripts
            cval = cltoh(pvals[0], pvals[1], delims=_alt_sep_scr, full=True)
    else:
        cval = pvals[0]

    return cval


# Convert tagged person name into destination markup.
def _compose_person_name (tsegs, fcap, markup, light):

    if markup == "docbook4":
        name_segs = []
        for seg, tags in tsegs:
            seg = xentitize(seg)
            tag = tags[0] if len(tags) > 0 else None
            if tag in _pn_tag_first:
                name_segs.append(" <firstname>%s</firstname>" % seg.strip())
            elif tag in _pn_tag_last:
                name_segs.append(" <surname>%s</surname>" % seg.strip())
            elif tag in _pn_tag_middle:
                name_segs.append(" <othername>%s</othername>" % seg.strip())
            else: # untagged
                name_segs.append(" %s" % seg.strip())
        name = "".join(name_segs).strip()
        if not light:
            name = "<personname>%s</personname>" % name

    else:
        name = simplify("".join([seg for seg, tags in tsegs]))

    return name


def norm_pkey (pkey):
    """
    Normalize internal property keys in trapnakron.

    @param pkey: property key or keys to normalize
    @type pkey: string or (string*) or [string*]

    @returns: normalized keys
    @rtype: as input
    """

    if isinstance(pkey, basestring):
        return cltoa(pkey)
    elif isinstance(pkey, tuple):
        return tuple(map(cltoa, pkey))
    elif isinstance(pkey, list):
        return map(cltoa, pkey)
    else:
        raise StandardError("Cannot normalize property keys given "
                            "as type '%s'." % type(pkey))


_norm_rtkey_rx = re.compile("\s", re.U)

def norm_rtkey (text):
    """
    Normalize text into runtime key for translation scripting.

    @param text: text to normalize into runtime key
    @type text: string

    @returns: runtime key
    @rtype: string
    """

    return _norm_rtkey_rx.sub("", text).lower()

