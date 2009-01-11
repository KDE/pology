# -*- coding: UTF-8 -*-

"""
Apply filters to translation.

Modify C{msgstr} fields by passing them through a combination of
filtering L{hooks<hook>} of type F1A (C{(text) -> text})
or F3* (C{(text/msgstr, msg, cat)->msgstr}).

Sieve parameters:
  - C{filter:<filter>,...}: comma-separated list of hook specifications
  - C{factory:<filter>~~...}: double-tilde separated list of factory arguments
  - C{nosync}: do not request syncing of the catalogs

Global hooks can be specified just by their module name, e.g. C{foo}
for C{pology.hook.foo}, if the module defines hook as C{process()} function;
while using C{foo/bar} for if the hook is given by the C{bar()} function.
Language specific hooks are preceded by the language code, e.g. C{ll:foo} for
C{process()} from the C{pology.l10n.ll.hook.foo} module,
and C{ll:foo/bar} for C{bar()} within the same module.
Hooks are applied in the order given by the C{filter} parameter.

If the specified hook is in fact a hook factory, C{factory} parameter
is used to specify factory arguments. The number of factory argument strings
(separated by C{~~}) must be equal to number of filters.
Each argument string is an ansamble of arguments as would be given
to the factory call inside Python code (without wrapping parenthesis).
If an argument string is empty, the hook corresponding to it is considered
a plain hook rather than factory, and skipped on evaluation of factories.

Using the C{nosync} parameter, the sieve can be chained with a checker sieve,
to filter C{msgstr} before sending the checker sieve gets to operate on it.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

from pology.misc.langdep import get_hook_lreq
from pology.misc.report import report, warning, error


class Sieve (object):

    def __init__ (self, options):

        self.tfilters = []
        if "filter" in options:
            options.accept("filter")
            freqs = options["filter"].split(",")
            self.tfilters = [[get_hook_lreq(x, abort=True), x] for x in freqs]

        # After filtering hooks have been loaded.
        if "factory" in options:
            options.accept("factory")
            fargs = options["factory"].split("~~")
            if len(fargs) != len(self.tfilters):
                error("number of filters (%d) and factories (%d) "
                      "does not match" % (len(self.tfilters), len(fargs)))
            for i in range(len(self.tfilters)):
                if fargs[i]: # empty strings not factories
                    factory = self.tfilters[i][0]
                    self.tfilters[i][0] = eval("factory(%s)" % fargs[i])

        # Whether to not request syncing of the catalog.
        self.nosync = False
        if "nosync" in options:
            options.accept("nosync")
            self.nosync = True

        # Number of modified messages.
        self.nmod = 0

        # Do not request syncing of the catalog if requested.
        if self.nosync:
            self.caller_sync = False
            self.caller_monitored = False


    def process (self, msg, cat):

        mcount = msg.modcount

        for i in range(len(msg.msgstr)):
            for tfilter, tfname in self.tfilters:
                try: # try as type F1A hook
                    msg.msgstr[i] = tfilter(msg.msgstr[i])
                except TypeError:
                    try: # try as type F3* hook
                        msg.msgstr[i] = tfilter(msg.msgstr[i], msg, cat)
                    except TypeError:
                        warning("cannot execute filter '%s'" % tfname)
                        raise

        if mcount < msg.modcount:
            self.nmod += 1


    def finalize (self):

        if self.nmod:
            report("Total modified by filtering: %d" % self.nmod)

