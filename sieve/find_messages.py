# -*- coding: UTF-8 -*-

import sys, os, re


def error (msg, code=1):

    cmdname = os.path.basename(sys.argv[0])
    sys.stderr.write("%s: error: %s\n" % (cmdname, msg))
    sys.exit(code)


class Sieve (object):
    """Find messages matching given criterion."""

    def __init__ (self, options, global_options):

        self.nmatch = 0

        self.accel_explicit = False
        self.accel = ""
        if "accel" in options:
            options.accept("accel")
            self.accel = "".join(options["accel"])
            self.accel_explicit = True

        self.rxflags = re.U
        if "case" in options:
            options.accept("case")
        else:
            self.rxflags |= re.I

        self.field = ""
        for field in ("msgctxt", "msgid", "msgstr"):
            if field in options:
                options.accept(field)
                self.field = field
                self.regex = re.compile(options[field], self.rxflags)

        if not self.field:
            error("no search pattern given")

        # Indicators to the caller:
        self.caller_sync = False # no need to sync catalogs
        self.caller_monitored = False # no need for monitored messages


    def process_header (self, hdr, cat):

        # Check if the catalog itself states the accelerator character,
        # unless specified explicitly by the command line.
        if not self.accel_explicit:
            accel = cat.possible_accelerator()
            if accel:
                self.accel = accel
            else:
                self.accel = ""


    def process (self, msg, cat):

        if msg.obsolete:
            return

        if self.field == "msgctxt":
            texts = [msg.msgctxt]
        elif self.field == "msgid":
            texts = [msg.msgid, msg.msgid_plural]
        elif self.field == "msgstr":
            texts = msg.msgstr
        else:
            error("unknown search field '%s'" % self.field)

        for text in texts:
            # Remove accelerators.
            for c in self.accel:
                text = text.replace(c, "")

            # Check for match.
            if self.regex.search(text):
                self.nmatch += 1
                if self.nmatch == 1:
                    print "--------------------"
                print "%s:%d(%d)" % (cat.filename, msg.refline, msg.refentry)
                print msg.to_string().rstrip()
                print "--------------------"
                break


    def finalize (self):

        if self.nmatch:
            print "Total matching: %d" % (self.nmatch,)

