# -*- coding: UTF-8 -*-

import os
from pology.misc.fsops import collect_catalogs
from pology.misc.tabulate import tabulate
from pology.misc.split import split_text
from pology.file.catalog import Catalog


# Summit: Dig out the set of branches for the message.
def get_summit_branches (msg):

    # Prefix of auto-comment with list of branches for the message.
    br_prefix = "+>"

    for c in msg.auto_comment:
        if c.startswith(br_prefix):
            return set(c[len(br_prefix):].strip().split())

    return set()


class Sieve (object):
    """General statistics."""

    def __init__ (self, options, global_options):

        # Characters to consider as shortcut markers.
        self.shortcut = ""
        if "accel" in options and len(options["accel"]) > 0:
            options.accept("accel")
            self.shortcut = options["accel"]
        else:
            # Assume & and _, these are the most typical.
            self.shortcut = "&_"

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

        # Dictionary of catalogs which are not fully translated.
        # Key is the catalog filename.
        # Value is a doublet list: number fuzzy, number untranslated entries.
        self.incomplete_catalogs = {}

        # Counted categories.
        self.count_spec = (
            ("trn", u"translated"),
            ("fuz", u"fuzzy"),
            ("unt", u"untranslated"),
            ("tot", u"total"),
            ("obs", u"obsolete"),
        )
        self.count = dict([(x[0], [0] * 5) for x in self.count_spec])

        # Indicator of all visited catalogs.
        self.visited_cats = {}

        # Collections of all confirmed templates and tentative template subdirs.
        self.matched_templates = []
        self.template_subdirs = []

        # Indicators to the caller:
        self.caller_sync = False # no need to sync catalogs
        self.caller_monitored = False # no need for monitored messages


    def process (self, msg, cat):

        # If template correspondence requested, handle template matching.
        if (    self.tspec
            and cat.filename not in self.visited_cats
            and not cat.filename.endswith(".pot")):

            self.visited_cats[cat.filename] = True

            # Construct expected template path.
            tpath = cat.filename.replace(self.tspec_srch, self.tspec_repl, 1)
            pdot = tpath.rfind(".")
            if pdot >= 0:
                tpath = tpath[:pdot] + ".pot"
            # Inform if the template does not exist.
            if not os.path.isfile(tpath):
                print "expected template catalog missing: %s" % tpath
            # Indicate the template has been matched.
            if tpath not in self.matched_templates:
                self.matched_templates.append(tpath)
            # Store tentative template subdir.
            tsubdir = os.path.dirname(tpath)
            if tsubdir not in self.template_subdirs:
                self.template_subdirs.append(tsubdir)

        # Summit: if branches were given, skip the message if it does not
        # belong to any of the given branches.
        if self.branches:
            msg_branches = get_summit_branches(msg)
            if not set.intersection(self.branches, msg_branches):
                return

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
                self.incomplete_catalogs[cat.filename] = [0, 0]
            self.incomplete_catalogs[cat.filename][0] += 1
        elif msg.untranslated:
            self.count["unt"][0] += 1
            categories.append("unt")
            if cat.filename not in self.incomplete_catalogs:
                self.incomplete_catalogs[cat.filename] = [0, 0]
            self.incomplete_catalogs[cat.filename][1] += 1

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
            lnwords = [] # this group word count, for averaging
            lnchars = [] # this group character count, for averaging
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

        # Add the word count to detected categories.
        for cat in categories:
            self.count[cat][1] += nwords["orig"]
            self.count[cat][2] += nwords["tran"]
            self.count[cat][3] += nchars["orig"]
            self.count[cat][4] += nchars["tran"]


    def finalize (self):

        # If template correspondence requested, handle POTs without POs.
        if self.template_subdirs:
            # Collect all catalogs in collected subdirs.
            tpaths = collect_catalogs(self.template_subdirs)
            # Filter to have only POTs remain.
            tpaths = [x for x in tpaths if x.endswith(".pot")]
            # Filter to leave out matched templates.
            tpaths = [x for x in tpaths if x not in self.matched_templates]
            # Add stats on all unmached templates.
            for tpath in tpaths:
                cat = Catalog(tpath, monitored=False)
                for msg in cat:
                    self.process(msg, cat)

        # Summit: If branches were given, indicate conspicuously up front.
        if self.branches:
            print ">>> selected-branches: %s" % " ".join(self.branches)

        # Collected data.
        data = [[self.count[tkey][y] for tkey, tname in self.count_spec]
                for y in range(5)]

        # Derived data: messages/words completition ratios.
        for col, ins in ((0, 1), (1, 3)):
            compr = []
            for tkey, tname in self.count_spec:
                if tkey not in ("tot", "obs") and self.count["tot"][col] > 0:
                    r = float(self.count[tkey][col]) / self.count["tot"][col]
                    compr.append(r * 100)
                else:
                    compr.append(None)
            data.insert(ins, compr)

        if self.detailed:
            # Derived data: word and character ratios.
            for o, t, ins in ((1, 2, 7), (3, 4, 8)):
                ratio = []
                for tkey, tname in self.count_spec:
                    if self.count[tkey][o] > 0 and self.count[tkey][t] > 0:
                        r = float(self.count[tkey][t]) / self.count[tkey][o]
                        ratio.append((r - 1) * 100)
                    else:
                        ratio.append(None)
                data.insert(ins, ratio)

        if self.detailed:
            # Derived data: character/word ratio, word/message ratio.
            for w, c, ins in ((0, 1, 9), (0, 2, 10), (1, 3, 11), (2, 4, 12)):
                chpw = []
                for tkey, tname in self.count_spec:
                    if self.count[tkey][w] > 0 and self.count[tkey][c] > 0:
                        r = float(self.count[tkey][c]) / self.count[tkey][w]
                        chpw.append(r)
                    else:
                        chpw.append(None)
                data.insert(ins, chpw)

        # Row, column names and formats.
        rown = [tname for tkey, tname in self.count_spec]
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
                       space="   ", none=u"-")

        # Output the table of catalogs which are not fully translated,
        # if requested.
        if self.incomplete and len(self.incomplete_catalogs) > 0:
            filenames = self.incomplete_catalogs.keys()
            filenames.sort()
            data = []
            # Column of catalog filenames.
            data.append(filenames)
            # Column of numbers fuzzy.
            data.append([self.incomplete_catalogs[x][0] for x in filenames])
            # Column of numbers untranslated.
            data.append([self.incomplete_catalogs[x][1] for x in filenames])
            # Column of the two added.
            data.append([x + y for x, y in zip(*data[1:3])])
            # Column names and formats.
            coln = ["incomplete-catalog", "fuzz", "untr", "fuzz+untr"]
            maxfl = max([len(x) for x in filenames])
            dfmt = ["%%-%ds" % maxfl, "%d", "%d"]
            # Output.
            print "-"
            print tabulate(data, coln=coln, dfmt=dfmt, space="   ", none=u"-")

