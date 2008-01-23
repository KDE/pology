# -*- coding: UTF-8 -*-

import os, re, codecs
from pology.misc.escape import split_escaped
from pology.misc.comments import manc_parse_flag_list


def error (msg, code=1):
    cmdname = os.path.basename(sys.argv[0])
    sys.stderr.write("%s: error: %s\n" % (cmdname, msg))
    sys.exit(code)


# Pipe flag used to manually prevent matching for a particular message.
flag_no_bad_patterns = "no-bad-patterns"


# Load pattern string from the file:
# one pattern per non-empty line in the file,
# leading and trailing whitespace stripped,
# #-comments possible.
def load_patterns (filepath):

    ifl = codecs.open(filepath, "r", "UTF-8")

    rem_cmnt_rx = re.compile(r"#.*")
    patterns = []
    for line in ifl.readlines():
        line = rem_cmnt_rx.sub("", line).strip()
        if line:
            patterns.append(line)

    return patterns


# Process given list of pattern strings.
# If rxmatch is True, patterns are compiled into regexes.
# If casesens is False, re.I flag is used in regex compilation, or
# if regex patterns are not requested, patterns are lower-cased.
def process_patterns (patterns, rxmatch=False, casesens=True):

    patterns_cmp = []
    if rxmatch:
        rx_flags = re.U
        if not casesens:
            rx_flags |= re.I
        for pattern in patterns:
            patterns_cmp.append(re.compile(pattern, rx_flags))
    else:
        for pattern in patterns:
            if not casesens:
                patterns_cmp.append(pattern.lower())
            else:
                patterns_cmp.append(pattern)

    return patterns_cmp


# Try to match the text by all patterns in the list.
# If rxmatch is False, the patterns are considered plain substrings,
# otherwise compiled regexes.
# If msg is non-empty string, for each matched pattern an info line
# is output to stdout: either the msg as it is if pnames is empty,
# or (msg % pnames[i]) where pnames is list of pattern names of same
# length as the pattern
# Return the list of patterns that matched if pnames is empty,
# otherwise the list of (pattern, patname) tuples for patterns that matched.
def match_patterns (text, patterns, rxmatch=False, msg="", pnames=[]):

    matched_patterns = []
    for i in range(len(patterns)):
        pattern = patterns[i]

        matched = False
        if rxmatch:
            if pattern.search(text):
                matched = True
        else:
            if text.find(pattern) >= 0:
                matched = True

        if matched:
            if pnames:
                matched_patterns.append((pattern, pnames[i]))
                print msg % pnames[i]
            else:
                matched_patterns.append(pattern)
                print msg

    return matched_patterns


class Sieve (object):
    """Check for presence of deprecated patterns in translation."""

    def __init__ (self, options, global_options):

        self.nbad = 0

        # Patterns given by the command line.
        self.patterns = []
        if "pattern" in options:
            self.patterns = split_escaped(options["pattern"], ",")
            options.accept("pattern")

        # The patterns given by files (comma-separated list of paths):
        # one pattern per non-empty line in the file,
        # leading and trailing whitespace stripped, #-comments possible.
        if "fromfile" in options:
            files = split_escaped(options["fromfile"], ",")
            for file in files:
                if not os.path.isfile(file):
                    error("given path '%s' does not point to a file" % file)
                self.patterns.extend(load_patterns(file))
            options.accept("fromfile")

        # Whether pattern matching is case-sensitive.
        self.casesens = False
        if "casesens" in options:
            self.casesens = True
            options.accept("casesens")

        # Whether the patterns are regexes instead of plain substrings.
        self.rxmatch = False
        if "rxmatch" in options:
            self.rxmatch = True
            options.accept("rxmatch")

        # Process patterns.
        self.patterns_cmp = process_patterns(self.patterns,
                                             rxmatch=self.rxmatch,
                                             casesens=self.casesens)

        # Indicators to the caller:
        self.caller_sync = False # no need to sync catalogs to the caller
        self.caller_monitored = False # no need for monitored messages


    def process (self, msg, cat):

        # Check only translated messages.
        if not msg.translated:
            return

        # Do not check messages when told so.
        if flag_no_bad_patterns in manc_parse_flag_list(msg, "|"):
            return

        # Match patterns in all msgstr.
        msgfmt = (  "%s:%d(%d): bad pattern detected in translation: %s"
                  % (cat.filename, msg.refline, msg.refentry, "%s"))
        for msgstr in msg.msgstr:
            if not self.casesens:
                msgstr = msgstr.lower()
            self.nbad += len(match_patterns(msgstr, self.patterns_cmp,
                                            rxmatch=self.rxmatch, msg=msgfmt,
                                            pnames=self.patterns))


    def finalize (self):

        if self.nbad > 0:
            print "Total bad patterns detected in translation: %d" % self.nbad

