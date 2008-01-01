# -*- coding: UTF-8 -*-

class Sieve (object):
    """Unfuzzy when only a context difference to previous."""

    def __init__ (self, options, global_options):

        self.nmatch = 0

        # Add flag indicating unreviewed context?
        self.flag_review = True
        if "no-review" in options:
            options.accept("no-review")
            self.flag_review = False

        # Indicators to the caller:
        # - monitor to avoid unnecessary reformatting when unfuzzied
        self.caller_monitored = True


    def process (self, msg, cat):

        if msg.fuzzy \
        and msg.msgid == msg.msgid_previous \
        and msg.msgid_plural == msg.msgid_plural_previous:
            msg.fuzzy = False
            if self.flag_review:
                # Add as manual comment, as any other type will vanish
                # when catalog is merged with template.
                msg.manual_comment.append(u"unreviewed-context")
            self.nmatch += 1
            msg.modcount = 1 # in case of non-monitored messages


    def finalize (self):

        if self.nmatch > 0:
            print "Total unfuzzied due to context: %d" % (self.nmatch,)
