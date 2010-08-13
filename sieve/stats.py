# -*- coding: UTF-8 -*-

"""
Statistics: message and word counts by category, etc.

Various statistics on catalogs, that may help review the progress,
split up the work, find out what needs updating, etc.

Sieve parameters:
  - C{accels:<chars>}: accelerator markers in GUI messages
  - C{detail}: give more detailed statistics
  - C{incomplete}: additionally list catalogs which are not 100% translated
  - C{incompfile:<file>}: write filenames of incomplete catalogs into a file,
        one path per line
  - C{templates:<spec>}: compare translation with templates (see below)
  - C{minwords:<number>}: count only messages with at least this many words
  - C{maxwords:<number>}: count only messages with at most this many words
  - C{lspan:<from>:<to>}: include only messages in this range of lines
  - C{espan:<from>:<to>}: include only messages in this range of entries
  - C{branch:<branch_id>}: consider only messages from this branch (summit)
  - C{bydir}: display report by each leaf directory, followed by totals
  - C{byfile}: display report by each catalog, followed by totals
  - C{msgbar}: show statistics as ASCII bar of message counts
  - C{wbar}: show statistics as ASCII bar of word counts
  - C{absolute}: make bars show absolute rather than relative info
  - C{ondiff}: split word and character counts in fuzzy messages
        based on difference ratio
  - C{mincomp}: include only catalogs with sufficient completeness
  - C{filter:<hookspec>}: apply F1A filtering hook to translation prior
        to matching (see L{getfunc.get_hook_ireq} for the format
        of hook specifications)

The accelerator characters should be removed from the messages before
counting, in order not to introduce word splits where there are none.
If accelerator character is not given by C{accel} parameter, the sieve will try
to guess the accelerator; it may choose wrongly or decide that there are no
accelerators. E.g. an C{X-Accelerator-Marker} header field is checked for the
accelerator character.

If there exists both the directory with translated POs and with template POTs,
using the C{templates} parameter the sieve can be instructed to count POTs
with no same-named PO counterpart as fully untranslated in the statistics.
Value to C{templates} parameter is in the form of C{search:replace}, where
C{search} is the substring in the directory paths of processed PO files that
will be replaced with C{replace} string to construct directory paths of POTs.
For example::

    $ cd $MYTRANSLATIONS
    $ ls
    my_lang  templates
    $ posieve.py stats -stemplates:my_lang:templates my_lang/

Several parameters are used to restrict counting to catalogs and messages
satisfying a certain criterion:

  - C{minwords} and C{maxwords} restrict counting to messages satisfying
    these word limits, in I{either} the original or translation.

  - Counting may be restricted to a range of messages, given by parameters
    C{lspan} (by referent line numbers) and C{espan} (by entry numbers).
    The span is inclusive by start value, exclusive by end value
    (e.g. C{espan:4:8} includes messages with entry numbers 4, 5, 6, 7).
    If start value is omitted (e.g. C{lspan::100}), 0 is assumed;
    if end value is omitted (e.g. C{lspan:100:}), total number of lines
    or entries is assumed.

  - For L{summited<scripts.posummit>} catalogs, C{branch} parameter is used to
    count only messages from the given branch (several branch IDs may
    be given as a comma-separated list).

  - Fuzzy messages are often very easy to correct (e.g. a typo fixed), which
    may make their word count misleading when estimating effort.
    To amend this somewhat, if parameter C{ondiff} is issued the word
    and character counts of fuzzy messages are reduced by
    the difference ratio between current and previous C{msgid} fields,
    if previous C{msgid} is available and the difference between them
    is smaller than some threshold.
    The removed parts of counts are added to translated category,
    so that total counts remain the same.

  - Parameter C{mincomp} can be used to restrict counting only to catalogs
    of completeness equal to or higher than this (measured by ratio of
    translated to all messages, excluding obsolete).
    This may be especially useful when there are no templates around,
    instead all catalogs being initialized as empty, to include only
    those catalogs which have been actually worked on.

If more than one restriction parameter is used, all must be satisfied for
the catalog or message to be taken into account.


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

    $ posieve.py --no-sync normctx-ooo,stats openoffice-fr/

Note that C{normctx-*} sieves, since they modify messages, would by default
cause the catalogs to be modified on disk. Option C{--no-sync} is therefore
used to prevent modified catalogs from being synced to disk.

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

The output with C{detail} parameter in effect is the same, with
several columns of derived data appended to the table:
  - C{w-ef}: word expansion factor
        (increase in words from original to translation)
  - C{ch-ef}: character expansion factor
        (increase in characters from original to translation)
  - C{w/msg-or}: average of words per message in original
  - C{w/msg-tr}: average of words per message in translation
  - C{ch/w-or}: average of characters per message in original
  - C{ch/w-tr}: average of characters per message in translation

If any of the sieve parameters that restrict counting to certain messages
have been supplied, this is confirmed in output by a C{>>>} message
before the table. For example::

    $ posieve.py stats -smaxwords:5 frobaz/
    >>> at-most-words: 5
    (...the stats table follows...)

When C{incomplete} parameter is given, the statistics table is followed by
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

When parameters C{msgbar} or C{wbar} are in effect, statistics is given
in the form of an ASCII bar, giving visual relation between numbers of
translated, fuzzy, and untranslated messages or words::

    $ posieve.py stats -swbar frobaz/
    4572/1829/2533 w-or |¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤¤×××××××××············|

A typical condensed overview of translation state is obtained by::

    $ posieve.py stats -sbyfile -smsgbar frobaz/
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
into absolute display using the C{absolute} parameter, where single bar-cell
stands for a fixed number of messages or words, determined by taking
into account the stats across all bars in the run. When absolute mode
is engaged, the bars are shown only for the most specific count level
(e.g. only for files if C{byfile} in effect).

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
    "Reduce word and character counts in fuzzy messages based on "
    "difference ratio between current and previous original text, "
    "and add the removed parts to translated category."
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
        if self.p.msgbar or self.p.wbar:
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

        self.pfilters = []
        for hreq in self.p.filter or []:
            self.pfilters.append(get_hook_ireq(hreq, abort=True))


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
            dr2 = dr / drth
            if dr2 > 1.0:
                dr2 = 1.0
            # Split counts between primary fuzzy count, and secondary
            # translated, so that total remains the same.
            nswords.update({"trn": {}, "fuz": {}})
            nschars.update({"trn": {}, "fuz": {}})
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
                nitems2["trn"][src] = num - rnum
                nitems2["fuz"][src] = rnum

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
        if (not self.p.wbar or not self.p.msgbar) and (not self.p.table):
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
        if self.p.incompfile and self.incomplete_catalogs:
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
                _("@title:column percentage of words to total in translation",
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

