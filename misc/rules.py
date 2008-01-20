# -*- coding: UTF-8 -*-

import re
from codecs import open
from time import time

from pology.misc.timeout import timed_out

"""Parse rule files and propose a convenient interface to rules"""

TIMEOUT=8 # Time in sec after which a rule processing is timedout

# Accent substitution dict
accents={}
accents[u"e"] = u"[%s]" % u"|".join([u'e', u'é', u'è', u'ê', u'E', u'É', u'È', u'Ê'])
accents[u"é"] = u"[%s]" % u"|".join([u'é', u'è', u'ê', u'É', u'È', u'Ê'])
accents[u"è"] = u"[%s]" % u"|".join([u'é', u'è', u'ê', u'É', u'È', u'Ê'])
accents[u"ê"] = u"[%s]" % u"|".join([u'é', u'è', u'ê', u'É', u'È', u'Ê'])
accents[u"a"] = u"[%s]" % u"|".join([u'a', u'à', u'â', u'A', u'À', u'Â'])
accents[u"à"] = u"[%s]" % u"|".join([u'à', u'â', u'À', u'Â'])
accents[u"â"] = u"[%s]" % u"|".join([u'à', u'â', u'À', u'Â'])
accents[u"u"] = u"[%s]" % u"|".join([u'u', u'ù', u'û', u'U', u'Ù', u'Û'])
accents[u"ù"] = u"[%s]" % u"|".join([u'ù', u'û', u'Ù', u'Û'])
accents[u"û"] = u"[%s]" % u"|".join([u'ù', u'û', u'Ù', u'Û'])
accentPattern=re.compile(u"@([%s])" % u"|".join(accents.keys()))

def loadRules(filePath):
    """Load rule file and return list of Rule objects
    @return: list of Rule object"""

    rules=[]
    inRule=False #Flag that indicate we are currently parsing a rule
    
    patternPattern=re.compile("\[(.*)\]")
    validPattern=re.compile("valid (.*)")
    #validPatternContent=re.compile('(.*?)="(.*?)"')
    validPatternContent=re.compile(r'(.*?)="(.*?(?<!\\))"')
    hintPattern=re.compile("""hint="(.*)""")
    
    pattern=u""
    valid=[]
    hint=u""

    try:
        for line in open(filePath, "r", "utf-8"):
            line=line.rstrip("\n")
            
            if line.startswith("#"):
                continue
            
            if line.strip()=="" and inRule:
                inRule=False
                rules.append(Rule(pattern, hint, valid))
                pattern=u""
                valid=[]
                hint=u""
                continue
                
            result=patternPattern.match(line)
            if result and not inRule:
                inRule=True
                pattern=result.group(1)
                continue
            
            result=validPattern.match(line)
            if result and inRule:
                valid.append(validPatternContent.findall(result.group(1)))
                continue
            
            result=hintPattern.match(line)
            if result and inRule:
                hint=result.group(1)
                continue 
    except IOError, e:
        print "Cannot read rule file at %s. Error was (%s)" % (filePath, e)

    return rules
 
def convert_entities(string):
    """Convert entities in string en returns it"""
    
    string=string.replace("&cr;", "\r")
    string=string.replace("&lf;", "\n")
    string=string.replace("&lt;", "<")
    string=string.replace("&gt;", ">")
    string=string.replace("&sp;", " ")
    string=string.replace("&quot;", '\"')
    string=string.replace("&lwb;", u"(?=[^\wéèêàâùûôÉÈÊÀÂÙÛÔ])")
    string=string.replace("&rwb;", u"(?<=[^\wéèêàâùûôÉÈÊÀÂÙÛÔ])")
    string=string.replace("&amp;", "&")
    string=string.replace("&unbsp;", u"\xa0")
    string=string.replace("&nbsp;", " ")
  
    return string
      
class Rule(object):
    """Represent a single rule"""
    
    def __init__(self, pattern, hint, valid=[]):
        """Create a rule
        @param pattern: valid regexp pattern that trigger the rule
        @type pattern: unicode
        @param hint: hint given to user when rule match
        @type hint: unicode
        @param valid: list of valid case that should not make rule matching
        @type valid: list of unicode key=value """
        
        # Define instance variable
        self.pattern=None # Compiled regexp into re.pattern object
        self.valid=None   # Parsed valid definition
        self.hint=None    # Hint message return to user
        self.count=0      # Number of time rule have been triggered
        self.time=0       # Total time of rule process calls
        self.span=(0, 0)  # start, end offset where rule match

        # Compile pattern
        self.rawPattern=pattern
        self.setPattern(pattern)
        
        self.hint=hint

        #Parse valid key=value arguments
        self.setValid(valid)

    def setPattern(self, pattern):
        """Compile pattern"""
        try:
            for accentMatch in accentPattern.finditer(pattern):
                letter=accentMatch.group(1)
                pattern=pattern.replace("@%s" % letter, accents[letter])
            self.pattern=re.compile(convert_entities(pattern))
        except Exception:
            print "Invalid pattern '%s', cannot compile" % pattern
        
    def setValid(self, valid):
        """Parse valid key=value arguments of valid list"""
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
                        #print value
                        value=re.compile(value)
                    entry[key]=value
                self.valid.append(entry)
            # TO be finished. Waiting for valid structure definition
            except ValueError:
                print "Invalid 'Valid' definition '%s'. Skipping" % item
                continue

    @timed_out(TIMEOUT)
    def process(self, msgstr, msgid, msgctxt, filename):
        """Process the given message
        @return: True if rule match, False if rule do not match, None if rule cannot be applied"""
        if self.pattern is None:
            print "Pattern not defined. Skipping rule"
            return
        
        begin=time()
        cancel=None  # Flag to indicate we have to cancel rule triggering. None indicate rule does not match

        #print "working on pattern: %s" % self.rawPattern
        #print "with msg:%s" % msg
        patternMatches=self.pattern.finditer(msgstr)

        for patternMatch in patternMatches:
            cancel=False
            self.span=patternMatch.span()

            # Rule pattern match. Now see if a valid exception exists
            for entry in self.valid:
                #print "E"
                before=False
                after=False
                if entry.has_key("file"):
                    if entry["file"]!=filename:
                        continue # This valid entry does not apply to this file
                if entry.has_key("ctx"):
                    if not entry["ctx"].match(msgctxt):
                        continue # This valid entry does not apply to this context
                #process valid here
                if entry.has_key("before"):
                    #print "before..."
                    beforeMatches=re.finditer(entry["before"], msgstr)
                    for beforeMatch in beforeMatches:
                        #print "B(%s)" % entry["before"],
                        #print "before match %s - pattern match %s" % (beforeMatch.start(), patternMatch.end())
                        if beforeMatch.start()==patternMatch.end():
                            before=True
                            break
                if entry.has_key("after"):
                    #print "after..."
                    afterMatches=re.finditer(entry["after"], msgstr)
                    for afterMatch in afterMatches:
                        #print "A(%s)" % entry["after"],
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
            self.time+=1000*(time()-begin)
            if cancel:
                # Rule match but was canceled by a "valid" expression
                return False
            else:
                # Rule match, return hint
                return True