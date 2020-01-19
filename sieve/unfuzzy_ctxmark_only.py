# -*- coding: UTF-8 -*-

"""
Unfuzzy messages fuzzied only due to a change in UI context marker.

Documented in C{doc/user/sieving.docbook}.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import re

from pology import _, n_
from pology.report import report


def setup_sieve (p):

    p.set_desc(_("@info sieve discription",
    "Unfuzzy messages which got fuzzy only due to changed context marker."
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


_strip_rx = re.compile(r"^\s*@[^\s]+(.*)", re.U)
_norm_rx = re.compile(r"[^\w]", re.U)

# Strip the KUIT context marker, and normalize rest of the string.
def _stripped (ctxt):
    m = _strip_rx.search(ctxt)
    if m: stripped = m.group(1)
    else: stripped = ctxt
    return _norm_rx.sub("", stripped.lower())


class Sieve (object):

    def __init__ (self, params):

        self.flag_review = not params.noreview

        self.nmatch = 0


    def process (self, msg, cat):

        if (    msg.fuzzy
            and msg.msgid == msg.msgid_previous
            and msg.msgid_plural == msg.msgid_plural_previous
            and (   _stripped(msg.msgctxt or u"")
                 == _stripped(msg.msgctxt_previous or u""))
        ):
            msg.unfuzzy()
            if self.flag_review:
                # Add as manual comment, as any other type will vanish
                # when catalog is merged with template.
                msg.manual_comment.append(u"unreviewed-context")
            self.nmatch += 1


    def finalize (self):

        if self.nmatch > 0:
            msg = n_("@info:progress",
                     "Unfuzzied %(num)d message fuzzy due to "
                     "difference in context marker only.",
                     "Unfuzzied %(num)d messages fuzzy due to "
                     "difference in context marker only.",
                     num=self.nmatch)
            report("===== " + msg)

