# -*- coding: UTF-8 -*-

"""
Accent equivalence in regular expression patterns.

@author: Javier Viñal <fjvinal@gmail.com>
@license: GPLv3
"""

import re

accents={}
accents[u"e"] = u"[%s]" % u"|".join([u'e', u'é', u'è', u'ê', u'E', u'É', u'È', u'Ê'])
accents[u"é"] = u"[%s]" % u"|".join([u'é', u'è', u'ê', u'É', u'È', u'Ê'])
accents[u"è"] = u"[%s]" % u"|".join([u'é', u'è', u'ê', u'É', u'È', u'Ê'])
accents[u"ê"] = u"[%s]" % u"|".join([u'é', u'è', u'ê', u'É', u'È', u'Ê'])
accents[u"a"] = u"[%s]" % u"|".join([u'a', u'à', u'â', u'A', u'À', u'Â'])
accents[u"à"] = u"[%s]" % u"|".join([u'à', u'â', u'À', u'Â'])
accents[u"â"] = u"[%s]" % u"|".join([u'à', u'â', u'À', u'Â'])
accents[u"u"] = u"[%s]" % u"|".join([u'u', u'ù', u'û', u'U', u'Ù', u'Û'])
accents[u"ù"] = u"[%s]" % u"|".join([u'ù', u'û', u'Ù', u'Û'])
accents[u"û"] = u"[%s]" % u"|".join([u'ù', u'û', u'Ù', u'Û'])
accentPattern=re.compile(u"@([%s])" % u"|".join(accents.keys()))


def patternAccents(pattern):
    """Replace every C{@x} in the pattern by the value C{accents["x"]}."""

    for accentMatch in accentPattern.finditer(pattern):
        letter=accentMatch.group(1)
        pattern=pattern.replace("@%s" % letter, accents[letter])

    return pattern

