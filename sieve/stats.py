# -*- coding: UTF-8 -*-

from pology.misc.tabulate import tabulate
from pology.misc.split import split_text

class Sieve (object):
    """General statistics."""

    def __init__ (self, options, global_options):

        # Characters to consider as shortcut markers.
        self.shortcut = ""
        if "accel" in options and len(options["accel"]) > 0:
            options.accept("accel")
            self.shortcut = "".join(options["accel"])
        else:
            # Assume & and _, these are the most typical.
            self.shortcut = "&_"

        # Display detailed statistics?
        self.detailed = False
        if "detail" in options:
            self.detailed = True
            options.accept("detail")

        self.count_spec = (
            ("trn", u"translated"),
            ("fuz", u"fuzzy"),
            ("unt", u"untranslated"),
            ("tot", u"total"),
            ("obs", u"obsolete"),
        );
        self.count = dict([(x[0], [0] * 5) for x in self.count_spec])

        # Indicators to the caller:
        self.caller_sync = False # no need to sync catalogs
        self.caller_monitored = False # no need for monitored messages

    def process (self, msg, cat):

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
        elif msg.untranslated:
            self.count["unt"][0] += 1
            categories.append("unt")

        # Count the words and characters in original and translation.
        # Remove shortcut markers prior to counting; don't include words
        # which do not start with a letter.
        nwords = {"orig" : 0, "tran" : 0}
        nchars = {"orig" : 0, "tran" : 0}
        for src, texts in (("orig", (msg.msgid, msg.msgid_plural)),
                           ("tran", msg.msgstr)):
            for text in texts:
                for c in self.shortcut:
                    text = text.replace(c, "")
                words = split_text(text, True, msg.format)[0]
                words = [w for w in words if w[0:1].isalpha()]
                nwords[src] += len(words)
                nchars[src] += len("".join(words))

        # Add the word count to detected categories.
        for cat in categories:
            self.count[cat][1] += nwords["orig"]
            self.count[cat][2] += nwords["tran"]
            self.count[cat][3] += nchars["orig"]
            self.count[cat][4] += nchars["tran"]

    def finalize (self):

        # Collected data.
        data = [[self.count[tkey][y] for tkey, tname in self.count_spec]
                for y in range(5)]

        # Derived data: messages/words completition ratios.
        for col, ins in ((0, 1), (1, 3)):
            compr = []
            for tkey, tname in self.count_spec:
                if tkey not in ("tot", "obs") and self.count["tot"] > 0:
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
