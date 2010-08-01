# -*- coding: UTF-8 -*-

"""
Generate an XML tree from the input PO files.

This sieve allows the generation of an XML representation of a PO file or
a list of PO files (depending on options of the posieve.py command line).

Each PO file is represented by a C{<po>} tag which contains a list of C{<msg>} tag, for each message. 
The C{<msg>} tag contains the classical entries describing a PO message :
  - C{<line>}: Line number of the message
  - C{<refentry>}: Reference entry
  - C{<status>}: Current status of the message (obsolete, translated,
    untranslated, fuzzy)
  - C{<msgid>}: Message Identifier
  - C{<msgstr>}: Translated Message
  - C{<msgctxt>}: Message Context

Please note that if the translated message contains plural forms, they will be
described as C{<plural>} subtags of C{<msgstr>} tag.

The sieve parameters are:
  - C{xml:<filename>}: Export the input PO files into the file instead
    of the standard output
  - C{translatedOnly}: Only export translated entries (and so, ignore obsolete,
    untranslated and fuzzy strings)

@author: Nicolas Ternisien <nicolas.ternisien@gmail.com>
@license: GPLv3
"""

from codecs import open
import locale
import os
from os.path import abspath, basename, dirname, isdir, isfile, join
import sys

from pology import _, n_
from pology.report import report
from pology.rules import loadRules, Rule
from pology.timeout import TimedOutException


def setup_sieve (p):

    p.set_desc(_("@info sieve discription",
    "Generate an XML tree from the input PO files."
    "\n\n"
    "See documentation for the description of the XML format used."
    ))

    p.add_param("xml", unicode,
                metavar=_("@info sieve parameter value placeholder", "FILE"),
                desc=_("@info sieve parameter discription",
    "Write the XML tree into a file instead to standard output."
    ))
    # FIXME: Parameter name out of style.
    p.add_param("translatedOnly", bool, defval=False,
                desc=_("@info sieve parameter discription",
    "Consider only translated messages."
    ))


class Sieve (object):

    def __init__ (self, params):

        self.xmlFile = None # File handle to write XML output
        self.filename = ""     # File name we are processing
        self.translatedOnly = False
        
        
        # Also output in XML file ?
        if params.xml:
            xmlPath = params.xml
            if os.access(dirname(abspath(xmlPath)), os.W_OK):
                self.xmlFile=open(xmlPath, "w", "utf-8")
            else:
                warning(_("@info",
                          "Cannot open file '%(file)s'. XML output disabled.",
                          file=xmlPath))
        
        self.translatedOnly = params.translatedOnly
        

        self.output('<?xml version="1.0" encoding="UTF-8"?>\n')
        self.output('<pos>\n')

        self.count = {}
        self.count["obs"] = 0
        self.count["tot"] = 0
        self.count["trn"] = 0
        self.count["fuz"] = 0
        self.count["unt"] = 0

        # Indicators to the caller:
        self.caller_sync = False # no need to sync catalogs
        self.caller_monitored = False # no need for monitored messages

    def process(self, msg, cat):
        filename=basename(cat.filename)
        
        # Handle start/end of files for XML output (not needed for text output)
        if self.filename!=filename:
            if self.filename != "":
                self.write_stats()
                # close previous
                self.output("</po>\n")

            self.filename=filename
            # open new po
            self.output('<po name="%s">\n' % filename)

        # Test the add or not of this message
        if self.add_message(msg) is False:
            return

        # Statistics updating
        if msg.obsolete:
            self.count["obs"] += 1
            status = "obsolete"
        else:
            self.count["tot"] += 1
            if msg.translated:
                self.count["trn"] += 1
                status = "translated"
            elif msg.fuzzy:
                self.count["fuz"] += 1
                status = "fuzzy"
            elif msg.untranslated:
                self.count["unt"] += 1
                status = "untranslated"
                
        # Output writing
        self.output("\t<msg>\n")
        self.output("\t\t<line>%s</line>\n" % msg.refline)
        self.output("\t\t<refentry>%s</refentry>\n" % msg.refentry)
        self.output("\t\t<status>%s</status>\n" % status)
        self.output("\t\t<msgid><![CDATA[%s]]></msgid>\n" % self.replace_cdata(msg.msgid) )
        self.output("\t\t<msgstr>%s</msgstr>\n" % self.join_plural_form(msg.msgstr) )
        
        if not msg.msgctxt:
            self.output("\t\t<msgctxt></msgctxt>\n")
        else:
            self.output("\t\t<msgctxt><![CDATA[%s]]></msgctxt>\n" % self.replace_cdata(msg.msgctxt) )
            
        self.output("\t</msg>\n")

    def join_plural_form(self, message_list):
        if len(message_list) == 1:
            return "<![CDATA[%s]]>" % self.replace_cdata(message_list[0])

        message_str = ""
        for msgstr in message_list:
            message_str += "<plural><![CDATA[%s]]></plural>" % self.replace_cdata(msgstr)
        
        return message_str
        

    def add_message(self, msg):
        if self.translatedOnly is False:
            return True
        
        if self.translatedOnly is True and msg.translated is True:
            return True
        
        return False


    def replace_cdata(self, msg):
        return msg.replace("<![CDATA[", "&lt;![CDATA[").replace("]]>", "]]&gt;")
    
    def output(self, content):
        if self.xmlFile:
            self.xmlFile.write(content)
        else:
            report(content.rstrip("\n"))

    def write_stats(self):
        self.output("\t<stats>\n")
        self.output("\t\t<obsolete>%s</obsolete>\n" % self.count["obs"])
        self.output("\t\t<total>%s</total>\n" % self.count["tot"])
        self.output("\t\t<translated>%s</translated>\n" % self.count["trn"])
        self.output("\t\t<fuzzy>%s</fuzzy>\n" % self.count["fuz"])
        self.output("\t\t<untranslated>%s</untranslated>\n" % self.count["unt"])
        self.output("\t</stats>\n")
        self.count["obs"] = 0
        self.count["tot"] = 0
        self.count["trn"] = 0
        self.count["fuz"] = 0
        self.count["unt"] = 0

    def finalize (self):
        self.write_stats()
        self.output("</po>\n")
        self.output('</pos>\n')
        
        if self.xmlFile:
            # Close last po tag and xml file
            self.xmlFile.close()

