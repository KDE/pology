#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import fallback_import_paths

import sys
import os
import re
import locale

from pology import PologyError, version, _, n_
from pology.l10n.sr.hook.wconv import ctol, hictoall
from pology.l10n.sr.trapnakron import rootdir
from pology.l10n.sr.trapnakron import trapnakron_ui
from pology.l10n.sr.trapnakron import norm_pkey, norm_rtkey
from pology.misc.colors import ColorOptionParser
from pology.misc.fsops import str_to_unicode
from pology.misc.normalize import identify
from pology.misc.report import report, warning, format_item_list
from pology.misc.vcs import VcsSubversion


def validate (tp, onlysrcs=None, onlykeys=None, demoexp=False, expwkeys=False):

    needed_pkeys = set()

    nom_pkeys = (
        [u"н"],
        [u"нм", u"нж", u"нс", u"ну"],
    )
    needed_pkeys.update(sum(nom_pkeys, []))

    gender_pkey = u"_род"
    needed_pkeys.add(gender_pkey)

    known_genders = set((u"м", u"ж", u"с", u"у"))
    known_genders.update(map(ctol, known_genders))

    known_alts = [
        ("_s", u"сист"),
        ("_a", u"алт"),
        ("_a2", u"алт2"),
        ("_a3", u"алт3"),
    ]
    base_envs = [u"", u"л", u"иј", u"ијл"]
    all_envs = set(base_envs)
    for aenv in [x[1] for x in known_alts]:
        all_envs.update(x + aenv for x in base_envs)

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
            seenesuffs = set()
            cenvs = tp.envs(dkey)
            for cenv in cenvs:
                if cenv != "":
                    envmatched = False
                    for ksuff, esuff in known_alts:
                        if cenv in all_envs and cenv.endswith(esuff):
                            envmatched = True
                            break
                else:
                    envmatched = True
                    ksuff, esuff = "", ""
                if envmatched and esuff not in seenesuffs:
                    dkeym = dkey + ksuff
                    props = dict([(x, tp.get2(dkeym, norm_pkey(x)))
                                   for x in needed_pkeys])
                    aprops.append((esuff, props))
                    seenesuffs.add(esuff)
                elif cenv not in all_envs:
                    warning(_("@info",
                              "Derivation at %(file)s:%(line)d:%(col)d "
                              "defines unknown environment '%(env)s'.",
                              file=path, line=lno, col=cno, env=cenv))
                    cnproblems += 1
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
                        warning(_("@info",
                                  "Derivation at %(file1)s:%(line1)d:%(col1)d "
                                  "has normalized nominative equal to "
                                  "derivation at %(file2)s:%(line2)d:%(col2)d.",
                                  file1=path, line1=lno, col1=cno,
                                  file2=opath, line2=olno, col2=ocno))
                        cnproblems += 1
                for rtkey in rtkeys: # must be in new loop
                    dkeys_by_rtkey[rtkey] = dkey

            # Assure presence of gender on noun derivations.
            if props.get(nom_pkeys[0][0]) is not None:
                gender = props.get(gender_pkey)
                if gender is None:
                    warning(_("@info",
                              "Derivation at %(file)s:%(line)d:%(col)d "
                              "does not define gender.",
                              file=path, line=lno, col=cno))
                    cnproblems += 1
                else:
                    for gender in hictoall(gender):
                        if gender not in known_genders:
                            warning(_("@info",
                                      "Derivation at %(file)s:%(line)d:%(col)d "
                                      "defines unknown gender '%(gen)s'.",
                                      file=path, line=lno, col=cno, gen=gender))
                            cnproblems += 1

            # Show selection of expanded properties if requested.
            if demoexp and not cnproblems:
                demoprops = [(x, props.get(x)) for x in demoexp_pkeys]
                demoprops = filter(lambda x: x[1] is not None, demoprops)
                fmtprops = ["%s=%s" % (x[0], _escape_pval(x[1]))
                            for x in demoprops]
                fmtsyns = ["%s" % _escape_syn(x) for x in tp.syns(dkey)]
                fmtexp = ", ".join(fmtsyns) + ": " + ", ".join(fmtprops)
                if expwkeys:
                    fmtdkeys = ", ".join(sorted(tp.altdkeys(dkey)))
                    fmtexp = "# " + fmtdkeys + "\n" + fmtexp
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
        fmtsrcs = format_item_list(sorted(getattr(x, "pattern", x)
                                          for x in unmatched_srcs))
        warning(_("@info",
                  "Sources requested by name not found: %(srclist)s.",
                  srclist=fmtsrcs))
    if unmatched_keys:
        fmtkeys = format_item_list(sorted(getattr(x, "pattern", x)
                                          for x in unmatched_keys))
        warning(_("@info",
                  "Derivations requested by key not found: %(keylist)s.",
                  keylist=fmtkeys))

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
            raise PologyError(
                _("@info",
                  "Unknown matcher type '%(type)s'.",
                  type=type(test)))

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

    # Collect the unified diff of trapnakron root.
    vcs = VcsSubversion()
    udiff = vcs.diff(rootdir())
    udiff = _elim_moved_blocks(udiff)

    # Collect key syntagmas related to added lines.
    asyns = set()
    skip_file = True
    prev_syns = None
    for tag, data in udiff:
        if tag == "@":
            continue

        fpath = data
        if tag == ":":
            if not fpath.endswith(".sd"):
                skip_file = True
            else:
                srcname = os.path.splitext(os.path.basename(fpath))[0]
                if onlysrcs is None:
                    skip_file = False
                else:
                    skip_file = not _match_text(srcname, onlysrcs)
        if skip_file:
            continue

        line = data.strip()
        if line.startswith(("#", ">")) or not line:
            continue
        if tag == " ":
            if not line.startswith("@"):
                prev_syns = _parse_syns(line)
        elif tag == "+":
            if not line.startswith("@"):
                syns = _parse_syns(line)
            elif prev_syns:
                syns = prev_syns
            asyns.update(syns)
            prev_syns = []

    # Collect derivation keys from syntagmas.
    onlykeys_mod = set()
    dkeys_in_tp = set(tp.dkeys(single=True))
    for syn in asyns:
        dkey = identify(syn)
        if (    dkey and dkey in dkeys_in_tp
            and (onlykeys is None or _match_text(dkey, onlykeys))
        ):
            onlykeys_mod.add(dkey)

    return None, onlykeys_mod


