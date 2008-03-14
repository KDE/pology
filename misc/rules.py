# -*- coding: UTF-8 -*-

"""
Parse rule files and propose a convenient interface to rules.

@author: Sébastien Renard <sebastien.renard@digitalfox.org>
@license: GPLv3
"""

import re
from codecs import open
from time import time
from os.path import dirname, isdir, join
from os import listdir
import sys
from locale import getdefaultlocale

from pology.misc.timeout import timed_out
from pology.misc.colors import BOLD, RED, RESET

TIMEOUT=8 # Time in sec after which a rule processing is timeout

def printErrorMsg(msg, cat, rule, pluralId=0):
    """Print formated error message on screen
    @param msg: pology.file.message.Message object
    @param cat: pology.file.catalog.Catalog object
    @param rule: pology.misc.rules.Rule object
    @param pluralId: msgstr count in case of plural form. Default to 0"""
    msgstr=msg.msgstr[pluralId]
    msgtext=msg.to_string()
    msgtext=msgtext[0:msgtext.find('msgstr "')].rstrip()
    msgtext=msgtext[0:msgtext.find('msgstr[')].rstrip()
    for word in ("msgid", "msgctxt"):
        msgtext=msgtext.replace(word, BOLD+word+RESET)

    print "-"*(len(msgstr)+8)
    print BOLD+"%s:%d(%d)" % (cat.filename, msg.refline, msg.refentry)+RESET
    try:
        print msgtext
        print BOLD+'msgstr'+RESET+' "%s"' % (msgstr[0:rule.span[0]]+BOLD+RED+
                              msgstr[rule.span[0]:rule.span[1]]+RESET+
                              msgstr[rule.span[1]:])
        print "("+rule.rawPattern+")"+BOLD+RED+"==>"+RESET+BOLD+rule.hint+RESET
    except UnicodeEncodeError, e:
        print RED+("UnicodeEncodeError, cannot print message (%s)" % e)+RESET

def xmlErrorMsg(msg, cat, rule, pluralId=0):
    """Create and returns error message in XML format
    @param msg: pology.file.message.Message object
    @param cat: pology.file.catalog.Catalog object
    @param rule: pology.misc.rules.Rule object
    @param pluralId: msgstr count in case of plural form. Default to 0
    @return: XML message as a list of unicode string"""
    error=[]
    error.append("\t<error>\n")
    error.append("\t\t<line>%s</line>\n" % msg.refline)
    error.append("\t\t<refentry>%s</refentry>\n" % msg.refentry)
    error.append("\t\t<msgctxt><![CDATA[%s]]></msgctxt>\n" % msg.msgctxt)
    error.append("\t\t<msgid><![CDATA[%s]]></msgid>\n" % msg.msgid)
    error.append("\t\t<msgstr><![CDATA[%s]]></msgstr>\n" % msg.msgstr[pluralId])
    error.append("\t\t<start>%s</start>\n" % rule.span[0])
    error.append("\t\t<end>%s</end>\n" % rule.span[1])
    error.append("\t\t<pattern><![CDATA[%s]]></pattern>\n" % rule.rawPattern)
    error.append("\t\t<hint><![CDATA[%s]]></hint>\n" % rule.hint)
    error.append("\t</error>\n")
    return error

def printStat(rules, nmatch):
    """Print rules match statistics
    @param rules: list of rule files
    @param nmatch: total number of matched items
    """
    if nmatch:
        print "----------------------------------------------------"
        print "Total matching: %d" % nmatch
    stat=list(((r.rawPattern, r.count, r.time/r.count, r.time) for r in rules if r.count!=0 and r.stat is True))
    if stat:
        print "Rules stat (raw_pattern, calls, average time (ms), total time (ms)"
        stat.sort(lambda x, y: cmp(x[3], y[3]))
        for p, c, t, tt in stat:
            print "%-20s\t\t%6d\t\t%6.1f\t\t%6d" % (p, c, t, tt)


