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

Entity definition files are plain text files of the following format::

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

from pology import _, n_
from pology.misc.entities import read_entities
from pology.misc.msgreport import warning_on_msg
from pology.misc.report import report, format_item_list
from pology.misc.resolve import resolve_entities
from pology.misc.stdsvpar import add_param_entdef


def setup_sieve (p):

    p.set_desc(_("@info sieve discription",
    "Resolve XML entities in translation."
    ))

    add_param_entdef(p)
    p.add_param("ignore", unicode, seplist=True,
                metavar=_("@info sieve parameter value placeholder",
                          "ENTITY1,..."),
                desc=_("@info sieve parameter discription",
    "Comma-separated list of entity names to ignore."
    ))


class Sieve (object):

    def __init__ (self, params):

        self.entity_files = params.entdef or []

        self.ignored_entities = ["lt", "gt", "apos", "quot", "amp"]
        if params.ignore:
            self.ignored_entities.extend(params.ignore)

        # Read entity definitions.
        self.entities = read_entities(self.entity_files)

        self.nresolved = 0


    def process (self, msg, cat):

        for i in range(len(msg.msgstr)):
            msg.msgstr[i], resolved, unknown = \
                resolve_entities(msg.msgstr[i],
                                 self.entities, self.ignored_entities,
                                 cat.filename)
            self.nresolved += len(resolved)
            if unknown:
                warning_on_msg(_("@info",
                                 "Unknown entities in translation: "
                                 "%(entlist)s.",
                                 entlist=format_item_list(unknown)),
                               msg, cat)


    def finalize (self):

        if self.nresolved > 0:
            msg = n_("@info:progress",
                     "Resolved %(num)d entity in translation.",
                     "Resolved %(num)d entities in translation.",
                     num=self.nresolved)
            report("===== " + msg)

