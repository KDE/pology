#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import sys
import os
import re
from optparse import OptionParser

from pology.misc.report import report, warning
from pology.misc.fsops import str_to_unicode
from pology.l10n.sr.trapnakron import trapnakron_ui
from pology.l10n.sr.trapnakron import split_althyb
from pology.l10n.sr.trapnakron import norm_pkey, norm_rtkey
from pology.l10n.sr.hook.cyr2lat import cyr2lat
from pology.misc.normalize import identify
from pology.l10n.sr.trapnakron import rootdir
from pology.misc.fsops import collect_files_by_ext
from pology.misc.vcs import VcsSubversion


def validate (tp, onlysrcs=None, onlykeys=None, demoexp=False):

    needed_pkeys = set()

    nom_pkeys = (
        [u"н"],
        [u"нм", u"нж", u"нс", u"ну"],
    )
    needed_pkeys.update(sum(nom_pkeys, []))

    gender_pkey = u"_род"
    needed_pkeys.add(gender_pkey)

    known_genders = set((u"м", u"ж", u"с", u"у"))
    known_genders.update(map(cyr2lat, known_genders))

    known_alts = [
        ("", u""),
        ("_s", u"сист"),
        ("_a", u"алт"),
        ("_a2", u"алт2"),
        ("_a3", u"алт3"),
    ]

    if demoexp:
        demoexp_pkeys = [u"н", u"г", u"д", u"а", u"в", u"и",
                         u"нк", u"гк", u"дк", u"ак", u"вк",
                         u"нм", u"нмп"]
        needed_pkeys.update(demoexp_pkeys)

    dkeys_by_rtkey = {}

    # Sort keys such that derivations are checked by file and position.
    dkeys = tp.dkeys(single=onlykeys is None)
    def sortkey (x):
        path, lno, cno = tp.source_pos(x)
        return path.count(os.path.sep), path, lno, cno
    dkeys = sorted(dkeys, key=sortkey)

    nproblems = 0
    unmatched_srcs = set(onlysrcs) if onlysrcs is not None else None
    unmatched_keys = set(onlykeys) if onlykeys is not None else None
    reported_fmtexps = set()

    for dkey in dkeys:
        srcname = tp.source_name(dkey)
        path, lno, cno = tp.source_pos(dkey)
        cnproblems = 0

        if (   (    onlysrcs is not None
                and not _match_text(srcname, onlysrcs, unmatched_srcs))
            or (    onlykeys is not None
                and not _match_text(dkey, onlykeys, unmatched_keys))
        ):
            continue

        try:
            aprops = []
            for ksuff, esuff in known_alts:
                dkeym = dkey + ksuff
                props = dict([(x, tp.get2(dkeym, norm_pkey(x)))
                               for x in needed_pkeys])
                aprops.append((esuff, props))
        except Exception, e:
            warning(unicode(e))
            cnproblems += 1
            continue

        for esuff, props in aprops:
            # Assure all nominative forms are unique.
            for pkeys in nom_pkeys: # select first nominative set by priority
                pvals = [props.get(x) for x in pkeys]
                noms = filter(lambda x: x is not None, pvals)
                if noms:
                    break
            if noms:
                rtkeys = map(norm_rtkey, noms)
                for rtkey in rtkeys:
                    odkey = dkeys_by_rtkey.get(rtkey)
                    if odkey is not None and tp.props(dkey) != tp.props(odkey):
                        opath, olno, ocno = tp.source_pos(odkey)
                        warning("Derivation at %s:%d:%d has normalized "
                                "nominative equal to derivation at %s:%d:%d."
                                % (path, lno, cno, opath, olno, ocno))
                        cnproblems += 1
                for rtkey in rtkeys: # must be in new loop
                    dkeys_by_rtkey[rtkey] = dkey

            # Assure presence of gender on noun derivations.
            if props.get(nom_pkeys[0][0]) is not None:
                gender = props.get(gender_pkey)
                if gender is None:
                    warning("Derivation at %s:%d:%d does not define gender."
                            % (path, lno, cno))
                    cnproblems += 1
                else:
                    for gender in split_althyb(gender):
                        if gender not in known_genders:
                            warning("Derivation at %s:%d:%d defines "
                                    "unknown gender '%s'."
                                    % (path, lno, cno, gender))
                            cnproblems += 1

            # Show selection of expanded properties if requested.
            if demoexp and not cnproblems:
                demoprops = [(x, props.get(x)) for x in demoexp_pkeys]
                demoprops = filter(lambda x: x[1] is not None, demoprops)
                fmtprops = ["%s=%s" % (x[0], _escape_pval(x[1]))
                            for x in demoprops]
                fmtsyns = ["%s" % _escape_syn(x) for x in tp.syns(dkey)]
                fmtexp = ", ".join(fmtsyns) + ": " + ", ".join(fmtprops)
                if fmtexp not in reported_fmtexps:
                    if not esuff:
                        report(fmtexp)
                        reported_fmtexps.add(fmtexp)
                    else:
                        afmtexp = "    @" + esuff + ": " + ", ".join(fmtprops)
                        report(afmtexp)

        nproblems += cnproblems
        tp.empty_pcache()

    if unmatched_srcs:
        warning("Sources requested by name not found: %s"
                % " ".join(sorted([getattr(x, "pattern", x)
                                   for x in unmatched_srcs])))
    if unmatched_keys:
        warning("Derivations requested by key not found: %s"
                % " ".join(sorted([getattr(x, "pattern", x)
                                   for x in unmatched_keys])))

    return nproblems


class _Wre (object):

    def __init__ (self, pattern):

        self.regex = re.compile(pattern, re.U)
        self.pattern = pattern


