# -*- coding: UTF-8 -*-

"""
Apply hooks to translation.

Documented in C{doc/user/sieving.docbook}.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

from pology import _, n_
from pology.getfunc import get_hook_ireq
from pology.msgreport import report_msg_content
from pology.report import report, warning, error
from pology.sieve import add_param_filter
from pology.sieve import SieveError


def setup_sieve (p):

    p.set_desc(_("@info sieve discription",
    "Apply hooks to translation."
    "\n\n"
    "Message msgstr fields are passed through one or more of "
    "F1A, F3A/C, V1A, V3A/C, S1A, S3A/C hooks."
    ))

    add_param_filter(p, _("@info sieve parameter discription",
    "Specification of the hook through which msgstr fields are passed."
    ))
    p.add_param("showmsg", bool, defval=False,
                desc=_("@info sieve parameter discription",
    "Report message to standard output if it got modified."
    ))


class Sieve (object):

    def __init__ (self, params):

        self.p = params

        self.tfilters = [[get_hook_ireq(x, abort=True), x]
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
                        raise SieveError(
                            _("@info",
                              "Cannot execute filter '%(filt)s'.",
                              filt=tfname))

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
            msg = n_("@info:progress",
                     "Modified %(num)d message by filtering.",
                     "Modified %(num)d messages by filtering.",
                     num=self.nmod)
            report("===== " + msg)

