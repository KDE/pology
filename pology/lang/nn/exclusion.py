# -*- coding: UTF-8 -*

"""
Catch inofficial ortography forms in Norwegian Nynorsk translation.

The check expects that the translation is plain text,
i.e. that any markup has been removed from it beforehand;
otherwise, problems masked by markup may not be reported.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import os
import re
import codecs

from pology import datadir, _, n_
from pology.fsops import collect_files_by_ext
from pology.split import split_text


def exclude_forms (dictnames):
    """
    Check for excluded ortography forms in translation [hook factory].

    @param dictnames: base names of files from which to collect excluded forms;
        file paths will be assembled as
        C{<datadir>/lang/nn/exclusion/<dictname>.dat}
    @type dictnames: <string*>

    @return: type V3C hook
    @rtype: C{(msgstr, msg, cat) -> spans}
    """

    phrases = _load_phrases(dictnames)
    maxwords = max(map(lambda x: len(split_text(x)[0]), phrases))

    def hook (msgstr, msg, cat):

        spans = []

        words, interps = split_text(msgstr)
        for phstart in range(len(words)):
            for phlen in range(min(maxwords, len(words) - phstart), 0, -1):
                # Construct and test the following phrases:
                # - with inner and trailing intersections
                # - with leading and inner intersections
                # - with inner intersections
                for off1, off2 in ((1, 1), (0, 0), (1, 0)):
                    parts = []
                    if off1 == 0:
                        parts.append(interps[phstart])
                    parts.append(words[phstart])
                    for i in range(1, phlen):
                        parts.append(interps[phstart + i])
                        parts.append(words[phstart + i])
                    if off2 == 1:
                        parts.append(interps[phstart + phlen])

                    phrase = _normph("".join(parts))
                    if phrase in phrases:
                        p1 = (  sum(map(len, words[:phstart]))
                            + sum(map(len, interps[:phstart + off1])))
                        p2 = (  sum(map(len, words[:phstart + phlen]))
                            + sum(map(len, interps[:phstart + phlen + off2])))
                        emsg = _("@info",
                                "Excluded form '%(word)s'.",
                                word=msgstr[p1:p2].strip())
                        spans.append((p1, p2, emsg))
                        break

        return spans

    return hook


def _load_phrases (dictnames):

    phrases = set()

    for dictname in dictnames:
        exfile = os.path.join(datadir(), "lang", "nn", "exclusion",
                              dictname + ".dat")

        phrases1 = codecs.open(exfile, "r", "UTF-8").read().split("\n")[:-1]
        phrases1 = map(_normph, phrases1)
        phrases.update(phrases1)

    return phrases


_wsseq_rx = re.compile(r"\s{2,}", re.U)

def _normph (phrase):

    return _wsseq_rx.sub(r" ", phrase.lower().strip())

