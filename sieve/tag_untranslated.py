# -*- coding: UTF-8 -*-

class Sieve (object):
    """Add flag "untranslated" to untranslated messages."""

    def __init__ (self, options, global_options):

        self.nmatch = 0

        # Indicators to the caller:
        # - monitor to avoid unnecessary reformatting when unfuzzied
        self.caller_monitored = True


    def process (self, msg, cat):

        flag_untranslated = u"untranslated"

        # Add flag if untranslated.
        if msg.untranslated:
            msg.flag.add(flag_untranslated)
            self.nmatch += 1
            msg.modcount = 1 # in case of non-monitored messages

        # Remove flag if already there, but message is no longer untranslated.
        elif flag_untranslated in msg.flag and not msg.untranslated:
            msg.flag.remove(flag_untranslated)
            msg.modcount = 1 # in case of non-monitored messages


    def finalize (self):

        if self.nmatch > 0:
            print "Total untranslated tagged: %d" % (self.nmatch,)
