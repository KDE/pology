# -*- coding: UTF-8 -*-

"""
Post-filter resolved UI references in summit docu POs in KDE repository.

Resolved UI text comes in with ampersands in entities escaped by C{&amp;}.
When unescaped, then the entity corresponds to entity in documentation
which may have a tagged value, whereas plain text is needed.
Therefore:
  - unescape escaped ampersands when in entity position
  - add C{_ot} to base entity to get to plain text valued entity

Do this only for entities which have grammar categories attached,
i.e. hyphen (-) followed by none or more characters; the base entity
then is the part before the hyphen.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import re


_entity_tail_rx = re.compile(r"([\w_:][\w\d._:-]*);")

def process (text):
    """
    Type F1A hook.

    @return: text
    """

    eamp = "&amp;"

    p = 0
    tsegs = []
    while True:
        pp = p
        p = text.find(eamp, p)
        if p < 0:
            tsegs.append(text[pp:])
            break

        tsegs.append(text[pp:p])

        m = _entity_tail_rx.match(text, p + len(eamp))
        if m:
            ent = m.group(1)
            q = ent.rfind("-")
            if q < 0:
                q = len(ent)
            ent = ent[:q] + "_ot" + ent[q:]
            tsegs.append("&%s;" % ent)
            p = m.end()
        else:
            tsegs.append(eamp)
            p += len(eamp)

    return "".join(tsegs)

