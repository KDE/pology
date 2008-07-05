# -*- coding: UTF-8 -*-

"""
Replacement of segments in text which define some underlying values.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import re
import xml.parsers.expat
import difflib


def parse_entities (defstr, src=None):
    """
    Parse XML entity definitions from given string.

    The string should contain only entity definitions in DTD form,
    without any prolog or epilogue::

      ...
      <!ENTITY foo 'Foo-fum'>
      <!ENTITY bar 'Bar-boo'>
      ...

    If the same entity is defined several times, the last read definition
    is taken as final.

    @param defstr: entity-defining string
    @type defstr: string

    @param src: name of the source, for problem reporting
    @param src: C{None} or string

    @returns: name-value pairs of parsed entities
    @rtype: dict
    """

    # Equip with prolog and epilogue.
    defstr = "<?xml version='1.0' encoding='UTF-8'?>\n" \
             "<!DOCTYPE entityLoader [" + defstr + "]><done/>"
    # Parse entities.
    entities = {}
    def handler (name, is_parameter_entity, value,
                    base, systemId, publicId, notationName):
        entities[name] = value
    p = xml.parsers.expat.ParserCreate()
    p.EntityDeclHandler = handler
    try:
        p.Parse(defstr, True)
    except xml.parsers.expat.ExpatError, inst:
        if src:
            raise StandardError ("%s: %s\n" % (src, inst))
        else:
            raise StandardError ("<STRING>: %s\n" % inst)

    return entities


def read_entities (*fnames):
    """
    Read XML entity definitions from given file names.

    Just passes contents from the files to L{parse_entities}.

    @param fnames: paths of entity-defining files
    @type fnames: strings

    @returns: name-value pairs of parsed entities
    @rtype: dict

    @see: L{parse_entities}
    """

    entities = {}
    for fname in fnames:
        # Scoop up file contents, as raw bytes (UTF-8 expected).
        ifs = open(fname, "r")
        defstr = "".join(ifs.readlines())
        ifs.close()
        # Parse entities.
        entities.update(parse_entities(defstr, src=fname))

    return entities


def resolve_entities (text, entities, ignored_entities,
                      srcname=None, fcap=False, nalts=0):
    """
    Replace XML entities in the text with their values.

    Entity values are defined by the supplied dictionary of name-value pairs.
    Not all entities need be replaced, some can be explicitly ignored.
    If an entity is neither defined nor ignored, a warning may be reported
    to standard output.

    Special services on request:

      - if the entity name starts with a capital letter, and is not among
        defined entities, the lookup is tried with the lowercased initial
        letter, and if found, the first letter in the value is uppercased

      - when the auto-uppercasing is in effect, and the entity value starts
        with an alternatives directive, the starting letter of each of the
        alternatives is uppercased (see L{resolve_alternatives})

    @param text: the text to transform
    @type text: string

    @param entities: entity name-value pairs
    @type entities: dict

    @param ignored_entities: entity names to ignore
    @type ignored_entities:
        any sequence that can be tested by C{in} for entity name

    @param srcname:
        if not None, report unknown entities to standard output,
        with this parameter as source identifier
    @type srcname: None or string

    @param fcap: whether auto-uppercasing is in effect
    @type fcap: bool

    @param nalts:
        non-zero indicate possible presence of alternatives directives,
        with this many alternatives per directive (when fcap is in effect)
    @type nalts: int >= 0

    @returns:
        the resulting text, resolved entities names, and unknown entity names
    @rtype:
        string, list of strings, list of strings

    @see: L{resolve_alternatives}
    """

    unknown = []
    resolved = []
    new_text = ""
    while True:
        p = text.find("&")
        if p < 0:
            new_text += text
            break

        new_text += text[0:p + 1]
        text = text[p + 1:]
        m = re.match(r"^([\w_:][\w\d._:-]*);", text)
        if m:
            entname = m.group(1)
            if entname not in ignored_entities:

                entname_orig = entname
                if fcap and not entname in entities:
                    # Allowed to also try entity with first letter lowercased.
                    entname = first_to_lower(entname)

                if entname in entities:
                    resolved.append(entname)
                    entval = entities[entname]
                    if fcap and entname_orig != entname:
                        entval = first_to_upper(entval, nalts)
                    new_text = new_text[:-1] + entval
                    text = text[len(m.group(0)):]
                else:
                    unknown.append(entname)
                    if srcname is not None:
                        # Try to suggest some near matches.
                        nears = difflib.get_close_matches(entname, entities)
                        if fcap and entname_orig != entname:
                            if nears:
                                print   "%s: unknown entity, either '%s' " \
                                        "or '%s' (near matches: %s)" \
                                      % (srcname, entname_orig, entname,
                                         ", ".join(nears))
                            else:
                                print   "%s: unknown entity, either '%s' " \
                                        "or '%s'" \
                                      % (srcname, entname_orig, entname)
                        else:
                            if nears:
                                print   "%s: unknown entity '%s' " \
                                        "(near matches: %s)" \
                                      % (srcname, entname, ", ".join(nears))
                            else:
                                print   "%s: unknown entity '%s'" \
                                      % (srcname, entname)

    # Recursive resolving if at least one entity has been resolved.
    if len(resolved) > 0:
        new_text, resolved_extra, unknown_extra \
            = resolve_entities(new_text, entities, ignored_entities, srcname)
        resolved.extend(resolved_extra)
        unknown.extend(unknown_extra)

    return new_text, resolved, unknown


def resolve_entities_simple (text, entities, ignored_entities,
                             srcname=None, fcap=False, nalts=0):
    """
    As L{resolve_entities}, but returns only the resolved text.

    @returns: the resulting text
    @rtype: string

    @see: L{resolve_entities}
    """

    return resolve_entities(text, entities, ignored_entities,
                            srcname=srcname, fcap=fcap, nalts=nalts)[0]


_alt_head = "~@"
_alt_hlen = len(_alt_head)

def resolve_alternatives (text, select, total, fmtstr=None, srcname=None,
                          condf=None):
    """
    Replace alternatives directives in the text with the selected alternative.

    Alternatives directives are of the form C{~@/.../.../...}, for example::

        I see a ~@/pink/white/ elephant.

    where C{~@} is the directive identifier, followed by a character that
    defines the delimiter of alternatives (like in C{sed} command).
    The number of alternatives per directive is not defined by the directive
    itself, but is provided as an external parameter.

    Alternative directive is resolved into one of the alternative substrings
    by given index of the alternative (one-based). Optionally, before
    substituting the directive, the selected alternative can be filtered
    through a string containing C{%s} format directive.

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

    @param fmtstr:
        if not None, filter string containing single C{%s} format directive
    @type fmtstr: None or string

    @param srcname:
        if not None, report malformed directives to standard output,
        with this string as source identifier
    @type srcname: None or string

    @param condf:
        resolve current alternative directive only when this function
        returns C{True} on call with each alternative as argument
    @type condf: None or C{(x_1, ..., x_n) -> True/False}

    @returns:
        resulting text, number of resolved alternatives, and an indicator
        of well-formedness (C{True} if all directives well-formed)
    @rtype:
        string, int, bool
    """

    original_text = text
    new_text = u""
    nresolved = 0
    malformed = False
    p = -1
    while True:
        pp = p + 1
        p = text.find(_alt_head, pp)
        if p < 0:
            new_text += text[pp:]
            break
        ps = p

        # Append segment prior to alternatives directive to the result.
        new_text += text[pp:p]
        rep_text = text[p:] # text segment for error reporting

        # Must have at least 2 characters after the head.
        if len(text) < p + _alt_hlen + 2:
            malformed = True
            if srcname is not None:
                print "%s: malformed directive: " \
                      "\"...%s\"" % (srcname, rep_text)
            break

        # Read the separating character.
        p += _alt_hlen
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
                    print "%s: too little alternatives in the directive: " \
                          "\"...%s\"" % (srcname, rep_text)
                break
            alts.append(text[pp:p])

        # Replace the alternative if admissible, or leave directive untouched.
        isel = select - 1
        if isel < len(alts) and (not condf or condf(*alts)):
            alt = alts[isel]
            if fmtstr is not None:
                alt = fmtstr % alt
            new_text += alt
            nresolved += 1
        else:
            new_text += text[ps:p+1]

    if malformed:
        new_text = original_text
        nresolved = 0

    return new_text, nresolved, malformed


def resolve_alternatives_simple (text, select, total, fmtstr=None,
                                 srcname=None, condf=None):
    """
    As L{resolve_alternatives}, but return only the resolved text.

    @returns: the resulting text
    @rtype: string

    @see: L{resolve_alternatives}
    """

    ntext, d1, malformed = resolve_alternatives(text, select, total,
                                                fmtstr=fmtstr, srcname=srcname,
                                                condf=condf)
    if malformed:
        return text
    return ntext


def first_to_case (text, upper=True, nalts=0):
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

    @returns: the resulting text
    @rtype: string

    @see: L{resolve_alternatives}
    """

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
              and nalts and not remalts and text[i:i+_alt_hlen] == _alt_head):
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


def first_to_upper (text, nalts=0):
    """
    Uppercase the first letter in the text.

    A shortcut for L{first_to_case} for uppercasing.

    @see: L{first_to_case}
    """

    return first_to_case(text, upper=True, nalts=nalts)


def first_to_lower (text, nalts=0):
    """
    Lowercase the first letter in the text.

    A shortcut for L{first_to_case} for lowercasing.

    @see: L{first_to_case}
    """

    return first_to_case(text, upper=False, nalts=nalts)


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

    return "".join(ntext)

