# -*- coding: UTF-8 -*-

"""
Unfuzzy those messages fuzzied only due to a context change.

Documented in C{doc/user/sieving.docbook}.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

from pology import _, n_
from pology.msgreport import report_msg_content
from pology.msgreport import report_msg_to_lokalize
from pology.report import report
from pology.sieve import add_param_poeditors


def setup_sieve (p):

    p.set_desc(_("@info sieve discription",
    "Unfuzzy messages which got fuzzy only due to changed context."
    "\n\n"
    "Possible only if catalogs were merged with --previous option."
    "\n\n"
    "By default, unfuzzied messages will get a translator comment with "
    "the string '%(str)s', so that they can be reviewed later.",
    str="unreviewed-context"
    ))

    p.add_param("noreview", bool, defval=False,
                desc=_("@info sieve parameter discription",
    "Do not add translator comment indicating unreviewed context."
    ))
    p.add_param("eqmsgid", bool, defval=False,
                desc=_("@info sieve parameter discription",
    "Do not unfuzzy messages which have same msgid as another message, "
    "and report them together with all other messages with the same msgid."
    ))
    add_param_poeditors(p)


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
            msg = n_("@info:progress",
                     "Unfuzzied %(num)d message fuzzy due to "
                     "difference in context only.",
                     "Unfuzzied %(num)d messages fuzzy due to "
                     "difference in context only.",
                     num=self.nunfuzz)
            report("===== " + msg)
        if self.nrep > 0:
            msg = n_("@info:progress",
                     "Reported %(num)d message due to equality "
                     "of '%(field)s' field.",
                     "Reported %(num)d messages due to equality "
                     "of '%(field)s' field.",
                     num=self.nrep, field="msgid")
            report("===== " + msg)

