#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Obtains a list of proper words (that that begins with a capital letter or
# contains an intermediate capital letter)
# that are not included yet in the local dictionary.
# It is a tool that helps to complete the local dictionary.

try:
    import fallback_import_paths
except:
    pass

import sys
import os
import re
import locale
import enchant

from pology import version, _, n_
from pology.catalog import Catalog
from pology.colors import ColorOptionParser
from pology.fsops import str_to_unicode, collect_catalogs
from pology.fsops import collect_paths_cmdline
from pology.report import report
from pology.stdcmdopt import add_cmdopt_filesfrom


def _main ():

    locale.setlocale(locale.LC_ALL, "")

    usage= _("@info command usage",
        "%(cmd)s [OPTIONS] VCS [POPATHS...]",
        cmd="%prog")
    desc = _("@info command description",
        "Obtains a list of proper words from the message text ")
    ver = _("@info command version",
        u"%(cmd)s (Pology) %(version)s\n"
        u"Copyright ©  2011 "
        u"Javier Viñal &lt;%(email)s&gt;",
        cmd="%prog", version=version(), email="fjvinal@gmail.com")

    opars = ColorOptionParser(usage=usage, description=desc, version=ver)
    add_cmdopt_filesfrom(opars)

    (options, free_args) = opars.parse_args(str_to_unicode(sys.argv[1:]))

    # Collect PO files in given paths.
    popaths = collect_paths_cmdline(rawpaths=free_args,
                                    filesfrom=options.files_from,
                                    elsecwd=True,
                                    respathf=collect_catalogs,
                                    abort=True)

    for path in popaths:
        extract_proper_words(path)


_ent_proper_word = re.compile("^\w*?[A-Z]\w*$")

def extract_proper_words (path):

    cat = Catalog(path)

    dict_en = enchant.Dict("en_US")
    dict_local = enchant.Dict()

    for msg in cat:
        for word in msg.msgid.split():
            if _ent_proper_word.match(word):
                if not dict_local.check(word) and not dict_en.check(word):
                    report("%s" %(word))
    
if __name__ == '__main__':
    _main()

