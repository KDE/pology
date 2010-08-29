# -*- coding: UTF-8 -*-

"""
Constructors of syntagma derivators for trapnakron.

Trapnakron -- transcriptions and translation of names and acronyms --
is a collection of syntagma derivator definitions residing in
C{pology/lang/sr/trapnakron/}.
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
a basic L{Synder<pology.synder.Synder>} object, this module provides
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

    >>> from pology.lang.sr.trapnakron import trapnakron_plain
    >>> from pology.resolve import resolve_entities_simple as resents
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

import pology
from pology import PologyError, _, n_
from pology.lang.sr.nobr import to_nobr_hyphens, nobrhyp_char
from pology.lang.sr.wconv import ctol, cltoa
from pology.lang.sr.wconv import hctoc, hctol, hitoe, hitoi, hctocl
from pology.lang.sr.wconv import cltoh, tohi
from pology.fsops import collect_files_by_ext
from pology.normalize import identify, xentitize, simplify
from pology.report import format_item_list
from pology.resolve import first_to_upper
from pology.synder import Synder


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
_suff_gnmatch_m = "_rm" # for "rod muski"
_suff_gnmatch_m_id = 30
_suff_gnmatch_z = "_rz" # for "rod zenski"
_suff_gnmatch_z_id = 31
_suff_gnmatch_s = "_rs" # for "rod srednji"
_suff_gnmatch_s_id = 32
_suff_gnmatch_u = "_ru" # for "rod muski zivi"
_suff_gnmatch_u_id = 33
_suff_gnmatch_mk = "_rmk" # for "rod muski mnozine"
_suff_gnmatch_mk_id = 34
_suff_gnmatch_zk = "_rzk" # for "rod zenski mnozine"
_suff_gnmatch_zk_id = 35
_suff_gnmatch_sk = "_rsk" # for "rod srednji mnozine"
_suff_gnmatch_sk_id = 36
_suff_gnmatch_uk = "_ruk" # for "rod muski zivi mnozine"
_suff_gnmatch_uk_id = 37
_gnmatch_suffs = [_suff_gnmatch_m, _suff_gnmatch_z,
                  _suff_gnmatch_s, _suff_gnmatch_u,
                  _suff_gnmatch_mk, _suff_gnmatch_zk,
                  _suff_gnmatch_sk, _suff_gnmatch_uk]
_gnmatch_suff_ids = [_suff_gnmatch_m_id, _suff_gnmatch_z_id,
                     _suff_gnmatch_s_id, _suff_gnmatch_u_id,
                     _suff_gnmatch_mk_id, _suff_gnmatch_zk_id,
                     _suff_gnmatch_sk_id, _suff_gnmatch_uk_id]
_gnmatch_suff_ids_set = set(_gnmatch_suff_ids)
_gnmatch_suffs_genums = [
    (_suff_gnmatch_m_id, (u"м", u"m"), (u"ј", u"j")),
    (_suff_gnmatch_z_id, (u"ж", u"ž"), (u"ј", u"j")),
    (_suff_gnmatch_s_id, (u"с", u"s"), (u"ј", u"j")),
    (_suff_gnmatch_u_id, (u"у", u"u"), (u"ј", u"j")),
    (_suff_gnmatch_mk_id, (u"м", u"m"), (u"к", u"k")),
    (_suff_gnmatch_zk_id, (u"ж", u"ž"), (u"к", u"k")),
    (_suff_gnmatch_sk_id, (u"с", u"s"), (u"к", u"k")),
    (_suff_gnmatch_uk_id, (u"у", u"u"), (u"к", u"k")),
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
_suff_pname_f = "_im" # for "ime"
_suff_pname_f_id = 60
_suff_pname_l = "_pr" # for "prezime"
_suff_pname_l_id = 61
_pname_suffs = [_suff_pname_f, _suff_pname_l]
_pname_suff_ids = [_suff_pname_f_id, _suff_pname_l_id]
_pname_suff_ids_set = set(_pname_suff_ids)


def trapnakron (envec=u"", envel=u"л", envic=u"иј", envil=u"ијл",
                markup="plain", tagmap=None,
                ptsuff=None, ltsuff=None, gnsuff=None,
                stsuff=None, adsuff=None, nmsuff=None,
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
    the L{identify()<normalize.identify>} function.
    In derivations where this will result in strange keys,
    additional keys should be defined through hidden syntagmas.
    Property keys are transliterated into
    L{stripped-ASCII<lang.sr.wconv.cltoa>}.

    Conflict resolution for derivation keys is not strict
    (see L{derivator constructor<synder.Synder.__init__>}).

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
        the resolved value is of certain gender and number; parameter C{gnsuff}
        can be used to provide a tuple of 4 suffixes for gender in singular
        and 4 suffixes for gender in plural,
        such that the property will resolve only if the value of
        gender and number matches the gender and number suffix.
      - Parameters C{stsuff} and C{adsuff} provide suffixes through
        which systematic transcription and alternative derivations
        are requested.
        They are actually tuples, where the first element is the key suffix,
        and the second element the suffix to primary environment
        which produces the systematic/alternative environment.
        C{adsuff} can also be a tuple of tuples, if several alternative
        derivations should be reachable.
      - In case the entry is a person's name with tagged first and last name,
        parameter C{nmsuff} can provide a tuple of 2 suffixes by which
        only the first or last name are requested, respectively.

    Ordinary hyphens may be converted into non-breaking hyphens
    by setting the C{nobrhyp} parameter to C{True}.
    Non-breaking hyphens are added heuristically, see
    the L{to_nobr_hyphens()<lang.sr.nobr.to_nobr_hyphens>} hook.
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
    @param gnsuff: suffixes by gender and number, to have no resolution
        if gender or number do not match
    @type gnsuff: [(string, string)*]
    @param stsuff: derivation key and environment name suffixes
        to report systematic transcriptions
    @type stsuff: (string, string)
    @param adsuff: derivation key and environment name suffixes
        to report alternative derivations
    @type adsuff: (string, string) or ((string, string)*)
    @param nmsuff: suffixes for fetching only first or last name of a person
    @type nmsuff: (string, string)
    @param npkeyto: property key to substitute for empty key, when given
    @type npkeyto: string or (string, [string*])
    @param nobrhyp: whether to convert some ordinary into non-breaking hyphens
    @type nobrhyp: bool
    @param disamb: string to replace each disambiguation marker with
    @type disamb: string
    @param runtime: whether to include runtime-only derivations
    @type runtime: bool

    @returns: trapnakron derivator
    @rtype: L{Synder<synder.Synder>}
    """

    env0s = [envec, envel, envic, envil]
    combo =  "".join([(x is not None and "1" or "0") for x in env0s])
    if combo not in _good_eicl_combos:
        raise PologyError(
            _("@info",
              "Invalid combination of Ekavian/Ijekavian Cyrillic/Latin "
              "environments to trapnakron derivator."))

    if markup not in _known_markups:
        raise PologyError(
            _("@info",
              "Unknown markup type '%(mtype)s' to trapnakron derivator "
              "(known markups: %(mtypelist)s).",
              mtype=markup, mtypelist=format_item_list(_known_markups)))

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
    if gnsuff:
        if len(gnsuff) != 8:
            raise PologyError(
                _("@info",
                  "Sequence of gender-number suffixes must have "
                  "exactly 8 elements."))
        mvends.update(zip(gnsuff, _gnmatch_suff_ids))
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
                for esuff1 in (esuff, ""):
                    for env0 in env1:
                        aenv1.append(env0 + esuff1)
                aenv.append(tuple(aenv1))
            aenvs[suff_id] = tuple(aenv)
    if nmsuff:
        if len(nmsuff) != 2:
            raise PologyError(
                _("@info",
                  "Sequence of person name suffixes must have "
                  "exactly 2 elements."))
        mvends.update(zip(nmsuff, _pname_suff_ids))

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

    return os.path.join(pology.rootdir(), "lang", "sr", "trapnakron")


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
        other alternatives; C{_im} and C{_pr} for person's last and first name.

      - Non-breaking hyphens are heuristically replacing ordinary hyphens.

      - Empty property key is converted into C{am} (accusative masculine
        descriptive adjective), providing that it is equal to C{gm}
        (genitive masculine descriptive adjective);
        i.e. if the descriptive adjective is invariable.
    """

    return trapnakron(
        envec, envel, envic, envil,
        markup="plain",
        gnsuff=_gnmatch_suffs,
        stsuff=_systr_ksuff_esuff,
        adsuff=_altdv_ksuffs_esuffs,
        nmsuff=_pname_suffs,
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
        gnsuff=_gnmatch_suffs,
        stsuff=_systr_ksuff_esuff,
        adsuff=_altdv_ksuffs_esuffs,
        nmsuff=_pname_suffs,
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
        gnsuff=_gnmatch_suffs,
        stsuff=_systr_ksuff_esuff,
        adsuff=_altdv_ksuffs_esuffs,
        nmsuff=_pname_suffs,
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

        # Whether the gender and number is matching.
        if _gnmatch_suff_ids_set.intersection(found_suff_ids):
            gstr = sd.get2(dkey, "_rod")
            nstr = sd.get2(dkey, "_broj", "j")
            genders = list(set(map(ctol, hctocl(gstr)))) if gstr else []
            numbers = list(set(map(ctol, hctocl(nstr)))) if nstr else []
            if (   not (len(genders) == 1) or not (len(numbers) == 1)
                or not all([(   x[0] not in found_suff_ids
                             or (genders[0] in x[1] and numbers[0] in x[2]))
                            for x in _gnmatch_suffs_genums])
            ):
                dkey = None

        # Whether to use one of alternative environments.
        esuffid = None
        found_aenv_suff_ids = _aenv_suff_ids_set.intersection(found_suff_ids)
        if found_aenv_suff_ids:
            esuffid = tuple(found_aenv_suff_ids)[0]

        # Whether to select only first or last name (persons).
        nsuffid = None
        found_pname_suff_ids = _pname_suff_ids_set.intersection(found_suff_ids)
        if found_pname_suff_ids:
            nsuffid = tuple(found_pname_suff_ids)[0]

        return dkey, fcap, tag, ltmarkup, pltext, esuffid, nsuffid

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

        fcap, tag, ltmarkup, pltext, d5, nsuffid = dkrest
        if pkey.startswith("_"):
            fcap = False
            tag = None
            pltext = True

        pvals = []
        for tsegs, (islatin, isije) in zip(mtsegs, envprops):
            if tsegs is None:
                return None
            pval1 = _compose_text(tsegs, markup, nobrhyp, disamb,
                                  fcap, tag, ltmarkup, pltext, nsuffid,
                                  pkey, islatin)
            if pval1 is None:
                return None
            pvals.append(pval1)

        pval = _hybridize(envprops, pvals)

        return pval

    return transf, "pkey", "dkrest", "self"


# Transformation for derivation syntagmas.
# Like for property value transformation,
# except for alternatives/hybridization.
def _sd_ksyn_transf (markup, nobrhyp, disamb):

    def transf (tsegs, dkrest, sd):

        fcap, tag, ltmarkup, pltext, d5, nsuffid = dkrest

        ksyn = _compose_text(tsegs, markup, nobrhyp, disamb,
                             fcap, tag, ltmarkup, pltext, nsuffid)

        return ksyn

    return transf, "dkrest", "self"


# Transformation for derivation environments.
# Returns a non-default environment on request from keys processing.
def _sd_env_transf (aenvs):

    def transf (env, dkrest):

        d1, d2, d3, d4, esuffid, d6 = dkrest

        if esuffid is not None:
            return aenvs[esuffid]
        else:
            return env

    return transf, "dkrest"


def _compose_text (tsegs, markup, nobrhyp, disamb,
                   fcap, tag, ltmarkup, pltext, nsuffid,
                   pkey=None, tolatin=False):

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
        text = _compose_person_name(tsegs, fcap, markup_mod, ltmarkup, nsuffid,
                                    pkey)
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

    if text is None:
        return None

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
        cvalc = tohi(pvals[0], pvals[2], delims=_alt_sep_dlc)
        cvall = tohi(pvals[1], pvals[3], delims=_alt_sep_dlc)
        if ctol(cvalc) != cvall:
            cval = cltoh(cvalc, cvall, delims=_alt_sep_scr, full=True)
        else:
            cval = cvalc
    elif len(envprops) == 2:
        if envprops[0][0] == envprops[1][0]: # different dialects
            cval = tohi(pvals[0], pvals[1], delims=_alt_sep_dlc)
        else: # different scripts
            cval = cltoh(pvals[0], pvals[1], delims=_alt_sep_scr, full=True)
    else:
        cval = pvals[0]

    return cval


# Convert tagged person name into destination markup.
def _compose_person_name (tsegs, fcap, markup, light, nsuffid, pkey):

    # Reduce the name to one of its elements if requested.
    # If the reduction results in empty string, revert to full name.
    upperlast = False
    if nsuffid is not None:
        ntsegs = []
        for seg, tags in tsegs:
            tag = tags[0] if len(tags) > 0 else None
            if (   (tag in _pn_tag_first and nsuffid == _suff_pname_f_id)
                or (tag in _pn_tag_last and nsuffid == _suff_pname_l_id)
            ):
                ntsegs.append((seg, tags))
        if "".join([seg for seg, tags in ntsegs]).strip():
            tsegs = ntsegs
            # Take care to uppercase title to last name ("von", "al", etc.)
            # if last name alone is selected.
            upperlast = nsuffid == _suff_pname_l_id
    # Otherwise, if the requested property is of special type,
    # cancel the derivation if full name contains several name elements.
    # FIXME: Actually do this once decided how the client should supply
    # the test for special keys.
    elif False: #pkey and len(pkey) > 2:
        seentags = set()
        for seg, tags in tsegs:
            if not seg.strip():
                continue
            tag = tags[0] if len(tags) > 0 else None
            if tag in _pn_tag_first:
                seentags.add(_pn_tag_first[0])
            elif tag in _pn_tag_last:
                seentags.add(_pn_tag_last[0])
            elif tag in _pn_tag_middle:
                seentags.add(_pn_tag_middle[0])
            else:
                seentags.add(None)
        if len(seentags) > 1:
            return None

    if markup == "docbook4":
        name_segs = []
        for seg, tags in tsegs:
            seg = xentitize(seg).strip()
            if not seg:
                continue
            tag = tags[0] if len(tags) > 0 else None
            if tag in _pn_tag_first:
                name_segs.append(" <firstname>%s</firstname>" % seg)
            elif tag in _pn_tag_last:
                if upperlast:
                    seg = seg[0].upper() + seg[1:]
                    upperlast = False
                name_segs.append(" <surname>%s</surname>" % seg)
            elif tag in _pn_tag_middle:
                name_segs.append(" <othername>%s</othername>" % seg)
            else: # untagged
                name_segs.append(" %s" % seg)
        name = "".join(name_segs).strip()
        if not light:
            name = "<personname>%s</personname>" % name

    else:
        name = simplify("".join([seg for seg, tags in tsegs]))
        if upperlast:
            name = name[0].upper() + name[1:]

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
        raise PologyError(
            _("@info",
              "Normalization of property keys requested "
              "on unsupported data type '%(type)s'.",
              type=type(pkey)))


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

