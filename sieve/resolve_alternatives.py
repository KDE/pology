# -*- coding: UTF-8 -*-

import sys, os, re
from pology.misc.resolve import resolve_alternatives


def error (msg, code=1):

    cmdname = os.path.basename(sys.argv[0])
    sys.stderr.write("%s: error: %s\n" % (cmdname, msg))
    sys.exit(code)


class Sieve (object):
    """Resolve alternatives directives in msgstr."""

    def __init__ (self, options, global_options):

        self.nresolved = 0
        self.nmalformed = 0

        # Number of alternatives per directive.
        if "alt" in options:
            for spec in options["alt"].split(","):
                if spec.endswith("t"):
                    self.total = int(spec[:-1])
                else:
                    self.select = int(spec)
            if not hasattr(self, "total"):
                error("number of alternatives not provided")
            if not hasattr(self, "select"):
                error("selected alternative not provided")
            if self.total < 1:
                error("invalid number of alternatives: %d" % self.total)
            if self.select < 1 or self.select > self.total:
                error("selected alternative out of range: %d" % self.select)
            options.accept("alt")
        else:
            error("need alternatives specification (-salt:<select>,<total>t)")


    def process (self, msg, cat):

        for i in range(len(msg.msgstr)):
            msg.msgstr[i], nresolved, malformed = \
                resolve_alternatives(msg.msgstr[i], self.select, self.total,
                                     srcname=cat.filename)
            if not malformed:
                self.nresolved += nresolved
            else:
                self.nmalformed += 1


    def finalize (self):

        if self.nresolved > 0:
            print "Total resolved alternatives: %d" % self.nresolved
        if self.nmalformed > 0:
            print "Total malformed alternatives: %d" % self.nmalformed

