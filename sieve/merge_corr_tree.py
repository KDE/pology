# -*- coding: UTF-8 -*-

"""
Merge translation corrections from (partial) PO files tree into main tree.

When doing corrections on a copy of PO files tree it is not possible to easy
merge back just updated translations as word wrapping in PO file can be
different, generating much more difference than it should.

Additionally, using tools like C{pogrep} from Translate Toolkit will give new
partial tree as output with matched messages only. This sieve will help
translator to merge changes made in that partial tree back into main tree.

Give main PO files tree as input and provide path difference where partial
correction tree is available.

There is just one sieve parameter:
  - C{pathdelta:<find>:<replace>}: Specify that partial tree is available
    at path obtained when C{<find>} is replaced with C{<replace>} inside
    input path

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@author: Goran Rakic (Горан Ракић) <grakic@devbase.net>
@license: GPLv3
"""

import os

from pology import _, n_
from pology.file.catalog import Catalog
from pology.file.header import Header
from pology.misc.report import report
from pology.sieve import SieveError


def setup_sieve (p):

    p.set_desc(_("@info sieve discription",
    "Merge translation corrections from partial PO files tree into main tree."
    "\n\n"
    "Give main PO files tree as input and provide the path difference to "
    "where the partial correction tree is available."
    ))

    p.add_param("pathdelta", unicode, mandatory=True,
                metavar=_("@info sieve parameter value placeholder",
                          "FIND[:REPLACE]"),
                desc=_("@info sieve parameter discription",
    "Specify that partial tree is available at path obtained when "
    "first FIND in the input path is replaced with REPLACE. "
    "If REPLACE is not given, FIND is just removed. "
    "Example:"
    "\n\n"
    "pathdelta:ui:ui-check"
    ))


class Sieve (object):

    def __init__ (self, params):

        self.ncorr = 0

        pathdelta = params.pathdelta
        if ":" not in pathdelta:
            self.pd_srch = pathdelta
            self.pd_repl = ""
        else:
            self.pd_srch, self.pd_repl = pathdelta.split(":", 1)


    def process_header (self, hdr, cat):

        # Cancel prior correction catalog.
        self.corr_cat = None

        # Construct expected path to correction catalog.
        corr_path = cat.filename.replace(self.pd_srch, self.pd_repl, 1)

        # Open the catalog if it exists.
        if os.path.isfile(corr_path):
            self.corr_cat = Catalog(corr_path)


    def process (self, msg, cat):

        if not self.corr_cat: # No correction catalog for this one, skip
            return

        if msg in self.corr_cat:

            corr_msg = self.corr_cat[msg]

            oldcount = msg.modcount

            # Need to take over manual comments too (the translator may have
            # made some upon correction), but without those added by pofilter.
            corr_manual_comment = []
            for cmnt in corr_msg.manual_comment:
                if "(pofilter)" not in cmnt:
                    corr_manual_comment.append(cmnt)

            # Take over all extraction-invariant parts
            # and set cleaned up comments.
            msg.set_inv(corr_msg)
            msg.manual_comment[:] = corr_manual_comment

            if msg.modcount > oldcount:
                self.ncorr += 1


    def finalize (self):

        if self.ncorr > 0:
            msg = n_("@info:progress",
                     "Merged %(num)d corrected message.",
                     "Merged %(num)d corrected messages.",
                     num=self.ncorr)
            report("===== " + msg)

