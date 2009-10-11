#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import os
import re

from pology.misc.report import warning
from pology.l10n.sr.trapnakron import trapnakron_ui
from pology.l10n.sr.hook.cyr2lat import cyr2lat as c2l
from pology.l10n.sr.hook.cyr2lat import cyr2lat_stripped as c2a
from pology.misc.resolve import resolve_alternatives_simple as resalts


def validate (tp):

    nom_pkeys = (
        normkey_tp([u"н"]),
        normkey_tp([u"нм", u"нж", u"нс", u"ну"]),
    )
    gender_pkey = normkey_tp(u"_род")
    known_genders = set((u"м", u"ж", u"с", u"у"))
    known_genders.update(map(c2l, known_genders))

    dkeys_by_rtkey = {}

    # Sort keys such that derivations are checked by file and position.
    dkeys = tp.dkeys(single=True)
    def sortkey (x):
        path, lno, cno = tp.source_pos(x)
        return path.count(os.path.sep), path, lno, cno
    dkeys = sorted(dkeys, key=sortkey)

    nproblems = 0

    for dkey in dkeys:
        path, lno, cno = tp.source_pos(dkey)
        try:
            props = tp.props(dkey)
        except Exception, e:
            warning(unicode(e))
            continue

        # Assure all nominative forms are unique.
        for pkeys in nom_pkeys: # select first nominative set by priority
            pvals = [props.get(x) for x in pkeys]
            noms = filter(lambda x: x is not None, pvals)
            if noms:
                break
        if noms:
            rtkeys = map(normkey_rt, noms)
            for rtkey in rtkeys:
                odkey = dkeys_by_rtkey.get(rtkey)
                if odkey is not None and tp.props(dkey) != tp.props(odkey):
                    opath, olno, ocno = tp.source_pos(odkey)
                    warning("Derivation at %s:%d:%d has normalized nominative "
                            "equal to derivation at %s:%d:%d."
                            % (path, lno, cno, opath, olno, ocno))
                    nproblems += 1
            for rtkey in rtkeys: # must be in new loop
                dkeys_by_rtkey[rtkey] = dkey

        # Assure presence of gender on noun derivations.
        if props.get(nom_pkeys[0][0]) is not None:
            gender = props.get(gender_pkey)
            if gender is None:
                warning("Derivation at %s:%d:%d does not define gender."
                        % (path, lno, cno))
                nproblems += 1
            else:
                for gender in resalthyb(gender):
                    if gender not in known_genders:
                        warning("Derivation at %s:%d:%d defines "
                                "unknown gender '%s'."
                                % (path, lno, cno, gender))
                        nproblems += 1

        tp.empty_pcache()

    return nproblems


# Normalize property keys in the same way as in trapnakron derivator.
def normkey_tp (pkey):

    if isinstance(pkey, list):
        return map(c2a, pkey)
    elif isinstance(pkey, tuple):
        return tuple(map(c2a, pkey))
    else:
        return c2a(pkey)


# Normalize pmap keys in the same way as at runtime (Transcript).
_normkey_rt_rx = re.compile("\s", re.U)

def normkey_rt (key):

    return _normkey_rt_rx.sub("", key).lower()


# Return list with resolved forms from text with alternatives/hybridization.
def resalthyb (text):

    # TODO: Resolve hybridization.

    if "~@" in text:
        return (resalts(text, 1, 2), resalts(text, 2, 2))
    else:
        return (text,)


def _main ():

    try:
        import psyco
        psyco.full()
    except ImportError:
        pass

    # Create and validate the trapnakron.
    tp = trapnakron_ui()
    validate(tp)


if __name__ == '__main__':
    _main()