# Eliminate difference blocks due to pure moving between and within files.
def _elim_moved_blocks (udiff):

    segcnt_ad = {}
    segcnt_rm = {}
    ctag = ""
    cseg = []
    for tag, data in udiff + [("@", None)]: # sentry
        if tag == "@":
            if ctag in ("+", "-"):
                cskey = "".join(cseg)
                segcnt = segcnt_ad if ctag == "+" else segcnt_rm
                if cskey not in segcnt:
                    segcnt[cskey] = 0
                segcnt[cskey] += 1
            ctag = ""
            cseg = []
        elif tag in ("+", "-"):
            if ctag and ctag != tag:
                ctag = "xxx"
            else:
                ctag = tag
                cseg.append(data)

    udiff_mod = []
    subdiff = []
    ctag = ""
    cseg = []
    for tag, data in udiff + [("@", None)]:
        if tag in (":", "@"):
            if subdiff:
                cskey = "".join(cseg)
                if (   ctag not in ("+", "-")
                    or segcnt_ad.get(cskey, 0) != 1
                    or segcnt_rm.get(cskey, 0) != 1
                ):
                    udiff_mod.extend(subdiff)
            subdiff = []
            cseg = []
            ctag = ""
            if tag == ":":
                udiff_mod.append((tag, data))
            else:
                subdiff = [(tag, data)]
        else:
            subdiff.append((tag, data))
            if tag in ("+", "-"):
                if ctag and ctag != tag:
                    ctag = "xxx"
                else:
                    ctag = tag
                    cseg.append(data)

    return udiff_mod


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
            if pos < llen:
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
        report(_("@info statistics; side note stating that not all entries "
                 "have been taken into account, but only some selected",
                 "(Selection active.)"))
    report(_("@info statistics",
             "Total derivations: %(num)d",
             num=len(dkeys)))
    if len(fpaths) > 0:
        report(_("@info statistics",
                 "Total files: %(num)d",
                 num=len(fpaths)))
        report(_("@info statistics",
                 "Average derivations per file: %(num).1f",
                 num=(float(len(dkeys)) / len(fpaths))))
        bydif = sorted([(v[1], v[0]) for k, v in fpaths.items()])
        report(_("@info statistics",
                 "Most derivations in a file: %(num)d (%(file)s)",
                 num=bydif[-1][0], file=bydif[-1][1]))


def _main ():

    locale.setlocale(locale.LC_ALL, "")

    usage= _("@info command usage",
        "%(cmd)s [OPTIONS] [DKEY|SRCPATH|:SRCNAME]...",
        cmd="%prog")
    desc = _("@info command description",
        "Check validity and expand derivations from internal trapnakron.")
    ver = _("@info command version",
        u"%(cmd)s (Pology) %(version)s\n"
        u"Copyright © 2009, 2010 "
        u"Chusslove Illich (Часлав Илић) &lt;%(email)s&gt;",
        cmd="%prog", version=version(), email="caslav.ilic@gmx.net")

    opars = ColorOptionParser(usage=usage, description=desc, version=ver)
    opars.add_option(
        "-e", "--expansion-sample",
        action="store_true", dest="demoexp", default=False,
        help=_("@info command line option description",
               "Show a sample of expanded properties for "
               "each valid derivation."))
    opars.add_option(
        "-k", "--show-keys",
        action="store_true", dest="expwkeys", default=False,
        help=_("@info command line option description",
               "When expanding, also show all derivation keys by derivation."))
    opars.add_option(
        "-m", "--modified",
        action="store_true", dest="modified", default=False,
        help=_("@info command line option description",
               "Validate or expand only modified derivations."))
    opars.add_option(
        "-r", "--regex",
        action="store_true", dest="regex", default=False,
        help=_("@info command line option description",
               "Source names and derivation keys given in command line "
               "are regular expressions."))
    opars.add_option(
        "-s", "--statistics",
        action="store_true", dest="statistics", default=False,
        help=_("@info command line option description",
               "Show statistics."))

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
        if os.path.isfile(arg):
            test = os.path.splitext(arg.split(os.path.sep)[-1])[0]
            onlysrcs.add(test)
        elif arg.startswith(sksep):
            test = arg[len(sksep):]
            if options.regex:
                test = _Wre(test)
            onlysrcs.add(test)
        else:
            if options.regex:
                arg = _Wre(arg)
            else:
                arg = identify(arg)
            onlykeys.add(arg)

    onlysrcs = onlysrcs or None
    onlykeys = onlykeys or None

    # Create and validate the trapnakron.
    tp = trapnakron_ui()
    if options.modified:
        onlysrcs, onlykeys = _collect_mod_dkeys(tp, onlysrcs, onlykeys)
    validate(tp, onlysrcs, onlykeys, options.demoexp, options.expwkeys)

    if options.statistics:
        _statistics(tp, onlysrcs, onlykeys)


if __name__ == '__main__':
    _main()

