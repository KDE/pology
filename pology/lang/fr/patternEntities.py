# -*- coding: UTF-8 -*-

"""
Convert special entities in rule patterns.

@author: Sébastien Renard <sebastien.renard@digitalfox.org>
@license: GPLv3
"""

from pology.resolve import resolve_entities_simple


entities={}
entities["cr"]=u"\r"
entities["lf"]=u"\n"
entities["lt"]=u"<"
entities["gt"]=u">"
entities["sp"]=u" "
entities["quot"]=u'\"'
entities["amp"]=u"&"
entities["unbsp"]=u"\xa0"
entities["nbsp"]=u" "


def patternEntities(pattern):
    """Convert entities in pattern."""

    return resolve_entities_simple(pattern, entities)
