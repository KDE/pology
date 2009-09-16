# -*- coding: UTF-8 -*-

"""
Resolve XML entities in translation.

XML entities are substrings of the form C{&entityname;},
which are resolved at build time or run time into underlying values.
Sometimes it may be advantageous to have them resolved alreayd in
the PO file itself.

Sieve parameters:
  - C{entdef:<filepath>}: path to file containing entity definitions;
        can be repeated to add several files
  - C{ignore:<entname1>,...}: entities to ignore when resolving

Entity definition files are plain text files of the following format:

    <!-- This is a commment. -->
    <!ENTITY name1 'value1'>
    <!ENTITY name2 'value2'>
    <!ENTITY name3 'value3'>
    ...

Standard XML entities (C{&lt;}, C{&gt;}, C{&apos;}, C{&quot;}, C{&amp;})
are ignored by default.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

from pology.misc.entities import read_entities
from pology.misc.resolve import resolve_entities
from pology.misc.report import report


def setup_sieve (p):

    p.set_desc(
    "Resolve XML entities in translation."
    )

    p.add_param("entdef", unicode, multival=True,
                metavar="FILE",
                desc=
    "File with entity definitions. "
    "Can be repeated to add several files."
    )
    p.add_param("ignore", unicode, seplist=True,
                metavar="ENTNAME1,...",
                desc=
    "Comma-separated list of entity names to ignore."
    )



class Sieve (object):

    def __init__ (self, params):

        self.nresolved = 0
        self.nunknown = 0

        self.entity_files = params.entdef or []

        self.ignored_entities = ["lt", "gt", "apos", "quot", "amp"]
        if params.ignore:
            self.ignored_entities.extend(params.ignore)

        # Read entity definitions.
        self.entities = read_entities(self.entity_files)


    def process (self, msg, cat):

        for i in range(len(msg.msgstr)):
            msg.msgstr[i], resolved, unknown = \
                resolve_entities(msg.msgstr[i],
                                 self.entities, self.ignored_entities,
                                 cat.filename)
            self.nresolved += len(resolved)
            self.nunknown += len(unknown)


    def finalize (self):

        if self.nresolved > 0:
            report("Total resolved entities: %d" % self.nresolved)
        if self.nunknown > 0:
            report("Total unknown entities: %d" % self.nunknown)

