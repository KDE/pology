# -*- coding: UTF-8 -*-

"""
Unfuzzy messages fuzzied only due to a change in context marker.

This sieve is similar to L{unfuzzy-context-only<unfuzzy_context_only>},
but it unfuzzies the message when the only change is in a specific part
of C{msgctxt}, in the I{context marker}.

Context marker is a part of KUIT markup (KDE user interface text),
which states more formally the general usage intent for the PO entry.
For example, there may be two messages which are same in English,
but one applied as a menu item, and another as a dialog title;
using KUIT, they would be marked as::

    msgctxt "@action:inmenu File"
    msgid "Export as HTML"
    msgstr ""

    msgctxt "@title:window"
    msgid "Export as HTML"
    msgstr ""

The context marker is the leading part of the context, starting with C{@...}
and ending with the first whitespace. This sieve will unfuzzy the message
if only the context marker has changed (or was added or removed), but not if
the change was in the rest of the context, after the first whitespace.

Sieve parameters:
  - C{noreview}: do not add comment about unreviewed context (I{not advised})

@see: L{unfuzzy-context-only<sieve.unfuzzy_context_only>}

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

