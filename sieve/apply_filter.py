# -*- coding: UTF-8 -*-

"""
Apply filters to translation.

Modify C{msgstr} fields by filtering them through a combination of
pure text hooks (C{(text) -> text} hook type) from global C{pology.hook}
and language specific C{pology.l10n.<lang>.hook} modules.

Sieve options:
  - C{filter:<filter>,...}: comma-separated list of pure text hooks

Global hooks are specified just by their module name, e.g. C{foo}
for C{pology.hook.foo}, if the hook is the default C{process()} function,
while C{foo/bar} for a method C{bar()} representing the hook.
Language specific hooks are preceded by the language code, e.g. C{ll:foo} for
C{process()} from the C{pology.l10n.ll.hook.foo} module,
and C{ll:foo/bar} for C{bar()} within the same module.
Hooks are applied in the order given by the C{filter} option.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

from pology.misc.langdep import get_hook_lreq


class Sieve (object):

    def __init__ (self, options, global_options):

        self.tfilters = []
        if "filter" in options:
            options.accept("filter")
            freqs = options["filter"].split(",")
            self.tfilters = [get_hook_lreq(x, abort=True) for x in freqs]

        # Number of modified messages.
        self.nmod = 0


    def process (self, msg, cat):

        mcount = msg.modcount

        for i in range(len(msg.msgstr)):
            for tfilter in self.tfilters:
                msg.msgstr[i] = tfilter(msg.msgstr[i])

        if mcount < msg.modcount:
            self.nmod += 1


    def finalize (self):

        if self.nmod:
            print "Total modified by filtering: %d" % self.nmod

