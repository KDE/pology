# -*- coding: UTF-8 -*-

import re
import math

from pology.misc.tabulate import tabulate

class Sieve (object):
    """Count number of messages with KUIT context markers."""

    def __init__ (self, options, global_options):
        self.nmatch = 0
        self.counts_by_file = {}

        self.report_by_file = False
        if "byfile" in options:
            options.accept("byfile")
            self.report_by_file = True

        # Indicators to the caller:
        self.caller_sync = False # no need to sync catalogs to the caller
        self.caller_monitored = False # no need for monitored messages

    def process (self, msg, cat):
        if not msg.obsolete:
            if cat.filename not in self.counts_by_file:
                self.counts_by_file[cat.filename] = {}
                self.counts_by_file[cat.filename]["total"] = 0
                self.counts_by_file[cat.filename]["match"] = 0
            self.counts_by_file[cat.filename]["total"] += 1

            if re.search(r"^\s*@[a-z]+", msg.msgctxt):
                self.nmatch += 1
                self.counts_by_file[cat.filename]["match"] += 1

    def finalize (self):
        print "Total with context markers: %d" % (self.nmatch,)
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
            print tabulate(data, coln=coln, rown=rown, dfmt=dfmt)
