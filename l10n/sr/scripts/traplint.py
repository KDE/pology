#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import sys
import os
import re
from optparse import OptionParser

from pology.misc.report import warning
from pology.misc.fsops import str_to_unicode
from pology.l10n.sr.trapnakron import trapnakron_ui
from pology.l10n.sr.hook.cyr2lat import cyr2lat as c2l
from pology.l10n.sr.hook.cyr2lat import cyr2lat_stripped as c2a
from pology.misc.resolve import resolve_alternatives_simple as resalts


def validate (tp, onlysrcs=None, onlykeys=None):

    needed_pkeys = set()

    nom_pkeys = (
        normkey_tp([u"н"]),
        normkey_tp([u"нм", u"нж", u"нс", u"ну"]),
    )
    needed_pkeys.update(sum(nom_pkeys, []))

    gender_pkey = normkey_tp(u"_род")
    needed_pkeys.add(gender_pkey)

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

    unmatched_srcs = set(onlysrcs) if onlysrcs is not None else None
    unmatched_keys = set(onlykeys) if onlykeys is not None else None

    for dkey in dkeys:
        srcname = tp.source_name(dkey)
        path, lno, cno = tp.source_pos(dkey)

        check = True
        if onlysrcs is not None:
            if srcname not in onlysrcs:
                check = False
            if srcname in unmatched_srcs:
                unmatched_srcs.remove(srcname)
        if onlykeys is not None:
            if dkey not in onlykeys:
                check = False
            if dkey in unmatched_keys:
                unmatched_keys.remove(dkey)
        if not check:
            continue

        try:
            props = dict([(x, tp.get2(dkey, x)) for x in needed_pkeys])
        except Exception, e:
            warning(unicode(e))
            nproblems += 1
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

    if unmatched_srcs:
        warning("Sources requested by name not found: %s"
                % " ".join(sorted(unmatched_srcs)))
    if unmatched_keys:
        warning("Derivations requested by key not found: %s"
                % " ".join(sorted(unmatched_keys)))

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

    usage = u"""
  %prog [OPTIONS]
  %prog [OPTIONS] SRCNAME...
  %prog [OPTIONS] :DKEY...
""".rstrip()
    description = u"""
Check validity of internal trapnakron.
""".strip()
    version = u"""
%prog (Pology) experimental
Copyright © 2009 Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
""".strip()

    opars = OptionParser(usage=usage, description=description, version=version)

    (options, free_args) = opars.parse_args(str_to_unicode(sys.argv[1:]))

    try:
        import psyco
        psyco.full()
    except ImportError:
        pass

    onlysrcs = set()
    onlykeys = set()
    sksep = ":"
    for arg in free_args:
        if arg.startswith(sksep):
            onlykeys.add(arg[len(sksep):])
        else:
            onlysrcs.add(arg)
    onlysrcs = onlysrcs or None
    onlykeys = onlykeys or None

    # Create and validate the trapnakron.
    tp = trapnakron_ui()
    validate(tp, onlysrcs, onlykeys)


if __name__ == '__main__':
    _main()

