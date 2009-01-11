# -*- coding: UTF-8 -*-

"""
Transform ASCII single and double quotes into fancy counterparts.

Ordinary ASCII quotes are easy to type on most keyboard layouts, and are
frequently encountered in English original messages -- rather than proper
English text quotes, i.e. "fancy" quotes. Translators are therefore easily
moved to use ASCII quotes instead of the fancy quotes appropriate for their
language. Use this sieve to replace ASCII quotes in the translation with
selected fancy quotes.

Sieve options for simple, character-to-character quote replacement:
  - C{single:<quotes>}: opening and closing single qoute (two characters)
  - C{double:<quotes>}: opening and closing double qoute (two characters)

Sieve options for character-to-string quote replacement, useful e.g. when target quotes are tags or wiki markup:
  - C{longsingle:<open>,<close>}: opening and closing single quotes
  - C{longdouble:<open>,<close>}: opening and closing double quotes

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import os, re
from pology.misc.comments import manc_parse_flag_list
from pology.misc.escape import split_escaped
from pology.misc.report import error


# Pipe flag used to manually prevent transformation into fancy quotes.
flag_no_fancy_quote = "no-fancy-quote"


class Sieve (object):

    def __init__ (self, options):

        self.nrepl_single = 0
        self.nrepl_double = 0

        # Pair of single quotes.
        self.singles = ()
        if "single" in options and "longsingle" in options:
            error("cannot specify both character and string replacement "
                  "of single quotes")
        if "single" in options:
            quotes = options["single"]
            if len(quotes) != 2:
                error("invalid specification of single quotes '%s', "
                      "expected two characters" % quotes)
            self.singles = (quotes[0], quotes[1])
            options.accept("single")
        elif "longsingle" in options:
            quotes = split_escaped(options["longsingle"], ",")
            if len(quotes) != 2:
                error("invalid specification of single quotes '%s', "
                      "expected two strings" % quotes)
            self.singles = (quotes[0], quotes[1])
            options.accept("longsingle")

        # Pair of double quotes.
        self.doubles = ()
        if "double" in options and "longdouble" in options:
            error("cannot specify both character and string replacement "
                  "of double quotes")
        if "double" in options:
            quotes = options["double"]
            if len(quotes) != 2:
                error("invalid specification of double quotes '%s', "
                      "expected two characters" % quotes)
            self.doubles = (quotes[0], quotes[1])
            options.accept("double")
        elif "longdouble" in options:
            quotes = split_escaped(options["longdouble"], ",")
            if len(quotes) != 2:
                error("invalid specification of double quotes '%s', "
                      "expected two strings" % quotes)
            self.doubles = (quotes[0], quotes[1])
            options.accept("longdouble")


    def process (self, msg, cat):

        # Skip the message when told so.
        if flag_no_fancy_quote in manc_parse_flag_list(msg, "|"):
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

        if self.nrepl_single > 0 or self.nrepl_double > 0:
            print   "Total quote pairs replaced (single+double): %d+%d" \
                  % (self.nrepl_single, self.nrepl_double)


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
        elif text[i:i+2*len(squote)] == squote + squote:
            no_mod_len = 2 * len(squote)

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

