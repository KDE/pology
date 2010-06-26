# -*- coding: UTF-8 -*-

"""
Remove obsolete messages from catalogs.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

from pology import _, n_
from pology.misc.report import report


def setup_sieve (p):

    p.set_desc(_("@info sieve discription",
    "Remove obsolete messages from catalogs."
    ))


class Sieve (object):

    def __init__ (self, params):

        self.nmatch = 0


    def process (self, msg, cat):

        if msg.obsolete:
            cat.remove_on_sync(msg)
            self.nmatch += 1


    def finalize (self):

        if self.nmatch > 0:
            msg = n_("@info:progress",
                     "Removed %(num)d obsolete message.",
                     "Removed %(num)d obsolete messages.",
                     num=self.nmatch)
            report("===== " + msg)

