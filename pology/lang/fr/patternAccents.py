# -*- coding: UTF-8 -*-

"""
Accent equivalence in regular expression patterns.

@author: Sébastien Renard <sebastien.renard@digitalfox.org>
@license: GPLv3
"""

import re

accents={}
accents["e"] = "[%s]" % "|".join(['e', 'é', 'è', 'ê', 'E', 'É', 'È', 'Ê'])
accents["é"] = "[%s]" % "|".join(['é', 'è', 'ê', 'É', 'È', 'Ê'])
accents["è"] = "[%s]" % "|".join(['é', 'è', 'ê', 'É', 'È', 'Ê'])
accents["ê"] = "[%s]" % "|".join(['é', 'è', 'ê', 'É', 'È', 'Ê'])
accents["a"] = "[%s]" % "|".join(['a', 'à', 'â', 'A', 'À', 'Â'])
accents["à"] = "[%s]" % "|".join(['à', 'â', 'À', 'Â'])
accents["â"] = "[%s]" % "|".join(['à', 'â', 'À', 'Â'])
accents["u"] = "[%s]" % "|".join(['u', 'ù', 'û', 'U', 'Ù', 'Û'])
accents["ù"] = "[%s]" % "|".join(['ù', 'û', 'Ù', 'Û'])
accents["û"] = "[%s]" % "|".join(['ù', 'û', 'Ù', 'Û'])
accentPattern=re.compile("@([%s])" % "|".join(list(accents.keys())))


def patternAccents(pattern):
    """Replace every C{@x} in the pattern by the value C{accents["x"]}."""

    for accentMatch in accentPattern.finditer(pattern):
        letter=accentMatch.group(1)
        pattern=pattern.replace("@%s" % letter, accents[letter])

    return pattern

