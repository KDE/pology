# -*- coding: UTF-8 -*-

import re

class Sieve (object):
    """Replace normal space by unbreakable space when needed"""

    def __init__ (self, options, global_options):

        self.nmatch = 0
        
        # Add flag indicating unreviewed context?
        self.flag_review = True
        if "no-review" in options:
            options.accept("no-review")
            self.flag_review = False

        self.percent=re.compile("( %)(?=$| |\.|,)")
        # Indicators to the caller:
        # - monitor to avoid unnecessary reformatting when unfuzzied
        self.caller_monitored = True


    def process (self, msg, cat):

        changed=False

        for i in range(len(msg.msgstr)):
            msgstr=self.setUbsp(msg.msgstr[i])
            if msgstr!=msg.msgstr[i]:
                msg.msgstr[i]=msgstr
                changed=True
                self.nmatch += 1
                msg.modcount = 1 # in case of non-monitored messages

        if self.flag_review and changed:
            # Add as manual comment, as any other type will vanish
            # when catalog is merged with template.
            msg.manual_comment.append(u"unreviewed-context")

    def finalize (self):

        if self.nmatch > 0:
            print "Total messages changed: %d" % (self.nmatch,)

    def setUbsp(self, text):
        """Set correctly unbreakable spaces"""
        text=text.replace(u"\xa0", u" ")
        text=text.replace(u"&nbsp;:", u"\xc2\xa0:")
        text=text.replace(u" :", u"\xa0:")
        text=text.replace(u" ;", u"\xa0;")
        text=text.replace(u" ?", u"\xa0?")
        text=text.replace(u" !", u"\xa0!")
        text=text.replace(u"« ", u"«\xa0")
        text=text.replace(u" »", u"\xa0»")
        text=self.percent.sub(u"\xa0%", text)
        
        return text