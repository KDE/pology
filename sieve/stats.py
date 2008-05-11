# -*- coding: UTF-8 -*-

"""
Statistics: message and word counts by category, etc.

Various statistics on catalogs, that may help review the progress,
split up the work, find out what needs updating, etc.

Sieve options:
  - C{accel:<character>}: accelerator marker in GUI messages
  - C{detail}: give more detailed statistics
  - C{incomplete}: additionally list catalogs which are not 100% translated
  - C{templates:<spec>}: compare translation with templates (see below)
  - C{minwords:<number>}: count only messages with at least this many words
  - C{maxwords:<number>}: count only messages with at most this many words
  - C{branch:<branch_id>}: consider only messages from this branch (summit)
  - C{bydir}: display report by each leaf directory, followed by totals
  - C{byfile}: display report by each catalog, followed by totals
  - C{msgbar}: show an ASCII bar giving overview of message counts
  - C{wbar}: show an ASCII bar giving overview of word counts
  - C{notab}: do not show the table (typically when bars are enabled)
  - C{absolute}: make bars show absolute rather than relative info

The accelerator characters should be removed from the messages before
counting, in order not to introduce word splits where there are none.
The sieve will try to guess the accelerator if C{accel} option is not given,
and if doesn't find one, it will remove the characteres most usually used
for this purpose (C{&}, C{_}, C{~}).

If there exists both the directory with translated POs and with template POTs,
using the C{templates} option the sieve can be instructed to count POTs
with no same-named PO counterpart as fully untranslated in the statistics.
Value to C{templates} option is in the form C{search:replace}, where
C{search} is the substring in the given PO paths that will be replaced with
C{replace} string to construct the POT paths. For example::

    $ cd $MYTRANSLATIONS
    $ ls
    my_lang  templates
    $ posieve.py stats -stemplates:my_lang:templates my_lang/

Options C{minwords} and C{maxwords} tell the sieve to account only those
messages satisfying these limits, in I{either} the original or translation,
not necessarily both.

For L{summited<posummit>} catalogs, C{branch} option is used to restrict
the counting to the given branch only. Several branch IDs may be given as
a comma-separated list.

Custom Contexts
===============

Some older PO files will have message contexts embedded into the C{msgid}
field, instead of using the Gettext proper C{msgctxt} field. There are
several customary ways in which this is done, but in general it depends on
the translation environment where such PO files are used.

Embedded contexts will skew the statistics. Pology contains several sieves
for converting embedded context into C{msgctxt} context, named C{normctx-*},
where C{*} usually names the translation environment in question. When the
statistics on such PO files is desired, the C{stats} sieve should be
preceeded in the chain by the context conversion sieve::

    $ posieve.py normctx-ooo,stats openoffice-fr/

Note that C{normctx-*} sieves, while they modify the messages, by default
do not request synchronization of catalogs to disk. This is precisely so
that they may be run as prefilters to non-modifying sieves such as C{stats}.

Output Legend
=============

    The basic output is the table where rows present statistics for
    a category of messages, and columns the statistical bits of data::

        $ posieve.py stats frobaz/
        -              msg  msg/tot  w-or  w/tot-or  w-tr  ch-or  ch-tr
        translated     ...    ...    ...     ...     ...    ...    ...
        fuzzy          ...    ...    ...     ...     ...    ...    ...
        untranslated   ...    ...    ...     ...     ...    ...    ...
        total          ...    ...    ...     ...     ...    ...    ...
        obsolete       ...    ...    ...     ...     ...    ...    ...

    The C{total} row is the sum of C{translated}, C{fuzzy}, and
    C{untranslated}, but not C{obsolete}. The columns are as follows:
      - C{msg}: number of messages
      - C{msg/tot}: percentage of messages relative to C{total}
      - C{w-or}: number of words in original
      - C{w/tot-or}: percentage of words in original relative to C{total}
      - C{w-tr}: number of words in translation
      - C{ch-or}: number of characters in original
      - C{ch-tr}: number of characters in translation

    The output with C{detail} sieve option in effect is the same, with
    several columns of derived data appended to the table:
      - C{w-dto}: increase in words from original to translation
      - C{ch-dto}: increase in characters from original to translation
      - C{w/msg-or}: average of words per message in original
      - C{w/msg-tr}: average of words per message in translation
      - C{ch/w-or}: average of characters per message in original
      - C{ch/w-tr}: average of characters per message in translation

    If any of the sieve options that restrict counting to certain messages
    have been supplied, this is confirmed in output by a C{>>>} message
    before the table. For example::

        $ posieve.py stats -smaxwords:5 frobaz/
        >>> at-most-words: 5
        (...the stats table follows...)

    When C{incomplete} option is given, the statistics table is followed by
    a table of not fully translated catalogs, with counts of fuzzy and
    untranslated messages and words::

        $ posieve.py stats -sincomplete frobaz/
        (...the stats table...)
        incomplete-catalog   msg/f   msg/u   msg/f+u   w/f   w/u   w/f+u
        frobaz/foxtrot.po        0      11        11     0   123     123
        frobaz/november.po      19      14        33    85    47     132
        frobaz/sierra.po        22       0        22   231     0     231

    In the column names, C{msg/*} and C{w/*} stand for messages and words;
    C{*/f}, C{*/u}, and C{*/f+u} stand for fuzzy, untranslated, and the
    two summed.

    When options C{msgbar} or C{wbar} are in effect, then bellow the table
    an ASCII bar is displayed, giving visual relation between numbers of
    translated, fuzzy, and untranslated messages or words::

        $ posieve.py stats -swbar frobaz/
        (...the stats table...)
        4572/1829/2533 w-or |¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤×××××××××············|

    The output of the table can be prevented using the C{notab} option.
    A typical condensed overview of translation state is obtained by::

        $ posieve.py stats frobaz/ -sbyfile -smsgbar -snotab
        --- frobaz/foxtrot.po   34/ -/11 msgs |¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤·····|
        --- frobaz/november.po  58/19/14 msgs |¤¤¤¤¤¤¤¤¤¤¤×××××····|
        --- frobaz/sierra.po    65/22/ - msgs |¤¤¤¤¤¤¤¤¤¤¤¤¤¤××××××|
        === (overall)          147/41/25 msgs |¤¤¤¤¤¤¤¤¤¤¤¤¤××××···|

    though one may want to use C{-swbar} instead, as word counts are more
    representative of amount of work needed to complete the translation.
    The rounding for bars is such that while there is at least one fuzzy
    or untranslated message or word, the bar will show one incomplete cell.

    By default bars are presenting relative information, i.e. the percentages
    of translated, fuzzy, and untranslated messages. This can be changed
    into absolute display using the C{absolute} option, where single bar-cell
    stands for a fixed number of messages or words, determined by taking
    into account the stats across all bars in the run. However, the length of
    an absolute bar will never be below three cells.

Notes on Counting
=================

    The word and character counts for a given message field are obtained
    in the following way:
      - accelerator marker, if defined, is removed
      - XML-like markup is eliminated (C{<...>})
      - special tokens, such as format directives, are also eliminated
        (e.g. C{%s} in a message marked as C{c-format})
      - the text is split into words by taking all contiguous sequences of
        C{word} characters, as defined by C{\w} regular expression class
        (this means letters, numbers, underscore)
      - all words not starting with a letter are eliminated
      - the words that remain count into statistics

    In plural messages, the counts of the original are those of C{msgid}
    and C{msgid_plural} fields I{averaged}, and so for the translation,
    the averages of all C{msgstr} fields. In this way, the comparative
    statistics between the original and the translation is not skewed for
    languages that have other than two plural forms.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import os, sys
from pology.misc.fsops import collect_catalogs
from pology.misc.tabulate import tabulate
from pology.misc.split import split_text
from pology.misc.comments import parse_summit_branches
from pology.file.catalog import Catalog
from pology.misc.report import warning
import pology.misc.colors as C


class Sieve (object):

    def __init__ (self, options, global_options):

        # Characters to consider as shortcut markers.
        self.shortcut_explicit = False
        self.shortcut_usual = "&_~" # some typical markers
        self.shortcut = ""
        if "accel" in options and len(options["accel"]) > 0:
            options.accept("accel")
            self.shortcut = options["accel"]
            self.shortcut_explicit = True

        # Display detailed statistics?
        self.detailed = False
        if "detail" in options:
            self.detailed = True
            options.accept("detail")

        # Display compact list of catalogs with fuzzy/untranslated messages?
        self.incomplete = False
        if "incomplete" in options:
            self.incomplete = True
            options.accept("incomplete")

        # Templates correspondence.
        # Mapping of catalogs to templates, in form of <search>:<replace>.
        # For each catalog file path, the first <search> substring is replaced
        # by <replace>, and .po replaced with .pot, to construct its template
        # file path. All templates not found under such paths are reported.
        # Furthermore, all subdirs of these paths are searched for templates
        # without corresponding catalogs, and every such template is counted
        # as fully untranslated PO.
        self.tspec = ""
        if "templates" in options:
            self.tspec = options["templates"]
            if ":" not in self.tspec:
                self.tspec_srch = self.tspec
                self.tspec_repl = ""
            else:
                self.tspec_srch, self.tspec_repl = self.tspec.split(":", 1)
            options.accept("templates")

        # Summit: consider only messages belonging to given branches.
        self.branches = None
        if "branch" in options:
            self.branches = set(options["branch"].split(","))
            options.accept("branch")

        # Count in only the messages which have at most this many words,
        # either in original or translation.
        self.maxwords = None
        if "maxwords" in options:
            self.maxwords = int(options["maxwords"])
            options.accept("maxwords")

        # Count in only the messages which have at least this many words,
        # either in original or translation.
        self.minwords = None
        if "minwords" in options:
            self.minwords = int(options["minwords"])
            options.accept("minwords")

        # Report statistics per leaf directory and/or per file.
        self.bydir = None
        if "bydir" in options:
            self.bydir = True
            options.accept("bydir")
        self.byfile = None
        if "byfile" in options:
            self.byfile = True
            options.accept("byfile")

        # Forms of the statistics.
        self.table = True
        if "notab" in options:
            self.table = False
            options.accept("notab")
        self.wbar = False
        if "wbar" in options:
            self.wbar = True
            options.accept("wbar")
        self.msgbar = False
        if "msgbar" in options:
            self.msgbar = True
            options.accept("msgbar")

        # Absolute or relative bars.
        self.absolute = False
        if "absolute" in options:
            self.absolute = True
            options.accept("absolute")

        # Filenames of catalogs which are not fully translated.
        self.incomplete_catalogs = {}

        # Counted categories.
        self.count_spec = (
            ("trn", u"translated"),
            ("fuz", u"fuzzy"),
            ("unt", u"untranslated"),
            ("tot", u"total"),
            ("obs", u"obsolete"),
        )

        # Number of counts per category:
        # messages, words in original, words in translation,
        # characters in original, characters in translation.
        self.counts_per_cat = 5

        # Category counts per catalog filename.
        self.counts = {}

        # Collections of all confirmed templates and tentative template subdirs.
        self.matched_templates = {}
        self.template_subdirs = {}

        # Some indicators of metamessages.
        self.xml2po_meta_msgid = dict([(x, True) for x in
            ("translator-credits",)])
        self.xml2pot_meta_msgid = dict([(x, True) for x in
            ("ROLES_OF_TRANSLATORS", "CREDIT_FOR_TRANSLATORS")])
        self.kde_meta_msgctxt = dict([(x, True) for x in
            ("NAME OF TRANSLATORS", "EMAIL OF TRANSLATORS")])

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
        if (    self.tspec
            and not cat.filename.endswith(".pot")):

            # Construct expected template path.
            tpath = cat.filename.replace(self.tspec_srch, self.tspec_repl, 1)
            pdot = tpath.rfind(".")
            if pdot >= 0:
                tpath = tpath[:pdot] + ".pot"
            # Inform if the template does not exist.
            if not os.path.isfile(tpath):
                warning("expected template catalog missing: %s" % tpath)
            # Indicate the template has been matched.
            if tpath not in self.matched_templates:
                self.matched_templates[tpath] = True
            # Store tentative template subdir.
            tsubdir = os.path.dirname(tpath)
            if tsubdir not in self.template_subdirs:
                csubdir = os.path.dirname(cat.filename)
                self.template_subdirs[tsubdir] = csubdir

        # Check if the catalog itself states the shortcut character,
        # unless specified explicitly by the command line.
        if not self.shortcut_explicit:
            accel = cat.possible_accelerator()
            if accel:
                self.shortcut = accel
            else:
                self.shortcut = self.shortcut_usual


    def process (self, msg, cat):

        # Summit: if branches were given, skip the message if it does not
        # belong to any of the given branches.
        if self.branches:
            msg_branches = parse_summit_branches(msg)
            if not set.intersection(self.branches, msg_branches):
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

        # Count the words and characters in original and translation.
        # Remove shortcut markers prior to counting; don't include words
        # which do not start with a letter; remove scripted part.
        # For plural messages compute averages of msgid and msgstr groups,
        # to normalize comparative counts on varying number of plural forms.
        nwords = {"orig" : 0, "tran" : 0}
        nchars = {"orig" : 0, "tran" : 0}
        msgids = [msg.msgid]
        if msg.msgid_plural:
            msgids.append(msg.msgid_plural)
        for src, texts in (("orig", msgids), ("tran", msg.msgstr)):
            if ismeta: # consider metamessages as zero counts
                continue
            lnwords = [] # this group's word count, for averaging
            lnchars = [] # this group's character count, for averaging
            for text in texts:
                for c in self.shortcut:
                    text = text.replace(c, "")
                pf = text.find("|/|")
                if pf >= 0:
                    text = text[0:pf]
                words = split_text(text, True, msg.format)[0]
                words = [w for w in words if w[0:1].isalpha()]
                lnwords.append(len(words))
                lnchars.append(len("".join(words)))
            nwords[src] += int(round(float(sum(lnwords)) / len(texts)))
            nchars[src] += int(round(float(sum(lnchars)) / len(texts)))

        # If the number of words has been limited, skip the message if it
        # does not fall in the range.
        if self.maxwords is not None:
            if not (   nwords["orig"] <= self.maxwords
                    or nwords["tran"] <= self.maxwords):
                return
        if self.minwords is not None:
            if not (   nwords["orig"] >= self.minwords
                    or nwords["tran"] >= self.minwords):
                return

        # Detect categories and add the counts.
        categories = []

        if not msg.obsolete:
            self.count["tot"][0] += 1
            categories.append("tot")
        else:
            self.count["obs"][0] += 1
            categories.append("obs")

        if msg.translated:
            self.count["trn"][0] += 1
            categories.append("trn")
        elif msg.fuzzy:
            self.count["fuz"][0] += 1
            categories.append("fuz")
            if cat.filename not in self.incomplete_catalogs:
                self.incomplete_catalogs[cat.filename] = True
        elif msg.untranslated:
            self.count["unt"][0] += 1
            categories.append("unt")
            if cat.filename not in self.incomplete_catalogs:
                self.incomplete_catalogs[cat.filename] = True

        for cat in categories:
            self.count[cat][1] += nwords["orig"]
            self.count[cat][2] += nwords["tran"]
            self.count[cat][3] += nchars["orig"]
            self.count[cat][4] += nchars["tran"]


    # Sort filenames as if templates-only were within language subdirs.
    def _sort_equiv_filenames (self, filenames):

        def equiv_template_path (x):
            cdir = os.path.dirname(x)
            if cdir in self.template_subdirs:
                cdir = self.template_subdirs[cdir]
                return os.path.join(cdir, os.path.basename(x))
            else:
                return x

        filenames.sort(lambda x, y: cmp(equiv_template_path(x),
                                        equiv_template_path(y)))


    def finalize (self):

        # If template correspondence requested, handle POTs without POs.
        if self.template_subdirs:
            # Collect all catalogs in collected subdirs.
            tpaths = collect_catalogs(self.template_subdirs)
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

        # Assemble sets of total counts by requested divisions.
        count_overall = self._count_zero()
        counts_bydir = {}
        filenames_bydir = {}
        for filename, count in self.counts.iteritems():

            count_overall = self._count_sum(count_overall, count)

            if self.bydir:
                cdir = os.path.dirname(filename)
                if cdir in self.template_subdirs:
                    # Pretend templates-only are within language subdir.
                    cdir = self.template_subdirs[cdir]
                if cdir not in counts_bydir:
                    counts_bydir[cdir] = self._count_zero()
                    filenames_bydir[cdir] = []
                counts_bydir[cdir] = self._count_sum(counts_bydir[cdir], count)
                filenames_bydir[cdir].append(filename)

        # Arrange sets into ordered list with titles.
        counts = []
        if self.bydir:
            cdirs = counts_bydir.keys();
            cdirs.sort()
            for cdir in cdirs:
                if self.byfile:
                    self._sort_equiv_filenames(filenames_bydir[cdir])
                    for filename in filenames_bydir[cdir]:
                        counts.append(("--- %s" % filename,
                                       self.counts[filename]))
                counts.append(("+++ %s/" % cdir, counts_bydir[cdir]))
            counts.append(("=== (overall)", count_overall))

        elif self.byfile:
            filenames = self.counts.keys()
            self._sort_equiv_filenames(filenames)
            for filename in filenames:
                counts.append(("--- %s" % filename, self.counts[filename]))
            counts.append(("=== (overall)", count_overall))

        else:
            counts.append((None, count_overall))

        # See if the output will admit color sequences.
        can_color = sys.stdout.isatty()

        # Summit: If branches were given, indicate conspicuously up front.
        if self.branches:
            print ">>> selected-branches: %s" % " ".join(self.branches)

        # If the number of words has been limited, indicate conspicuously.
        if self.maxwords is not None and self.minwords is None:
            print ">>> at-most-words: %d" % self.maxwords
        if self.minwords is not None and self.maxwords is None:
            print ">>> at-least-words: %d" % self.minwords
        if self.minwords is not None and self.maxwords is not None:
            print ">>> words-in-range: %d-%d" % (self.minwords, self.maxwords)

        # Should titles be output in-line or on separate lines.
        self.inline = False
        maxtitlecw = 0
        if (not self.wbar or not self.msgbar) and (not self.table):
            for title, count in counts:
                if title is not None:
                    self.inline = True
                    titlecw = len(title)
                    if maxtitlecw < titlecw:
                        maxtitlecw = titlecw

        # Output statistics in requested forms.
        for title, count in counts:
            # Output the title if defined.
            if title is not None:
                if self.inline:
                    ntitle = (("%%-%ds" % maxtitlecw) % title)
                else:
                    ntitle = title
                if can_color:
                    # Must color after padding, to avoid it seeing the colors.
                    ntitle = C.BOLD + ntitle + C.RESET
                if self.inline:
                    print ntitle,
                else:
                    print ntitle

            if self.table:
                self._tabular_stats(counts, title, count, can_color)
            if self.msgbar:
                self._msg_bar_stats(counts, title, count, can_color)
            if self.wbar:
                self._w_bar_stats(counts, title, count, can_color)

        # Output the table of catalogs which are not fully translated,
        # if requested.
        if self.incomplete and self.incomplete_catalogs:
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
            coln = ["incomplete-catalog",
                    "msg/f", "msg/u", "msg/f+u", "w/f", "w/u", "w/f+u"]
            maxfl = max([len(x) for x in filenames])
            dfmt = ["%%-%ds" % maxfl, "%d", "%d", "%d", "%d", "%d", "%d"]
            # Output.
            print "-"
            print tabulate(data, coln=coln, dfmt=dfmt, space="   ", none=u"-",
                           colorized=can_color)


    def _tabular_stats (self, counts, title, count, can_color):

        # Order counts in tabular form.
        selected_cats = self.count_spec
        if False and self.incomplete: # skip this for the moment
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

        if self.detailed:
            # Derived data: word and character ratios.
            for o, t, ins in ((1, 2, 7), (3, 4, 8)):
                ratio = []
                for tkey, tname in selected_cats:
                    if count[tkey][o] > 0 and count[tkey][t] > 0:
                        r = float(count[tkey][t]) / count[tkey][o]
                        ratio.append((r - 1) * 100)
                    else:
                        ratio.append(None)
                data.insert(ins, ratio)

        if self.detailed:
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
        coln = ["msg", "msg/tot",
                "w-or", "w/tot-or", "w-tr", "ch-or", "ch-tr"]
        dfmt = ["%d", "%.1f%%",
                "%d", "%.1f%%", "%d", "%d", "%d"]
        if self.detailed:
            coln.extend(["w-dto", "ch-dto",
                         "w/msg-or", "w/msg-tr", "ch/w-or", "ch/w-tr"])
            dfmt.extend(["%+.1f%%", "%+.1f%%",
                         "%.1f", "%.1f", "%.1f", "%.1f"])

        # Output the table.
        print tabulate(data, rown=rown, coln=coln, dfmt=dfmt,
                       space="   ", none=u"-", colorized=can_color)


    def _msg_bar_stats (self, counts, title, count, can_color):

        self._bar_stats(counts, title, count, can_color, "msgs", 0)


    def _w_bar_stats (self, counts, title, count, can_color):

        self._bar_stats(counts, title, count, can_color, "w-or", 1)


    def _bar_stats (self, counts, title, count, can_color, dlabel, dcolumn):

        # Count categories to display and chars/colors associated to them.
        # Note: Use only characters from Latin1.
        tspecs = (("trn", u"×", C.GREEN),
                  ("fuz", u"¤", C.BLUE),
                  ("unt", u"·", C.RED))

        # Find out maximum counts overall.
        maxcounts = dict(trn=0, fuz=0, unt=0, tot=0)
        maxcounts_jumbled = maxcounts.copy()
        for otitle, ocount in counts:
            # Count both messages and words, for the number display later.
            for tkey in maxcounts_jumbled:
                for dcol in (0, 1):
                    c = ocount[tkey][dcol]
                    if maxcounts_jumbled[tkey] < c:
                        maxcounts_jumbled[tkey] = c

            # If absolute bars, compare counts only for same-level titles.
            if self.absolute:
                if title is None:
                    if otitle is not None:
                        continue
                else:
                    if otitle is None or not otitle.startswith(title[:1]):
                        continue

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
            if can_color:
                fmt_counts.append(tcol + cfmt + C.RESET)
            else:
                fmt_counts.append(cfmt)
        fmt_counts = "/".join(fmt_counts)

        # Maximum and nominal bar widths in characters.
        # TODO: Make options.
        if self.inline:
            nombarcw = 20
            maxbarcw = 50
        else:
            nombarcw = 40
            maxbarcw = 80

        def roundup (x):
            ix = int(x)
            if x - ix > 1e-16:
                ix += 1
            return ix

        # Compute number of cells per category.
        n_cells = {}
        if self.absolute:
            # Absolute bar.
            n_per_cell = 0
            for npc in (1, 2, 5,
                        10, 20, 50,
                        100, 200, 500,
                        1000, 2000, 5000,
                        10000, 20000, 50000):
                if npc * maxbarcw > maxcounts["tot"]:
                    n_per_cell = npc
                    break
            if not n_per_cell:
                warning("too great count, cannot display bar graph")
                return
            for tkey in ("fuz", "unt", "tot"):
                c = count[tkey][dcolumn]
                n_cells[tkey] = roundup(float(c) / n_per_cell)
            if n_cells["tot"] < 3:
                n_cells["tot"] = 3
            n_cells["trn"] = n_cells["tot"] - n_cells["fuz"] - n_cells["unt"]
        else:
            # Relative bar.
            n_per_cell = float(nombarcw) / count["tot"][dcolumn]
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
            if can_color:
                fmt_bar.append(tcol)
            fmt_bar.append(tchar * n_cells[tkey])
        if can_color:
            fmt_bar.append(C.RESET)
        fmt_bar = "".join(fmt_bar)

        # Assemble final output.
        print "%s %s |%s|" % (fmt_counts, dlabel, fmt_bar)

