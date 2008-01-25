# -*- coding: UTF-8 -*-

""" Accent substitution dictionary
When in a rule the pattern @x is used, the x is replaced
by the value accents["x"]
Special key "pattern" is used to get the compiled regexp to match all accents key"""

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
accents[u"pattern"]=accentPattern
