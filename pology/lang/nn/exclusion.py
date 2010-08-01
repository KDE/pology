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

from pology import rootdir, _, n_
from pology.fsops import collect_files_by_ext
from pology.split import split_text


def inofficial_forms (msgstr, msg, cat):
    """
    Check for inofficial ortography forms in translation [type V3C hook].

    @return: erroneous spans
    """

    if not _phrases:
        _init_phrases()

    spans = []

    words, interps = split_text(msgstr)
    for phstart in range(len(words)):
        for phlen in range(min(_maxwords, len(words) - phstart), 0, -1):
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
                if phrase in _phrases:
                    p1 = (  sum(map(len, words[:phstart]))
                        + sum(map(len, interps[:phstart + off1])))
                    p2 = (  sum(map(len, words[:phstart + phlen]))
                        + sum(map(len, interps[:phstart + phlen + off2])))
                    emsg = (_("@info",
                              "Inofficial form '%(word)s'.")
                            % dict(word=msgstr[p1:p2].strip()))
                    spans.append((p1, p2, emsg))
                    break

    return spans


# Set of excluded phrases and maximum number of words per phrase.
_phrases = set()
_maxwords = 0

def _init_phrases ():

    global _maxwords

    exdir = os.path.join(rootdir(), "lang", "nn", "exclusion")
    exfiles = collect_files_by_ext(exdir, "dat")

    for exfile in exfiles:

        phrases = codecs.open(exfile, "r", "UTF-8").read().split("\n")[:-1]
        phrases = map(_normph, phrases)
        _phrases.update(phrases)

        maxwords = max(map(lambda x: len(split_text(x)[0]), phrases))
        if _maxwords < maxwords:
            _maxwords = maxwords


_wsseq_rx = re.compile(r"\s{2,}", re.U)

def _normph (phrase):

    return _wsseq_rx.sub(r" ", phrase.lower().strip())