def _match_text (text, tests, unmatched_tests=None):

    match = False
    for test in tests:
        if isinstance(test, basestring):
            if test == text:
                match = True
                break
        elif isinstance(test, _Wre):
            if test.regex.search(text):
                match = True
                break
        elif callable(test):
            if test(text):
                match = True
                break
        else:
            raise StandardError("Unknown matcher type '%s'." % type(test))

    if unmatched_tests is not None:
        if match and test in unmatched_tests:
            unmatched_tests.remove(test)

    return match


def _escape_pval (pval):

    pval = pval.replace(",", "\,")
    return pval


def _escape_syn (pval):

    pval = pval.replace(",", "\,")
    pval = pval.replace(":", "\:")
    return pval


def _collect_mod_dkeys (tp, onlysrcs=None, onlykeys=None):

    # Collect all modified lines.
    vcs = VcsSubversion()
    mlines = []
    fpaths = collect_files_by_ext(rootdir(), ["sd"])
    for fpath in fpaths:
        if onlysrcs is not None: # cheaper than vcs.is_versioned
            srcname = os.path.splitext(os.path.basename(fpath))[0]
            if not _match_text(srcname, onlysrcs):
                continue
        if not vcs.is_versioned(fpath):
            continue
        mlines.extend(vcs.mod_lines(fpath))

    # Remove lines only moved between files and removed lines.
    mlines_added = set([x[1] for x in mlines if x[0] == "+"])
    mlines_removed = set([x[1] for x in mlines if x[0] == "-"])
    mlines_mod = []
    for mline in mlines:
        if mline[1] in mlines_added and not mline[1] in mlines_removed:
            mlines_mod.append(mline)
    mlines = mlines_mod

    # Collect derivation keys from new lines.
    onlykeys_mod = set()
    dkeys_in_tp = set(tp.dkeys(single=True))
    for tag, line in mlines:
        dkeys = map(identify, _parse_syns(line))
        if onlykeys is not None:
            dkeys = filter(lambda x: _match_text(x, onlykeys), dkeys)
        dkeys = filter(lambda x: x in dkeys_in_tp, dkeys)
        onlykeys_mod.update(dkeys)

    return None, onlykeys_mod


def _parse_syns (line):

    if line.strip().startswith(("#", ">")):
        return []

    llen = len(line)
    pos = 0
    syns = []
    csyn = ""
    intag = False
    while pos < llen:
        c = line[pos]
        if c == "\\":
            pos += 1
            csyn += line[pos]
        elif intag:
            if cltag:
                if c == cltag:
                    intag = False
            else:
                cn = line[pos + 1:pos + 2]
                if cn in (",", ":") or cn.isspace():
                    intag = False
        elif c == "~":
            intag = True
            cltag = "}" if line[pos + 1:pos + 2] == "{" else ""
        elif c in (",", ":"):
            csyn = csyn.strip()
            if csyn.startswith("|"):
                csyn = csyn[1:]
            syns.append(csyn)
            if c == ":":
                break
            else:
                csyn = ""
                spos = pos + 1
        else:
            csyn += line[pos]
        pos += 1

    return syns


def _statistics (tp, onlysrcs, onlykeys):

    dkeys = set()
    fpaths = {}
    for dkey in tp.dkeys(single=True):
        srcname = tp.source_name(dkey)
        fpath, lno, cno = tp.source_pos(dkey)

        if (   (onlysrcs is not None and not _match_text(srcname, onlysrcs))
            or (onlykeys is not None and not _match_text(dkey, onlykeys))
        ):
            continue

        dkeys.add(dkey)
        if fpath not in fpaths:
            fpaths[fpath] = [srcname, 0]
        fpaths[fpath][1] += 1

    report("-" * 40)
    if onlysrcs is not None or onlykeys is not None:
        report("(Selection active.)")
    report("Total derivations: %d" % len(dkeys))
    if len(fpaths) > 0:
        report("Total files: %d" % len(fpaths))
        report("Average derivations per file: %.1f"
            % (float(len(dkeys)) / len(fpaths)))
        bydif = sorted([(v[1], v[0]) for k, v in fpaths.items()])
        report("Maximum derivations in a file: %d (%s)" % bydif[-1])


def _main ():

    usage = u"""
  %prog [OPTIONS]
  %prog [OPTIONS] FILEPATH...
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
    opars.add_option(
        "-e", "--expansion-sample",
        action="store_true", dest="demoexp", default=False,
        help="Show a sample of expanded properties for each valid derivation.")
    opars.add_option(
        "-r", "--regex",
        action="store_true", dest="regex", default=False,
        help="Source names and derivation keys given in command line "
             "are regular expressions.")
    opars.add_option(
        "-m", "--modified",
        action="store_true", dest="modified", default=False,
        help="Validate only modified derivations.")
    opars.add_option(
        "-s", "--statistics",
        action="store_true", dest="statistics", default=False,
        help="Show various statistics.")

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
            test = arg[len(sksep):]
            if options.regex:
                test = _Wre(test)
            else:
                test = identify(test)
            onlykeys.add(test)
        else:
            if os.path.isfile(arg):
                test = os.path.splitext(arg.split(os.path.sep)[-1])[0]
                onlysrcs.add(test)
            else:
                test = arg
                if options.regex:
                    test = _Wre(test)
                onlysrcs.add(test)
    onlysrcs = onlysrcs or None
    onlykeys = onlykeys or None

    # Create and validate the trapnakron.
    tp = trapnakron_ui()
    if options.modified:
        onlysrcs, onlykeys = _collect_mod_dkeys(tp, onlysrcs, onlykeys)
    validate(tp, onlysrcs, onlykeys, options.demoexp)

    if options.statistics:
        _statistics(tp, onlysrcs, onlykeys)


if __name__ == '__main__':
    _main()

