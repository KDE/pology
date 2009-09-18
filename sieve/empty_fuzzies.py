# -*- coding: UTF-8 -*-

"""
Make all fuzzy messages untranslated.

For every fuzzy message, the translation and fuzzy data (the flag,
previous fields) are removed. Manual (translator) comments are left in
by default, but can be removed as well.
Obsolete fuzzy messages are completely removed.

Sieve options:
  - C{rmcomments}: also remove manual comments
  - C{noprev}: clear only fuzzy messages not having previous fields

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

from pology.misc.report import report


def setup_sieve (p):

    p.set_desc(
    "Make all fuzzy messages untranslated."
    )

    p.add_param("rmcomments", bool, defval=False,
                desc=
    "Also remove translator comments from fuzzy messages."
    )
    p.add_param("noprev", bool, defval=False,
                desc=
    "Clear only fuzzy messages which do not have previous fields."
    )


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
            report("Total fuzzy messages emptied: %d" % self.nemptied)

