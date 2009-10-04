# -*- coding: UTF-8 -*-

"""
Constructors of syntagma derivators for trapnakron.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import os
import re

from pology.misc.synder import Synder
from pology.misc.normalize import identify, xentitize, simplify
from pology.l10n.sr.hook.cyr2lat import cyr2lat, cyr2lat_stripped
from pology.l10n.sr.hook.nobr import to_nobr_hyphens
from pology.l10n.sr.hook.nobr import nobrhyp_char
from pology.misc.resolve import first_to_upper
from pology.misc.fsops import collect_files_by_ext
from pology import rootdir


# Allowed environment compositions, out of, in order:
# Ekavian Cyrillic, Ekavian Latin, Ijekavian Cyrillic, Ijekavian Latin.
# 1 indicates environment present, 0 absent.
_good_eicl_combos = set((
    "1000", "0100", "0010", "0001",
    "1100", "0011", "1010", "0101",
    "1111",
))

# Elements for composing alternatives directives.
_alt_head = u"~@" # must match runtime
_alt_sep = u"¦"

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

# Enumeration of known entry key suffixes, for modifying derived values.
_suff_pltext = 10
_suff_ltmarkup = 20


def trapnakron (env=(u"",),
                envl=(u"л", u""),
                envij=(u"иј", u""),
                envijl=(u"ијл", u"л", u"иј", u""),
                markup="plain", tagmap=None,
                ptsuff=None, ltsuff=None,
                nobrhyp=False, npkeyto=None):
    """
    Main trapnakron constructor, covering all options.

    The trapnakron derivator automatically sets and behaves as follows:

      - Values are returned as alternatives/hybridized compositions of
        Ekavian Cyrillic, Ekavian Latin, Ijekavian Cyrillic, and Ijekavian Latin
        forms, as applicable.
        Any of these forms can be excluded from derivation by setting
        its C{env*} parameter to C{None}.
        C{env*} parameters can also be used to change the environment chain
        for deriving the particular form.

      - The entry and property key separator is ASCII hyphen (C{-}).

      - Entry keys are derived from syntagmas by applying
        the L{identify()<misc.normalize.identify>} function.
        In entries where this will result in strange keys,
        additional keys should be defined through hidden syntagmas.

      - Entry keys are constructed by converting entry syntagmas into
        L{ASCII identifiers<misc.normalize.identify>}.
        Property keys are transliterated into
        L{stripped-ASCII<l10n.sr.hook.cyr2lat.cyr2lat_stripped>}.

      - Conflict resolution for entry keys is not strict (see documentation
        to L{derivator constructor<misc.synder.Synder.__init__>}).

    Optional behavior includes:

      - Instead of plain text, properties may be reported with some markup.
        The markup type is given by C{markup} parameter, and can be one of
        C{"plain"}, C{"xml"}, C{"docbook4"}.
        The C{tagmap} parameter contains mapping of entry keys
        to tags which should wrap properties of these entries.

      - Entry keys can have several suffixes which effect how
        the properties are reported.
        Presence of the suffix given by C{ptsuff} parameter signals that
        properties should be forced to plain text, if another markup is
        globally in effect.
        Parameter C{ltsuff} states the suffix which produces lighter version
        of the markup, where applicable (e.g. people names in Docbook).

      - Ordinary hyphens may be converted into non-breaking hyphens
        by setting the C{nobrhyp} parameter to C{True}.
        Non-breaking hyphens are added heuristically, see
        the L{to_nobr_hyphens()<l10n.sr.hook.nobr.to_nobr_hyphens>} hook.
        Useful e.g. to avoid wrapping on hyphen-separated case endings.

      - Property key normally cannot be empty, but C{npkeyto} parameter
        can be used to automatically substitute another property key
        when empty property key is seen in request for properties.
        In the simpler version, value of C{npkeyto} is just a string
        of the key to substitute for empty.
        In the more complex version, the value is a tuple containing
        the key to substitute and the list of two or more supplemental
        property keys: empty key is replaced only if all supplemental
        property values exist and are equal (see e.g. L{trapnakron_ui}
        for usage of this).

    @param env: environment chain for Ekavian Cyrillic derivation
    @type env: string or (string...) or ((string...)...)
    @param envl: environment chain for Ekavian Latin derivation
    @type envl: string or (string...) or ((string...)...)
    @param envij: environment chain for Ijekavian Cyrillic derivation
    @type envij: string or (string...) or ((string...)...)
    @param envijl: environment chain for Ijekavian Latin derivation
    @type envijl: string or (string...) or ((string...)...)
    @param markup: target markup
    @type markup: string
    @param tagmap: tags to assign to properties by entry keys
    @type tagmap: dict string -> string
    @param ptsuff: entry key suffix to report plain text properties
    @type ptsuff: string
    @param ltsuff: entry key suffix to report properties with lighter markup
    @type ltsuff: string
    @param nobrhyp: whether to convert some ordinary into non-breaking hyphens
    @type nobrhyp: bool
    @param npkeyto: property key to substitute for empty key, when given
    @type npkeyto: string or (string, [strings])

    @returns: trapnakron derivator
    @rtype: L{Synder<misc.synder.Synder>}
    """

    envs = [env, envl, envij, envijl]
    combo =  "".join([(x and "1" or "0") for x in envs])
    if combo not in _good_eicl_combos:
        raise StandardError("Invalid combination of Ekavian/Ijekavian "
                            "Cyrillic/Latin environments "
                            "to trapnakron derivator.")

    if markup not in _known_markups:
        raise StandardError("Unknown markup '%s' to trapnakron derivator "
                            "(known markups: %s)."
                            % (markup, " ".join(_known_markups)))

    # Setup up requests by entry key ending.
    mvends = {}
    if ptsuff:
        mvends[ptsuff] = _suff_pltext
    if ltsuff:
        mvends[ltsuff] = _suff_ltmarkup

    expkeys = []
    if isinstance(npkeyto, tuple):
        npkeyto, expkeys = npkeyto

    # Create transformators.
    ekeytf = _sd_ekey_transf(mvends, tagmap)
    pkeytf = _sd_pkey_transf(npkeyto, expkeys)
    pvaltf = _sd_pval_transf(env, envl, envij, envijl, markup, nobrhyp)
    esyntf = _sd_esyn_transf(markup, nobrhyp)

    # Build the derivator.
    sd = Synder(env=[x for x in envs if x],
                pkeysep="-",
                ekeytf=ekeytf, ekeyitf=identify,
                pkeytf=pkeytf, pkeyitf=cyr2lat_stripped,
                pvaltf=pvaltf, esyntf=esyntf,
                strictkey=False)

    # Collect synder files composing the trapnakron.
    sdfiles = _get_trapnakron_files()

    # Import into derivator.
    for sdfile in sdfiles:
        sd.import_file(sdfile)

    return sd


def _get_trapnakron_files (runtime=False):

    root = os.path.join(rootdir(), "l10n", "sr", "trapnakron")
    files = collect_files_by_ext(root, ["sd"], recurse=False)
    if runtime:
        rtroot = os.path.join(root, "runtime")
        rtfiles = collect_files_by_ext(rtroot, ["sd"], recurse=False)
        files.extend(files)

    return files


def trapnakron_ui (env=(u"",),
                   envl=(u"л", u""),
                   envij=(u"иј", u""),
                   envijl=(u"ијл", u"л", u"иј", u"")):
    """
    Constructs trapnakron suitable for application to UI texts.

    Calls L{trapnakron} with the following setup:

      - Markup is plain text (C{plain}).

      - Non-breaking hyphens are heuristically replacing ordinary hyphens.

      - Empty declination key is converted into C{am} (accusative masculine
        descriptive adjective), providing that it is equal to C{gm}
        (genitive masculine descriptive adjective);
        i.e. if the descriptive adjective is invariable.

      - Files with C{@latin} modifier are picked up as Latin script variants
        of same-name ordinary file, and their declinations combined
        by alternative directives.
    """

    return trapnakron(
        env, envl, envij, envijl,
        markup="plain",
        nobrhyp=True,
        npkeyto=("am", ("am", "gm")),
    )


def trapnakron_docbook4 (env=(u"",),
                         envl=(u"л", u""),
                         envij=(u"иј", u""),
                         envijl=(u"ијл", u"л", u"иј", u""),
                         tagmap=None):
    """
    Constructs trapnakron suitable for application to Docbook 4 texts.

    Calls L{trapnakron} with the following setup:

      - Markup is Docbook 4 (C{docbook4}).

      - Suffixes: C{_sp} ("samo prevod") for translation-only properties,
        C{_ot} ("obican tekst") for plain-text properties,
        C{_lv} ("laksa varijanta") for lighter variant of the markup.
        Lighter markup currently applies to: people names
        (no outer C{<personname>}, e.g. when it should be elideded due to
        particular text segmentation on Docbook->PO extraction).

      - Non-breaking hyphens and empty property keys
        are treated like in L{trapnakron_ui}.
    """

    return trapnakron(
        env, envl, envij, envijl,
        markup="docbook4",
        tagmap=tagmap,
        ptsuff="_ot", # for "obican text"
        ltsuff="_lv", # for "laksa varijanta"
        nobrhyp=True,
        npkeyto=("am", ("am", "gm")),
    )


# Transformation for entry keys:
# - lowercase first letter if upper-case, and indicate value uppercasing
# - strip special endings and indicate value modifications based on them
def _sd_ekey_transf (endings, tagmap):

    def transf (ekey):

        # Whether to uppercase the first letter of properties.
        fcap = ekey[0:1].isupper()
        if fcap:
            ekey = ekey[0].lower() + ekey[1:]

        # Collect and strip all known special endings.
        found_endings = set()
        while True:
            plen_endings = len(found_endings)
            for ending in endings:
                if ekey.endswith(ending):
                    ekey = ekey[:-len(ending)]
                    found_endings.add(ending)
            if len(found_endings) == plen_endings:
                break
        found_reqs = set([endings[x] for x in found_endings])

        # Tag which wraps the properties of this entry.
        # Do not add tags if manually requested not to.
        tag = None
        if tagmap and _suff_pltext not in found_reqs:
            tag = tagmap.get(ekey)

        # Whether to use lighter variant of the markup, where applicable.
        ltmarkup = _suff_ltmarkup in found_reqs

        return ekey, fcap, tag, ltmarkup

    return transf


# Transformation for property keys:
# - try to convert empty into non-empty key
def _sd_pkey_transf (npkeyto, npkey_eqpkeys):

    def transf (pkey, ekey, sd):

        # If key not empty, return it as-is.
        if pkey:
            return pkey

        # Empty ending allowed if all declinations requested
        # by supplementary keys are both existing and equal.
        # In that case, report the indicated key instead of empty.
        alleq = True
        ref_pval = None
        for tpkey in npkey_eqpkeys:
            pval = sd.get2(ekey, tpkey)
            if pval is None:
                alleq = False
                break
            if ref_pval is None:
                ref_pval =pdval
            elif ref_pval != pval:
                alleq = False
                break
        if alleq:
            return npkeyto
        else:
            return pkey

    return transf, "ekey", "self"


# Transformation for property values:
# - capitalize on request from key processing
# - add tags on request from key processing
# - optionally replace ordinary with no-break hyphens
# - resolve known taggings according to selected markup
# - add outer tags according to selected markup
# - construct alternatives/hybridized forms out of multiple values
def _sd_pval_transf (env, envl, envij, envijl, markup, nobrhyp):

    envspec = [x for x in ((env, False), (envl, True),
                           (envij, False), (envijl, True)) if x[0]]

    def transf (mtsegs, ekrest, sd):

        fcap, tag, ltmarkup = ekrest

        pvals = []
        for tsegs, (env1, islatin) in zip(mtsegs, envspec):
            pval1 = _compose_text(tsegs, markup, nobrhyp, fcap, tag, ltmarkup,
                                  islatin)
            pvals.append(pval1)

        pval = _compose_althyb(env, envl, envij, envijl, pvals)

        return pval

    return transf, "ekrest", "self"


# Transformation for entry syntagmas.
# Like for property value transformation,
# except for alternatives/hybridization.
def _sd_esyn_transf (markup, nobrhyp):

    def transf (tsegs, ekrest, sd):

        fcap, tag, ltmarkup = ekrest

        esyn = _compose_text(tsegs, markup, nobrhyp, fcap, tag, ltmarkup)

        return esyn

    return transf, "ekrest", "self"


def _compose_text (tsegs, markup, nobrhyp, fcap, tag, ltmarkup, tolatin=False):

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
        text = _compose_person_name(tsegs, fcap, markup, ltmarkup)
    else:
        # Ordinary entries.
        text = simplify("".join([x[0] for x in tsegs]))
        if fcap: # before adding outer tags
            text = first_to_upper(text)
        if vescape: # before adding outer tags
            text = vescape(text)
        if tag:
            text = tagsubs % dict(t=tag, v=text)

    if nobrhyp: # before conversion to Latin
        text = to_nobr_hyphens(unsafe=True)(text)
    if tolatin:
        text = cyr2lat(text)

    return text


# Combine Ekavian/Ijekavian Cyrillic/Latin forms
# into alternatives and hybridization directives.
def _compose_althyb (env, envl, envij, envijl, pvals):

    if env and envl and envij and envijl:
        raise StandardError("Ekavian/ijekavian hybridization not implemented.")
    elif env and envij:
        raise StandardError("Ekavian/ijekavian hybridization not implemented.")
    elif envl and envijl:
        raise StandardError("Ekavian/ijekavian hybridization not implemented.")
    elif (env and envl) or (envij and envijl):
        if cyr2lat(pvals[0]) != pvals[1]:
            cval = _alt_head + _alt_sep.join([""] + pvals + [""])
        else:
            cval = pvals[0]
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

