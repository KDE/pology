# -*- coding: UTF-8 -*-

import sys, re
import xml.parsers.expat

class Sieve (object):
    """Resolve XML entities in msgstr."""

    def __init__ (self, options, global_options):

        self.nresolved = 0
        self.nunknown = 0

        # Files defining entities.
        self.entity_files = []
        if "from" in options:
            options.accept("from")
            self.entity_files = options["from"]

        # Ignored entities.
        self.ignored_entities = ["lt", "gt", "apos", "quot", "amp"]
        if "ignore" in options:
            options.accept("ignore")
            self.ignored_entities.extend(options["ignore"])

        # Read entity definitions.
        self.entities = {}
        for fname in self.entity_files:
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
                self.entities[name] = value
            p = xml.parsers.expat.ParserCreate()
            p.EntityDeclHandler = handler
            try:
                p.Parse(defstr, True)
            except xml.parsers.expat.ExpatError, inst:
                sys.stderr.write("%s: %s\n" % (fname, inst))
                sys.exit(1)


    def process (self, msg, cat):

        for i in range(len(msg.msgstr)):
            msg.msgstr[i] = self.resolve_entities(msg.msgstr[i], cat.filename)


    def finalize (self):

        if self.nresolved > 0:
            print "Total resolved entities: %d" % self.nresolved
        if self.nunknown > 0:
            print "Total unknown entities: %d" % self.nunknown


    def resolve_entities (self, text, fname):

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
                if entname not in self.ignored_entities:
                    if entname in self.entities:
                        self.nresolved += 1
                        new_text = new_text[:-1] + self.entities[entname]
                        text = text[len(m.group(0)):]
                    else:
                        self.nunknown += 1
                        print "%s: unknown entity '%s'" % (fname, entname)

        return new_text
