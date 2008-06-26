# -*- coding: UTF-8 -*-

"""
Sieves messages with GNU aspell spell checker (http://aspell.net/)

@author: Sébastien Renard <sebastien.renard@digitalfox.org>
@license: GPLv3
"""

from pology.misc.colors import RED, RESET
from pology.external.pyaspell import Aspell, AspellConfigError, AspellError
from pology.misc.report import spell_error, spell_xml_error
from pology.misc.split import proper_words
from pology import rootdir
from locale import getdefaultlocale, getpreferredencoding
import os, re, sys
from os.path import abspath, basename, dirname, isfile, join
from codecs import open
from time import strftime


class Sieve (object):
    """Process messages through the aspell spell checker"""
    
    def __init__ (self, options, global_options):
    
        self.nmatch = 0 # Number of match for finalize
        self.aspell=None # Instance of Aspell parser
        self.encoding=getdefaultlocale()[1] # Local encoding to encode aspell output
        self.list=None # If not None, only list of faulty word is display (to ease copy/paste into personal dictionary)
        self.ignoredContext=[] # List of all PO message context for which no spell check should be done
        self.filename=""     # File name we are processing
        self.xmlFile=None # File handle to write XML output

        if "lang" in options:
            options.accept("lang")
            self.lang=str(options["lang"])
        else:
            self.lang="fr"
        
        if "list" in options:
            options.accept("list")
            self.list=[]
 
        personalDict=join(rootdir(), "l10n", self.lang, "spell", "dict.aspell")
        if not isfile(personalDict):
            #print "Personal dictionary is not available for your language"
            aspellOptions=(("lang", self.lang), ("mode", "sgml"), ("encoding", "utf-8"))
        else:
            #print "Using language-specific dictionary (%s)" % personalDict
            aspellOptions=(("lang", self.lang), ("mode", "sgml"), ("encoding", "utf-8"), ("personal-path", str(personalDict)))

        # Create Aspell object
        try:
            self.aspell=Aspell(aspellOptions)
        except AspellConfigError, e:
            print RED+("Aspell Configuration error:\n%s" % e) + RESET
            sys.exit(1)
        except AspellError, e:
            print RED+"Cannot initialize Aspell"+RESET
            print RED+"\t- Check that you correctly install Aspell and the according language dictionary."+RESET
            print RED+"\t- Check that you did not use special characters in you personal dictionary."+RESET
            sys.exit(1) 

        # Load ignoredContext
        ignoredContextFile=join(rootdir(), "l10n", self.lang, "spell", "ignoredContext")
        if isfile(ignoredContextFile):
            for line in open(ignoredContextFile, "r", "utf-8"):
                line=line.strip()
                if line.startswith("#") or line=="":
                    continue
                else:
                    self.ignoredContext.append(line.lower())

        # Also output in XML file ?
        if "xml" in options:
            options.accept("xml")
            xmlPath=options["xml"]
            if os.access(dirname(abspath(xmlPath)), os.W_OK):
                #TODO: create nice api to manage xml file and move it to misc/
                self.xmlFile=open(xmlPath, "w", "utf-8")
                self.xmlFile.write('<?xml version="1.0" encoding="UTF-8"?>\n')
                self.xmlFile.write('<pos date="%s">\n' % strftime('%c').decode(getpreferredencoding()))
            else:
                print "Cannot open %s file. XML output disabled" % xmlPath

        # Remove accelerators?
        self.accel_explicit = False
        self.accel_usual = "&_~"
        self.accel = ""
        if "accel" in options:
            options.accept("accel")
            self.accel = options["accel"]
            self.accel_explicit = True

        # Pattern for words to skip.
        self.skipRx = None
        if "skip" in options:
            options.accept("skip")
            self.skipRx = re.compile(options["skip"], re.U|re.I)

        # Indicators to the caller:
        self.caller_sync = False # no need to sync catalogs
        self.caller_monitored = False # no need for monitored messages


    def process_header (self, hdr, cat):

        # Check if the catalog itself states the shortcut character,
        # unless specified explicitly by the command line.
        if not self.accel_explicit:
            accel = cat.possible_accelerator()
            if accel:
                self.accel = accel
            else:
                self.accel = self.accel_usual

        # Close previous/open new XML section.
        if self.xmlFile:
            filename = os.path.basename(cat.filename)
            #print "(Processing %s)" % filename # better not contaminate stdout?
            # Close previous PO.
            if self.filename != "":
                self.xmlFile.write("</po>\n")
            self.filename = filename
            # Open new PO.
            poTag='<po name="%s">\n' % filename
            self.xmlFile.write(poTag) # Write to result


    def process (self, msg, cat):

        if msg.obsolete:
            return

        id=0 # Count msgstr plural forms

        for msgstr in msg.msgstr:
            # Skip message with context in the ignoredContext list
            msg.msgctxt.lower()
            skip=False
            for context in self.ignoredContext:
                if context in msg.msgctxt.lower():
                    skip=True
                    break
            if skip:
                break

            # Split text into words.
            words = proper_words(msgstr, True, self.accel)

            # Possibly eliminate some words from checking.
            if self.skipRx:
                words = [x for x in words if not self.skipRx.search(x)]

            for word in words:
                # Encode word for Aspell.
                encodedWord=word.encode("utf-8")
                spell=self.aspell.check(encodedWord)
                if spell is False:
                    try:
                        self.nmatch+=1
                        if self.list is not None:
                            if word not in self.list:
                                self.list.append(word)
                        else:
                            suggestions=self.aspell.suggest(encodedWord)
                            if self.xmlFile:
                                xmlError=spell_xml_error(msg, cat, word, suggestions, id)
                                self.xmlFile.writelines(xmlError)
                            else:
                                spell_error(msg, cat, word, [i.encode(self.encoding) for i in suggestions])
                    except UnicodeEncodeError:
                        print "Cannot encode this word in your codec (%s)" % self.encoding
            id+=1 # Increase msgstr id count


    def finalize (self):
        if self.list is not None:
            print "\n".join([i.decode(self.encoding) for i in self.list])
        else:
            if self.nmatch:
                print "----------------------------------------------------"
                print "Total matching: %d" % self.nmatch
        if self.xmlFile:
            self.xmlFile.write("</po>\n")
            self.xmlFile.write("</pos>\n")
            self.xmlFile.close()

