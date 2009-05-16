# -*- coding: UTF-8 -*-

class Sieve (object):
    """Remove obsolete messages."""

    def __init__ (self, options):
        self.nmatch = 0

    def process (self, msg, cat):
        if msg.obsolete:
            cat.remove_on_sync(msg)
            self.nmatch += 1

    def finalize (self):
        if self.nmatch > 0:
            print "Total obsolete removed: %d" % (self.nmatch,)
