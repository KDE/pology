# -*- coding: UTF-8 -*-

import re
import xml.parsers.expat


def read_entities (*fnames):
    """Read XML entity definitions from given file names into a dictionary.

    The files should contain only entity definitions in DTD form,
    without any prolog or epilogue::

      ...
      <!ENTITY foo 'Foo-fum'>
      <!ENTITY bar 'Bar-boo'>
      ...

    If same entity is defined several times, the last read definition wins.
    """

    entities = {}
    for fname in fnames:
        # Scoop up file contents, as raw bytes (UTF-8 expected).
        ifs = open(fname, "r")
        defstr = "".join(ifs.readlines())
        ifs.close()
        # Equip with prolog and epilogue.
        defstr = "<?xml version='1.0' encoding='UTF-8'?>\n" \
                    "<!DOCTYPE entityLoader [" + defstr + "]><done/>"
        # Parse entities.
        def handler (name, is_parameter_entity, value,
                        base, systemId, publicId, notationName):
            entities[name] = value
        p = xml.parsers.expat.ParserCreate()
        p.EntityDeclHandler = handler
        try:
            p.Parse(defstr, True)
        except xml.parsers.expat.ExpatError, inst:
            raise StandardError ("%s: %s\n" % (fname, inst))

    return entities


def resolve_entities (text, entities, ignored_entities,
                      srcname=None, fcap=False, nalts=0):
    """Replace XML entities in the text with their values.

    Parameters::

      text             - the text to transform
      entities         - dictionary of entity names/values
      ignored_entities - list of entity names to ignore (any sequence that
                         can be tested by operator in for entity name)
      srcname          - if not None, unknown entities will be reported to
                         stdout, with this parameter as source identifier
      fcap             - if the exact entity is not found, try one with
                         first letter in lowercase; if such is found, upcase
                         the first letter in its value before replacement
      nalts            - entity values may have alternatives directives
                         with this many alternatives per directive;
                         important when fcap is in effect

    Return tuple of resulting text, list of resolved entities and
    list of unknown entities.
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
                        if fcap and entname_orig != entname:
                            print   "%s: unknown entity, either '%s' or '%s'" \
                                  % (srcname, entname_orig, entname)
                        else:
                            print "%s: unknown entity '%s'" % (srcname, entname)

    # Recursive resolving if at least one entity has been resolved.
    if len(resolved) > 0:
        new_text, resolved_extra, unknown_extra \
            = resolve_entities(new_text, entities, ignored_entities, srcname)
        resolved.extend(resolved_extra)
        unknown.extend(unknown_extra)

    return new_text, resolved, unknown


def resolve_entities_simple (text, entities, ignored_entities,
                             srcname=None, fcap=False, nalts=0):
    """As resolve_entities(), but returns only the resolved text."""

    return resolve_entities(text, entities, ignored_entities,
                            srcname=srcname, fcap=fcap, nalts=nalts)[0]


_alt_head = "~@"
_alt_hlen = len(_alt_head)

def resolve_alternatives (text, select, total, fmtstr=None, srcname=None):
    """Replace alternatives directives in the text with selected alternative.

    Parameters::

      text    - the text to transform
      select  - index of alternative to select, one-based
      total   - total number of alternatives per directive
      fmtstr  - if not None, the string to which the selected alternative
                is sent by %-operator and then added into resolved text
      srcname - if not None, malformed directives will be reported to
                stdout, with this parameter as source identifier

    Alternatives directive is in the form "~@/text1/text2/.../".
    The slash-character can be replaced consistently with any other (sed-like).
    The number of alternatives must match given total, or else the directive
    is considered malformed.

    Return tuple of resulting text, number of resolved alternatives and
    boolean indicating whether a malformed directive was encountered.
    If at least one directive was malformed, the resulting text is same
    as original text, and number of resolved entities is zero.
    """

    original_text = text
    new_text = u""
    nresolved = 0
    malformed = False

    while True:
        p = text.find(_alt_head)
        if p < 0:
            new_text += text
            break

        # Append segment prior to alternatives directive to the result.
        new_text += text[:p]
        rep_text = text[p:] # text segment for error reporting

        # Must have at least 2 characters after the head.
        if len(text) < p + _alt_hlen + 2:
            malformed = True
            if srcname is not None:
                print "%s: malformed directive: " \
                      "\"...%s\"" % (srcname, rep_text)
            break

        # Read the separating character and trim source text.
        sep = text[p + _alt_hlen]
        text = text[p + _alt_hlen + 1:]

        # Parse requested number of inserts,
        # choose the one with matching index for the result.
        for i in range(total):
            # Ending separator for this insert.
            p = text.find(sep)

            # Must have exactly the given total number of alternatives.
            if p < 0:
                malformed = True
                if srcname is not None:
                    print "%s: too little alternatives in the directive: " \
                          "\"...%s\"" % (srcname, rep_text)
                break

            # If at requested alternative, append to the result.
            if i == select - 1:
                alt = text[:p]
                if fmtstr is not None:
                    alt = fmtstr % alt
                new_text += alt
                nresolved += 1
                # Don't break here, should check if the total number
                # of alternatives match.

            # Trim source text.
            text = text[p + 1:]

    if malformed:
        new_text = original_text
        nresolved = 0

    return new_text, nresolved, malformed


def resolve_alternatives_simple (text, select, total, fmtstr=None,
                                 srcname=None):
    """As resolve_alternatives(), but return only the resolved text.

    If an alternatives directive is malformed, return original text.
    """

    ntext, d1, malformed = resolve_alternatives(text, select, total,
                                                fmtstr=fmtstr, srcname=srcname)
    if malformed:
        return text
    return ntext


def first_to_case (text, upper=True, nalts=0):
    """Change case of the first letter in the text.

    If nalts is greater than zero, consider that text may have alternatives
    directives with this many alternatives; if the first letter is found
    within an alternative, change cases for first letters in other alternatives
    of the same directive too.
    """

    tlen = len(text)
    remalts = 0
    checkcase = True
    ncchanged = 0
    textcc = ""
    i0 = 0
    i = 0
    while i < tlen:
        i0 = i
        c = text[i]
        cchange = False

        if nalts and not remalts and text[i:i+_alt_hlen] == _alt_head:
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

        elif remalts and c == altsep:
            # Alternative separator found, reduce number of remaining
            # alternatives and reactivate case checking.
            remalts -= 1
            checkcase = True

        elif checkcase and c.isalpha():
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
    """Upper case first letter in the text.

    See first_to_case().
    """

    return first_to_case(text, upper=True, nalts=nalts)


def first_to_lower (text, nalts=0):
    """Lower case first letter in the text.

    See first_to_case().
    """

    return first_to_case(text, upper=False, nalts=nalts)
