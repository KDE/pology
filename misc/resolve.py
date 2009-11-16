# -*- coding: UTF-8 -*-

"""
Replacement of segments in text which define some underlying values.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import os
import re
import difflib

from pology.misc.report import warning


# Defult starting string of alternatives directives.
DEFAULT_ALTHEAD = "~@"


_entity_ref_rx = re.compile(r"&([\w_:][\w\d._:-]*);")

def resolve_entities (text, entities, ignored=set(), srcname=None,
                      vfilter=None, undefrepl=None):
    """
    Replace XML entities in the text with their values.

    Entity values are defined by the supplied dictionary of name-value pairs.
    Not all entities need to be replaced, some can be explicitly ignored.
    If an entity is neither defined nor ignored, a warning will be reported
    to standard output if C{srcname} is given.

    An undefined entity is by default left untouched in the resulting text.
    Instead, the parameter C{undefrepl} can be used to supply a string to
    substitute for every undefined entity, or a function which takes
    the undefined entity name and returns the string to substitute.

    @param text: the text to transform
    @type text: string
    @param entities: entity name-value pairs
    @type entities: dict
    @param ignored: entities to ignore; a sequence of entity names,
        or function taking the entity name and returning C{True} if ignored
    @type ignored: a sequence or (string)->bool
    @param srcname: if not None, report unknown entities to standard output,
        with this parameter as source identifier
    @type srcname: None or string
    @param vfilter: format string (with single C{%s} directive) or function
        to apply to every resolved entity value
    @type vfilter: string or (string)->string
    @param undefrepl: string or function to use in case of undefined entity
    @type undefrepl: string of (string)->string

    @returns: the resulting text, resolved entities names,
        and unknown entity names
    @rtype: (string, [string...], [string...])
    """

    ignoredf = ignored if callable(ignored) else lambda x: x in ignored

    unknown = []
    resolved = []
    segs = []
    p = 0
    while True:
        pp = p
        p = text.find("&", p)
        if p < 0:
            segs.append(text[pp:])
            break

        segs.append(text[pp:p])
        m = _entity_ref_rx.match(text, p)
        if m:
            entref = m.group(0)
            entname = m.group(1)
            if not ignoredf(entname):
                entval = entities.get(entname)
                entvalr = entval
                if entval is not None:
                    resolved.append(entname)
                else:
                    unknown.append(entname)
                    if undefrepl is not None:
                        if isinstance(undefrepl, basestring):
                            entvalr = undefrepl
                        else:
                            entvalr = undefrepl(entname)

                if entvalr is not None:
                    if vfilter is not None:
                        if isinstance(vfilter, basestring):
                            entvalr = vfilter % entvalr
                        else:
                            entvalr = vfilter(entvalr)
                    # Recurse in case entity resolves into new entities.
                    res = resolve_entities(entvalr, entities, ignoredf,
                                           srcname, vfilter, undefrepl)
                    entvalr, resolved_extra, unknown_extra = res
                    resolved.extend(resolved_extra)
                    unknown.extend(unknown_extra)
                    segs.append(entvalr)
                else:
                    segs.append(entref)

                if entval is None and srcname is not None:
                    # Try to suggest some near matches.
                    #nears = difflib.get_close_matches(entname, entities)
                    # FIXME: Too slow for a lot entities.
                    nears = []
                    if nears:
                        warning("%s: unknown entity '%s' "
                                "(near matches: %s)"
                                % (srcname, entname, ", ".join(nears)))
                    else:
                        warning("%s: unknown entity '%s'"
                                % (srcname, entname))
            else:
                segs.append(entref)

            p += len(entref)
        else:
            p += 1

    new_text = "".join(segs)

    return new_text, resolved, unknown


def resolve_entities_simple (text, entities, ignored=set(),
                             srcname=None, vfilter=None):
    """
    As L{resolve_entities}, but returns only the resolved text.

    @returns: the resulting text
    @rtype: string

    @see: L{resolve_entities}
    """

    return resolve_entities(text, entities, ignored,
                            srcname=srcname, vfilter=vfilter)[0]


def resolve_alternatives (text, select, total, althead=DEFAULT_ALTHEAD,
                          altfilter=None, outfilter=None, condf=None,
                          srcname=None):
    """
    Replace alternatives directives in the text with the selected alternative.

    Alternatives directives are of the form C{~@/.../.../...}, for example::

        I see a ~@/pink/white/ elephant.

    where C{~@} is the directive head, followed by a character that
    defines the delimiter of alternatives (like in C{sed} command).
    The number of alternatives per directive is not defined by the directive
    itself, but is provided as an external parameter.

    Alternative directive is resolved into one of the alternative substrings
    by given index of the alternative (one-based).
    Before substituting the directive, the selected alternative can be filtered
    through function given by C{altfilter} parameter.
    Text outside of directives can be filtered as well, piece by piece,
    through the function given by C{outfilter} parameter.

    If an alternatives directive is malformed (e.g. to little alternatives),
    it may be reported to standard output. Unless all encountered directives
    were well-formed, the original text is returned instead of the partially
    resolved one.

    @param text: the text to transform
    @type text: string
    @param select: index of the alternative to select (one-based)
    @type select: int > 0
    @param total: number of alternatives per directive
    @type total: int > 0
    @param althead: directive head to use instead of the default one
    @type althead: string
    @param altfilter: filter to apply to chosen alternatives
    @type altfilter: (string) -> string
    @param outfilter: filter to apply to text outside of directives
    @type outfilter: (string) -> string
    @param condf:
        resolve current alternative directive only when this function
        returns C{True} on call with each alternative as argument
    @type condf: None or C{(x_1, ..., x_n) -> True/False}
    @param srcname:
        if not None, report malformed directives to standard output,
        with this string as source identifier
    @type srcname: None or string
    @returns:
        resulting text, number of resolved alternatives, and an indicator
        of well-formedness (C{True} if all directives well-formed)
    @rtype:
        string, int, bool
    """

    alt_head = althead
    alt_hlen = len(althead)

    if outfilter is None:
        outfilter = lambda x: x
    if altfilter is None:
        altfilter = lambda x: x

    original_text = text
    new_text = u""
    nresolved = 0
    malformed = False
    p = -1
    while True:
        pp = p + 1
        p = text.find(alt_head, pp)
        if p < 0:
            new_text += outfilter(text[pp:])
            break
        ps = p

        # Append segment prior to alternatives directive to the result.
        new_text += outfilter(text[pp:p])
        rep_text = text[p:] # text segment for error reporting

        # Must have at least 2 characters after the head.
        if len(text) < p + alt_hlen + 2:
            malformed = True
            if srcname is not None:
                warning("%s: malformed directive: "
                        "\"...%s\"" % (srcname, rep_text))
            break

        # Read the separating character.
        p += alt_hlen
        sep = text[p]

        # Parse requested number of inserts,
        # choose the one with matching index for the result.
        alts = []
        for i in range(total):
            pp = p + 1
            p = text.find(sep, pp)
            # Must have exactly the given total number of alternatives.
            if p < 0:
                malformed = True
                if srcname is not None:
                    warning("%s: too little alternatives in the directive: "
                            "\"...%s\"" % (srcname, rep_text))
                break
            alts.append(text[pp:p])
        if malformed:
            break

        # Replace the alternative if admissible, or leave directive untouched.
        isel = select - 1
        if isel < len(alts) and (not condf or condf(*alts)):
            new_text += altfilter(alts[isel])
            nresolved += 1
        else:
            new_text += text[ps:p+1]

    if malformed:
        new_text = original_text
        nresolved = 0

    return new_text, nresolved, not malformed


def resolve_alternatives_simple (text, select, total, althead=DEFAULT_ALTHEAD,
                                 altfilter=None, outfilter=None, condf=None,
                                 srcname=None):
    """
    As L{resolve_alternatives}, but return only the resolved text.

    @returns: the resulting text
    @rtype: string

    @see: L{resolve_alternatives}
    """

    res = resolve_alternatives(text, select, total, althead,
                               altfilter, outfilter, condf,
                               srcname)
    ntext, d1, valid = res
    if not valid:
        return text
    return ntext


def first_to_case (text, upper=True, nalts=0, althead=DEFAULT_ALTHEAD):
    """
    Change case of the first letter in the text.

    Text may also have alternatives directives (see L{resolve_alternatives}).
    In that case, if the first letter is found within an alternative, change
    cases for first letters in other alternatives of the same directive too.

    @param text: the text to transform
    @type text: string

    @param upper: whether to transform to uppercase (lowercase otherwise)
    @type upper: bool

    @param nalts: if non-zero, the number of alternatives per directive
    @type nalts: int >= 0

    @param althead: alternatives directive head instead of the default one
    @type althead: string

    @returns: the resulting text
    @rtype: string

    @see: L{resolve_alternatives}
    """

    alt_head = althead
    alt_hlen = len(althead)

    tlen = len(text)
    remalts = 0
    checkcase = True
    intag = False
    ncchanged = 0
    textcc = ""
    i0 = 0
    i = 0
    while i < tlen:
        i0 = i
        c = text[i]
        cchange = False

        if c == "<":
            # A markup tag is just starting.
            intag = True

        elif c == ">":
            # A markup tag is just ending.
            intag = False

        elif (    not intag
              and nalts and not remalts and text[i:i+alt_hlen] == alt_head):
            # An alternatives directive is just starting.
            i += 2
            if i >= tlen: # malformed directive, bail out
                textcc = text
                break
            # Record alternatives separator, set number of remaining
            # alternatives, reactivate case checking.
            altsep = text[i]
            remalts = nalts
            checkcase = True

        elif not intag and remalts and c == altsep:
            # Alternative separator found, reduce number of remaining
            # alternatives and reactivate case checking.
            remalts -= 1
            checkcase = True

        elif not intag and checkcase and c.isalpha():
            # Case check is active and the character is a letter;
            # request case change.
            cchange = True
            # No more case checks until next alternatives separator.
            checkcase = False

        # Go to next character.
        i += 1

        # Check if previous segment should be added with case change, or as is.
        cseg = text[i0:i]
        if cchange:
            ncchanged += 1
            if upper: textcc += cseg.upper()
            else:     textcc += cseg.lower()
        else:
            textcc += cseg

        # If any letter has been upcased and there are no more alternatives
        # to be processed, we're done.
        if ncchanged > 0 and remalts == 0:
            textcc += text[i:]
            break

    return textcc


def first_to_upper (text, nalts=0, althead=DEFAULT_ALTHEAD):
    """
    Uppercase the first letter in the text.

    A shortcut for L{first_to_case} for uppercasing.

    @see: L{first_to_case}
    """

    return first_to_case(text, upper=True, nalts=nalts, althead=althead)


def first_to_lower (text, nalts=0, althead=DEFAULT_ALTHEAD):
    """
    Lowercase the first letter in the text.

    A shortcut for L{first_to_case} for lowercasing.

    @see: L{first_to_case}
    """

    return first_to_case(text, upper=False, nalts=nalts, althead=althead)


def expand_vars (text, varmap, head="%"):
    """
    Expand variables in the text.

    Expansion directives start with a directive head (C{head} parameter),
    followed by variable name consisting of alphanumeric characters and
    underscores, and ending by any other character.
    Variable name may also be explicitly delimited within braces.
    Variable values for substitution are looked up by name in
    the C{varmap} dictionary; if not found, C{NameError} is raised.

    Some examples::

        expand_vars("Mary had a little %mammal.", {"mammal":"lamb"})
        expand_vars("Quite a %{critic}esque play.", {"critic":"burl"})
        expand_vars("Lost in single ~A.", {"A":"parenthesis"}, "~")

    Dictionary values are filtered as C{"%s" % value} prior to substitution.
    Directive head may be escaped by repeating it twice in a row.

    @param text: string to expand
    @type text: string

    @param varmap: mapping of variable names to values
    @type varmap: (name, value) dictionary

    @param head: opening sequence for expansion directive
    @type head: string
    """

    p = 0
    hlen = len(head)
    tlen = len(text)
    ntext = []
    while p < tlen:
        pp = p
        p = text.find(head, pp)
        if p < 0:
            ntext.append(text[pp:])
            break
        ntext.append(text[pp:p])
        p += hlen
        if p < tlen and text[p:p+hlen] == head: # escaped
            ntext.append(head)
            p += hlen
            continue
        if p == tlen:
            raise NameError, \
                  ("variable expansion: trailing-off expansion directive "
                   "at column %d in string '%s'" % (p - hlen, text))
        braced = False
        if text[p] == "{":
            braced = True
            p += 1
        pp = p
        while p < tlen:
            c = text[p]
            if (   (not braced and not (c.isalnum() or c == "_"))
                or (braced and c == "}")
            ):
                break
            p += 1
        if braced and p == tlen:
            raise NameError, \
                  ("variable expansion: unclosed expansion directive "
                   "at column %d in string '%s'" % (pp - 1 - hlen, text))
        varname = text[pp:p]
        if braced:
            p += 1

        varvalue = varmap.get(varname)
        if varvalue is None:
            raise NameError, \
                  ("variable expansion: unknown variable '%s' "
                   "at column %d in string '%s'" % (varname, pp, text))
        ntext.append("%s" % varvalue)

    return type(text)("").join(ntext)


_usual_accels = list("_&~^")

def remove_accelerator (text, accels=None, greedy=False):
    """
    Remove accelerator from the text.

    Accelerator markers are characters which determine which letter in
    the text will be used as keyboard accelerator in user interface.
    They are usually a single non-alphanumeric character,
    and inserted before the letter which should be the accelerator,
    e.g. C{"Foo &Bar"}, C{"Foo _Bar"}, etc.
    Sometimes, especially in CJK texts, accelerator letter is separated out
    in parenthesis, at the start or end of the text, such as C{"Foo Bar (&B)"}.

    This function will try to remove the accelerator in a smart way.
    E.g. it will ignore ampersand in C{"Foo & Bar"}, and completely
    remove a CJK-style accelerator.

    If C{accels} is C{None}, the behavior depends on the value of C{greedy}.
    If it is C{False}, text is removed as is. If it is C{True}, some usual
    accelerator markers are considered: C{_}, C{&}, C{~}, and C{^}.

    @param text: text to clear of the accelerator
    @type text: string
    @param accels: possible accelerator markers
    @type accels: sequence of strings or C{None}
    @param greedy: whether to try known markers if C{accels} is C{None}
    @type greedy: bool

    @returns: text without the accelerator
    @rtype: string
    """

    if accels is None:
        if not greedy:
            return text
        else:
            accels = _usual_accels

    for accel in accels:
        alen = len(accel)
        p = 0
        while True:
            p = text.find(accel, p)
            if p < 0:
                break

            if text[p + alen:p + alen + 1].isalnum():
                # If the accelerator marker is &, do not remove it if it
                # looks like an XML entity (less damage than otherwise).
                if accel == "&":
                    m = _entity_ref_rx.match(text, p)
                    if m:
                        p = m.span()[1]
                        continue

                # Valid accelerator.
                text = text[:p] + text[p + alen:]

                # May have been an accelerator in style of
                # "(<marker><alnum>)" at the start or end of text.
                if (text[p - 1:p] == "(" and text[p + 1:p + 2] == ")"):
                    # Check if at start or end, ignoring non-alphanumerics.
                    tlen = len(text)
                    p1 = p - 2
                    while p1 >= 0 and not text[p1].isalnum():
                        p1 -= 1
                    p1 += 1
                    p2 = p + 2
                    while p2 < tlen and not text[p2].isalnum():
                        p2 += 1
                    p2 -= 1
                    if p1 == 0:
                        text = text[:p - 1].lstrip() + text[p2 + 1:]
                    elif p2 + 1 == tlen:
                        text = text[:p1] + text[p + 2:].rstrip()

                # Do not break, remove all accelerator markers,
                # as it is indeterminate which one is the real one.

            if text[p + alen:p + 2 * alen] == accel:
                # Escaped accelerator marker.
                text = text[:p] + text[p + alen:]

            p += alen

    return text


def remove_fmtdirs (text, format, subs=""):
    """
    Remove format directives from the text.

    Format directives are used to substitute values in the text.
    An example text with directives in several formats::

        "%d men on a %s man's chest."  # C
        "%(num)d men on a %(attrib)s man's chest."  # Python
        "%1 men on a %2 man's chest." # KDE/Qt

    Format is specified by a string keyword. The following formats are
    known at the moment: C{c}, C{qt}, c{kde}, c{python}.
    Format string may also have C{-format} appended to the keyword, for
    compatibility with Gettext format flags.

    @param text: text from which to remove format directives
    @type text: string
    @param format: format keyword
    @type format: string
    @param subs: text to replace format directives instead of just removing it
    @type subs: string

    @returns: text without format directives
    @rtype: string
    """

    format = format.lower()
    if format.endswith("-format"):
        format = format[:format.rfind("-")]

    if 0: pass
    elif format == "c":
        text = _remove_fmtdirs_c(text, subs)
    elif format in ("kde", "qt"):
        # FIXME: Actually, there are some differences between the two.
        text = _remove_fmtdirs_qt(text, subs)
    elif format == "python":
        text = _remove_fmtdirs_python(text, subs) # must be first
        text = _remove_fmtdirs_c(text, subs)

    return text


# FIXME: Make it tighter.
_fmtdir_tail_c = r"[ +-]?\d*\.?\d*[a-z]"
_fmtdir_tail_c_rx = re.compile(_fmtdir_tail_c)

def _remove_fmtdirs_c (text, subs=""):

    p = 0
    nsegs = []
    while True:
        pp = p
        p = text.find("%", p)
        if p < 0:
            nsegs.append(text[pp:])
            break
        nsegs.append(text[pp:p])
        p += 1
        if text[p:p+1] == "%":
            nsegs.append("%")
            p += 1
            continue
        m = _fmtdir_tail_c_rx.match(text, p)
        if m:
            p = m.span()[1]
            if subs:
                nsegs.append(subs)

    return "".join(nsegs)


# FIXME: Make it tighter?
_fmtdir_tail_python_rx = re.compile(r"(\(.*?\))?" + _fmtdir_tail_c)

def _remove_fmtdirs_python (text, subs=""):

    p = 0
    nsegs = []
    while True:
        pp = p
        p = text.find("%", p)
        if p < 0:
            nsegs.append(text[pp:])
            break
        nsegs.append(text[pp:p])
        p += 1
        if text[p:p+1] == "%":
            nsegs.append("%")
            p += 1
            continue
        m = _fmtdir_tail_python_rx.match(text, p)
        if m:
            p = m.span()[1]
            if subs:
                nsegs.append(subs)

    return "".join(nsegs)


_fmtdir_tail_qt_rx = re.compile(r"L?\d{1,2}")

def _remove_fmtdirs_qt (text, subs=""):

    p = 0
    nsegs = []
    while True:
        pp = p
        p = text.find("%", p)
        if p < 0:
            nsegs.append(text[pp:])
            break
        nsegs.append(text[pp:p])
        p += 1
        m = _fmtdir_tail_qt_rx.match(text, p)
        if m:
            p = m.span()[1]
            if subs:
                nsegs.append(subs)
        else:
            nsegs.append("%")

    return "".join(nsegs)


def remove_literals (text, subs="", substrs=[], regexes=[], heuristic=True):
    """
    Remove literal substrings from the text.

    Literal substrings are URLs, email addresses, web site names,
    command options, etc. This function will heuristically try to
    remove such substrings from the text.

    Additional literals to remove may be specified as verbatim substrings
    (C{substrs} parameter) and regular expressions (C{regexes}).
    These are applied before the internal heuristic matchers.
    Heuristic removal may be entirely disabled by setting C{heuristic}
    to C{False}.

    @param text: text from which to remove literals
    @type text: string
    @param subs: text to replace literals instead of just removing them
    @type subs: string
    @param substrs: additional substrings to remove by direct string match
    @type substrs: sequence of strings
    @param regexes: additional substrings to remove by regex match
    @type regexes: sequence of compiled regular expressions
    @param heuristic: whether to apply heuristic at all
    @type heuristic: bool

    @returns: text without literals
    @rtype: string
    """

    # Apply explicit literals before heuristics.
    for substr in substrs:
        text = text.replace(substr, subs)
    for regex in regexes:
        text = regex.sub(subs, text)

    if heuristic:
        text = _remove_literals_url(text, subs)
        text = _remove_literals_email(text, subs)
        text = _remove_literals_web(text, subs) # after URLs and email
        text = _remove_literals_cmd(text, subs)
        text = _remove_literals_file(text, subs)

    return text


def _remove_by_rx (text, rx, subs=""):

    p = 0
    nsegs = []
    while True:
        m = rx.search(text, p)
        if not m:
            nsegs.append(text[p:])
            break
        p1, p2 = m.span()
        nsegs.append(text[p:p1])
        if subs:
            nsegs.append(subs)
        p = p2

    return "".join(nsegs)


_literal_url_rx = re.compile(r"\S+://\S*[\w&=]", re.U)

def _remove_literals_url (text, subs=""):

    return _remove_by_rx(text, _literal_url_rx, subs)


_literal_web_rx = re.compile(r"\w{3,}(\.[\w-]{2,})+", re.U)

def _remove_literals_web (text, subs=""):

    return _remove_by_rx(text, _literal_web_rx, subs)


_literal_email_rx = re.compile(r"\w[\w.-]*@\w+\.[\w.-]*\w")

def _remove_literals_email (text, subs=""):

    return _remove_by_rx(text, _literal_email_rx, subs)


_literal_cmd_rx = re.compile(r"[a-z\d_-]+\(\d\)", re.I)
_literal_cmdopt_rx = re.compile(r"(?<!\S)-[a-z\d]+", re.I)
_literal_cmdoptlong_rx = re.compile(r"(?<!\S)--[a-z\d-]+", re.I)

def _remove_literals_cmd (text, subs=""):

    text = _remove_by_rx(text, _literal_cmd_rx, subs)
    text = _remove_by_rx(text, _literal_cmdopt_rx, subs)
    text = _remove_by_rx(text, _literal_cmdoptlong_rx, subs)
    return text


_literal_filehome_rx = re.compile(r"~(/[\w.-]+)+/?", re.I|re.U)
_literal_fileext_rx = re.compile(r"\*\.[a-z\d]+", re.I)

def _remove_literals_file (text, subs=""):

    text = _remove_by_rx(text, _literal_filehome_rx, subs)
    text = _remove_by_rx(text, _literal_fileext_rx, subs)
    return text

