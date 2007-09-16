# -*- coding: UTF-8 -*-

import sys, os, re


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
        if "alt" in options and len(options["alt"]) == 2:
            for spec in options["alt"]:
                if spec.endswith("t"):
                    self.total = int(spec[:-1])
                else:
                    self.select = int(spec)
            if not hasattr(self, "total"):
                error("number of alternatives not provided")
            if self.total < 1:
                error("invalid number of alternatives: %d" % self.total)
            if self.select < 1 or self.select > self.total:
                error("selected alternative out of range: %d" % self.select)
            options.accept("alt")
        else:
            error("need alternatives specification (-s alt:<select>,<total>t)")


    def process (self, msg, cat):

        for i in range(len(msg.msgstr)):
            msg.msgstr[i] = self.resolve_alts(msg.msgstr[i], cat.filename)


    def finalize (self):

        if self.nresolved > 0:
            print "Total resolved alternatives: %d" % self.nresolved
        if self.nmalformed > 0:
            print "Total malformed alternatives: %d" % self.nmalformed


    def resolve_alts (self, text, fname):

        head = "~@"
        hlen = len(head)

        original_text = text
        new_text = u""
        malformed = False
        nresolved_local = 0

        while True:
            p = text.find(head)
            if p < 0:
                new_text += text
                break

            # Append segment prior to alternatives directive to the result.
            new_text += text[:p]
            rep_text = text[p:] # text segment for error reporting

            # Must have at least 2 characters after the head.
            if len(text) < p + hlen + 2:
                malformed = True
                print "%s: malformed directive: \"...%s\"" % (fname, rep_text)
                break

            # Read the separating character and trim source text.
            sep = text[p + hlen]
            text = text[p + hlen + 1:]

            # Parse requested number of inserts,
            # choose the one with matching index for the result.
            for i in range(self.total):
                # Ending separator for this insert.
                p = text.find(sep)

                # Must have exactly the given total number of alternatives.
                if p < 0:
                    malformed = True
                    print "%s: too little alternatives in the directive: " \
                          "\"...%s\"" % (fname, rep_text)
                    break

                # If at requested alternative, append to the result.
                if i == self.select - 1:
                    new_text += text[:p]
                    nresolved_local += 1
                    # Don't break here, should check if the total number
                    # of alternatives match.

                # Trim source text.
                text = text[p + 1:]

        if malformed:
            self.nmalformed += 1
            new_text = original_text
        else:
            self.nresolved += nresolved_local

        return new_text
