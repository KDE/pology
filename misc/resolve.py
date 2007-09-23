# -*- coding: UTF-8 -*-

import re
import xml.parsers.expat


def read_entities (*fnames):
    """Read XML entity definitions from given file names into a dictionary.

    The files should contain only entity definitions in DTD form,
    without any prolog or epilogue:
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


def resolve_entities (text, entities, ignored_entities, srcname=None):
    """Replace XML entities in the text with their values.

    Parameters:
      text             - the text to transform
      entities         - dictionary of entity names/values
      ignored_entities - list of entity names to ignore (any sequence that
                         can be tested by operator in for entity name)
      srcname          - if not None, unknown entities will be reported to
                         stdout, with this parameter as source identifier

    Return tuple of resulting text, number of resolved entities and
    number of unknown entities.
    """

    nunknown = 0
    nresolved = 0
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
                if entname in entities:
                    nresolved += 1
                    new_text = new_text[:-1] + entities[entname]
                    text = text[len(m.group(0)):]
                else:
                    nunknown += 1
                    if srcname is not None:
                        print "%s: unknown entity '%s'" % (srcname, entname)

    # Recursive resolving if at least one entity has been resolved.
    if nresolved > 0:
        new_text, nresolved_extra, nunknown_extra \
            = resolve_entities(new_text, entities, ignored_entities, srcname)
        nresolved += nresolved_extra
        nunknown += nunknown_extra

    return new_text, nresolved, nunknown


def resolve_entities_simple (text, entities, ignored_entities, srcname=None):
    """As resolve_entities(), but returns only the resolved text."""

    return resolve_entities(text, entities, ignored_entities, srcname)[0]


def resolve_alternatives (text, select, total, srcname=None):
    """Replace alternatives directives in the text with selected alternative.

    Parameters:
      text    - the text to transform
      select  - index of alternative to select, one-based
      total   - total number of alternatives per directive
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

    head = "~@"
    hlen = len(head)

    original_text = text
    new_text = u""
    nresolved = 0
    malformed = False

    while True:
        p = text.find(head)
        if p < 0:
            new_text += text
            break

        # Append segment prior to alternatives directive to the result.
        new_text += text[:p]
        rep_text = text[p:] # text segment for error reporting

        # Must have at least 2 characters after the head.
        if len(text) < p + hlen + 2:
            malformed = True
            if srcname is not None:
                print "%s: malformed directive: " \
                      "\"...%s\"" % (srcname, rep_text)
            break

        # Read the separating character and trim source text.
        sep = text[p + hlen]
        text = text[p + hlen + 1:]

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
                new_text += text[:p]
                nresolved += 1
                # Don't break here, should check if the total number
                # of alternatives match.

            # Trim source text.
            text = text[p + 1:]

    if malformed:
        new_text = original_text
        nresolved = 0

    return new_text, nresolved, malformed


def resolve_alternatives_simple (text, select, total, srcname=None):
    """As resolve_alternatives(), but return only the resolved text.

    If an alternatives directive is malformed, return original text.
    """

    ntext, d1, malformed = resolve_alternatives(text, select, total, srcname)
    if malformed:
        return text
    return ntext
