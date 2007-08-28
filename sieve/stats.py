# -*- coding: UTF-8 -*-

from pology.misc.tabulate import tabulate
from pology.misc.split import split_text

class Sieve (object):
    """General statistics."""

    def __init__ (self, options, global_options):

        self.shortcut = ""
        if "accel" in options and len(options["accel"]) > 0:
            options.accept("accel")
            self.shortcut = "".join(options["accel"])
        else:
            # Assume & and _, these are the most typical.
            self.shortcut = "&_"

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
                words = split_text(text, True)[0]
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
        data = [[self.count[x[0]][y] for x in self.count_spec]
                for y in range(5)]

        # Derived data: word and character ratios.
        for o, t, ins in ((1, 2, 3), (3, 4, 6)):
            ratio = list()
            for x in self.count_spec:
                if self.count[x[0]][o] > 0 and self.count[x[0]][t] > 0:
                    r = float(self.count[x[0]][t]) / self.count[x[0]][o]
                    d = (r - 1) * 100
                    ratio.append(d)
                    #ratio.append(u"%+.1f" % (d,))
                else:
                    ratio.append(None)
            data.insert(ins, ratio)

        # Derived data: character/word ratio, word/message ratio.
        for w, c, ins in ((1, 3, 7), (2, 4, 8), (0, 1, 9), (0, 2, 10)):
            chpw = list()
            for x in self.count_spec:
                if self.count[x[0]][w] > 0 and self.count[x[0]][c] > 0:
                    r = float(self.count[x[0]][c]) / self.count[x[0]][w]
                    chpw.append(r)
                else:
                    chpw.append(None)
            data.insert(ins, chpw)

        # Row, column names and formats.
        rown = [x[1] for x in self.count_spec]
        coln = ["msg",
                "w-or", "w-tr", "w-dto",
                "ch-or", "ch-tr", "ch-dto",
                "ch/w-or", "ch/w-tr", "w/msg-or", "w/msg-tr"]
        dfmt = ["%d", "%d", "%d", "%+.1f%%", "%d", "%d", "%+.1f%%",
                "%.1f", "%.1f", "%.1f", "%.1f"]

        # Output the table.
        print tabulate(data, rown=rown, coln=coln, dfmt=dfmt,
                       space="   ", none=u"-")
