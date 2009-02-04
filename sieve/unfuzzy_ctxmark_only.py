# -*- coding: UTF-8 -*-

"""
Unfuzzy those messages fuzzied only due to a change in context marker.

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

Sieve options:
  - C{no-review}: do not add comment about unreviewed context (I{not advised!})

@see: L{unfuzzy-context-only<unfuzzy_context_only>}

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import re


_strip_rx = re.compile(r"^\s*@[^\s]+(.*)", re.U)
_norm_rx = re.compile(r"[^\w]", re.U)
def _stripped (ctxt):
    """Strip the KUIT context marker, and normalize rest of the string."""
    m = _strip_rx.search(ctxt)
    if m: stripped = m.group(1)
    else: stripped = ctxt
    return _norm_rx.sub("", stripped.lower())


class Sieve (object):
    """Unfuzzy when only a KUIT context mark difference to previous."""

    def __init__ (self, options):

        self.nmatch = 0

        # Add flag indicating unreviewed context?
        self.flag_review = True
        if "no-review" in options:
            options.accept("no-review")
            self.flag_review = False


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
            print "Total unfuzzied due to context marker: %d" % (self.nmatch,)

