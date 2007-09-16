# -*- coding: UTF-8 -*-

import sys, re
import xml.parsers.expat
from pology.misc.resolve import read_entities
from pology.misc.resolve import resolve_entities

class Sieve (object):
    """Resolve XML entities in msgstr."""

    def __init__ (self, options, global_options):

        self.nresolved = 0
        self.nunknown = 0

        # Files defining entities.
        self.entity_files = []
        if "entdef" in options:
            options.accept("entdef")
            self.entity_files = options["entdef"]

        # Ignored entities.
        self.ignored_entities = ["lt", "gt", "apos", "quot", "amp"]
        if "ignore" in options:
            options.accept("ignore")
            self.ignored_entities.extend(options["ignore"])

        # Read entity definitions.
        self.entities = read_entities(*self.entity_files)


    def process (self, msg, cat):

        for i in range(len(msg.msgstr)):
            msg.msgstr[i], nresolved, nunknown = \
                resolve_entities(msg.msgstr[i],
                                 self.entities, self.ignored_entities,
                                 cat.filename)
            self.nresolved += nresolved
            self.nunknown += nunknown


    def finalize (self):

        if self.nresolved > 0:
            print "Total resolved entities: %d" % self.nresolved
        if self.nunknown > 0:
            print "Total unknown entities: %d" % self.nunknown

