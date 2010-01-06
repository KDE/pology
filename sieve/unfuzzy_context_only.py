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
    "Do not unfuzzy messages which have same msgid as another message, "
    "and report them together with all other messages with the same msgid."
    )
    p.add_param("lokalize", bool, defval=False,
                desc=
    "Open reported messages in Lokalize."
    )


class Sieve (object):

    def __init__ (self, params):

        self.p = params

        self.nunfuzz = 0
        self.nrep = 0


    def process_header (self, hdr, cat):

        self.msgs_by_msgid = {}
        self.msgs_to_unfuzzy_by_msgid = {}


    def process (self, msg, cat):

        if msg.obsolete:
            return

        if msg.msgid not in self.msgs_by_msgid:
            self.msgs_by_msgid[msg.msgid] = []
        self.msgs_by_msgid[msg.msgid].append(msg)

        if (    msg.fuzzy
            and msg.msgid == msg.msgid_previous
            and msg.msgid_plural == msg.msgid_plural_previous
        ):
            if msg.msgid not in self.msgs_to_unfuzzy_by_msgid:
                self.msgs_to_unfuzzy_by_msgid[msg.msgid] = []
            self.msgs_to_unfuzzy_by_msgid[msg.msgid].append(msg)


    def process_header_last (self, hdr, cat):

        msgs_to_report = []
        keys_of_msgs_to_report = set()
        if self.p.eqmsgid:
            for msg in cat:
                if msg.obsolete:
                    continue
                msgs = self.msgs_by_msgid.get(msg.msgid)
                msgs_to_unfuzzy = self.msgs_to_unfuzzy_by_msgid.get(msg.msgid)
                if len(msgs) > 1 and msgs_to_unfuzzy:
                    msgs_to_report.append(msg)
                    keys_of_msgs_to_report.add(msg.key)

        for msgs in self.msgs_to_unfuzzy_by_msgid.values():
            for msg in msgs:
                if msg.key not in keys_of_msgs_to_report:
                    msg.unfuzzy()
                    self.nunfuzz += 1

        for msg in msgs_to_report:
            if self.p.lokalize:
                report_msg_to_lokalize(msg, cat)
            else:
                report_msg_content(msg, cat, delim="-" * 20)
            self.nrep += 1


    def finalize (self):

        if self.nunfuzz > 0:
            report("Total unfuzzied due to context: %d" % self.nunfuzz)
        if self.nrep > 0:
            report("Total reported due to equality of msgid: %d" % self.nrep)

