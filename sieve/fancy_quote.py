# -*- coding: UTF-8 -*-

"""
Transform ASCII single and double quotes into fancy counterparts.

Ordinary ASCII quotes are easy to type on most keyboard layouts, and are
frequently encountered in English original messages -- rather than proper
English text quotes, i.e. "fancy" quotes. Translators are therefore easily
moved to use ASCII quotes instead of the fancy quotes appropriate for their
language. Use this sieve to replace ASCII quotes in the translation with
selected fancy quotes.

Sieve parameters for simple, character-to-character quote replacement:
  - C{single:<quotes>}: opening and closing single qoute (two characters)
  - C{double:<quotes>}: opening and closing double qoute (two characters)

Sieve parameters for character-to-string quote replacement,
useful e.g. when target quotes are tags or wiki markup:
  - C{longsingle:<open>,<close>}: opening and closing single quotes
  - C{longdouble:<open>,<close>}: opening and closing double quotes

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import os
import re

from pology import _, n_
from pology.misc.comments import manc_parse_flag_list
from pology.misc.escape import split_escaped
from pology.misc.report import report
from pology.sieve import SieveError


def setup_sieve (p):

    p.set_desc(_("@info sieve discription",
    "Transform ASCII single and double quotes into fancy counterparts."
    ))

    p.add_param("single", unicode,
                metavar=_("@info sieve parameter value placeholder", "QUOTES"),
                desc=_("@info sieve parameter discription",
    "Opening and closing single quote (two characters)."
    ))
    p.add_param("double", unicode,
                metavar=_("@info sieve parameter value placeholder", "QUOTES"),
                desc=_("@info sieve parameter discription",
    "Opening and closing double quote (two characters)."
    ))
    p.add_param("longsingle", unicode,
                metavar=_("@info sieve parameter value placeholder",
                          "OPEN,CLOSED"),
                desc=_("@info sieve parameter discription",
    "Opening and closing single quote longer than single character."
    ))
    p.add_param("longdouble", unicode,
                metavar=_("@info sieve parameter value placeholder", 
                          "OPEN,CLOSED"),
                desc=_("@info sieve parameter discription",
    "Opening and closing double quote longer than single character."
    ))


# Pipe flag used to manually prevent transformation into fancy quotes.
_flag_no_fancy_quote = "no-fancy-quote"


class Sieve (object):

    def __init__ (self, params):

        self.nrepl_single = 0
        self.nrepl_double = 0

        # Pair of single quotes.
        self.singles = ()
        if params.single is not None and params.longsingle is not None:
            raise SieveError(
                _("@info",
                  "Both single- and multi-character replacement of "
                  "single quotes issued."))
        if params.single is not None:
            quotes = params.single
            if len(quotes) != 2:
                raise SieveError(
                    _("@info",
                      "Invalid specification of single quotes (%(quotes)s), "
                      "expected two characters.",
                      quotes=quotes))
            self.singles = (quotes[0], quotes[1])
        elif params.longsingle is not None:
            quotes = split_escaped(params.longsingle, ",")
            if len(quotes) != 2:
                raise SieveError(
                    _("@info",
                      "Invalid specification of single quotes (%(quotes)s), "
                      "expected two strings.",
                      quotes=quotes))
            self.singles = (quotes[0], quotes[1])

        # Pair of double quotes.
        self.doubles = ()
        if params.double is not None and params.longdouble is not None:
            raise SieveError(
                _("@info",
                  "Both single- and multi-character replacement of "
                  "double quotes issued."))
        if params.double is not None:
            quotes = params.double
            if len(quotes) != 2:
                raise SieveError(
                    _("@info",
                      "Invalid specification of double quotes (%(quotes)s), "
                      "expected two characters.",
                      quotes=quotes))
            self.doubles = (quotes[0], quotes[1])
        elif params.longdouble is not None:
            quotes = split_escaped(params.longdouble, ",")
            if len(quotes) != 2:
                raise SieveError(
                    _("@info",
                      "Invalid specification of double quotes '%(quotes)s', "
                      "expected two strings.",
                      quotes=quotes))
            self.doubles = (quotes[0], quotes[1])


    def process (self, msg, cat):

        # Skip the message when told so.
        if _flag_no_fancy_quote in manc_parse_flag_list(msg, "|"):
            return

        # Skip the message if special by context (one of meta-messages).
        if _spec_msgctxt_rx.search(msg.msgctxt or ""):
            return

        # Skip the message if auto comments identify it as literal user input.
        for cmnt in msg.auto_comment:
            cmnt = cmnt.lower()
            # - extracted by KDE's xml2pot
            if "tag:" in cmnt:
                tag = cmnt[cmnt.find(":")+1:].strip()
                if tag in _xml_literal_tags:
                    return

        # Modify quotes in all translations.
        for i in range(len(msg.msgstr)):
            text = msg.msgstr[i]
            if self.singles:
                text, nrepl = equip_fancy_quotes(text, "'", self.singles)
                self.nrepl_single += nrepl
            if self.doubles:
                text, nrepl = equip_fancy_quotes(text, '"', self.doubles)
                self.nrepl_double += nrepl
            msg.msgstr[i] = text


    def finalize (self):

        nrepl_both = self.nrepl_single + self.nrepl_double
        if nrepl_both > 0:
            msg = n_("@info:progress",
                     "Replaced %(num)d pair of quotes in translation "
                     "(single+double: %(nums)d+%(numd)d).",
                     "Replaced %(num)d pairs of quotes in translation "
                     "(single+double: %(nums)d+%(numd)d).",
                     num=nrepl_both,
                     nums=self.nrepl_single, numd=self.nrepl_double)
            report("===== %s" % msg)


# Regular expression for matching special messages by context.
_spec_msgctxt = (
    "qtdt-format",
)
_spec_msgctxt_rx = re.compile("|".join(_spec_msgctxt))

# Regular expression for matching no-modify nodes in XML markup.
_xml_literal_tags = (
    # HTML
    "tt", "code",
    # KUIT
    "icode", "bcode",
    # Docbook
    "screen", "screenco", "userinput", "code", "literal", "markup",
    "programlisting", "programlistingco", "returnvalue", "command",
    "synopsis", "cmdsynopsis", "synopfragment", "synopfragmentref",
    "guilabel", "guimenuitem", "action", "errorname", 
)
_xml_literal_rx = re.compile(r"< *(%s)\b" % "|".join(_xml_literal_tags))

def equip_fancy_quotes (text, squote, fquotes):
    """
    Heuristically replace simple with fancy quotes (eg. "foo" with “foo”).

    The replacement tries to avoid quotes in markup (e.g. XML attributes),
    and other situations where the original quoting should not be touched.

    @param text: the text to equip with fancy quotes
    @type text: string

    @param squote: the simple quote, used for both opening and closing
    @type squote: string

    @param fquotes: the opening and closing fancy quote
    @type fquotes: two-tuple of strings

    @returns: the modified text and number of fancy pairs replaced
    @rtype: string, int
    """

    # Quick check: simple quote valid, any simple quotes at all?
    if not squote or squote not in text:
        return text, 0

    nrepl = 0
    no_mod_end = ""
    i_after_close = 0
    i_open = -1
    i = 0
    ntext = ""
    lensq = len(squote)
    while i < len(text):

        # Calculate the length of no-modify segment if it starts here.
        no_mod_len = 0

        # - known XML nodes which are literal user input to computer
        m = _xml_literal_rx.match(text, i)
        if m:
            tag = m.group(1)
            end_rx = re.compile(r"\b%s *>" % tag)
            m = end_rx.search(text, i + len(tag))
            if m: # skip only if closed, otherwise stay put
                no_mod_len = m.span()[1] - i

        # - within XML tags
        elif text[i] == "<":
            ic = text.find(">", i + 1)
            if ic >= 0: # markup only if closed, otherwise stay put
                no_mod_len = ic - i + 1

        # - text in special parenthesis
        elif text[i] in ("{", "["):
            qopen = text[i]
            if qopen == "{":
                qclose = "}"
            else:
                qclose = "]"
            # Look for balanced pair.
            nopen = 1
            ic = i + 1
            while ic < len(text) and nopen > 0:
                if text[ic] == qopen:
                    nopen += 1
                elif text[ic] == qclose:
                    nopen -= 1
                ic += 1
            if nopen == 0: # special only if closed, otherwise stay put
                no_mod_len = ic - i

        # - simple quotes with no text in between
        elif text[i:i + 2 * lensq] == squote + squote:
            no_mod_len = 2 * lensq

        # - ASCII quote just after a number, and no opening quote so far
        # (may be a unit: inch, foot, minute, second)
        elif i_open < 0 and text[i:i + 1].isdigit():
            if text[i + 1:i + 1 + lensq] == squote:
                no_mod_len = 1 + lensq

        # Advance past the end of no-modify segment if found.
        if no_mod_len > 0:
            i += no_mod_len

        # If at simple quote.
        elif text[i:i+len(squote)] == squote:
            if i_open < 0:
                # No quote opened, this is opening quote.
                i_open = i # record opening position
                ntext += text[i_after_close:i_open] # append text so far
            else:
                # Quote opened beforehand, this is closing quote.
                tseg = text[i_open + len(squote) : i] # quoted segment
                ntext += fquotes[0] + tseg + fquotes[1] # append fancy-quoted
                nrepl += 1 # count added fancy pair
                i_open = -1 # cancel opened state
                i_after_close = i + len(squote) # record position after closing

            # Advance past the simple quote
            i += len(squote)

        else:
            # Nothing special, advance to next char.
            i += 1

    # Append the remaining text.
    if i_open >= 0:
        # Unpaired opening quote.
        ntext += text[i_open:]
    else:
        # All quotes paired.
        ntext += text[i_after_close:]

    return ntext, nrepl

