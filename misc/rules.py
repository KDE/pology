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

    # Directives affecting all the rules.
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

An example rule, to fail a message when the original part contains the word
"foo" and the translation does not contain "bar", except in PO catalog
"qwyx" where it should contain "baz" instead, would be::

    # A contrieved example rule.
    {\\bfoo}i
    valid msgstr="\\bbar"
    valid cat="qwyx" msgstr="\\bbaz"
    hint="Translate 'foo' with 'bar' (only in qwyx.po use 'baz')"

The elements of a rule are detailed in the following.

Trigger Pattern
===============

Trigger pattern is a regular expression, which can be given within curly or
square brackets, C{{...}} or C{[...]}, if the intention is to match
the original or translation parts of the message, respectively.
Following the brackets there may the optional match-modifier character C{i},
which indicates case-insensitive matching for I{all} the patterns
in the rule (default is case-sensitive).

This was the shorthand notation of the trigger pattern. The more verbose
notation is C{*<part>/<regex>/<flags>}, where for separation instead of the slash (C{/}) any other non-letter character can be used consistently.
This notation is needed when some other part of the message except
the original and translation is to be matched, or when using brackets would
cause balancing issues (e.g. when a closing curly bracket without
the opening one is a part of the match for the original text).
For all messages, C{<part>} can be one of the keywords: C{msgid}, C{msgstr},
C{msgctxt}.
E.g. C{{\\bfoo}i} is equivalent to C{*msgid/\\bfoo/i}.

