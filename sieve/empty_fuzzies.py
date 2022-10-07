# -*- coding: UTF-8 -*-

"""
Make all fuzzy messages untranslated.

Documented in C{doc/user/sieving.docbook}.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

from pology import _, n_
from pology.report import report


def setup_sieve (p):

    p.set_desc(_("@info sieve discription",
    "Clear all fuzzy messages of translation."
    ))

    p.add_param("rmcomments", bool, defval=False,
                desc=_("@info sieve parameter discription",
    "Also remove translator comments from fuzzy messages."
    ))
    p.add_param("noprev", bool, defval=False,
                desc=_("@info sieve parameter discription",
    "Clear only fuzzy messages which do not have previous fields."
    ))


class Sieve (object):

    def __init__ (self, params):

        self.rmcomments = params.rmcomments
        self.noprev = params.noprev

        self.nemptied = 0


    def process (self, msg, cat):

        if (   (not self.noprev and msg.fuzzy)
            or (self.noprev and msg.fuzzy and msg.msgid_previous is None)
        ):
            if not msg.obsolete:
                msg.clear(keepmanc=(not self.rmcomments))
                self.nemptied += 1
            else:
                cat.remove_on_sync(msg)


    def finalize (self):

        if self.nemptied > 0:
            msg = n_("@info:progress",
                     "Cleared %(num)d fuzzy message of translation.",
                     "Cleared %(num)d fuzzy messages of translation.",
                     num=self.nemptied)
            report("===== " + msg)

