# -*- coding: UTF-8 -*-

"""
Conversions between character sets in Serbian texts.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

from pology import _, n_
from pology.report import warning


chset_iso8859_5 = set(
u" !\"#$%&'()*+,-./0123456789:;<=>?@"
u"ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`"
u"abcdefghijklmnopqrstuvwxyz{|}~\u00a0"
u"ЁЂЃЄЅІЇЈЉЊЋЌ­ЎЏАБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
u"абвгдежзийклмнопрстуфхцчшщъыьэюя№ёђѓєѕіїјљњћќ§ўџ"
)

translit_iso8859_5 = {
}

chset_iso8859_2 = set(
u" !\"#$%&'()*+,-./0123456789:;<=>?@"
u"ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`"
u"abcdefghijklmnopqrstuvwxyz{|}~\u00a0"
u"Ą˘Ł¤ĽŚ§¨ŠŞŤŹ­ŽŻ°"
u"ą˛ł´ľśˇ¸šşťź˝žż"
u"ŔÁÂĂÄĹĆÇČÉĘËĚÍÎĎĐŃŇÓÔŐÖ×ŘŮÚŰÜÝŢß"
u"ŕáâăäĺćçčéęëěíîďđńňóôőö÷řůúűüýţ˙"
)

translit_iso8859_2 = {
    u"×": u"×",
}

translit_ascii = {
    u"—": "--",
    u"–": "-",
    u"„": "\"",
    u"“": "\"",
    u"‘": "'",
    u"’": "'",
    u"€": "EUR",
    u"©": "c",
    u"×": "x",
    u"\u2011": "-", # non-breaking hyphen
    u"\u00a0": " ", # no-break space
    u"\u2009": "", # thin space
    u"\u202f": "", # narrow no-break space
    u"\u200b": "", # zero-width space
    u"ä": "ae",
    u"ö": "oe",
    u"ü": "ue",
    # TODO: Add more.
    #u"": "",
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