For plural messages, C{msgid/.../} (and conversely C{{...}} matches in
either the C{msgid} or C{msgid_plural} fields, whereas C{msgstr}
(and C{[...]}) in any of the C{msgstr} fields. That is, there is an
implied boolean OR relationship when matching in corresponding groups.
If particular among these fields are wanted, the following keywords
can be used instead: C{msgid_singular}, C{msgid_plural}, C{msgstr_<N>},
where C{N} is a number corresponding to the index of C{msgstr} field.

The trigger pattern is the main element of the rule; if it matches,
the message is by default considered failed by the rule. Tests that follow
in subdirectives are there to pass the message if additional conditions
are met.

Subdirectives
=============

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
  - C{span}: passes if the part of the text matched by the trigger pattern
        is matched by this regular expression as well
  - C{before}: passes if the part of the text matched by the trigger pattern
        is placed exactly before the part matched by this regular expression
  - C{after}: passes if the part of the text matched by the trigger pattern
        is placed exactly after the part matched by this regular expression
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

Global Directives
=================

Global directives are typically placed at the beginning of a rule file,
before any rules, and are used to define common elements for rules to source,
or to set state for all rules below them. Global directives can also be placed
in the middle of the rule file, between two rules, when they affect all the
rules that follow.

One global directive is C{validGroup}, which defines common groups of
C{valid} directives, which can be sourced by any rule::

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

Another global directive is to set the specific environment for the rules
that follow (unless overriden with namesake rule subdirective)::

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

Quoting and Escaping
====================

Similar as with the verbose notation for the trigger pattern,
any quoted value may consistently use any other character other than
the double quote (single quote, slash, etc.) Literal quote inside
the value can also be escaped using the backslash.
The values of fields that are regular expressions are sent to the regular
expression engine without resolving any escape sequences other
than for the quote character itself.

@author: Sébastien Renard <sebastien.renard@digitalfox.org>
@license: GPLv3
"""

import re
from codecs import open
from time import time
from os.path import dirname, basename, isdir, join
from os import listdir
import sys
from locale import getlocale

from pology.misc.timeout import timed_out
from pology.misc.colors import BOLD, RED, RESET
from pology import rootdir
from pology.misc.report import warning, error

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


def loadRules(lang, stat, env=None, envOnly=False, ruleFiles=None):
    """Load rules for a given language
    @param lang: lang as a string in two caracter (i.e. fr). If none or empty, try to autodetect language
    @param stat: stat is a boolean to indicate if rule should gather count and time execution
    @param env: also load rules applicable in this environment
    @param envOnly: load only rules applicable in the given environment
    @param ruleFiles: a list of rule files to load instead of internal
    @return: list of rules objects or None if rules cannot be found (with complaints on stdout)
    """
    ruleDir=""             # Rules directory
    rules=[]               # List of rule objects
    l10nDir=join(rootdir(), "l10n") # Base of all language specific things

    # Detect language
    #TODO: use PO language header once it has been implemented
    if ruleFiles is not None:
        if not lang:
            error("language must be explicitly given when using external rules")
        print "Using external %s rules" % lang
    else:
        if lang:
            ruleDir=join(l10nDir, lang, "rules")
            print "Using %s rules" % lang
        else:
            # Try to autodetect language
            languages=[d for d in listdir(l10nDir) if isdir(join(l10nDir, d, "rules"))]
            print "Rules available in the following languages: %s" % ", ".join(languages)
            for lang in languages:
                if lang in sys.argv[-1] or lang in getlocale()[0]:
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
            error("The rule directory is not a directory or is not accessible")
    
    # Find accents substitution dictionary
    try:
        m=__import__("pology.l10n.%s.accents" % lang, globals(), locals(), [""])
        accents=m.accents
    except ImportError:
        print "No accents substitution dictionary found for %s language" % lang
        accents=None
    for ruleFile in ruleFiles:
        rules.extend(loadRulesFromFile(ruleFile, accents, stat))

    # Remove rules with specific but different to given environment,
    # or any rule not in given environment in environment-only mode.
    srules=[]
    for rule in rules:
        if envOnly and rule.environ!=env:
            continue
        elif rule.environ and rule.environ!=env:
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


_rule_start = "*"

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

    valid=[]
    pattern=u""
    msgpart=""
    hint=u""
    ident=None
    disabled=False
    casesens=True
    environ=None
    validGroup={}
    validGroupName=u""
    identLines={}
    globalEnviron=None
    i=0

    try:
        lines=open(filePath, "r", "UTF-8").readlines()
        lines.append("\n") # sentry line
        for line in lines:
            i+=1
            fields = _parseRuleLine(line)
            
            # End of rule bloc
            # FIXME: Remove 'not fields' when global directives too
            # start with something. This will eliminate rule separation
            # by empty lines, and skipping comment-only lines.
            if line.strip().startswith("#"):
                continue
            if not fields or fields[0][0] in (_rule_start,):
                if inRule:
                    inRule=False
                    rules.append(Rule(pattern, msgpart,
                                      hint=hint, valid=valid, accents=accents,
                                      stat=stat, casesens=casesens,
                                      ident=ident, disabled=disabled,
                                      environ=(environ or globalEnviron)))
                    pattern=u""
                    msgpart=""
                    hint=u""
                    ident=None
                    disabled=False
                    casesens=True
                    environ=None
                elif inGroup:
                    inGroup=False
                    validGroup[validGroupName]=valid
                    validGroupName=u""
                valid=[]
            
            if not fields:
                continue
            
            # Begin of rule (pattern)
            if fields[0][0]==_rule_start:
                inRule=True
                msgpart=fields[0][1]
                if msgpart not in _trigger_msgparts:
                    raise StandardError, \
                          "Unknown keyword '%s' in trigger pattern" % msgpart
                pattern=fields[1][0]
                for mmod in fields[1][1]:
                    if mmod not in _trigger_matchmods:
                        raise StandardError, \
                              "Unknown match modifier '%s' in trigger pattern" \
                              % mmod
                casesens=("i" not in fields[1][1])
            
            # valid line (for rule ou validGroup)
            elif fields[0][0]=="valid":
                if not inRule and not inGroup:
                    raise StandardError, \
                          "'%s' directive outside of rule or validity group" \
                          % "valid"
                valid.append(fields[1:])
            
            # Rule hint
            elif fields[0][0]=="hint":
                if not inRule:
                    raise StandardError, \
                          "'%s' directive outside of rule" % "hint"
                hint=fields[0][1]
            
            # Rule identifier
            elif fields[0][0]=="id":
                if not inRule:
                    raise StandardError, \
                          "'%s' directive outside of rule" % "id"
                ident=fields[0][1]
                if ident in identLines:
                    (prevLine, prevEnviron)=identLines[ident]
                    if prevEnviron==globalEnviron:
                        raise IdentError(ident, prevLine)
                identLines[ident]=(i, globalEnviron)
            
            # Whether rule is disabled
            elif fields[0][0]=="disabled":
                if not inRule:
                    raise StandardError, \
                          "'%s' directive outside of rule" % "disabled"
                disabled=True
            
            # Validgroup 
            elif fields[0][0]=="validGroup":
                if inGroup:
                    raise StandardError, \
                          "'%s' directive inside validity group" % "validGroup"
                if inRule:
                    # Use of validGroup directive inside a rule bloc
                    validGroupName=fields[1][0]
                    valid.extend(validGroup[validGroupName])
                else:
                    # Begin of validGroup
                    inGroup=True
                    validGroupName=fields[1][0]
            
            # Switch rule environment
            elif fields[0][0]=="environment":
                if inGroup:
                    raise StandardError, \
                          "'%s' directive inside validity group" % "environment"
                envName=fields[1][0]
                if inRule:
                    # Environment specification for current rule.
                    environ=envName
                else:
                    # Environment switch for rules that follow.
                    globalEnviron=envName
            
            else:
                raise StandardError, \
                      "unknown directive '%s'" % fields[0][0]

    except IdentError, e:
        warning("Identifier error in rule file: '%s' at %s:%d "
                "previously encountered at :%d"
                % (e.args[0], filePath, i, e.args[1]))
    except IOError, e:
        warning("Cannot read rule file at %s. Error was (%s)" % (filePath, e))
    except StandardError, e:
        warning("Syntax error in rule file %s:%d\n%s" % (filePath, i, e))

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


_trigger_msgparts = [
    # For matching in all messages.
    "msgctxt", "msgid", "msgstr",

    # For matching in plural messages part by part.
    "msgid_singular", "msgid_plural",
    "msgstr_0", "msgstr_1", "msgstr_2", "msgstr_3", "msgstr_4", "msgstr_5",
    "msgstr_6", "msgstr_7", "msgstr_8", "msgstr_9", # ought to be enough
]

_trigger_matchmods = [
    "i",
]

class Rule(object):
    """Represent a single rule"""

    _knownKeywords = set(("env", "cat", "span", "after", "before", "ctx", "msgid", "msgstr"))
    _regexKeywords = set(("span", "after", "before", "ctx", "msgid", "msgstr"))
    _listKeywords = set(("env", "cat"))

    def __init__(self, pattern, msgpart, hint=None, valid=[], accents=None,
                       stat=False, casesens=True, ident=None, disabled=False,
                       environ=None):
        """Create a rule
        @param pattern: valid regexp pattern that trigger the rule
        @type pattern: unicode
        @param msgpart: part of the message to be matched by C{pattern}
        @type msgpart: string
        @param hint: hint given to user when rule match
        @type hint: unicode
        @param valid: list of cases that should make or not make rule matching
        @param accents: specific language accents dictionary to use.
        @type valid: list of unicode key=value
        @param casesens: whether regex matching will be case-sensitive
        @type casesens: bool
        @param ident: rule identifier
        @type ident: unicode or C{None}
        @param disabled: whether rule is disabled
        @type disabled: bool
        @param environ: environment in which the rule applies
        @type environ: string or C{None}
        """

        # Define instance variable
        self.pattern=None # Compiled regexp into re.pattern object
        self.msgpart=msgpart # The part of the message to match
        self.valid=None   # Parsed valid definition
        self.hint=None    # Hint message return to user
        self.ident=None    # Rule identifier
        self.disabled=False # Whether rule is disabled
        self.accents=accents # Accents dictionary
        self.count=0      # Number of time rule have been triggered
        self.time=0       # Total time of rule process calls
        self.stat=stat    # Wheter to gather stat or not. Default is false (10% perf hit due to time() call)
        self.casesens=casesens # Whether regex matches are case-sensitive
        self.environ=None # Environment in which to apply the rule

        if msgpart not in _trigger_msgparts:
            raise StandardError, \
                  "Unknown message part '%s' for rule's main pattern" % msgpart

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
            print "Invalid pattern '%s', disabling rule" % pattern
            self.disabled=True
        
    def setValid(self, valid):
        """Parse valid key=value arguments of valid list
        @param valid: valid line as an unicode string"""
        self.valid=[]
        for item in valid:
            try:
                entry=[] # Empty valid entry
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
                    entry.append((key, value))
                self.valid.append(entry)
            except Exception:
                print "Invalid 'Valid' definition '%s'. Skipping" % item
                continue

    #@timed_out(TIMEOUT)
    def process (self, msg, cat, env=None, nofilter=False):
        """
        Apply rule to the message.

        If the rule matches, I{highlight specification} of offending spans is
        returned (see L{report_msg_content<misc.report.report_msg_content>});
        otherwise an empty list.

        Rule will normally apply its own filters to the message before
        matching (on a local copy, the original message will not be affected).
        If the message is already appropriately filtered, this self-filtering
        can be prevented by setting C{nofilter} to {True}.

        @param msg: message to which the texts belong
        @type msg: instance of L{Message_base}
        @param cat: catalog to which the message belongs
        @type cat: L{Catalog}
        @param env: environment in which the rule is applied
        @type env: string
        @param nofilter: avoid filtering the message if C{True}
        @type nofilter: bool

        @return: highlight specification (may be empty list)
        """

        if self.pattern is None:
            warning("Pattern not defined, skipping rule.")
            return []

        # If this rule belongs to a specific environment,
        # and the operating environment is different from it,
        # cancel the rule immediately.
        if self.environ and env != self.environ:
            return []

        # Cancel immediately if the rule is disabled.
        if self.disabled:
            return []

        if self.stat:
            begin=time()

        # Apply own filters to the message if not filtered already.
        if not nofilter:
            msg = self._filter_message(msg)

        if 0: pass
        elif self.msgpart == "msgid":
            text_spec = [("msgid", 0, msg.msgid),
                         ("msgid_plural", 0, msg.msgid_plural)]
        elif self.msgpart == "msgstr":
            text_spec = [("msgstr", i, msg.msgstr[i])
                         for i in range(len(msg.msgstr))]
        elif self.msgpart == "msgctxt":
            text_spec = [("msgctxt", 0, msg.msgctxt)]
        elif self.msgpart == "msgid_singular":
            text_spec = [("msgid", 0, msg.msgid)]
        elif self.msgpart == "msgid_plural":
            text_spec = [("msgid_plural", 0, msg.msgid_plural)]
        elif self.msgpart.startswith("msgstr_"):
            item = int(self.msgpart.split("_")[1])
            text_spec = [("msgstr", item, msg.msgstr[item])]
        else:
            raise StandardError, \
                  "Unknown trigger keyword '%s' in rule"

        failed_spans = {}
        for part, item, text in text_spec:

            # Get full data per match.
            pmatches = list(self.pattern.finditer(text))
            if not pmatches:
                # Main pattern does not match anything, go to next text.
                continue

            # Test all matched segments.
            for pmatch in pmatches:
                # First validity entry that matches excepts the current segment.
                cancel = False
                for entry in self.valid:
                    if self._is_valid(pmatch, text, entry, msg, cat, env):
                        cancel = True
                        break
                if not cancel:
                    # Record the span of problematic segment.
                    skey = (part, item)
                    if skey not in failed_spans:
                        failed_spans[skey] = (part, item, [], text)
                    failed_spans[skey][2].append(pmatch.span())

        # Update stats for matched rules.
        self.count += 1
        if self.stat:
            self.time += 1000 * (time() - begin)

        return failed_spans.values()


    def _filter_message (self, msg):

        # FIXME.
        error("Message filtering by a rule not implemented yet")
        return msg


    def _is_valid (self, pmatch, text, ventry, msg, cat, env):

        # All keys within a validity entry must match for the
        # entry to match as whole.
        valid = True
        for key, value in ventry:
            bkey = key
            invert = False
            if key.startswith("!"):
                bkey = key[1:]
                invert = True

            if bkey == "env":
                match = env in value
                if invert: match = not match
                if not match:
                    valid = False
                    break

            elif bkey == "cat":
                match = cat.name in value
                if invert: match = not match
                if not match:
                    valid = False
                    break

            elif bkey == "span":
                found = value.search(pmatch.group(0)) is not None
                if invert: found = not found
                if not found:
                    valid = False
                    break

            elif bkey == "after":
                # Search up to the match to avoid need for lookaheads.
                afterMatches = value.finditer(text, 0, pmatch.start())
                found = False
                for afterMatch in afterMatches:
                    if afterMatch.end() == pmatch.start():
                        found = True
                        break
                if invert: found = not found
                if not found:
                    valid = False
                    break

            elif bkey == "before":
                # Search from the match to avoid need for lookbehinds.
                beforeMatches = value.finditer(text, pmatch.end())
                found = False
                for beforeMatch in beforeMatches:
                    if beforeMatch.start() == pmatch.end():
                        found = True
                        break
                if invert: found = not found
                if not found:
                    valid = False
                    break

            elif bkey == "ctx":
                match = value.search(msg.msgctxt)
                if invert: match = not match
                if not match:
                    valid = False
                    break

            elif bkey == "msgid":
                match = False
                for msgid in (msg.msgid, msg.msgid_plural):
                    match = value.search(msgid)
                    if match:
                        break
                if invert: match = not match
                if not match:
                    valid = False
                    break

            elif bkey == "msgstr":
                match = False
                for msgstr in msg.msgstr:
                    match = value.search(msgstr)
                    if match:
                        break
                if invert: match = not match
                if not match:
                    valid = False
                    break

        return valid


def _parseRuleLine (line):
    """
    Split a rule line into fields as list of (name, value) pairs.

    If a field name is followed by '=' or '=""', the field value will be
    an empty string. If there is no equal sign, the value will be C{None}.

    If the line is the trigger pattern, the name of the first field
    is going to be the "*", and its value the keyword of the message part
    to be matched; the name of the second field is going to be
    the pattern itself, and its value the string of match modifiers.
    """

    llen = len(line)
    fields = []
    p = 0
    in_modifiers = False

    while p < llen:
        while line[p].isspace():
            p += 1
            if p >= llen:
                break
        if p >= llen or line[p] == "#":
            break

        if len(fields) == 0 and line[p] in ("[", "{"):
            # Shorthand trigger pattern.
            bropn = line[p]
            brcls, fname = {"{": ("}", "msgid"),
                            "[": ("]", "msgstr")}[bropn]

            # Collect the pattern.
            # Look for the balanced closing bracket.
            p1 = p + 1
            balance = 1
            while balance > 0:
                p += 1
                if p >= llen:
                    break
                if line[p] == bropn:
                    balance += 1
                elif line[p] == brcls:
                    balance -= 1
            if balance > 0:
                raise StandardError, \
                      "Unbalanced '%s' in shorthand trigger pattern" % bropn
            fields.append((_rule_start, fname))
            fields.append((line[p1:p], ""))

            p += 1
            in_modifiers = True

        elif len(fields) == 0 and line[p] == _rule_start:
            # Verbose trigger pattern.
            p += 1
            while p < llen and line[p].isspace():
                p += 1
            if p >= llen:
                raise StandardError, \
                      "Missing match keyword in trigger pattern"

            # Collect the match keyword.
            p1 = p
            while line[p].isalnum() or line[p] == "_":
                p += 1
                if p >= llen:
                    raise StandardError, \
                          "Malformed trigger pattern"
            fname = line[p1:p]

            # Collect the pattern.
            while line[p].isspace():
                p += 1
                if p >= llen:
                    raise StandardError, \
                          "No pattern after the trigger keyword"
            quote = line[p]
            p1 = p + 1
            p = _findEndQuote(line, p)
            fields.append((_rule_start, fname))
            fields.append((line[p1:p], ""))

            p += 1
            in_modifiers = True

        elif in_modifiers:
            # Modifiers after the trigger pattern.
            p1 = p
            while not line[p].isspace():
                p += 1
                if p >= llen:
                    break
            pattern, pmods = fields[-1]
            fields[-1] = (pattern, pmods + line[p1:p])

        else:
            # Subdirective field.

            # Collect field name.
            p1 = p
            while not line[p].isspace() and line[p] != "=":
                p += 1
                if p >= llen:
                    break
            fname = line[p1:p]
            if not re.match(r"^!?[a-z][\w-]*$", fname):
                raise StandardError, "Invalid field name: %s" % fname

            if p >= llen or line[p].isspace():
                fields.append((fname, None))
            else:
                # Collect field value.
                p += 1 # skip equal-character
                if p >= llen or line[p].isspace():
                    fields.append(fname, "")
                else:
                    quote = line[p]
                    p1 = p + 1
                    p = _findEndQuote(line, p)
                    fvalue = line[p1:p]
                    fields.append((fname, fvalue))
                    p += 1 # skip quote

    return fields


def _findEndQuote (line, pos=0):
    """
    Find end quote to the quote at given position in the line.

    Character at the C{pos} position is taken as the quote character.
    Closing quote can be escaped with backslash inside the string,
    in which the backslash is removed in parsed string;
    backslash in any other position is considered ordinary.

    @param line: the line to parse
    @type line: string
    @param pos: position of the opening quote
    @type pos: int

    @return: position of the closing quote
    @rtype: int
    """

    quote = line[pos]
    epos = pos + 1

    llen = len(line)
    string = ""
    while epos < llen:
        c = line[epos]
        if c == "\\":
            epos += 1
            c2 = line[epos]
            if c2 != quote:
                string += c
            string += c2
        elif c == quote:
            break
        else:
            string += c
        epos += 1

    if epos == llen:
        raise StandardError, "Non-terminated quoted string: %s" % line[pos:]

    return epos

