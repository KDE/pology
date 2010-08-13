# -*- coding: UTF-8 -*-

"""
Additions to resolving UI references.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import re

entity_tail_rxstr = r"([\w_:][\w\d._:-]*);"
_entity_tail_rx = re.compile(r"%s" % entity_tail_rxstr)
_entity_rx = re.compile(r"&%s" % entity_tail_rxstr)

def mod_entities (unescape=False, basesuff=""):
    """
    Modify entities in resolved UI text.

    If the UI text has been XML-escaped, any XML-entities in it have been
    escaped to C{&amp;<original>;} form. If C{unescents} is C{True}, such
    forms will be unescaped to original entity.

    If the original entity is of the form C{&<basename>-<suffix>;}, a suffix
    may be inserted to the base name itself using the parameter C{basesuff}.
    The entity then becomes C{&<basename><basesuff>-<suffix>;}.
    If there are several hyphens in the original name, the suffix is taken
    as part after the last hyphen; if there are no hyphens, the suffix is
    taken as empty string.

    @param unescape: whether to unescape escaped entities
    @type unescape: bool
    @param basesuff: suffix to append to base entity name
    @type basesuff: string

    @return: type F1A hook
    @rtype: C{(text) -> text}
    """

    if unescape:
        ent_head = "&amp;"
    else:
        ent_head = "&"

    def hook (text):

        p = 0
        tsegs = []
        while True:
            pp = p
            p = text.find(ent_head, p)
            if p < 0:
                tsegs.append(text[pp:])
                break

            tsegs.append(text[pp:p])

            m = _entity_tail_rx.match(text, p + len(ent_head))
            if m:
                ent = m.group(1)
                if basesuff:
                    q = ent.rfind("-")
                    if q < 0:
                        q = len(ent)
                    ent = ent[:q] + "_ot" + ent[q:]
                tsegs.append("&%s;" % ent)
                p = m.end()
            else:
                tsegs.append(ent_head)
                p += len(ent_head)

        return "".join(tsegs)

    return hook

