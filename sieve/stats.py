# -*- coding: UTF-8 -*-

"""
Catalog statistics: message and word counts, etc.

Documented in C{doc/user/sieving.docbook}.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import codecs
import locale
import os
import sys

from pology import _, n_
from pology.catalog import Catalog
from pology.message import MessageUnsafe
from pology.colors import ColorString, cjoin, cinterp
from pology.comments import parse_summit_branches
from pology.diff import tdiff
from pology.fsops import collect_catalogs
from pology.getfunc import get_hook_ireq
from pology.report import report, warning, format_item_list
from pology.split import proper_words
from pology.tabulate import tabulate
from pology.sieve import SieveError


def setup_sieve (p):

    p.set_desc(_("@info sieve discription",
    "Compute translation statistics.\n"
    "\n"
    "Provides basic count of number of messages by type (translated, fuzzy, "
    "etc.), along with words and character counts, and some other derived "
    "statistics on request."
    ))

    p.add_param("accel", unicode, multival=True,
                metavar=_("@info sieve parameter value placeholder", "CHAR"),
                desc=_("@info sieve parameter discription",
    "Character which is used as UI accelerator marker in text fields, "
    "to remove it before counting. "
    "If a catalog defines accelerator marker in the header, "
    "this value overrides it."
    ))
    p.add_param("detail", bool, defval=False,
                desc=_("@info sieve parameter discription",
    "Compute and display some derived statistical quantities."
    ))
    p.add_param("incomplete", bool, defval=False,
                desc=_("@info sieve parameter discription",
    "List catalogs which are not fully translated, with incompletness counts."
    ))
    p.add_param("incompfile", unicode,
                metavar=_("@info sieve parameter value placeholder", "FILE"),
                desc=_("@info sieve parameter discription",
    "Write paths of catalogs that are not fully translated into a file, "
    "one per line."
    ))
    p.add_param("templates", unicode,
                metavar=_("@info sieve parameter value placeholder",
                          "FIND:REPLACE"),
                desc=_("@info sieve parameter discription",
    "Count in templates without a corresponding catalog (i.e. translation on "
    "it has not started yet) into statistics. "
    "Assumes that translated catalogs and templates live in two root "
    "directories with same structure; then for each path of an existing "
    "catalog, its directory is taken and the path to corresponding templates "
    "directory constructed by replacing first occurence of FIND with REPLACE."
    ))
    p.add_param("branch", unicode, seplist=True,
                metavar=_("@info sieve parameter value placeholder", "BRANCH"),
                desc=_("@info sieve parameter discription",
    "In summit catalogs, count in only messages belonging to given branch. "
    "Several branches can be given as comma-separated list."
    ))
    p.add_param("maxwords", int,
                metavar=_("@info sieve parameter value placeholder", "NUMBER"),
                desc=_("@info sieve parameter discription",
    "Count in only messages which have at most this many words, "
    "either in original or translation."
    ))
    p.add_param("minwords", int,
                metavar=_("@info sieve parameter value placeholder", "NUMBER"),
                desc=_("@info sieve parameter discription",
    "Count in only messages which have at least this many words, "
    "either in original or translation."
    ))
    p.add_param("lspan", unicode,
                metavar=_("@info sieve parameter value placeholder", "FROM:TO"),
                desc=_("@info sieve parameter discription",
    "Count in only messages at or after line FROM, and before line TO. "
    "If FROM is empty, 0 is assumed; "
    "if TO is empty, total number of lines is assumed."
    ))
    p.add_param("espan", unicode,
                metavar=_("@info sieve parameter value placeholder", "FROM:TO"),
                desc=_("@info sieve parameter discription",
    "Count in only messages at or after entry FROM, and before entry TO. "
    "If FROM is empty, 0 is assumed; "
    "if TO is empty, total number of entries is assumed."
    ))
    p.add_param("bydir", bool, defval=False,
                desc=_("@info sieve parameter discription",
    "Report statistics per leaf directory in searched paths."
    ))
    p.add_param("byfile", bool, defval=False,
                desc=_("@info sieve parameter discription",
    "Report statistics per catalog."
    ))
    p.add_param("wbar", bool, defval=False,
                desc=_("@info sieve parameter discription",
    "Show statistics in form of word bars."
    ))
    p.add_param("msgbar", bool, defval=False,
                desc=_("@info sieve parameter discription",
    "Show statistics in form of message bars."
    ))
    p.add_param("msgfmt", bool, defval=False,
                desc=_("@info sieve parameter discription",
    "Show a minimal summary of the statistics (like msgfmt)."
    ))
    p.add_param("absolute", bool, defval=False,
                desc=_("@info sieve parameter discription",
    "Scale lengths of word and message bars to numbers they represent, "
    "rather than relative to percentage of translation state. "
    "Useful with '%(par1)s' and '%(par2)s' parameters, "
    "to compare sizes of different translation units.",
    par1="byfile", par2="bydir"
    ))
    p.add_param("ondiff", bool, defval=False,
                desc=_("@info sieve parameter discription",
    "Split word and character counts of fuzzy messages "
    "into translated and untranslated categories (leaving zero in fuzzy), "
    "based on difference ratio between current and previous original text."
    ))
    p.add_param("mincomp", float, defval=None,
                metavar=_("@info sieve parameter value placeholder", "RATIO"),
                desc=_("@info sieve parameter discription",
    "Include into statistics only catalogs with sufficient completeness, "
    "as ratio of translated to other messages (real value between 0 and 1)."
    ))
    p.add_param("filter", unicode, multival=True,
                metavar=_("@info sieve parameter value placeholder", "HOOK"),
                desc=_("@info sieve parameter discription",
    "F1A hook specification, to filter the translation through. "
    "Several filters can be specified by repeating the parameter."
    ))


class Sieve (object):

    def __init__ (self, params):

        self.p = params

        # Templates correspondence.
        # Mapping of catalogs to templates, in form of <search>:<replace>.
        # For each catalog file path, the first <search> substring is replaced
        # by <replace>, and .po replaced with .pot, to construct its template
        # file path. All templates not found under such paths are reported.
        # Furthermore, all subdirs of these paths are searched for templates
        # without corresponding catalogs, and every such template is counted
        # as fully untranslated PO.
        if self.p.templates:
            if ":" not in self.p.templates:
                self.tspec_srch = self.p.templates
                self.tspec_repl = ""
            else:
                self.tspec_srch, self.tspec_repl = self.p.templates.split(":", 1)

        # Turn off table display if a bar view has been selected.
        self.p.table = True
        if self.p.msgbar or self.p.wbar or self.p.msgfmt:
            self.p.table = False

        # Filenames of catalogs which are not fully translated.
        self.incomplete_catalogs = {}

        # Counted categories.
        self.count_spec = (
            ("trn",
             _("@title:row translated messages/words/characters",
               "translated")),
            ("fuz",
             _("@title:row fuzzy messages/words/characters",
               "fuzzy")),
            ("unt",
             _("@title:row untranslated messages/words/characters",
               "untranslated")),
            ("tot",
             _("@title:row fuzzy messages/words/characters",
               "total")),
            ("obs",
             _("@title:row fuzzy messages/words/characters",
               "obsolete")),
        )

        # FIXME: After parameter parser can deliver requested sequence type.
        if self.p.branch is not None:
            self.p.branch = set(self.p.branch)

        # Parse line/entry spans.
        def parse_span (spanspec):
            lst = spanspec is not None and spanspec.split(":") or ("", "")
            if len(lst) != 2:
                raise SieveError(
                    _("@info",
                      "Wrong number of elements in span "
                      "specification '%(spec)s'.",
                      spec=self.p.lspan))
            nlst = []
            for el in lst:
                if not el:
                    nlst.append(None)
                else:
                    try:
                        nlst.append(int(el))
                    except:
                        raise SieveError(
                            _("@info",
                              "Not an integer number in span "
                              "specification '%(spec)s'.",
                              spec=self.p.lspan))
            return tuple(nlst)
        self.lspan = parse_span(self.p.lspan)
        self.espan = parse_span(self.p.espan)

        # Number of counts per category:
        # messages, words in original, words in translation,
        # characters in original, characters in translation.
        self.counts_per_cat = 5

        # Category counts per catalog filename.
        self.counts = {}

        # Collections of all confirmed templates and tentative template subdirs.
        self.matched_templates = {}
        self.template_subdirs = []
        if self.p.templates:
            for rpath in params.root_paths:
                if os.path.isfile(rpath):
                    rpath = os.path.dirname(rpath)
                rpath = rpath.replace(self.tspec_srch, self.tspec_repl, 1)
                self.template_subdirs.append(rpath)
        # Map of template to translation subdirs.
        self.mapped_template_subdirs = {}

        # Some indicators of metamessages.
        self.xml2po_meta_msgid = dict([(x, True) for x in
            ("translator-credits",)])
        self.xml2pot_meta_msgid = dict([(x, True) for x in
            ("ROLES_OF_TRANSLATORS", "CREDIT_FOR_TRANSLATORS")])
        self.kde_meta_msgctxt = dict([(x, True) for x in
            ("NAME OF TRANSLATORS", "EMAIL OF TRANSLATORS")])

        # Resolve filtering hooks.
        self.pfilters = []
        for hreq in self.p.filter or []:
            self.pfilters.append(get_hook_ireq(hreq, abort=True))

        # Indicators to the caller:
        self.caller_sync = False # no need to sync catalogs
        self.caller_monitored = False # no need for monitored messages


    def _count_zero (self):

        return dict([(x[0], [0] * self.counts_per_cat)
                     for x in self.count_spec])


    def _count_sum (self, c1, c2):

        cs = self._count_zero()
        for cat, catname in self.count_spec:
            for i in range(self.counts_per_cat):
                cs[cat][i] = c1[cat][i] + c2[cat][i]

        return cs


    def process_header (self, hdr, cat):

        # Establish counts for this file.
        if cat.filename not in self.counts:
            self.counts[cat.filename] = self._count_zero()
        self.count = self.counts[cat.filename]

        # If template correspondence requested, handle template matching.
        if (    self.p.templates
            and not cat.filename.endswith(".pot")):

            # Construct expected template path.
            tpath = cat.filename.replace(self.tspec_srch, self.tspec_repl, 1)
            pdot = tpath.rfind(".")
            if pdot >= 0:
                tpath = tpath[:pdot] + ".pot"
            # Inform if the template does not exist.
            if not os.path.isfile(tpath):
                warning(_("@info",
                          "Expected template catalog '%(file)s' is missing.",
                          file=tpath))
            # Indicate the template has been matched.
            if tpath not in self.matched_templates:
                self.matched_templates[tpath] = True

        # Force explicitly given accelerators.
        if self.p.accel is not None:
            cat.set_accelerator(self.p.accel)


    def process (self, msg, cat):

        # Summit: if branches were given, skip the message if it does not
        # belong to any of the given branches.
        if self.p.branch:
            msg_branches = parse_summit_branches(msg)
            if not set.intersection(self.p.branch, msg_branches):
                return

        # If line/entry spans given, skip message if not in range.
        if self.lspan[0] is not None and msg.refline < self.lspan[0]:
            return
        if self.lspan[1] is not None and msg.refline >= self.lspan[1]:
            return
        if self.espan[0] is not None and msg.refentry < self.espan[0]:
            return
        if self.espan[1] is not None and msg.refentry >= self.espan[1]:
            return

        # Decide if a metamessage:
        ismeta = False
        # - msgid in form "@@<tag>: ..." from xml2po
        if msg.msgid.startswith("@@"):
            ps = msg.msgid.find(":")
            ismeta = (ps >= 0 and msg.msgid[2:ps].isalnum())
        # - translator credits from xml2po and xml2pot
        if (   msg.msgid in self.xml2po_meta_msgid
            or msg.msgid in self.xml2pot_meta_msgid
        ):
            ismeta = True
        # - translator credits in KDE GUI
        if msg.msgctxt in self.kde_meta_msgctxt:
            ismeta = True

        # Prepare filtered message for counting.
        if self.pfilters:
            msg = MessageUnsafe(msg)
            for pfilter in self.pfilters:
                for i in range(len(msg.msgstr)):
                    msg.msgstr[i] = pfilter(msg.msgstr[i])

        # Count the words and characters in original and translation.
        # Remove shortcut markers prior to counting; don't include words
        # which do not start with a letter; remove scripted part.
        # For plural messages compute averages of msgid and msgstr groups,
        # to normalize comparative counts on varying number of plural forms.
        nwords = {"orig" : 0, "tran" : 0}
        nchars = {"orig" : 0, "tran" : 0}
        msgids = [msg.msgid]
        if msg.msgid_plural is not None:
            msgids.append(msg.msgid_plural)
        for src, texts in (("orig", msgids), ("tran", msg.msgstr)):
            if ismeta: # consider metamessages as zero counts
                continue
            lnwords = [] # this group's word count, for averaging
            lnchars = [] # this group's character count, for averaging
            for text in texts:
                pf = text.find("|/|")
                if pf >= 0:
                    text = text[0:pf]
                words = proper_words(text, True, cat.accelerator(), msg.format)
                # If there are no proper words but there are some characters,
                # set to one empty word in order for a fuzzy or
                # an untranslated message not to be considered translated
                # when only word counts are observed.
                if not words and text:
                    words = [""]
                lnwords.append(len(words))
                lnchars.append(len("".join(words)))
            nwords[src] += int(round(float(sum(lnwords)) / len(texts)))
            nchars[src] += int(round(float(sum(lnchars)) / len(texts)))
            #nchars[src] += (nwords[src] - 1) # nominal space per each two words

        # If the number of words has been limited, skip the message if it
        # does not fall in the range.
        if self.p.maxwords is not None:
            if not (   nwords["orig"] <= self.p.maxwords
                    or nwords["tran"] <= self.p.maxwords):
                return
        if self.p.minwords is not None:
            if not (   nwords["orig"] >= self.p.minwords
                    or nwords["tran"] >= self.p.minwords):
                return

        # Split word and character counts in fuzzy original if requested.
        nswords = {}
        nschars = {}
        if self.p.ondiff and msg.fuzzy and msg.msgid_previous is not None:
            diff, dr = tdiff(msg.msgid_previous, msg.msgid, diffr=True)
            # Reduce difference ratio to a smaller range by some threshold.
            # Texts more different than the threshold need full review.
            drth = 0.4
            #dr2 = dr if dr < drth else 1.0
            dr2 = min(dr / drth, 1.0)
            # Split counts between primary fuzzy count, and secondary
            # translated, so that total remains the same.
            nswords.update({"trn": {}, "fuz": {}, "unt": {}})
            nschars.update({"trn": {}, "fuz": {}, "unt": {}})
            for nitems, nitems2, src in (
                (nwords, nswords, "orig"), (nwords, nswords, "tran"),
                (nchars, nschars, "orig"), (nchars, nschars, "tran"),
            ):
                num = nitems[src]
                # Difference ratio of 0 can happen if the new and old texts
                # are the same, normally when only the context has changed.
                # Fuzzy counts should not be totally eliminated then,
                # as it should be seen that message needs updating.
                if dr2 > 0.0:
                    rnum = int(round(dr2 * num + 0.5)) # round up
                else:
                    rnum = 1
                rnum = min(rnum, num) # in case of rounding overflow
                nitems2["trn"][src] = num - rnum
                nitems2["fuz"][src] = 0
                nitems2["unt"][src] = rnum

        # Detect categories and add the counts.
        categories = set()

        if not msg.obsolete: # do not count obsolete into totals
            self.count["tot"][0] += 1
            categories.add("tot")
            if nswords:
                categories.update(nswords.keys())

        if msg.obsolete: # do not split obsolete into fuzzy/translated
            self.count["obs"][0] += 1
            categories.add("obs")
            nswords = {}
            nschars = {}
        elif msg.translated:
            self.count["trn"][0] += 1
            categories.add("trn")
        elif msg.fuzzy:
            self.count["fuz"][0] += 1
            categories.add("fuz")
            if cat.filename not in self.incomplete_catalogs:
                self.incomplete_catalogs[cat.filename] = True
        elif msg.untranslated:
            self.count["unt"][0] += 1
            categories.add("unt")
            if cat.filename not in self.incomplete_catalogs:
                self.incomplete_catalogs[cat.filename] = True

        for cat in categories:
            nwords1 = nswords.get(cat, nwords)
            nchars1 = nschars.get(cat, nchars)
            self.count[cat][1] += nwords1["orig"]
            self.count[cat][2] += nwords1["tran"]
            self.count[cat][3] += nchars1["orig"]
            self.count[cat][4] += nchars1["tran"]


    # Sort filenames as if templates-only were within language subdirs.
    def _sort_equiv_filenames (self, filenames):

        def equiv_template_path (x):
            cdir = os.path.dirname(x)
            if cdir in self.mapped_template_subdirs:
                cdir = self.mapped_template_subdirs[cdir]
                return os.path.join(cdir, os.path.basename(x))
            else:
                return x

        filenames.sort(key=lambda x: equiv_template_path(x))


    def finalize (self):

        # If template correspondence requested, handle POTs without POs.
        if self.template_subdirs:
            # Collect all catalogs in template subdirs.
            tpaths = collect_catalogs(self.template_subdirs)
            tpaths = filter(self.p.is_cat_included, tpaths)
            # Filter to have only POTs remain.
            tpaths = [x for x in tpaths if x.endswith(".pot")]
            # Filter to leave out matched templates.
            tpaths = [x for x in tpaths if x not in self.matched_templates]
            # Add stats on all unmatched templates.
            for tpath in tpaths:
                cat = Catalog(tpath, monitored=False)
                self.process_header(cat.header, cat)
                for msg in cat:
                    self.process(msg, cat)
            # Map template to translation subdirs.
            for tpath in tpaths:
                tsubdir = os.path.dirname(tpath)
                subdir = tsubdir.replace(self.tspec_repl, self.tspec_srch, 1)
                self.mapped_template_subdirs[tsubdir] = subdir

        # If completeness limit in effect, eliminate catalogs not passing it.
        if self.p.mincomp is not None:
            ncounts = {}
            ninccats = {}
            for filename, count in self.counts.iteritems():
                cr = float(count["trn"][0]) / (count["tot"][0] or 1)
                if cr >= self.p.mincomp:
                    ncounts[filename] = count
                    inccat = self.incomplete_catalogs.get(filename)
                    if inccat is not None:
                        ninccats[filename] = inccat
            self.counts = ncounts
            self.incomplete_catalogs = ninccats

        # Assemble sets of total counts by requested divisions.
        count_overall = self._count_zero()
        counts_bydir = {}
        filenames_bydir = {}
        for filename, count in self.counts.iteritems():

            count_overall = self._count_sum(count_overall, count)

            if self.p.bydir:
                cdir = os.path.dirname(filename)
                if cdir in self.mapped_template_subdirs:
                    # Pretend templates-only are within language subdir.
                    cdir = self.mapped_template_subdirs[cdir]
                if cdir not in counts_bydir:
                    counts_bydir[cdir] = self._count_zero()
                    filenames_bydir[cdir] = []
                counts_bydir[cdir] = self._count_sum(counts_bydir[cdir], count)
                filenames_bydir[cdir].append(filename)

        # Arrange sets into ordered list with titles.
        counts = []
        if self.p.bydir:
            cdirs = counts_bydir.keys();
            cdirs.sort()
            for cdir in cdirs:
                if self.p.byfile:
                    self._sort_equiv_filenames(filenames_bydir[cdir])
                    for filename in filenames_bydir[cdir]:
                        counts.append((filename, self.counts[filename], False))
                counts.append(("%s/" % cdir, counts_bydir[cdir], False))
            counts.append((_("@item:intable sum of all other entries",
                             "(overall)"), count_overall, True))

        elif self.p.byfile:
            filenames = self.counts.keys()
            self._sort_equiv_filenames(filenames)
            for filename in filenames:
                counts.append((filename, self.counts[filename], False))
            counts.append((_("@item:intable sum of all other entries",
                             "(overall)"), count_overall, True))

        else:
            counts.append((None, count_overall, False))

        # Indicate conspicuously up front modifiers to counting.
        modstrs = []
        if self.p.branch:
            fmtbranches = format_item_list(self.p.branch)
            modstrs.append(_("@item:intext",
                             "branches (%(branchlist)s)",
                             branchlist=fmtbranches))
        if self.p.maxwords is not None and self.p.minwords is None:
            modstrs.append(n_("@item:intext",
                              "at most %(num)d word",
                              "at most %(num)d words",
                              num=self.p.maxwords))
        if self.p.minwords is not None and self.p.maxwords is None:
            modstrs.append(n_("@item:intext",
                              "at least %(num)d word",
                              "at least %(num)d words",
                              num=self.p.minwords))
        if self.p.minwords is not None and self.p.maxwords is not None:
            modstrs.append(n_("@item:intext",
                              "from %(num1)d to %(num)d word",
                              "from %(num1)d to %(num)d words",
                              num1=self.p.minwords, num=self.p.maxwords))
        if self.p.lspan:
            modstrs.append(_("@item:intext",
                             "line span %(span)s",
                             span=self.p.lspan))
        if self.p.espan:
            modstrs.append(_("@item:intext",
                             "entry span %(span)s",
                             span=self.p.espan))
        if self.p.ondiff:
            modstrs.append(_("@item:intext",
                             "scaled fuzzy counts"))

        # Should titles be output in-line or on separate lines.
        self.inline = False
        maxtitlecw = 0
        if (not self.p.wbar or not self.p.msgbar or not self.p.msgfmt) and (not self.p.table):
            for title, count, summed in counts:
                if title is not None:
                    self.inline = True
                    titlecw = len(title)
                    if maxtitlecw < titlecw:
                        maxtitlecw = titlecw

        # Output statistics in requested forms.
        for title, count, summed in counts:
            # Output the title if defined.
            if title is not None:
                if self.inline:
                    ntitle = (("%%-%ds" % maxtitlecw) % title)
                else:
                    ntitle = title
                # Must color after padding, to avoid it seeing the colors.
                ntitle = _("@title",
                           "<bold>%(title)s</bold>",
                           title=ntitle)
                if self.inline:
                    report(ntitle + " ", newline=False)
                else:
                    report(ntitle)

            if self.p.table:
                self._tabular_stats(counts, title, count)
            if self.p.msgbar:
                self._msg_bar_stats(counts, title, count, summed)
            if self.p.wbar:
                self._w_bar_stats(counts, title, count, summed)
            if self.p.msgfmt:
                self._msg_simple_stats(title, count, summed)

        # Output the table of catalogs which are not fully translated,
        # if requested.
        if self.p.incomplete and self.incomplete_catalogs:
            filenames = self.incomplete_catalogs.keys()
            self._sort_equiv_filenames(filenames)
            data = []
            # Column of catalog filenames.
            data.append(filenames)
            data.append([self.counts[x]["fuz"][0] for x in filenames])
            data.append([self.counts[x]["unt"][0] for x in filenames])
            data.append([x + y for x, y in zip(data[1], data[2])])
            data.append([self.counts[x]["fuz"][1] for x in filenames])
            data.append([self.counts[x]["unt"][1] for x in filenames])
            data.append([x + y for x, y in zip(data[4], data[5])])
            # Columns of the two added.
            # Column names and formats.
            coln = [_("@title:column",
                      "catalog"),
                    _("@title:column fuzzy messages",
                      "msg/f"),
                    _("@title:column untranslated messages",
                      "msg/u"),
                    _("@title:column fuzzy and untranslated messages",
                      "msg/f+u"),
                    _("@title:column words in fuzzy messages",
                      "w/f"),
                    _("@title:column words in untranslated messages",
                      "w/u"),
                    _("@title:column words in fuzzy and untranslated messages",
                      "w/f+u")]
            maxfl = max([len(x) for x in filenames])
            dfmt = ["%%-%ds" % maxfl, "%d", "%d", "%d", "%d", "%d", "%d"]
            # Output.
            report("-")
            report(tabulate(data, coln=coln, dfmt=dfmt, space="   ", none=u"-",
                            colorize=True))

        # Write file names of catalogs which are not fully translated
        # into a file, if requested.
        if self.p.incompfile:
            filenames = sorted(self.incomplete_catalogs.keys())
            cmdlenc = locale.getpreferredencoding()
            ofl = codecs.open(self.p.incompfile, "w", cmdlenc)
            ofl.writelines([x + "\n" for x in filenames])
            ofl.close()

        if modstrs:
            report(_("@item:intable",
                     "modifiers: %(modlist)s",
                     modlist=format_item_list(modstrs)))


    def _tabular_stats (self, counts, title, count):

        # Order counts in tabular form.
        selected_cats = self.count_spec
        if False and self.p.incomplete: # skip this for the moment
            # Display only fuzzy and untranslated counts.
            selected_cats = (self.count_spec[1], self.count_spec[2])
            # Skip display if complete.
            really_incomplete = True
            for tkey, tname in selected_cats:
                for col in range(self.counts_per_cat):
                    if count[tkey][col] > 0:
                        really_incomplete = False
                        break
            if really_incomplete:
                return
        data = [[count[tkey][y] for tkey, tname in selected_cats]
                for y in range(self.counts_per_cat)]

        # Derived data: messages/words completition ratios.
        for col, ins in ((0, 1), (1, 3)):
            compr = []
            for tkey, tname in selected_cats:
                if tkey not in ("tot", "obs") and count["tot"][col] > 0:
                    r = float(count[tkey][col]) / count["tot"][col]
                    compr.append(r * 100)
                else:
                    compr.append(None)
            data.insert(ins, compr)

        if self.p.detail:
            # Derived data: word and character expansion factors.
            for o, t, ins, incsp in ((1, 2, 7, None), (3, 4, 8, (1, 2, 0.0))):
                ratio = []
                for tkey, tname in selected_cats:
                    if count[tkey][o] > 0 and count[tkey][t] > 0:
                        inct, inco = 0.0, 0.0
                        if incsp:
                            co, ct, fact = incsp
                            inco = (count[tkey][co] - 1) * fact
                            inct = (count[tkey][ct] - 1) * fact
                        r = (count[tkey][t] + inct) / (count[tkey][o] + inco)
                        ratio.append((r - 1) * 100)
                    else:
                        ratio.append(None)
                data.insert(ins, ratio)

        if self.p.detail:
            # Derived data: character/word ratio, word/message ratio.
            for w, c, ins in ((0, 1, 9), (0, 2, 10), (1, 3, 11), (2, 4, 12)):
                chpw = []
                for tkey, tname in selected_cats:
                    if count[tkey][w] > 0 and count[tkey][c] > 0:
                        r = float(count[tkey][c]) / count[tkey][w]
                        chpw.append(r)
                    else:
                        chpw.append(None)
                data.insert(ins, chpw)

        # Row, column names and formats.
        rown = [tname for tkey, tname in selected_cats]
        coln = [_("@title:column messages",
                  "msg"),
                _("@title:column percentage of total messages",
                  "msg/tot"),
                _("@title:column words in original",
                  "w-or"),
                _("@title:column percentage of words to total in original",
                  "w/tot-or"),
                _("@title:column words in translation",
                  "w-tr"),
                _("@title:column characters in original",
                  "ch-or"),
                _("@title:column characters in translation",
                  "ch-tr")]
        dfmt = ["%d", "%.1f%%",
                "%d", "%.1f%%", "%d", "%d", "%d"]
        if self.p.detail:
            coln.extend([_("@title:column word efficiency",
                           "w-ef"),
                         _("@title:column character efficiency",
                           "ch-ef"),
                         _("@title:column words per message in original",
                           "w/msg-or"),
                         _("@title:column words per message in translation",
                           "w/msg-tr"),
                         _("@title:column characters per message in original",
                           "ch/w-or"),
                         _("@title:column characters per message in translation",
                           "ch/w-tr")])
            dfmt.extend(["%+.1f%%", "%+.1f%%",
                         "%.1f", "%.1f", "%.1f", "%.1f"])

        # Output the table.
        report(tabulate(data, rown=rown, coln=coln, dfmt=dfmt,
                        space="   ", none=u"-", colorize=True))


    def _msg_bar_stats (self, counts, title, count, summed):

        self._bar_stats(counts, title, count, summed,
                        _("@item:intable number of messages",
                          "msgs"),
                        0)


    def _w_bar_stats (self, counts, title, count, summed):

        self._bar_stats(counts, title, count, summed,
                        _("@item:intable number of words in original",
                          "w-or"),
                        1)


    def _bar_stats (self, counts, title, count, summed, dlabel, dcolumn):

        # Count categories to display and chars/colors associated to them.
        # Note: Use only characters from Latin1.
        tspecs = (("trn", u"×", "green"),
                  ("fuz", u"¤", "blue"),
                  ("unt", u"·", "red"))

        # Find out maximum counts overall.
        maxcounts = dict(trn=0, fuz=0, unt=0, tot=0)
        maxcounts_jumbled = maxcounts.copy()
        for otitle, ocount, osummed in counts:
            # If absolute bars, compare counts only for non-summed counts.
            if self.p.absolute and osummed:
                continue

            # Count both messages and words, for the number display padding.
            for tkey in maxcounts_jumbled:
                for dcol in (0, 1):
                    c = ocount[tkey][dcol]
                    if maxcounts_jumbled[tkey] < c:
                        maxcounts_jumbled[tkey] = c

            for tkey in maxcounts:
                c = ocount[tkey][dcolumn]
                if maxcounts[tkey] < c:
                    maxcounts[tkey] = c

        # Character widths of maximum count categories.
        maxcountscw = {}
        for tkey, tval in maxcounts.iteritems():
            maxcountscw[tkey] = len(str(tval))
        maxcountscw_jumbled = {}
        for tkey, tval in maxcounts_jumbled.iteritems():
            maxcountscw_jumbled[tkey] = len(str(tval))

        # Formatted counts by disjunct categories.
        fmt_counts = []
        for tkey, tchar, tcol in tspecs:
            cstr = str(count[tkey][dcolumn])
            if cstr == "0":
                cstr = "-"
            cfmt = ("%%%ds" % maxcountscw_jumbled[tkey]) % cstr
            if tcol is not None:
                fmt_counts.append((ColorString("<%s>%%s</%s>") % (tcol, tcol))
                                  % cfmt)
            else:
                fmt_counts.append(cfmt)
        fmt_counts = cjoin(fmt_counts, "/")

        # Maximum and nominal bar widths in characters.
        # TODO: Make parameters.
        if self.inline:
            nombarcw = 20
            maxbarcw = 50
        else:
            nombarcw = 40
            maxbarcw = 80

        def roundnear (x):
            return int(round(x, 0))

        def roundup (x):
            ix = int(x)
            if x - ix > 1e-16:
                ix += 1
            return ix

        # Compute number of cells per category.
        n_cells = {}
        if self.p.absolute:
            # Absolute bar.
            n_per_cell = 0
            for npc in (1, 2, 5,
                        10, 20, 50,
                        100, 200, 500,
                        1000, 2000, 5000,
                        10000, 20000, 50000,
                        100000, 200000, 500000):
                if npc * maxbarcw > maxcounts["tot"]:
                    n_per_cell = npc
                    break
            if not n_per_cell:
                warning(_("@info",
                          "Count too large, cannot display bar graph."))
                return
            for tkey, roundf in (("fuz", roundup), ("unt", roundup),
                                 ("tot", roundnear)):
                c = count[tkey][dcolumn]
                n_cells[tkey] = roundf(float(c) / n_per_cell)

            # Correct the situation when there are no cells.
            if n_cells["tot"] < 1:
                n_cells["tot"] = 1

            # Correct the situation when the sum of cells fuzzy+untranslated
            # goes over the total; give priority to untranslated when reducing.
            while n_cells["fuz"] + n_cells["unt"] > n_cells["tot"]:
                if n_cells["fuz"] >= n_cells["unt"]:
                    n_cells["fuz"] -= 1
                else:
                    n_cells["unt"] -= 1

            n_cells["trn"] = n_cells["tot"] - n_cells["fuz"] - n_cells["unt"]

        else:
            # Relative bar.
            if count["tot"][dcolumn] > 0:
                n_per_cell = float(nombarcw) / count["tot"][dcolumn]
            else:
                n_per_cell = 0
            for tkey in ("fuz", "unt"):
                c = count[tkey][dcolumn]
                n_cells[tkey] = roundup(c * n_per_cell)

            # When there are almost none translated, it may have happened that
            # the sum of cells fuzzy+untranslated is over nominal; reduce.
            while n_cells["fuz"] + n_cells["unt"] > nombarcw:
                if n_cells["fuz"] >= n_cells["unt"]:
                    n_cells["fuz"] -= 1
                else:
                    n_cells["unt"] -= 1

            n_cells["trn"] = nombarcw - n_cells["fuz"] - n_cells["unt"]

        # Create the bar.
        fmt_bar = []
        for tkey, tchar, tcol in tspecs:
            bar = tchar * n_cells[tkey]
            if tcol is not None:
                bar = (ColorString("<%s>%%s</%s>") % (tcol, tcol)) % bar
            fmt_bar.append(bar)
        fmt_bar = cjoin(fmt_bar)

        # Assemble final output.
        if not self.p.absolute or not summed:
            if count["tot"][dcolumn] == 0:
                fmt_bar = ""
            report(cinterp("%s %s |%s|", fmt_counts, dlabel, fmt_bar))
        else:
            report(cinterp("%s %s", fmt_counts, dlabel))


    def _msg_simple_stats (self, title, count, summed):
        """ msgfmt-style report """
        fmt_trn = n_("@item:intext",
                     "%(num)d translated message",
                     "%(num)d translated messages",
                     num=count["trn"][0])
        fmt_fuz = n_("@item:intext",
                     "%(num)d fuzzy translation",
                     "%(num)d fuzzy translations",
                     num=count["fuz"][0])
        fmt_unt = n_("@item:intext",
                     "%(num)d untranslated message",
                     "%(num)d untranslated messages",
                     num=count["unt"][0])
        report(_("@info composition of three previous messages",
                 "%(trn)s, %(fuz)s, %(unt)s",
                 trn=fmt_trn, fuz=fmt_fuz, unt=fmt_unt))

