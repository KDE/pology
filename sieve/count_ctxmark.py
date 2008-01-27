# -*- coding: UTF-8 -*-

import re
import math

from pology.misc.tabulate import tabulate

class Sieve (object):
    """Count number of messages with KUIT context markers."""

    def __init__ (self, options, global_options):

        self.nmatch = 0
        self.ntotal = 0
        self.counts_by_file = {}

        self.report_by_file = False
        if "byfile" in options:
            options.accept("byfile")
            self.report_by_file = True

        self.count_uniqs = False
        if "cuniq" in options:
            options.accept("cuniq")
            self.count_uniqs = True
            self.uniq_no_ctxmark = set()
            self.uniq_no_context = set()

        # Indicators to the caller:
        self.caller_sync = False # no need to sync catalogs to the caller
        self.caller_monitored = False # no need for monitored messages


    def process (self, msg, cat):

        # Skip obsolete messages.
        if msg.obsolete:
            return

        # Skip some special messages.
        if msg.msgctxt in ("NAME OF TRANSLATORS", "EMAIL OF TRANSLATORS"):
            return

        self.ntotal += 1

        if cat.filename not in self.counts_by_file:
            self.counts_by_file[cat.filename] = {}
            self.counts_by_file[cat.filename]["total"] = 0
            self.counts_by_file[cat.filename]["match"] = 0
            if self.count_uniqs:
                self.counts_by_file[cat.filename]["uniq_nocxm"] = set()
                self.counts_by_file[cat.filename]["uniq_noctx"] = set()
        counts = self.counts_by_file[cat.filename]

        counts["total"] += 1

        if re.search(r"^\s*@[a-z]+", msg.msgctxt):
            self.nmatch += 1
            counts["match"] += 1
            if self.count_uniqs:
                # Unique by no context marker.
                msgxid = msg.msgid
                p = msg.msgctxt.strip().find(" ")
                if p >= 0:
                    msgxid += msg.msgctxt.strip()[p:]
                self.uniq_no_ctxmark.add(msgxid)
                counts["uniq_nocxm"].add(msgxid)
                # Unique by no context at all.
                self.uniq_no_context.add(msg.msgid)
                counts["uniq_noctx"].add(msg.msgid)


    def finalize (self):

        print   "Total with context markers: %d/%d (%.1f%%)" \
              % (self.nmatch, self.ntotal, 100.0 * self.nmatch / self.ntotal)

        if self.count_uniqs:
            nuniq = len(self.uniq_no_ctxmark)
            print   "Total would-be unique without context marker: %d " \
                    "(%+.1f%% growth)" \
                  % (nuniq, 100.0 * (self.nmatch - nuniq) / nuniq)
            nuniq2 = len(self.uniq_no_context)
            print   "Total would-be unique without context at all: %d " \
                    "(%+.1f%% growth)" \
                  % (nuniq2, 100.0 * (self.nmatch - nuniq2) / nuniq2)

        if self.report_by_file:
            print "...in the following files:"
            counts = [x for x in self.counts_by_file.items()
                        if x[1]["match"] > 0]
            counts.sort(cmp=lambda x, y: cmp(y[1]["match"], x[1]["match"]))
            ratios = [
                # floor(...*1000)/10 rounds down the percent to one decimal
                math.floor(float(x[1]["match"]) / x[1]["total"] * 1000) / 10 \
                for x in counts]
            coln = ["match", "total",  "ratio"]
            dfmt = [   "%d",    "%d", "%.1f%%"]
            rown = [x[0] for x in counts]
            data = [[x[1]["match"] for x in counts],
                    [x[1]["total"] for x in counts],
                    ratios]
            if self.count_uniqs:
                coln.append("growth-cxm")
                dfmt.append("%+.1f%%")
                nuinqs = [len(x[1]["uniq_nocxm"]) for x in counts]
                data.append([100.0 * (x[1]["match"] - y) / y
                             for x, y in zip(counts, nuinqs)])
                coln.append("growth-ctx")
                dfmt.append("%+.1f%%")
                nuinqs2 = [len(x[1]["uniq_noctx"]) for x in counts]
                data.append([100.0 * (x[1]["match"] - y) / y
                             for x, y in zip(counts, nuinqs2)])
            print tabulate(data, coln=coln, rown=rown, dfmt=dfmt)

