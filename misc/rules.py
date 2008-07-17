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
from pology import rootdir
from pology.misc.config import strbool
from pology.misc.report import warning

TIMEOUT=8 # Time in sec after which a rule processing is timeout


def printStat(rules, nmatch):
    """Print rules match statistics
    @param rules: list of rule files
    @param nmatch: total number of matched items
    """
    if nmatch:
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
    l10nDir=join(rootdir(), "l10n") # Base of all language specific things

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

    class IdentError (Exception): pass

    rules=[]
    inRule=False #Flag that indicate we are currently parsing a rule bloc
    inGroup=False #Flag that indicate we are currently parsing a validGroup bloc
    
    patternPattern=re.compile("\[(.*)\](i?)")
    patternPatternMsgid=re.compile("\{(.*)\}(i?)")
    validPattern=re.compile("valid (.*)")
    #validPatternContent=re.compile('(.*?)="(.*?)"')
    validPatternContent=re.compile(r'(.*?)="(.*?(?<!\\))"')
    hintPattern=re.compile('''hint="(.*)"''')
    identPattern=re.compile('''id="(.*)"''')
    disabledPattern=re.compile('''disabled="(.*)"''')
    validGroupPattern=re.compile("""validGroup (.*)""")
    
    pattern=u""
    valid=[]
    hint=u""
    ident=None
    disabled=False
    onmsgid=False
    casesens=True
    validGroup={}
    validGroupName=u""
    identLines={}
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
                    rules.append(Rule(pattern, hint, valid, accents, stat, casesens, onmsgid, ident, disabled))
                    pattern=u""
                    hint=u""
                    ident=None
                    disabled=False
                    onmsgid=False
                    casesens=True
                elif inGroup:
                    inGroup=False
                    validGroup[validGroupName]=valid
                    validGroupName=u""
                valid=[]
                continue
            
            # Begin of rule (pattern)
            result=(patternPattern.match(line) or patternPatternMsgid.match(line))
            if result and not inRule:
                inRule=True
                pattern=result.group(1)
                onmsgid=result.group(0).startswith("{")
                casesens=("i" not in result.group(2))
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
            
            # Rule identifier
            result=identPattern.match(line)
            if result and inRule:
                ident=result.group(1)
                if ident in identLines:
                    raise IdentError(ident, identLines[ident])
                identLines[ident]=i
                continue
            
            # Whether rule is disabled
            result=disabledPattern.match(line)
            if result and inRule:
                disabled=strbool(result.group(1))
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

    except IdentError, e:
        warning("Identifier error in rule file: '%s' at %s:%d "
                "previously encountered at :%d"
                % (e.args[0], filePath, i, e.args[1]))
    except IOError, e:
        warning("Cannot read rule file at %s. Error was (%s)" % (filePath, e))
    except KeyError, e:
        warning("Syntax error in rule file %s:%d\n%s" % (filePath, i, e))

    # TODO: Make sure all identifiers (by id="..." fields) are unique.

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
    
    def __init__(self, pattern, hint, valid=[], accents=None, stat=False, casesens=True, onmsgid=False, ident=None, disabled=False):
        """Create a rule
        @param pattern: valid regexp pattern that trigger the rule
        @type pattern: unicode
        @param hint: hint given to user when rule match
        @type hint: unicode
        @param valid: list of cases that should make or not make rule matching
        @param accents: specific language accents dictionary to use.
        @type valid: list of unicode key=value
        @param casesens: whether regex matching will be case-sensitive
        @type casesens: bool
        @param onmsgid: whether the rule is for msgid (msgstr otherwise)
        @type onmsgid: bool
        @param ident: rule identifier
        @type ident: unicode or C{None}
        @param disabled: whether rule is disabled
        @type disabled: bool
        """

        # Define instance variable
        self.pattern=None # Compiled regexp into re.pattern object
        self.valid=None   # Parsed valid definition
        self.hint=None    # Hint message return to user
        self.ident=None    # Rule identifier
        self.disabled=False # Whether rule is disabled
        self.accents=accents # Accents dictionary
        self.count=0      # Number of time rule have been triggered
        self.time=0       # Total time of rule process calls
        self.span=(0, 0)  # start, end offset where rule match
        self.stat=stat    # Wheter to gather stat or not. Default is false (10% perf hit due to time() call)
        self.casesens=casesens # Whether regex matches are case-sensitive
        self.onmsgid=onmsgid # Whether to match rule on msgid

        # Get accentMatch from accent dictionary
        if self.accents:
            if self.accents.has_key("pattern"):
                self.accentPattern=self.accents["pattern"]
            else:
                print "Accent dictionary does not have pattern. Disabled it"
                self.accents=None

        # Flags for regex compilation.
        self.reflags=re.U
        if not self.casesens:
            self.reflags|=re.I

        # Compile pattern
        self.rawPattern=pattern
        self.setPattern(pattern)
        
        self.hint=hint
        self.ident=ident
        self.disabled=disabled

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
            self.pattern=re.compile(convert_entities(pattern), self.reflags)
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
                    bkey = key
                    if key.startswith("!"):
                        bkey = key[1:]
                    if bkey not in ("file", "after", "before", "ctx", "msgid", "msgstr"):
                        print "Invalid keyword '%s' in valid definition. Skipping" % key
                        continue
                    value=convert_entities(value)
                    if bkey in ("after", "before", "ctx", "msgid", "msgstr"):
                        # Compile regexp
                        value=re.compile(value, self.reflags)
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

        if not self.onmsgid:
            text = msgstr
        else:
            text = msgid

        cancel=None  # Flag to indicate we have to cancel rule triggering. None indicate rule does not match

        patternMatches=self.pattern.finditer(text)

        for patternMatch in patternMatches:
            self.span=patternMatch.span()

            # Rule pattern match. Now see if a valid exception exists
            # First validity entry that matches invokes exception.
            cancel=False
            for entry in self.valid:

                # All keys within a validity entry must match for the
                # entry to match as whole.
                cancel = True
                for key, value in entry.iteritems():
                    bkey = key
                    invert = False
                    if key.startswith("!"):
                        bkey = key[1:]
                        invert = True

                    if bkey == "file":
                        match = value == filename
                        if invert: match = not match
                        if not match:
                            cancel = False
                            break 

                    elif bkey == "after":
                        # Search up to the match to avoid need for lookaheads.
                        afterMatches = value.finditer(text, 0, patternMatch.start())
                        found = False
                        for afterMatch in afterMatches:
                            if afterMatch.end() == patternMatch.start():
                                found = True
                                break
                        if invert: found = not found
                        if not found:
                            cancel = False
                            break 

                    elif bkey == "before":
                        # Search from the match to avoid need for lookbehinds.
                        beforeMatches = value.finditer(text, patternMatch.end())
                        found = False
                        for beforeMatch in beforeMatches:
                            if beforeMatch.start() == patternMatch.end():
                                found = True
                                break
                        if invert: found = not found
                        if not found:
                            cancel = False
                            break 

                    elif bkey == "ctx":
                        match = value.search(msgctxt)
                        if invert: match = not match
                        if not match:
                            cancel = False
                            break 

                    elif bkey == "msgid":
                        match = value.search(msgid)
                        if invert: match = not match
                        if not match:
                            cancel = False
                            break 

                    elif bkey == "msgstr":
                        match = value.search(msgstr)
                        if invert: match = not match
                        if not match:
                            cancel = False
                            break 

                if cancel:
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
