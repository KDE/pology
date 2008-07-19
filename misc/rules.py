# -*- coding: UTF-8 -*-

"""
Match messages by rules of arbitrary specificity.

A message-matching rule, represented by L{Rule} object, is a series of
pattern matches to be applied to the message, leading to the decision
of whether or not the rule as whole matches the message.
Patterns can be of different kinds, act on different parts of the message,
and be applied in a boolean-like combinations.
The idea behind rules is to detect messages faulty in some way,
hence when a rule matches it is said that it "fails the message",
and when it does not match, that it "passes the message".

L{Rule} objects can be constructed by the same code that uses them,
but the primary intended use is that of maintaining collections of
rules in external, special-format files, and loading them on demand.
For example, there may be a collection of rules that catches typical
ortography errors in a given language, or checks terminology, etc.
Such collections of language and translation-environment dependent rules
are maintained within Pology itself, in C{l10n/<lang>/rules/} directories.

The L{check-rules<sieve.check_rules>} sieve is normally used to apply rules
to messages in PO files, while in custom code function L{loadRulesFromFile}
can be used to load rules from an arbitrary rule file, and L{loadRules}
to fetch rules from Pology's internal rule files.

Rule Files
==========

Rule files are kept simple, to facilitate easy editing without
verbose syntax getting in the way. Rule file has the following layout::

    # Title of the rule collection.
    # Author name.
    # License.

    global-directive
    ...
    global-directive

    # Rule 1.
    trigger-pattern
    subdirective-1
    ...
    subdirective-n

    # Rule 2.
    trigger-pattern
    subdirective-1
    ...
    subdirective-n

    ...

    # End of rules

where the header (title, author, license) and footer comments are mandatory.
Rules are separated by a blank line, and each rule starts with the main
trigger pattern. #-comments always start from the beginning of the line.
Example rule, to fail a message when the original part contains the word
"foo" and the translation does not contain "bar", except in PO catalog
"qwyx" where it should contain "baz" instead, would be::

    # A contrieved example rule.
    {\\bfoo}i
    valid msgstr="\\bbar"
    valid cat="qwyx" msgstr="\\bbaz"
    hint="Translate 'foo' with 'bar' (only in qwyx.po use 'baz')"

Trigger pattern is a regular expression within curly or square brackets,
C{{...}} or C{[...]}, depending if it should be matched against original or
translation part of the message, respectively. Additionaly, following the
brackets there may be an C{i}-flag, to indicate case-insensitive matching
for all the patterns in the rule (default is case-sensitive).
The trigger pattern is the main element of the rule; tests that follow
in subdirectives are to amend the trigger pattern, to pass the message
even if the trigger pattern fails it.

There are several types of rule subdirectives. The main one is C{valid},
which provides additional tests to pass the message. These tests are
given by a list of C{name="pattern"} entries, which test different parts
of the message and in different ways. For a C{valid} directive to pass
the message all its tests must pass it, and if any of the C{valid}
directives passes the message, then the rule as whole passes it.
Effectively, this means the boolean AND relationship within a directive,
and OR across directives.

The following tests can be used within C{valid} directives:
  - C{msgid}: passes if the original text matches a regular expression
  - C{msgstr}: passes if the translation text matches a regular expression
  - C{ctx}: passes if the message context matches a regular expression
  - C{before}: passes if the part of the text matched by the trigger pattern
        is placed exactly before the part matched by this regular expression
  - C{after}: passes if the part of the text matched by the trigger pattern
        is placed exactly after the part matched by this regular expression
  - C{file}: passes if the PO file name is contained in this comma-separated
        list of file names
  - C{cat}: passes if the PO catalog name is contained in this
        comma-separated list of catalog names
  - C{env}: passes if the operating environment is contained in this
        comma-separated list of environment names

Each test can be negated by prefixing it with exclamation sign, e.g.
C{!cat="foo,bar"} will pass if catalog name is neither C{foo} nor C{bar}.
Tests are short-circuiting, so it is good for performance to put simple
string matching rules (e.g. C{cat}, C{env}) before more intensive
regular expression ones (C{msgid}, C{msgstr}, etc.)
For C{before} and C{after} tests, when there are several matched substrings,
by the trigger pattern and/or by the test patterns, then the test passes if
any two are in the requested order.

Subdirectives other than C{valid} set states and properties of the rule.
The property directives are written simply as C{property="value"}.
These include:
  - C{hint}: hint which may be shown to the user when the rule fails a message
  - C{id}: "almost" unique rule identifier (see part on rule environments)

State directives are given by the directive name, possibly followed by
keyword parameters: C{directive arg1 ...}. These are:
  - C{validGroup <groupname>}: source a predefined group of C{valid} directives
  - C{environment <envname>}: explicitly set the environment of the rule
  - c{disabled}: disable the rule, i.e. make it pass all messages

Global directives, which are typically placed at the beginning of a rule file,
before any rules, are used to define common elements for rules to source,
or to set state for all rules below them. One such directive is C{validGroup},
which defines common groups of C{valid} directives::

    # Global validity group.
    validGroup passIfQuoted
    valid after="“" before="”"
    valid after="‘" before="’"

    ....

    # Rule X.
    {...}
    validGroup passIfQuoted
    valid ...
    ...

    # Rule Y.
    {...}
    validGroup passIfQuoted
    valid ...
    ...

Another global directive is setting specific environment on all rules that
follow after it (unless overriden with namesake rule subdirective)::

    # Global environment.
    environment FOO

    ...

    # Rule X, belongs to FOO.
    {...}
    ...

    # Rule Y, overrides to BAR.
    {...}
    environment BAR
    ...

Rule Environments
=================

When there are no C{environment} directives in a rule file, either global or
as subdirectives, then all rules loaded from it are considered as being
environment-agnostic. This comes into picture when applying a rule, using
L{Rule.process} method, which may take an "operating environment" as argument.
If the operating environment is given and the rule is environment-agnostic,
it will try to fail or pass the message ignoring the operating environment.
However, if there was an C{environment} directive in the file which covered
the rule, i.e. the rule itself is now environment-specific, then it will try
to fail the message only if its environment matches the operating environment,
and otherwise it will pass it unconditionally.

Rule environments are used to control application of rules between
diverse translation environments, where some rules may be common, some
may be somewhat common, and some not common at all. In such a scenario,
common rules would be made environment-agnostic (i.e. not covered by
an C{environment} directive), while totally non-common rules would be
provided in separate rule files per environment, with one global
C{environment} directive in each.

The rules falling in between may be treated differently.
Sometimes it may be organizationally convenient to keep in a single file
rules from different environments, but still similar in some way;
then the environment can either be switched by a global directive in the middle
of the file, or rules may be given their own environment directives.
At other times, the rules are wholly similar, needing only a C{valid}
subdirective or two different across environments; then the C{valid}
directives for specific environments may be started with the C{env} test.

When mixing environment-agnostic and environment-specific rules, the rule
identifier, given by C{id} property subdirective, plays a special role.
If an environment-specific rule has the same identifier as
an environment-agnostic rule, and the operating environment is same as
that of the environment-specific rule, than L{loadRules} will "shadow"
the environment-agnostic rule, excluding it from its returned list of rules.
This is used when there is a rule common to most translation environments,
except for one or few outliers -- the outliers' rule and the common rule
to be shadowed should be given same identifiers.

The L{check-rules<sieve.check_rules>} sieve has the C{env} parameter to
specify the operating environment, when it will apply the rules according
to previous passages. This means that if the operating environment
is not specified, from sieve user's point of view all environment-specific
rules are simply ignored.

@author: Sébastien Renard <sebastien.renard@digitalfox.org>
@license: GPLv3
"""