def loadRules(lang, stat):
    """Load all rules of given language
    @param lang: lang as a string in two caracter (i.e. fr). If none or empty, try to autodetect language
    @param stat: stat is a boolean to indicate if rule should gather count and time execution
    @return: list of rules objects or None if rules cannot be found (with complaints on stdout)
    """
    ruleFiles=[]           # List of rule files
    ruleDir=""             # Rules directory
    rules=[]               # List of rule objects
    l10nDir=join(dirname(sys.argv[0]), "l10n") # Base of all language specific things

    # Detect language
    #TODO: use PO language header once it has been implemented 
    if lang:
        ruleDir=join(l10nDir, lang, "rules")
        print "Using %s rules" % lang
    else:
        # Try to autodetect language
        languages=[d for d in listdir(l10nDir) if isdir(join(l10nDir, d, "rules"))]
        print "Rules available in the following languages: %s" % ", ".join(languages)
        for lang in languages:
            if lang in sys.argv[-1] or lang in getdefaultlocale()[0]:
                print "Autodetecting %s language" % lang
                ruleDir=join(l10nDir, lang, "rules")
                break
    
    if not ruleDir:
        print "Using default rule files (French)..."
        lang="fr"
        ruleDir=join(l10nDir, lang, "rules")
    if isdir(ruleDir):
        ruleFiles=[join(ruleDir, f) for f in listdir(ruleDir) if f.endswith(".rules")]
    else:
        print "The rule directory is not a directory or is not accessible"
    
    # Find accents substitution dictionary
    try:
        m=__import__("pology.l10n.%s.accents" % lang, globals(), locals(), [""])
        accents=m.accents
    except ImportError:
        print "No accents substitution dictionary found for %s lang" % lang
        accents=None
    for ruleFile in ruleFiles:
        rules.extend(loadRulesFromFile(ruleFile, accents, stat))
    
    return rules


def loadRulesFromFile(filePath, accents, stat):
    """Load rule file and return list of Rule objects
    @param filePath: full path to rule file
    @param accents: specific language l10n accents dictionary to use
    @param stat: stat is a boolean to indicate if rule should gather count and time execution
    @return: list of Rule object"""

    rules=[]
    inRule=False #Flag that indicate we are currently parsing a rule bloc
    inGroup=False #Flag that indicate we are currently parsing a validGroup bloc
    
    patternPattern=re.compile("\[(.*)\]")
    validPattern=re.compile("valid (.*)")
    #validPatternContent=re.compile('(.*?)="(.*?)"')
    validPatternContent=re.compile(r'(.*?)="(.*?(?<!\\))"')
    hintPattern=re.compile('''hint="(.*)"''')
    validGroupPattern=re.compile("""validGroup (.*)""")
    
    pattern=u""
    valid=[]
    hint=u""
    validGroup={}
    validGroupName=u""
    i=0

    try:
        for line in open(filePath, "r", "utf-8"):
            line=line.rstrip("\n")
            i+=1
            
            # Comments
            if line.startswith("#"):
                continue
            
            # End of rule bloc
            if line.strip()=="":
                if inRule:
                    inRule=False
                    rules.append(Rule(pattern, hint, valid, accents, stat))
                    pattern=u""
                    hint=u""
                elif inGroup:
                    inGroup=False
                    validGroup[validGroupName]=valid
                    validGroupName=u""
                valid=[]
                continue
            
            # Begin of rule (pattern)
            result=patternPattern.match(line)
            if result and not inRule:
                inRule=True
                pattern=result.group(1)
                continue
            
            # valid line (for rule ou validGroup)
            result=validPattern.match(line)
            if result and (inRule or inGroup):
                valid.append(validPatternContent.findall(result.group(1)))
                continue
            
            # Rule hint
            result=hintPattern.match(line)
            if result and inRule:
                hint=result.group(1)
                continue
            
            # Validgroup 
            result=validGroupPattern.match(line)
            if result and not inGroup:
                if inRule:
                    # Use of validGroup directive inside a rule bloc
                    validGroupName=result.group(1).strip()
                    valid.extend(validGroup[validGroupName])
                else:
                    # Begin of validGroup
                    inGroup=True
                    validGroupName=result.group(1).strip()
                    continue            

    except IOError, e:
        print "Cannot read rule file at %s. Error was (%s)" % (filePath, e)
    except KeyError, e:
        print "Syntax error in rule file %s:%s\n%s" % (filePath, i, e)

    return rules
 
def convert_entities(string):
    """Convert entities in string en returns it"""
    #TODO: use pology entities function instead of specific one
    string=string.replace("&cr;", "\r")
    string=string.replace("&lf;", "\n")
    string=string.replace("&lt;", "<")
    string=string.replace("&gt;", ">")
    string=string.replace("&sp;", " ")
    string=string.replace("&quot;", '\"')
    string=string.replace("&rwb;", u"(?=[^\wéèêàâùûôÉÈÊÀÂÙÛÔ])")
    string=string.replace("&lwb;", u"(?<=[^\wéèêàâùûôÉÈÊÀÂÙÛÔ])")
    string=string.replace("&amp;", "&")
    string=string.replace("&unbsp;", u"\xa0")
    string=string.replace("&nbsp;", " ")
  
    return string
      
