# -*- coding: UTF-8 -*-

"""
Sieves messages with GNU aspell spell checker (http://aspell.net/)

@author: Sébastien Renard <sebastien.renard@digitalfox.org>
@license: GPLv3
"""

from pology.misc.colors import BOLD, RED, RESET
from pology.external.pyaspell import Aspell, AspellConfigError, AspellError
from locale import getdefaultlocale
import re, sys
from os.path import dirname, isfile, join
from codecs import open

# Regexp used to clean XML messages
XML=re.compile("<.*?>")
DIGIT=re.compile("\d")

class Sieve (object):
    """Process messages through the aspell spell checker"""
    
    def __init__ (self, options, global_options):
    
        self.nmatch = 0 # Number of match for finalize
        self.aspell=None # Instance of Aspell parser
        self.encoding=getdefaultlocale()[1] # Local encoding to encode aspell output
        self.list=None # If not None, only list of faulty word is display (to ease copy/paste into personal dictionary)
        self.ignoredContext=[] # List of all PO message context for which no spell check should be done

        if "lang" in options:
            options.accept("lang")
            self.lang=options["lang"]
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
            aspellOptions=(("lang", self.lang), ("mode", "sgml"), ("encoding", "utf-8"), ("personal-path", personalDict))

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

    def process (self, msg, cat):

        if msg.obsolete:
            return

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
                            print "-"*(len(msgstr)+8)
                            print BOLD+"%s:%d(%d)" % (cat.filename, msg.refline, msg.refentry)+RESET
                            #TODO: create a report function in the right place
                            #TODO: color in red part of context that make the mistake
                            print BOLD+"Faulty word: "+RESET+RED+word+RESET
                            suggestions=self.aspell.suggest(encodedWord)
                            if suggestions:
                                print BOLD+"Suggestion(s): "+RESET+", ".join([i.encode(self.encoding) for i in suggestions]) 
                            print
                    except UnicodeEncodeError:
                        print "Cannot encode this word in your codec (%s)" % self.encoding

    def finalize (self):
        if self.list is not None:
            print "\n".join(self.list)
        else:
            if self.nmatch:
                print "----------------------------------------------------"
                print "Total matching: %d" % self.nmatch

def cleanWord(word):
    """Clean word from any extra punctuation, trailing \n or accelerator check
    @param word: word to be cleaned
    @type word: unicode
    @return: word clean (unicode)"""
    for remove in ("&", ".", "...", ";", ",", "\n", "(", ")", "%", "@", "_", "«", "»", "*", "[", "]", "|", "\\"):
        word=word.replace(remove, "")
    return word