# -*- coding: UTF-8 -*-

"""
Apply filters to translation.

Pass C{msgstr} fields through a combination of L{hooks<hook>}, of types:
  - F1A (C{(text)->text}) or F3A/C (C{(text/msgstr, msg, cat)->msgstr}),
    to modify the translation
  - V1A (C{(text)->spans}) or V3A/C (C{(text/msgstr, msg, cat)->spans}),
    to validate the translation
  - S1A (C{(text)->spans}) or S3A/C (C{(text/msgstr, msg, cat)->spans}),
    for side-effects on translation (e.g. simpler checks which write notes
    to standard output, rather than reporting erroneous spans as V* hooks)

Sieve parameters:
  - C{filter:<hookspec>}: hook specification (see L{misc.langdep.get_hook_lreq}
        for the format of hook specifications).
        Can be repeated to chain several hooks, which are applied
        in the order of appearance in the command line.
  - C{showmsg}: report every modified message to standard output
        (for validation hooks, message is automatically output if not valid).

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

from pology.sieve import SieveError
from pology.misc.langdep import get_hook_lreq
from pology.misc.report import report, warning, error
from pology.misc.msgreport import report_msg_content
from pology.misc.stdsvpar import add_param_filter


def setup_sieve (p):

    p.set_desc(
    "Apply filters to translation."
    "\n\n"
    "Message's msgstr fields are passed through one or composition of "
    "F1A, F3A/C, V1A, V3A/C, S1A, S3A/C hooks, as filters. "
    "See documentation on pology.hook for details about hooks."
    )

    add_param_filter(p,
    "Specification of hook through which msgstr fields are to be filtered."
    )
    p.add_param("showmsg", bool, defval=False,
                desc=
    "Report message to standard output if it got modified."
    )


class Sieve (object):

    def __init__ (self, params):

        self.p = params

        self.tfilters = [[get_hook_lreq(x, abort=True), x]
                         for x in (params.filter or [])]

        # Number of modified messages.
        self.nmod = 0


    def process (self, msg, cat):

        mcount = msg.modcount

        for i in range(len(msg.msgstr)):
            for tfilter, tfname in self.tfilters:
                try: # try as type *1A hook
                    res = tfilter(msg.msgstr[i])
                except TypeError:
                    try: # try as type *3* hook
                        res = tfilter(msg.msgstr[i], msg, cat)
                    except TypeError:
                        warning("cannot execute filter '%s'" % tfname)
                        raise

                # Process result based on hook type.
                if isinstance(res, basestring):
                    # Modification hook.
                    msg.msgstr[i] = res
                elif isinstance(res, list):
                    # Validation hook.
                    if res:
                        report_msg_content(msg, cat,
                                           highlight=[("msgstr", i, res)],
                                           delim=("-" * 20))
                else:
                    # Side-effect hook, nothing to do.
                    # TODO: Perhaps report returned number?
                    pass

        if mcount < msg.modcount:
            self.nmod += 1
            if self.p.showmsg:
                report_msg_content(msg, cat, delim=("-" * 20))


    def finalize (self):

        if self.nmod:
            report("Total modified by filtering: %d" % self.nmod)