class Rule(object):
    """Represent a single rule"""
    
    def __init__(self, pattern, hint, valid=[], accents=None, stat=False):
        """Create a rule
        @param pattern: valid regexp pattern that trigger the rule
        @type pattern: unicode
        @param hint: hint given to user when rule match
        @type hint: unicode
        @param valid: list of valid case that should not make rule matching
        @param accents: specific language accents dictionary to use.
        @type valid: list of unicode key=value """
        
        # Define instance variable
        self.pattern=None # Compiled regexp into re.pattern object
        self.valid=None   # Parsed valid definition
        self.hint=None    # Hint message return to user
        self.accents=accents # Accents dictionary
        self.count=0      # Number of time rule have been triggered
        self.time=0       # Total time of rule process calls
        self.span=(0, 0)  # start, end offset where rule match
        self.stat=stat    # Wheter to gather stat or not. Default is false (10% perf hit due to time() call)

        # Get accentMatch from accent dictionary
        if self.accents and self.accents.has_key("pattern"):
            self.accentPattern=self.accents["pattern"]
        else:
            print "Accent dictionary does not have pattern. Disabled it"
            self.accents=None

        # Compile pattern
        self.rawPattern=pattern
        self.setPattern(pattern)
        
        self.hint=hint

        #Parse valid key=value arguments
        self.setValid(valid)

    def setPattern(self, pattern):
        """Compile pattern
        @param pattern: pattern as an unicode string"""
        try:
            if self.accents:
                for accentMatch in self.accentPattern.finditer(pattern):
                    letter=accentMatch.group(1)
                    pattern=pattern.replace("@%s" % letter, self.accents[letter])
            self.pattern=re.compile(convert_entities(pattern))
        except Exception:
            print "Invalid pattern '%s', cannot compile" % pattern
        
    def setValid(self, valid):
        """Parse valid key=value arguments of valid list
        @param valid: valid line as an unicode string"""
        self.valid=[]
        for item in valid:
            try:
                entry={} # Empty valid entry
                for (key, value) in item:
                    key=key.strip()
                    if key not in ("file", "after", "before", "ctx", "msgid"):
                        print "Invalid keyword '%s' in valid definition. Skipping" % key
                        continue
                    value=convert_entities(value)
                    if key in ("before", "after", "ctx"):
                        # Compile regexp
                        value=re.compile(value)
                    entry[key]=value
                self.valid.append(entry)
            except Exception:
                print "Invalid 'Valid' definition '%s'. Skipping" % item
                continue

    #@timed_out(TIMEOUT)
    def process(self, msgstr, msgid, msgctxt, filename):
        """Process the given message
        @return: True if rule match, False if rule do not match, None if rule cannot be applied"""
        if self.pattern is None:
            print "Pattern not defined. Skipping rule"
            return
        
        if self.stat: begin=time()

        cancel=None  # Flag to indicate we have to cancel rule triggering. None indicate rule does not match

        patternMatches=self.pattern.finditer(msgstr)

        for patternMatch in patternMatches:
            cancel=False
            self.span=patternMatch.span()

            # Rule pattern match. Now see if a valid exception exists
            for entry in self.valid:
                before=False
                after=False
                if entry.has_key("file"):
                    if entry["file"]==filename:
                        if not entry.has_key("after") and not entry.has_key("before") and not entry.has_key("ctx"):
                            # This rule should not be processed for this file
                            cancel=True
                            break
                    else:
                        continue # This valid entry does not apply to this file    
                if entry.has_key("ctx"):
                    if entry["ctx"].match(msgctxt):
                        if not entry.has_key("after") and not entry.has_key("before") and not entry.has_key("file"):
                            # This rule should not be processed for this context
                            cancel=True
                            break
                    else:
                        continue # This valid entry does not apply to this context
                #process valid here
                if entry.has_key("before"):
                    beforeMatches=re.finditer(entry["before"], msgstr)
                    for beforeMatch in beforeMatches:
                        if beforeMatch.start()==patternMatch.end():
                            before=True
                            break
                if entry.has_key("after"):
                    afterMatches=re.finditer(entry["after"], msgstr)
                    for afterMatch in afterMatches:
                        if afterMatch.end()==patternMatch.start():
                            after=True
                            break
                if (entry.has_key("before") and entry.has_key("after") and before and after) \
                 or(entry.has_key("before") and not entry.has_key("after") and before) \
                 or(not entry.has_key("before") and entry.has_key("after") and after):
                    # We are in a valid context. Cancel rule triggering
                    cancel=True
                    break
        
        if cancel is None:
            # Rule does not match anything
            # Return and do not update stats
            return False
        else:
            # stat
            self.count+=1
            if self.stat : self.time+=1000*(time()-begin)
            if cancel:
                # Rule match but was canceled by a "valid" expression
                return False
            else:
                # Rule match, return hint
                return True