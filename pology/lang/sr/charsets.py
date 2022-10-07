# -*- coding: UTF-8 -*-

"""
Conversions between character sets in Serbian texts.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

from pology import _, n_
from pology.report import warning


chset_iso8859_5 = set(
" !\"#$%&'()*+,-./0123456789:;<=>?@"
"ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`"
"abcdefghijklmnopqrstuvwxyz{|}~\u00a0"
"ЁЂЃЄЅІЇЈЉЊЋЌ­ЎЏАБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
"абвгдежзийклмнопрстуфхцчшщъыьэюя№ёђѓєѕіїјљњћќ§ўџ"
)

translit_iso8859_5 = {
}

chset_iso8859_2 = set(
" !\"#$%&'()*+,-./0123456789:;<=>?@"
"ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`"
"abcdefghijklmnopqrstuvwxyz{|}~\u00a0"
"Ą˘Ł¤ĽŚ§¨ŠŞŤŹ­ŽŻ°"
"ą˛ł´ľśˇ¸šşťź˝žż"
"ŔÁÂĂÄĹĆÇČÉĘËĚÍÎĎĐŃŇÓÔŐÖ×ŘŮÚŰÜÝŢß"
"ŕáâăäĺćçčéęëěíîďđńňóôőö÷řůúűüýţ˙"
)

translit_iso8859_2 = {
    "×": "×",
}

translit_ascii = {
    "—": "--",
    "–": "-",
    "„": "\"",
    "“": "\"",
    "‘": "'",
    "’": "'",
    "€": "EUR",
    "©": "c",
    "×": "x",
    "\u2011": "-", # non-breaking hyphen
    "\u00a0": " ", # no-break space
    "\u2009": "", # thin space
    "\u202f": "", # narrow no-break space
    "\u200b": "", # zero-width space
    "ä": "ae",
    "ö": "oe",
    "ü": "ue",
    # TODO: Add more.
    #"": "",
}


def limit_to_isocyr (text):
    """
    Limit characters to those available in ISO-8859-5 [type F1A hook].

    If a character is neither available in the target character set
    nor can be transliterated to it, conversion is undefined,
    and warning is reported to stderr.

    @return: text
    """

    return _limit_to_chset(text,
                           chset_iso8859_5, translit_iso8859_5, "ISO-8859-5")


def limit_to_isolat (text):
    """
    Limit characters to those available in ISO-8859-2 [type F1A hook].

    If a character is neither available in the target character set
    nor can be transliterated to it, conversion is undefined,
    and warning is reported to stderr.

    @return: text
    """

    return _limit_to_chset(text,
                           chset_iso8859_2, translit_iso8859_2, "ISO-8859-2")


def _limit_to_chset (text, chset, translit, cname):

    ltext = []
    for c in text:
        if c in chset:
            ltext.append(c)
            continue
        ct = translit.get(c) # must come before translit_ascii
        if ct is not None:
            ltext.append(ct)
            continue
        ct = translit_ascii.get(c)
        if ct is not None:
            ltext.append(ct)
            continue
        warning(_("@info",
                  "Character '%(char)s' (%(code)s) cannot be transliterated "
                  "into character set %(charset)s, removing it.",
                  char=c, code=("U+%X" % ord(c)), charset=cname))
        ltext.append("?")

    return "".join(ltext)

