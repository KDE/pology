# -*- coding: UTF-8 -*-

"""
Handle entity definitions.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import os
import xml.parsers.expat

from pology import PologyError, _, n_
from pology.fsops import collect_files_by_ext
from pology.report import warning


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
            raise PologyError(
                _("@info error report for a named source",
                  "%(src)s: %(msg)s",
                  src=src, msg=inst))
        else:
            raise PologyError(
                _("@info error report for a string",
                  "&lt;string&gt;: %(msg)s",
                  msg=inst))

    return entities


def read_entities (filepath, fcap=False):
    """
    Read XML entity definitions from given file path.

    Input argument can be a single file path, or a sequence of paths.
    Content of each file is parsed by L{parse_entities}.

    For each read entity, another entity may be added which has the first
    letter converted to upper-case, both in the entity name and value.
    See L{fcap_entities} for more details.

    @param filepath: path or paths of entity-defining file
    @type filepath: string or sequence of strings
    @param fcap: whether to add paired first-caps entities
    @type fcap: bool

    @returns: (name, value) dictionary of parsed entities
    @rtype: dict

    @see: L{parse_entities}
    """

    if isinstance(filepath, basestring):
        fnames = [filepath]
    else:
        fnames = filepath

    entities = {}
    for fname in fnames:
        # Scoop up file contents, as raw bytes (UTF-8 expected).
        ifs = open(fname, "r")
        defstr = "".join(ifs.readlines())
        ifs.close()
        # Parse entities.
        entities.update(parse_entities(defstr, src=fname))

    if fcap:
        fcap_entities(entities, update=True)

    return entities


def read_entities_by_env (entpathenv, recurse=True, fcap=False):
    """
    Read XML entity definitions from directory paths given by
    an environment variable.

    Directory paths given by environment variable are searched for files with
    C{.entities} extension, and all found files are sent to L{read_entities}.
    Search through directories can be recursive or non-recursive.

    See L{fcap_entities} for use of C{fcap} parameter.

    If the environment variable is not set, a warning is output and empty
    collection of entities returned.

    @param entpathenv: environment variable that holds directory paths
    @type entpathenv: string
    @param recurse: whether to search directories recursively
    @type recurse: bool
    @param fcap: whether to add paired first-caps entities
    @type fcap: bool

    @returns: (name, value) dictionary of parsed entities
    @rtype: dict
    """

    entities = {}

    entpath = os.getenv(entpathenv)
    if entpath is None:
        warning(_("@info",
                  "Environment variable with paths to entity definitions "
                  "'%(envar)s' is not set.",
                  envar=entpathenv))
        return entities

    entfilepaths = collect_files_by_ext(entpath.split(":"), "entities")
    entities.update(read_entities(entfilepaths, fcap))

    return entities


def fcap_entities (entities, update=False):
    """
    Create paired set of entities with first letters in upper-case.

    For each given entity, another entity may be created which has the first
    letter converted to upper-case, both in the entity name and value.
    Such entity is created only if the original entity has at least one
    letter in the name, and the first letter in the name is lower-case.

    New entities are either returned in a new dictionary, or are inserted
    into the original dictionary, which is then returned.

    @param entities: (name, value) dictionary of entities
    @type entities: dict
    @param update: whether to insert new entities into C{entities} itself
    @type update: bool

    @returns: (name, value) dictionary of upper-case entities
    @rtype: dict
    """

    if update:
        fcaps = entities
        iterents = entities.items()
    else:
        fcaps = {}
        iterents = entities.iteritems()

    for name, value in iterents:
        # Upper-case entity name.
        p = 0
        while p < len(name) and not name[p].isalpha():
            p += 1
        if p >= len(name): # nothing to upper-case, skip
            continue
        if not name[p].islower(): # first letter is not lower-case, skip
            continue
        name = name[:p] + name[p].upper() + name[p + 1:]

        # Upper-case entity value, if possible.
        p = 0
        while p < len(value) and not value[p].isalpha():
            p += 1
        if p < len(value):
            value = value[:p] + value[p].upper() + value[p + 1:]

        fcaps[name] = value

    return fcaps

