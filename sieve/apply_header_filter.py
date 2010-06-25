# -*- coding: UTF-8 -*-

"""
Apply filters to headers.

Pass catalog headers through a combination of L{hooks<hook>}, of types:
  - F4B (C{(hdr, cat)->numerr}) to modify the header
  - V4B (C{(hdr, cat)->spans}) to validate the header
  - S4B (C{(hdr, cat)->numerr}) for side-effects on the header

Sieve parameters:
  - C{filter:<hookspec>}: hook specification (see L{misc.langdep.get_hook_lreq}
        for the format of hook specifications)

Parameter C{filter} can be repeated to chain several hooks,
which are then applied in the order of appearance in the command line.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

from pology import _, n_
from pology.misc.langdep import get_hook_lreq
from pology.misc.report import report, warning
from pology.misc.stdsvpar import add_param_filter
from pology.sieve import SieveError


def setup_sieve (p):

    p.set_desc(_("@info sieve discription",
    "Apply filters to header."
    "\n\n"
    "Catalog header is passed through one or composition of "
    "F4B, V4B, S4B hooks. "
    "See documentation on pology.hook for details about hooks."
    ))

    add_param_filter(p, _("@info sieve parameter discription",
    "Specification of hook through which headers are to be filtered."
    ))


class Sieve (object):

    def __init__ (self, params):

        self.tfilters = [[get_hook_lreq(x, abort=True), x]
                          for x in (params.filter or [])]

        # Number of modified headers.
        self.nmod = 0


    def process_header (self, hdr, cat):

        mcount = hdr.modcount

        for tfilter, tfname in self.tfilters:
            try:
                res = tfilter(hdr, cat)
            except TypeError:
                raise SieveError(
                    _("@info",
                      "Cannot execute filter '%(filt)s'.",
                      filt=tfname))

            # Process result based on hook type.
            if isinstance(res, list):
                # Validation hook.
                # TODO: Better span reporting on headers.
                for part in res:
                    for span in part[2]:
                        if len(span) >= 3:
                            errmsg = span[2]
                            report("%s:header: %s", (cat.filename, errmsg))
            else:
                # Side-effect hook, nothing to do.
                # TODO: Perhaps report returned number?
                pass

        if mcount < hdr.modcount:
            self.nmod += 1


    def finalize (self):

        if self.nmod:
            msg = n_("@info:progress",
                     "Modified %(num)d header by filtering.",
                     "Modified %(num)d headers by filtering.",
                     num=self.nmod)
            report("===== %s" % msg)

