# -*- coding: UTF-8 -*-

"""
Convert special entities in rule patterns.

@author: Sébastien Renard <sebastien.renard@digitalfox.org>
@license: GPLv3
"""

from pology.resolve import resolve_entities_simple


entities={}
entities["cr"]="\r"
entities["lf"]="\n"
entities["lt"]="<"
entities["gt"]=">"
entities["sp"]=" "
entities["quot"]='\"'
entities["amp"]="&"
entities["unbsp"]="\xa0"
entities["nbsp"]=" "


def patternEntities(pattern):
    """Convert entities in pattern."""

    return resolve_entities_simple(pattern, entities)
