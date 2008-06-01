# -*- coding: UTF-8 -*-

"""
Unfuzzy those messages fuzzied only due to a context change.

When C{msgmerge} is run with C{--previous} option to merge the catalog with
its template, for fuzzy messages it embeds the previous values of C{msgctxt}
and C{msgid} fields in special C{#|} comments. Sometimes, the only change to
the message is in C{msgctxt}, e.g. context added where there was none before.
Some translators and languages may be less dependent on contexts than the
other, or there may be a hurry prior to the release of the translation.
In such case, this sieve can be used to remove the fuzzy state for messages
where only the context was added/modified, which can be detected by comparing
the current and the previous fields.

By default, the sieve will not only remove fuzzy state, but also insert a
manual comment line with C{unreviewed-context} string, so that translators
may still find and review the context at a later point. The addition of this
comment can be prevented by the C{no-review} option, but it is always better
to find some time later and review the message.

Sieve options:
  - C{no-review}: do not add comment about unreviewed context (I{not advised!})

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

class Sieve (object):

    def __init__ (self, options, global_options):

        self.nmatch = 0

        # Add flag indicating unreviewed context?
        self.flag_review = True
        if "no-review" in options:
            options.accept("no-review")
            self.flag_review = False


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


    def finalize (self):

        if self.nmatch > 0:
            print "Total unfuzzied due to context: %d" % (self.nmatch,)
