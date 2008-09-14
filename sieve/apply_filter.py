# -*- coding: UTF-8 -*-

"""
Apply filters to translation.

Modify C{msgstr} fields using a combination of filters from C{pology.filter}
and language specific C{pology.l10n.<lang>.filter} modules.

Sieve options:
  - C{filter:<filter>,...}: comma-separated list of filters

Global filters are specified just by their module name, e.g. C{foo}
for C{pology.filter.foo}, while language specific filters are preceded by
the language code, e.g. C{ll:foo} for C{pology.l10n.ll.filter.foo}.
Filters are applied in the order given by the C{filter} option.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

from pology.misc.langdep import get_filter_lreq


class Sieve (object):

    def __init__ (self, options, global_options):

        self.tfilters = []
        if "filter" in options:
            options.accept("filter")
            freqs = options["filter"].split(",")
            self.tfilters = [get_filter_lreq(x, abort=True) for x in freqs]

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

