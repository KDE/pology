# -*- coding: UTF-8 -*-

"""
Apply hooks to headers.

Documented in C{doc/user/sieving.docbook}.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

from pology import _, n_
from pology.getfunc import get_hook_ireq
from pology.report import report, warning
from pology.sieve import add_param_filter
from pology.sieve import SieveError


def setup_sieve (p):

    p.set_desc(_("@info sieve discription",
    "Apply hooks to header."
    "\n\n"
    "Catalog header is passed through one or more of "
    "F4B, V4B, S4B hooks. "
    ))

    add_param_filter(p, _("@info sieve parameter discription",
    "Specification of the hook through which headers are passed."
    ))


class Sieve (object):

    def __init__ (self, params):

        self.tfilters = [[get_hook_ireq(x, abort=True), x]
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
            report("===== " + msg)

