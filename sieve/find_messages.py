# -*- coding: UTF-8 -*-

import sys, os, re, locale

reload(sys)
encoding = locale.getdefaultlocale()[1]
sys.setdefaultencoding(encoding)

def error (msg, code=1):

    cmdname = os.path.basename(sys.argv[0])
    sys.stderr.write("%s: error: %s\n" % (cmdname, msg))
    sys.exit(code)


class Sieve (object):
    """Find messages matching given criterion."""

    def __init__ (self, options, global_options):

        self.nmatch = 0

        self.accel = ""
        if "accel" in options:
            options.accept("accel")
            self.accel = "".join(options["accel"])

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
                rxstr = unicode(options[field], encoding)
                self.regex = re.compile(rxstr, self.rxflags)

        if not self.field:
            error("no search pattern given")

        # Indicators to the caller:
        self.caller_sync = False # no need to sync catalogs
        self.caller_monitored = False # no need for monitored messages


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
                print "--------------------"
                print "%s:%d(%d)" % (cat.filename, msg.refline, msg.refentry)
                print msg.to_string().rstrip()
                break


    def finalize (self):

        if self.nmatch:
            print "--------------------"
            print "Total matching: %d" % (self.nmatch,)

