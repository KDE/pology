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
  - C{filter:<hookspec>}: hook specification

For a module C{pology.hook.FOO} which defines the C{process()} hook function,
the hook specification given by the C{filter} parameter is simply C{FOO}.
If the hook function is named C{BAR()} instead of C{process()},
the hook specification is given as C{FOO/BAR}.
Language specific hooks (C{pology.l10n.LANG.hook.FOO}) are aditionally
preceded by the language code with colon, as C{LANG:FOO} or C{LANG:FOO/BAR}.

If the hook is not a plain hook, but a L{hook factory<hook>} function,
the factory arguments are supplied after the basic hook specification,
separated by tilde: C{LANG:FOO/BAR~ARGLIST}
(with C{LANG:} and C{/BAR} possibly omitted, under the previous conditions).
Argument list is formatted just like it would be passed in Python code
to the factory function, omitting the surrounding parenthesis.

Parameter C{filter} can be repeated to chain several hooks,
which are then applied in the order of appearance in the command line.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

from pology.sieve import SieveError
from pology.misc.langdep import get_hook_lreq
from pology.misc.report import report, warning, error
from pology.misc.msgreport import report_msg_content


def setup_sieve (p):

    p.set_desc(
    "Apply filters to translation."
    "\n\n"
    "Message's msgstr fields are passed through one or composition of "
    "F1A, F3A/C, V1A, V3A/C, S1A, S3A/C hooks, as filters. "
    "See documentation on pology.hook for details about hooks."
    )

    p.add_param("filter", unicode, multival=True,
                metavar="HOOKSPEC",
                desc=
    "Specification of hook through which msgstr fields are to be filtered. "
    "\n\n"
    "For a module pology.hook.FOO which defines process() function, "
    "the hook specification is simply FOO. "
    "If the hook function is named BAR() instead of process(), then "
    "the hook specification is FOO/BAR. "
    "Language specific hooks (pology.l10n.LANG.hook.FOO) are aditionally "
    "preceded by the language code with colon, as LANG:FOO or LANG:FOO/BAR. "
    "\n\n"
    "If the function is actually a hook factory, the arguments for "
    "the factory are passed separated by tilde: LANG:FOO/BAR~ARGS "
    "(where LANG: and /BAR may be omitted under previous conditions). "
    "The ARGS string is a list of arguments as it would appear "
    "in the function call in Python code, omitting parenthesis. "
    "\n\n"
    "Several filters can be given by repeating the parameter, "
    "when they are applied in the given order."
    )


class Sieve (object):

    def __init__ (self, params):

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


    def finalize (self):

        if self.nmod:
            report("Total modified by filtering: %d" % self.nmod)

