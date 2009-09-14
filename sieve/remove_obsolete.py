# -*- coding: UTF-8 -*-

"""
Remove obsolete messages from catalogs.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

from pology.misc.report import report


def setup_sieve (p):

    p.set_desc(
    "Remove obsolete messages from catalogs."
    )


class Sieve (object):

    def __init__ (self, params):

        self.nmatch = 0


    def process (self, msg, cat):

        if msg.obsolete:
            cat.remove_on_sync(msg)
            self.nmatch += 1


    def finalize (self):

        if self.nmatch > 0:
            report("Total obsolete messages removed: %d" % self.nmatch)

