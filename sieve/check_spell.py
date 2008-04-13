# -*- coding: UTF-8 -*-

"""
Sieves messages with GNU aspell spell checker (http://aspell.net/)

@author: Sébastien Renard <sebastien.renard@digitalfox.org>
@license: GPLv3
"""

from pology.misc.colors import RED, RESET
from pology.external.pyaspell import Aspell, AspellConfigError, AspellError
from pology.misc.report import spell_error, spell_xml_error
from locale import getdefaultlocale, getpreferredencoding
import os, re, sys
from os.path import abspath, basename, dirname, isfile, join
from codecs import open
from time import strftime

# Regexp used to clean XML messages
XML=re.compile("<.*?>")
ENTITTY=re.compile("&\S*?;")
DIGIT=re.compile("\d")

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
 
        personalDict=join(dirname(sys.argv[0]), "l10n", self.lang, "spell", "dict.aspell")
        if not isfile(personalDict):
            print "Personal KDE dictionnary is not available for your language"
            aspellOptions=(("lang", self.lang), ("mode", "sgml"), ("encoding", "utf-8"))
        else:
            print "Using language specific KDE dictionnary (%s)" % personalDict
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
        ignoredContextFile=join(dirname(sys.argv[0]), "l10n", self.lang, "spell", "ignoredContext")
        if isfile(ignoredContextFile):
            for line in open(ignoredContextFile, "r", "utf-8"):
                line=line.strip()
                if line.startswith("#") or line=="":
                    continue
                else:
                    self.ignoredContext.append(line)

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

    def process (self, msg, cat):

        if msg.obsolete:
            return

        filename=basename(cat.filename)
  
        # New file handling
        if self.xmlFile and self.filename!=filename:
            print "(Processing %s)" % filename
            newFile=True
            if self.filename!="":
                # close previous
                self.xmlFile.write("</po>\n")
            self.filename=filename
        else:
            newFile=False
        
        # Handle start/end of files for XML output (not needed for text output)
        if self.xmlFile and newFile:
            # open new po
            poTag='<po name="%s">\n' % filename
            self.xmlFile.write(poTag) # Write to result

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
            msgstr.replace("\n", " ")
            msgstr=msgstr.replace("/", " ")
            msgstr=msgstr.replace(".", " ")
            msgstr=XML.sub(" ", msgstr) # Remove XML, HTML and CSS tags
            msgstr=ENTITTY.sub(" ", msgstr) # Remove docbook entities
            for word in msgstr.split():
                # Skip words with special caracters (URL, shell script, email adress..."
                if "@" in word or "+" in word or ":" in word or DIGIT.search(word) or word[0] in ("--", "/", "$") or word=="''":
                    continue
                # Clean word from accentuation
                word=cleanWord(word)
                # Skip place holder
                if word.startswith("{") and word.endswith("}"):
                    continue
                encodedWord=word.encode("utf-8") # Aspell wait for unicode encoded words
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
                                xmlError=spell_xml_error(msg, cat, word, suggestions)
                                self.xmlFile.writelines(xmlError)
                            else:
                                spell_error(msg, cat, word, [i.encode(self.encoding) for i in suggestions])
                    except UnicodeEncodeError:
                        print "Cannot encode this word in your codec (%s)" % self.encoding

    def finalize (self):
        if self.list is not None:
            #print "\n".join()
            print self.encoding
            print "\n".join([i.decode(self.encoding) for i in self.list])
        else:
            if self.nmatch:
                print "----------------------------------------------------"
                print "Total matching: %d" % self.nmatch
        if self.xmlFile:
            self.xmlFile.write("</po>\n")
            self.xmlFile.write("</pos>\n")
            self.xmlFile.close()

def cleanWord(word):
    """Clean word from any extra punctuation, trailing \n or accelerator check
    @param word: word to be cleaned
    @type word: unicode
    @return: word clean (unicode)"""
    word=word.strip("'")
    for remove in ("&", ".", "...", ";", ",", "\n", "(", ")", "%", "@", "_", "«", "»", "*", "[", "]", "|", "\\", "…", "=", "<", ">"):
        word=word.replace(remove, "")
    return word