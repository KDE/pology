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

Sieve parameters:
  - C{noreview}: do not add comments about unreviewed context
  - C{eqmsgid}: report messages with C{msgid} equal to an unfuzzied message
  - C{lokalize}: report messages by opening them in Lokalize
  - C{fexpr:<expr>}: process only messages matching the search expression

By default, unfuzzied messages will also be given a translator comment
with C{unreviewed-context} string, so that translator may later find and
review such messages.
Addition of this comment can be prevented by issuing the C{noreview} parameter,
but it is usually better to find some time later and review unfuzzied messages.

Sometimes a lot of messages may be automatically equiped with contexts
(e.g. to group items by a common property), and then it may be necessary
to review only those messages which got split into two or more messages due
to newly added contexts.
In this scenario, C{eqmsgid} parameter may be issued to specifically report
all translated messages which have the C{msgid} equal to an unfuzzied message
(including such unfuzzied messages themselves).
Depending on exactly what kind of contexts have been added,
C{noreview} parameter may be useful here too.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

from pology.misc.report import report
from pology.misc.msgreport import report_msg_content
from pology.misc.msgreport import report_msg_to_lokalize
from pology.sieve.find_messages import build_msg_fmatcher


def setup_sieve (p):

    p.set_desc(
    "Unfuzzy messages which got fuzzy only due to changed context."
    "\n\n"
    "(Possible only if catalogs were merged with --previous option.)"
    "\n\n"
    "By default, unfuzzied messages will get a translator comment with "
    "the string '%s', so that they can be reviewed later."
    % "unreviewed-context"
    )

    p.add_param("noreview", bool, defval=False,
                desc=
    "Do not add translator comment indicating unreviewed context."
    )
    p.add_param("eqmsgid", bool, defval=False,
                desc=
    "Report translated messages with msgid equal to an unfuzzied message."
    )
    p.add_param("lokalize", bool, defval=False,
                desc=
    "Open reported messages in lokalize."
    )
    p.add_param("fexpr", unicode,
                metavar="EXPRESSION",
                desc=
    "Consider only messages matched by the search expression. "
    "See description of the same parameter to '%s' sieve." % ("find-messages")
    )


class Sieve (object):

    def __init__ (self, params):

        self.p = params

        # Create message matcher if requested.
        self.matcher = None
        if self.p.fexpr:
            self.matcher = build_msg_fmatcher(self.p.fexpr, abort=True)

        self.nunfuzz = 0
        self.msgs_by_msgid_per_cat = []


    def process_header (self, hdr, cat):

        if self.p.eqmsgid:
            self.msgs_by_msgid = {}
            self.unfuzz_msgids = set()
            self.msgs_by_msgid_per_cat.append(
                (cat, self.msgs_by_msgid, self.unfuzz_msgids))


    def process (self, msg, cat):

        if (    msg.fuzzy
            and msg.msgid == msg.msgid_previous
            and msg.msgid_plural == msg.msgid_plural_previous
            and (not self.matcher or self.matcher(msg, cat))
        ):
            msg.unfuzzy()
            self.nunfuzz += 1

            if not self.p.noreview:
                # Add as manual comment, as any other type will vanish
                # when catalog is merged with template.
                msg.manual_comment.append(u"unreviewed-context")

            if self.p.eqmsgid:
                self.unfuzz_msgids.add(msg.msgid)

        if self.p.eqmsgid:
            if msg.msgid not in self.msgs_by_msgid:
                self.msgs_by_msgid[msg.msgid] = []
            self.msgs_by_msgid[msg.msgid].append(msg)


    def finalize (self):

        nrep = 0
        for cat, msgs_by_msgid, unfuzz_msgids in self.msgs_by_msgid_per_cat:
            msggrps = [msgs for msgid, msgs in self.msgs_by_msgid.items()
                            if len(msgs) > 1]
            for msgs in msggrps:
                if msgs[0].msgid not in unfuzz_msgids:
                    continue
                for msg in sorted(msgs, key=lambda x: x.msgid):
                    nrep += 1
                    if self.p.lokalize:
                        report_msg_to_lokalize(msg, cat)
                    else:
                        report_msg_content(msg, cat, delim="-" * 20)

        if self.nunfuzz > 0:
            report("Total unfuzzied due to context: %d" % self.nunfuzz)
        if nrep > 0:
            report("Total reported due to equality of msgid: %d" % nrep)