import re
from codecs import open
from time import time
from os.path import dirname, basename, isdir, join
from os import listdir
import sys
from locale import getdefaultlocale

from pology.misc.timeout import timed_out
from pology.misc.colors import BOLD, RED, RESET
from pology import rootdir
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


def loadRules(lang, stat, env=None):
    """Load all rules of given language
    @param lang: lang as a string in two caracter (i.e. fr). If none or empty, try to autodetect language
    @param stat: stat is a boolean to indicate if rule should gather count and time execution
    @param env: also load rules applicable in this environment only
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

    # Remove rules with specific but different environment.
    srules=[]
    for rule in rules:
        if rule.environ and rule.environ!=env:
            continue
        srules.append(rule)
    rules=srules

    # When operating in a specific environment, for two rules with
    # same identifiers consider that the one in operating environment
    # overrides the one in different or non-specific environment.
    if env:
        identsThisEnv=set()
        for rule in rules:
            if rule.ident and rule.environ==env:
                identsThisEnv.add(rule.ident)
        srules=[]
        for rule in rules:
            if rule.ident and rule.environ!=env and rule.ident in identsThisEnv:
                continue
            srules.append(rule)
        rules=srules

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
    disabledPattern=re.compile('''disabled\\b''')
    validGroupPattern=re.compile("""validGroup (.*)""")
    environPattern=re.compile("""environment (.*)""")
    
    valid=[]
    pattern=u""
    hint=u""
    ident=None
    disabled=False
    onmsgid=False
    casesens=True
    environ=None
    validGroup={}
    validGroupName=u""
    identLines={}
    globalEnviron=None
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
                    rules.append(Rule(pattern, hint, valid, accents, stat,
                                      casesens, onmsgid, ident, disabled,
                                      environ or globalEnviron))
                    pattern=u""
                    hint=u""
                    ident=None
                    disabled=False
                    onmsgid=False
                    casesens=True
                    environ=None
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
                    (prevLine, prevEnviron)=identLines[ident]
                    if prevEnviron==globalEnviron:
                        raise IdentError(ident, prevLine)
                identLines[ident]=(i, globalEnviron)
                continue
            
            # Whether rule is disabled
            result=disabledPattern.match(line)
            if result and inRule:
                disabled=True
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
            
            # Switch rule environment
            result=environPattern.match(line)
            if result and not inGroup:
                envName=result.group(1).strip()
                if inRule:
                    # Environment specification for current rule.
                    environ=envName
                else:
                    # Environment switch for rules that follow.
                    globalEnviron=envName
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

    _knownKeywords = set(("env", "file", "cat", "after", "before", "ctx", "msgid", "msgstr"))
    _regexKeywords = set(("after", "before", "ctx", "msgid", "msgstr"))
    _listKeywords = set(("env", "file", "cat"))

    def __init__(self, pattern, hint, valid=[], accents=None, stat=False,
                       casesens=True, onmsgid=False, ident=None, disabled=False,
                       environ=None):
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
        @param environ: environment in which the rule applies
        @type environ: string or C{None}
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
        self.environ=None # Environment in which to apply the rule

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
        self.environ=environ

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
                    if bkey not in Rule._knownKeywords:
                        print "Invalid keyword '%s' in valid definition. Skipping" % key
                        continue
                    value=convert_entities(value)
                    if bkey in Rule._regexKeywords:
                        # Compile regexp
                        value=re.compile(value, self.reflags)
                    if bkey in Rule._listKeywords:
                        # List of comma-separated words
                        value=[x.strip() for x in value.split(",")]
                    entry[key]=value
                self.valid.append(entry)
            except Exception:
                print "Invalid 'Valid' definition '%s'. Skipping" % item
                continue

    #@timed_out(TIMEOUT)
    def process(self, msgstr, msg, cat, filename=None, env=None):
        """Process the given message
        @return: True if rule match, False if rule do not match, None if rule cannot be applied"""
        if self.pattern is None:
            print "Pattern not defined. Skipping rule"
            return

        # If this rule belongs to a specific environment,
        # and the operating environment is different from it,
        # cancel the rule immediately.
        if self.environ and env != self.environ:
            return False

        # Cancel immediately if the rule is disabled.
        if self.disabled:
            return False

        if self.stat: begin=time()

        # Since catalog knows its file path, it would not be strictly
        # nessesary to pass its filename as an argument;
        # but, os.path.basename eats a lot of performance (!?),
        # so use it only if filename has not been manually passed.
        if filename is None:
            filename=basename(cat.filename)

        if not self.onmsgid:
            text = msgstr
        else:
            text = msg.msgid

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

                    if bkey == "env":
                        match = env in value
                        if invert: match = not match
                        if not match:
                            cancel = False
                            break 

                    elif bkey == "cat":
                        match = cat.name in value
                        if invert: match = not match
                        if not match:
                            cancel = False
                            break 

                    elif bkey == "file":
                        match = filename in value
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
                        match = value.search(msg.msgctxt)
                        if invert: match = not match
                        if not match:
                            cancel = False
                            break 

                    elif bkey == "msgid":
                        match = value.search(msg.msgid)
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
