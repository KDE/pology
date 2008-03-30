# -*- coding: UTF-8 -*-

"""
Sieves messages with GNU aspell spell checker (http://aspell.net/)

@author: Sébastien Renard <sebastien.renard@digitalfox.org>
@license: GPLv3
"""

from pology.misc.colors import BOLD, RED, RESET
from pology.misc.pyaspell import Aspell
from locale import getdefaultlocale
import re, sys
from os.path import dirname, isfile, join

# Regexp used to clean XML messages
XML=re.compile("<.*?>")
DIGIT=re.compile("\d")

class Sieve (object):
    """Process messages through the aspell spell checker"""
    
    def __init__ (self, options, global_options):
    
        self.nmatch = 0 # Number of match for finalize
        self.aspell=None # Instance of Aspell parser
        self.encoding=getdefaultlocale()[1] # Local encoding to encode aspell output

        if "lang" in options:
            options.accept("lang")
            self.lang=options["lang"]
        else:
            self.lang="fr"
        
        personalDict=join(dirname(sys.argv[0]), "l10n", self.lang, "dict")
        if not isfile(personalDict):
            print "Personal KDE dictionnary is not available for your language"
            self.aspell=Aspell((("lang", self.lang), ("mode", "sgml"), ("encoding", "utf-8")))
        else:
            print "Using language specific KDE dictionnary (%s)" % personalDict
            self.aspell=Aspell((("lang", self.lang), ("mode", "sgml"), ("encoding", "utf-8"), ("personal-path", personalDict)))

    def process (self, msg, cat):

        if msg.obsolete:
            return

        for msgstr in msg.msgstr:
            #TODO: better handling of those exceptions (separate file ?)
            if "name" in msg.msgctxt.lower():
                continue
            msgstr=XML.sub(" ", msgstr.replace("\n", " ")) # Remove XML, HTML and CSS tags
            for word in msgstr.split():
                #TODO: also split on "/" separator
                #TODO: better handling of those exceptions (separate file ?)
                if "@" in word or "+" in word or ":" in word or DIGIT.search(word) or word[0] in ("--", "/", "$"):
                    continue
                word=cleanWord(word)
                encodedWord=word.encode("utf-8")
                spell=self.aspell.check(encodedWord)
                if spell is False:
                    try:
                        self.nmatch+=1
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
        if self.nmatch:
            print "----------------------------------------------------"
            print "Total matching: %d" % self.nmatch

def cleanWord(word):
    """Clean word from any extra punctuation, trailing \n or accelerator check
    @param word: word to be cleaned
    @type word: unicode
    @return: word clean (unicode)"""
    for remove in ("&", ".", "...", ",", "\n", "(", ")", "%", "@", "_", "«", "»", "*", "[", "]", "|"):
        word=word.replace(remove, "")
    return word