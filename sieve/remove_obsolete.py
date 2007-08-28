# -*- coding: UTF-8 -*-

class Sieve (object):
    """Remove obsolete messages."""

    def __init__ (self, options, global_options):
        self.nmatch = 0
        # Indicators to the caller:
        # - no need for monitored messages, removing only
        self.caller_monitored = False

    def process (self, msg, cat):
        if msg.obsolete:
            cat.remove_on_sync(msg)
            self.nmatch += 1

    def finalize (self):
        if self.nmatch > 0:
            print "Total obsolete removed: %d" % (self.nmatch,)
