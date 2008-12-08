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
  - C{srcref}: passes if file path of one of the source references matches
        a regular expression
  - C{comment}: passes if any extracted or translator comment line matches
        a regular expression
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
  - C{head}: passes if the catalog header contains field/value combination;
        the format is C{<sep><field><sep><value>}, where C{<sep>} is
        an arbitrary separator character used consistently at both positions,
        and C{<field>} and C{<value>} are regular expressions on field name
        and value. Example: C{head="/Language.*/\\bsr"}

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

Files can be included into rule files using the C{include} directive::

    include file="foo.something"

If the file to be included is a relative path, it is taken as relative to
the file which includes it. One rule file should not include another
(with C{.rules} extension), as all rule files are sourced automatically.
Instead, an inclusion file should contain a subset of directives needed
in several rule files, such as filter sets.

Global directives are also used to set filters to apply to messages before
the rules are matched; these directives are detailed below.

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

Message Filtering
=================

It is frequently advantageous for a set of rules not to act on raw text
given by message fields, but on a suitably filtered variants.
For example, if rules are used for terminology checks, it would be good
to remove any markup from the text (e.g. for an C{<email>} tag not to
record as a real word missing proper translation).

Filters sets are created by issuing global C{addFilter*} directives::

    # Remove XML-like tags.
    addFilterRegex match="<.*?>" on="pmsgid,pmsgstr"
    # Remove long command-line options.
    addFilterRegex match="--[\w-]+" on="pmsgid,pmsgstr"

    # Rule A will act on a message filtered by previous two directives.
    {...}
    ...

    # Remove function calls like foo(x, y).
    addFilterRegex match="\w+\(.*?\)" on="pmsgid,pmsgstr"

    # Rule B will act on a message filtered by previous three directives.
    {...}
    ...

Filters are thus added cumulatively to the filter set, the current set
affecting all the rules beneath it. (Note that these examples are only
for illustration, there are more finely tuned filtering options to remove
markup or literals such as command line options.) C{addFilter*} directive
may also appear within a rule, when it adds only to the filter set for
that rule::

    # Rule C, with an additional filter just for itself.
    {...}
    addFilterRegex match="grep\(1\)" on="pmsgstr"
    ...

    # Rule D, sees only previous global filter additions.
    {...}
    ...

Every filter directive must have the C{on=} field, which lists parts of
the message or the rule to which the filter should apply. In the examples
above, C{pmsgid} and C{pmsgstr} indicate that the filter applies I{purely}
to msgid/msgstr, i.e. not taking into account rest of the message;
in comparison, C{msgid} and C{msgstr} would indicate that filter applies
to the same fields, but that it can also analyze the rest of the message
to decide its behavior. It depends on the filter directive which parts
it can state in the C{on=} field.

To remove a filter from the current set, the addition directive can give
filter a I{handle}, which is then given to the C{removeField} directive
to remove a filter::

    addFilterRegex match="<.*?>" on="pmsgid,pmsgstr" handle="tags"

    # Rule A, "tags" filter applies to it.
    {...}
    ...

    # Rule B, removes "tags" filter only for itself.
    {...}
    removeFilter handle="tags"
    ...

    # Rule C, "tags" filter applies to it again.
    {...}
    ...

    removeFilter handle="tags"

    # Rule D, "tags" filter does not apply to it and any following rule.
    {...}
    ...

Several filters may have the same handle, in which case a remove directive
removes them all from the current set. One filter can have several handles,
given by comma-separated in C{handle=} field, in which case it can be removed
by any of those handles. Likewise, C{handle=} field in remove directive can
state several handles by which to remove filters.
A remove directive within a rule influences the complete rule regardless
of where it is positioned (e.g. between two validity directives).

To completely clear filter set, C{clearFilters} directive is used, without
any fields. Like C{removeFilter}, it can be issued either globally, or
within a rule.

Parts of the message and the rule to which the filter may apply in general
(whereas the precise applicable subset depends on the filter type), given by
a comma-separate list in the C{on=} field, are:

  - C{msg}: filter applies to the complete message

  - C{msgid}: modifies only original fields (C{msgid}, C{msgid_plural}),
    but the precise behavior may depend on other parts of the message,
    e.g. on the presence of C{*-format} flags.

  - C{msgstr}: modifies only translation fields (C{msgstr} set),
    possibly depending on other parts of the mesage

  - C{pmsgid}: modifies only original fields, without considering
    other parts of the message

  - C{pmsgstr}: modifies only translation fields, without considering
    other parts of the message

  - C{pattern}: modifies all search patterns in the rule

A filter may be added or removed only in certain environments, specified
by the C{env=} field in C{addFilter*} and C{removeFilter} directives.

The following filters are currently available:

C{addFilterRegex}
-----------------

    Parts of the text to remove are determined by a regular expression.
    The pattern is given by the C{match=} field; if a replacement of
    the matched segment is wanted instead of full removal,
    the C{repl=} field may be used to specify the replacement string
    (which can include back-references)::

        # Replace %<number> format directives with a tilde in translation.
        addFilterRegex match="%\d+" repl="~" on="pmsgstr"

    Case-sensitivity of matching can be controlled by C{casesens=} field,
    see L{strbool<misc.config.strbool>} for boolean-like values it can use.
    By default, matching is case-sensitive.

    Applicable to C{pmsgid}, C{pmsgstr}, and C{pattern} parts.

C{addFilterHook}
----------------

    Hooks are functions with special signatures, defined in the submodules
    of L{pology.hook} module. The hook function to use is specified by the
    C{name=} field, the specification taking the form of
    C{[lang:]hook-module[/hook-function]}; optional C{lang} is given when
    the hook is language specific, in one of the C{pology.l10n.<lang>.hook}
    modules, and C{hook-function} when the function name in the hook module
    is not the default C{process()}.
    For example, to remove accelerator markers from GUI POs, possibly
    based on what each PO itself states the marker character to be,
    the following hook filter can be used::

        addFilterHook name="remove-subs/remove-accel-msg" on="msg"

    (see L{pology.hook.remove_subs.remove_accel_text} for details).

    It depends on the hook type to which parts of the message it can apply.
    Hooks of type F4A (C{(msg, cat) -> numerr}) must apply to C{msg},
    whereas F3A (C{(text, msg, cat) -> text}) can apply to C{msgid} and
    C{msgstr}; F3B and F3C hooks should be applied only to C{msgid} or
    C{msgstr}, respectively, to satisfy their type restrictions.
    Pure text hooks F1A (C{(text) -> text}) apply to C{pmsgid}, C{pmsgstr},
    and C{pattern}.

    Aside from hook functions, a hook module may provide I{hook factories}
    used to parametrize hook functions. Factory arguments can be given by
    the C{factory=} field, in the same form as they would be written when
    calling the factory from the code::

        addFilterHook name="remove-subs/remove-fmtdirs-msg-tick" \\
                      factory="'~'" on="msg"

    (see L{pology.hook.remove_subs.remove_fmtdirs_msg_tick} for details).

Cost of Filtering
-----------------

Filtering may be time expensive, and it normally is in real-life uses.
Therefore the implementation will try to assemble as little filter sets
as necessary, judging by their signatures -- a hash of ordering, type, and
fields of filters in the current set for a rule.
Likewise, L{check-rules<sieve.check_rules>} will apply one filter set only
once per message, distributing the appropriate filtered message to
a given rule.

This means that you should be conservative when adding and removing filters,
such to produce as little sets as really necessary.
For example, you may know that filters P and Q can be applied in any order,
and in one rule file give P followed by Q, but in another Q followed by P.
However, the implementation cannot know that the ordering does not matter,
so it will create two filter sets, and waste twice as much time in filtering.

For big filter sets which are needed in several rule files, it may be best
to split them out in a separate file and use C{include} directive
to include them into rule files.

Special Triggers
================

Regular expression matching of message fields is most of the time sufficient
as a trigger, and hence has the two succint notations provided.
But there are other trigger options, applicable like standard directives,
in the form of C{*<trigger_type> <field1>="<value1>"...}.

Every trigger can be given the field C{casesens=}, to control case-sensitivity
of pattern matching both in the trigger itself (if applicable), and in
other patterns in the rule (validity tests).
See L{strbool<misc.config.strbool>} for boolean-like values that can be used.
By default, matching is case-sensitive.

C{hook}
-------

    Like for filtering, a hook can serve as the rule trigger too.
    It is specified exactly like in the C{addFilterHook} directive,
    with C{name=}, C{factory=}, and C{on=} fields having the same meaning.
    The difference is in the type of hooks which are applicable in this
    context, which must be one of the validation types:
    V4A (C{(msg, cat) -> parts}) applies to C{msg} part as given by
    the C{on=} field), V3A (C{(text, msg, cat) -> spans}) applies to either
    C{msgid} or C{msgstr}, V3B and V3C to strictly C{msgid} or C{msgstr},
    respectively, and V1A (C{(text) -> spans}) to C{pmsgid} or C{pmsgstr}.
    Also unlike with filter hooks, C{on=} field can state only one
    message part to apply the validation hook to, not a comma-separated list.

    An example rule with a test hook as the trigger would be::

        *hook name="ui-references/check-ui" on="msgstr"
        id="check-ui-refs"
        hint="some UI references cannot be validated"

    (see L{hook.ui_references.check_ui} for details).

Quoting and Escaping
====================

Similar as with the verbose notation for the trigger pattern,
any quoted value may consistently use any other character other than
the double quote (single quote, slash, etc.) Literal quote inside
the value can also be escaped using the backslash.
The values of fields that are regular expressions are sent to the regular
expression engine without resolving any escape sequences other
than for the quote character itself.

A line is continued by a backslash in the last column.

@author: Sébastien Renard <sebastien.renard@digitalfox.org>
@license: GPLv3
"""

import re
from codecs import open
from time import time
from os.path import dirname, basename, isdir, join, isabs
from os import listdir
import sys
from locale import getlocale

from pology.misc.timeout import timed_out
from pology.misc.colors import BOLD, RED, RESET
from pology import rootdir
from pology.misc.report import report, warning, error
from pology.misc.config import strbool
from pology.misc.langdep import get_hook_lreq, split_req
from pology.file.message import MessageUnsafe
from pology.misc.tabulate import tabulate

TIMEOUT=8 # Time in sec after which a rule processing is timeout


def printStat(rules, nmatch):
    """Print rules match statistics
    @param rules: list of rule files
    @param nmatch: total number of matched items
    """
    if nmatch:
        report("Total problems detected by rules: %d" % nmatch)
    statRules=[r for r in rules if r.count!=0 and r.stat is True]
    if statRules:
        statRules.sort(lambda x, y: cmp(x.time, y.time))
        data=[]
        rown=[r.displayName for r in statRules]
        data.append([r.count for r in statRules])
        data.append([r.time/r.count*1000 for r in statRules])
        totTimeMsg=sum(data[-1])/1000
        data.append([r.time for r in statRules])
        totTime=sum(data[-1])
        data.append([r.time/totTime*100 for r in statRules])
        report("Rule application statistics:")
        coln=["calls", "avg-time [ms]", "tot-time [s]", "time-share"]
        dfmt=[   "%d",           "%.3f",          "%.1f",     "%.2f%%"]
        report(tabulate(data, rown=rown, coln=coln, dfmt=dfmt,
                        colorized=sys.stdout.isatty()))
        report("Total application time [s]: %.1f" % (totTime))
        report("Average application time per message [ms]: %.1f"
               % (totTimeMsg*1000))


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
    
    seenMsgFilters = {}
    for ruleFile in ruleFiles:
        rules.extend(loadRulesFromFile(ruleFile, stat, env, seenMsgFilters))

    # Remove rules with specific but different to given environment,
    # or any rule not in given environment in environment-only mode.
    # FIXME: This should be moved to loadRulesFromFile.
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

def loadRulesFromFile(filePath, stat, env=None, seenMsgFilters={}):
    """Load rule file and return list of Rule objects
    @param filePath: full path to rule file
    @param stat: stat is a boolean to indicate if rule should gather count and time execution
    @param env: environment in which the rules are to be applied
    @param seenMsgFilters: dictionary of previously encountered message
        filter functions, by their signatures; to avoid constructing
        same filters over different files
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
    globalMsgFilters=[]
    globalRuleFilters=[]
    msgFilters=None
    ruleFilters=None
    seenRuleFilters={}
    triggerFunc=None
    lno=0

    try:
        lines=open(filePath, "r", "UTF-8").readlines()
        lines.append("\n") # sentry line
        fileStack=[]
        while True:
            while lno >= len(lines):
                if not fileStack:
                    lines = None
                    break
                lines, filePath, lno = fileStack.pop()
            if lines is None:
                break
            lno += 1
            fields, lno = _parseRuleLine(lines, lno)

            # End of rule bloc
            # FIXME: Remove 'not fields' when global directives too
            # start with something. This will eliminate rule separation
            # by empty lines, and skipping comment-only lines.
            if lines[lno - 1].strip().startswith("#"):
                continue
            if not fields or fields[0][0] in (_rule_start,):
                if inRule:
                    inRule=False

                    if msgFilters is None:
                        msgFilters = globalMsgFilters
                    if ruleFilters is None:
                        ruleFilters = globalRuleFilters
                    # Use previously assembled filter with the same signature,
                    # to be able to compare filter functions by "is".
                    msgFilterSig = _filterFinalSig(msgFilters)
                    msgFilterFunc = seenMsgFilters.get(msgFilterSig)
                    if msgFilterFunc is None:
                        msgFilterFunc = _msgFilterComposeFinal(msgFilters)
                        seenMsgFilters[msgFilterSig] = msgFilterFunc
                    ruleFilterSig = _filterFinalSig(ruleFilters)
                    ruleFilterFunc = seenRuleFilters.get(ruleFilterSig)
                    if ruleFilterFunc is None:
                        ruleFilterFunc = _ruleFilterComposeFinal(ruleFilters)
                        seenRuleFilters[ruleFilterSig] = ruleFilterFunc

                    rules.append(Rule(pattern, msgpart,
                                      hint=hint, valid=valid,
                                      stat=stat, casesens=casesens,
                                      ident=ident, disabled=disabled,
                                      environ=(environ or globalEnviron),
                                      mfilter=msgFilterFunc,
                                      rfilter=ruleFilterFunc,
                                      trigger=triggerFunc))
                    pattern=u""
                    msgpart=""
                    hint=u""
                    ident=None
                    disabled=False
                    casesens=True
                    environ=None
                    msgFilters=None
                    ruleFilters=None
                    triggerFunc=None
                elif inGroup:
                    inGroup=False
                    validGroup[validGroupName]=valid
                    validGroupName=u""
                valid=[]
            
            if not fields:
                continue
            
            # Begin of rule (pattern or special)
            if fields[0][0]==_rule_start:
                inRule=True
                keyword=fields[0][1]
                if keyword in _trigger_msgparts:
                    msgpart=keyword
                    pattern=fields[1][0]
                    for mmod in fields[1][1]:
                        if mmod not in _trigger_matchmods:
                            raise SyntaxError, \
                                  "Unknown match modifier '%s' " \
                                  "in trigger pattern" % mmod
                    casesens=("i" not in fields[1][1])
                elif keyword in _trigger_specials:
                    casesens, rest = _triggerParseGeneral(fields[1:])
                    if keyword == "hook":
                        triggerFunc = _triggerFromHook(rest)
                else:
                    raise SyntaxError, \
                          "Unknown keyword '%s' in rule trigger" % tkeyw

            # valid line (for rule ou validGroup)
            elif fields[0][0]=="valid":
                if not inRule and not inGroup:
                    raise SyntaxError, \
                          "'%s' directive outside of rule or validity group" \
                          % "valid"
                valid.append(fields[1:])
            
            # Rule hint
            elif fields[0][0]=="hint":
                if not inRule:
                    raise SyntaxError, \
                          "'%s' directive outside of rule" % "hint"
                hint=fields[0][1]
            
            # Rule identifier
            elif fields[0][0]=="id":
                if not inRule:
                    raise SyntaxError, \
                          "'%s' directive outside of rule" % "id"
                ident=fields[0][1]
                if ident in identLines:
                    (prevLine, prevEnviron)=identLines[ident]
                    if prevEnviron==globalEnviron:
                        raise IdentError(ident, prevLine)
                identLines[ident]=(lno, globalEnviron)
            
            # Whether rule is disabled
            elif fields[0][0]=="disabled":
                if not inRule:
                    raise SyntaxError, \
                          "'%s' directive outside of rule" % "disabled"
                disabled=True
            
            # Validgroup 
            elif fields[0][0]=="validGroup":
                if inGroup:
                    raise SyntaxError, \
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
                    raise SyntaxError, \
                          "'%s' directive inside validity group" % "environment"
                envName=fields[1][0]
                if inRule:
                    # Environment specification for current rule.
                    environ=envName
                else:
                    # Environment switch for rules that follow.
                    globalEnviron=envName

            # Add or remove filters
            elif (   fields[0][0].startswith("addFilter")
                  or fields[0][0] in ["removeFilter", "clearFilters"]):
                # Select the proper filter lists on which to act.
                if inRule:
                    if msgFilters is None: # local filters not created yet
                        msgFilters = globalMsgFilters[:] # shallow copy
                    if ruleFilters is None:
                        ruleFilters = globalRuleFilters[:]
                    currentMsgFilters = msgFilters
                    currentRuleFilters = ruleFilters
                    currentEnviron = environ or globalEnviron
                else:
                    currentMsgFilters = globalMsgFilters
                    currentRuleFilters = globalRuleFilters
                    currentEnviron = globalEnviron

                if fields[0][0].startswith("addFilter"):
                    filterType = fields[0][0][len("addFilter"):]
                    handles, parts, fenvs, rest = _filterParseGeneral(fields[1:])
                    if fenvs is None and currentEnviron:
                        fenvs = [currentEnviron]
                    if filterType == "Regex":
                        func, sig = _filterCreateRegex(rest)
                    elif filterType == "Hook":
                        func, sig = _filterCreateHook(rest)
                    else:
                        raise SyntaxError, \
                              "Unknown filter directive '%s'" % fields[0][0]
                    msgParts = set(parts).difference(_filterKnownRuleParts)
                    if msgParts:
                        totFunc, totSig = _msgFilterSetOnParts(msgParts, func, sig)
                        currentMsgFilters.append([handles, fenvs, totFunc, totSig])
                    ruleParts = set(parts).difference(_filterKnownMsgParts)
                    if ruleParts and (env is None or env in fenvs):
                        totFunc, totSig = _ruleFilterSetOnParts(ruleParts, func, sig)
                        currentRuleFilters.append([handles, fenvs, totFunc, totSig])

                elif fields[0][0] == ("removeFilter"):
                    _filterRemove(fields[1:],
                                  (currentMsgFilters, currentRuleFilters), env)

                else: # remove all filters
                    if len(fields) != 1:
                        raise SyntaxError, \
                              "Expected no fields in " \
                              "all-filter removal directive"
                    # Must not loose reference to the selected lists.
                    while currentMsgFilters:
                        currentMsgFilters.pop()
                    while currentRuleFilters:
                        currentRuleFilters.pop()

            # Include another file
            elif fields[0][0] == "include":
                if inRule or inGroup:
                    raise SyntaxError, \
                          "'%s' directive inside a rule or group" % "include"
                fileStack.append((lines, filePath, lno))
                lines, filePath, lno = _includeFile(fields[1:], filePath)

            else:
                raise SyntaxError, \
                      "unknown directive '%s'" % fields[0][0]

    except IdentError, e:
        error("Identifier error in rule file: '%s' at %s:%d "
              "previously encountered at :%d"
              % (e.args[0], filePath, lno, e.args[1]))
    except IOError, e:
        error("Cannot read rule file at %s. Error was (%s)" % (filePath, e))
    except SyntaxError, e:
        error("Syntax error in rule file %s:%d\n%s" % (filePath, lno, e))

    return rules


def _checkFields (directive, fields, knownFields, mandatoryFields=set(),
                  unique=True):

    fieldDict = dict(fields)
    if unique and len(fieldDict) != len(fields):
        raise SyntaxError, \
              "Duplicate fields in '%s' directive" % directive

    if not isinstance(knownFields, set):
        knownFields = set(knownFields)
    unknownFields = set(fieldDict).difference(knownFields)
    if unknownFields:
        raise SyntaxError, \
              "Unknown fields in '%s' directive: %s" \
              % ", ".join(unknownFields)

    for name in mandatoryFields:
        if name not in fieldDict:
            raise SyntaxError, \
                  "Mandatory field '%s' missing in '%s' directive" \
                  % (name, directive)


def _includeFile (fields, includingFilePath):

    _checkFields("include", fields, ["file"], ["file"])
    fieldDict = dict(fields)

    relativeFilePath = fieldDict["file"]
    if isabs(relativeFilePath):
        filePath = relativeFilePath
    else:
        filePath = join(dirname(includingFilePath), relativeFilePath)

    if filePath.endswith(".rules"):
        warning("including one rules file into another, '%s' from '%s'"
                % (filePath, includingFilePath))

    lines=open(filePath, "r", "UTF-8").readlines()
    lines.append("\n") # sentry line

    return lines, filePath, 0


def _filterRemove (fields, filterLists, env):

    _checkFields("removeFilter", fields, ["handle", "env"], ["handle"])
    fieldDict = dict(fields)

    handleStr = fieldDict["handle"]

    fenvStr = fieldDict.get("env")
    if fenvStr is not None:
        fenvs = [x.strip() for x in fenvStr.split(",")]
        if not env or env not in fenvs:
            # We are operating in no environment, or operating environment
            # is not listed among the selected; skip removal.
            return

    handles = set([x.strip() for x in handleStr.split(",")])
    seenHandles = set()
    for flist in filterLists:
        k = 0
        while k < len(flist):
            commonHandles = flist[k][0].intersection(handles)
            if commonHandles:
                flist.pop(k)
                seenHandles.update(commonHandles)
            else:
                k += 1
    unseenHandles = handles.difference(seenHandles)
    if unseenHandles:
        raise SyntaxError, \
              "No filters with these handles to remove: %s" \
              % ", ".join(unseenHandles)


_filterKnownMsgParts = set([
    "msg", "msgid", "msgstr", "pmsgid", "pmsgstr",
])
_filterKnownRuleParts = set([
    "pattern",
])
_filterKnownParts = set(  list(_filterKnownMsgParts)
                        + list(_filterKnownRuleParts))

def _filterParseGeneral (fields):

    handles = set()
    parts = []
    envs = None

    rest = []
    for field in fields:
        name, value = field
        if name == "handle":
            handles = set([x.strip() for x in value.split(",")])
        elif name == "on":
            parts = [x.strip() for x in value.split(",")]
            unknownParts = set(parts).difference(_filterKnownParts)
            if unknownParts:
                raise SyntaxError, \
                      "Unknown parts for filter to act on: %s" \
                      % ", ".join(unknownParts)
        elif name == "env":
            envs = [x.strip() for x in value.split(",")]
        else:
            rest.append(field)

    if not parts:
        raise SyntaxError, \
              "No parts specified for the filter to act on"

    return handles, parts, envs, rest


def _msgFilterSetOnParts (parts, func, sig):

    chain = []
    parts = list(parts)
    parts.sort()
    for part in parts:
        if part == "msg":
            chain.append(_filterOnMsg(func))
        elif part == "msgstr":
            chain.append(_filterOnMsgstr(func))
        elif part == "msgid":
            chain.append(_filterOnMsgid(func))
        elif part == "pmsgstr":
            chain.append(_filterOnMsgstrPure(func))
        elif part == "pmsgid":
            chain.append(_filterOnMsgidPure(func))

    def composition (msg, cat):

        for func in chain:
            func(msg, cat)

    totalSig = sig + "\x04" + ",".join(parts)

    return composition, totalSig


def _filterFinalSig (filterList):

    sigs = [x[3] for x in filterList]
    finalSig = "\x05".join(sigs)

    return finalSig


def _msgFilterComposeFinal (filterList):

    if not filterList:
        return None

    fenvs_funcs = [(x[1], x[2]) for x in filterList]

    def composition (msg, cat, env):

        for fenvs, func in fenvs_funcs:
            # Apply filter if environment-agnostic or in operating environment.
            if fenvs is None or env in fenvs:
                func(msg, cat)

    return composition


def _filterOnMsg (func):

    def aggregate (msg, cat):

        func(msg, cat)

    return aggregate


def _filterOnMsgstr (func):

    def aggregate (msg, cat):

        for i in range(len(msg.msgstr)):
            tmp = func(msg.msgstr[i], msg, cat)
            if tmp is not None: msg.msgstr[i] = tmp

    return aggregate


def _filterOnMsgid (func):

    def aggregate (msg, cat):

        tmp = func(msg.msgid, msg, cat)
        if tmp is not None: msg.msgid = tmp
        tmp = func(msg.msgid_plural, msg, cat)
        if tmp is not None: msg.msgid_plural = tmp

    return aggregate


def _filterOnMsgstrPure (func):

    def aggregate (msg, cat):

        for i in range(len(msg.msgstr)):
            tmp = func(msg.msgstr[i])
            if tmp is not None: msg.msgstr[i] = tmp

    return aggregate


def _filterOnMsgidPure (func):

    def aggregate (msg, cat):

        tmp = func(msg.msgid)
        if tmp is not None: msg.msgid = tmp
        tmp = func(msg.msgid_plural)
        if tmp is not None: msg.msgid_plural = tmp

    return aggregate


def _ruleFilterSetOnParts (parts, func, sig):

    chain = []
    parts = list(parts)
    parts.sort()
    for part in parts:
        if part == "pattern":
            chain.append((_filterOnPattern(func), part))

    def composition (value, part):

        if part not in _filterKnownRuleParts:
            raise SyntaxError, \
                  "Requested to filter unknown rule part '%s'" % part

        for func, fpart in chain:
            if fpart == part:
                value = func(value)

        return value

    totalSig = sig + "\x04" + ",".join(parts)

    return composition, totalSig


def _ruleFilterComposeFinal (filterList):

    if not filterList:
        return None

    funcs = [x[2] for x in filterList]

    def composition (value, part):

        for func in funcs:
            value = func(value, part)

        return value

    return composition


def _filterOnPattern (func):

    def aggregate (pattern):

        tmp = func(pattern)
        if tmp is not None: pattern = tmp

        return pattern

    return aggregate


_filterRegexKnownFields = set(["match", "repl", "case"])

def _filterCreateRegex (fields):

    _checkFields("addFilterRegex", fields, _filterRegexKnownFields, ["match"])
    fieldDict = dict(fields)

    caseSens = _fancyBool(fieldDict.get("casesens", "0"))
    flags = re.U | re.S
    if not caseSens:
        flags |= re.I

    matchStr = fieldDict["match"]
    matchRx = re.compile(matchStr, flags)

    replStr = fieldDict.get("repl", "")

    def func (text):
        return matchRx.sub(replStr, text)

    sig = "\x04".join([matchStr, replStr, str(caseSens)])

    return func, sig


_filterHookKnownFields = set(["name", "factory"])

def _filterCreateHook (fields):

    _checkFields("addFilterHook", fields, _filterHookKnownFields, ["name"])
    fieldDict = dict(fields)

    hookName = fieldDict["name"]
    hook = get_hook_lreq(hookName, abort=False)

    sig = "\x04".join([x for x in split_req(hookName) if x is not None])

    factoryStr = fieldDict.get("factory")
    if factoryStr is not None:
        # The fetched hook is in fact a hook factory; produce the hook.
        hook, fsig = _fabricateHook(hook, factoryStr)
        sig += "\x04\x04" + fsig

    return hook, sig


def _fabricateHook (factory, argstr):

    hook = eval("factory(%s)" % argstr)

    argsig = argstr

    return hook, argsig


def _triggerParseGeneral (fields):

    casesens = True

    rest = []
    for field in fields:
        name, value = field
        if name == "casesens":
            casesens = _fancyBool(value)
        else:
            rest.append(field)

    return casesens, rest


_triggerKnownMsgParts = set([
    "msg", "msgid", "msgstr", "pmsgid", "pmsgstr",
])

def _triggerFromHook (fields):

    _checkFields("hook", fields, ["name", "factory", "on"], ["name", "on"])
    fieldDict = dict(fields)

    hookName = fieldDict["name"]
    hook = get_hook_lreq(hookName, abort=False)

    factoryStr = fieldDict.get("factory")
    if factoryStr is not None:
        # The hook we fetched is in fact a hook factory; produce the hook.
        hook, dummy = _fabricateHook(hook, factoryStr)

    msgpart = fieldDict["on"].strip()
    if msgpart not in _triggerKnownMsgParts:
        raise SyntaxError, \
              "Unknown message part for trigger to act on: %s" % msgpart

    if msgpart == "msg":
        def trigger (msg, cat):
            return hook(msg, cat)
    elif msgpart == "msgid":
        def trigger (msg, cat):
            hl = []
            hl.append(("msgid", 0, hook(msg.msgid, msg, cat)))
            hl.append(("msgid_plural", 0, hook(msg.msgid_plural, msg, cat)))
            return hl
    elif msgpart == "msgstr":
        def trigger (msg, cat):
            hl = []
            for i in range(len(msg.msgstr)):
                hl.append(("msgstr", i, hook(msg.msgstr[i], msg, cat)))
            return hl
    elif msgpart == "pmsgid":
        def trigger (msg, cat):
            hl = []
            hl.append(("msgid", 0, hook(msg.msgid)))
            hl.append(("msgid_plural", 0, hook(msg.msgid_plural)))
            return hl
    elif msgpart == "pmsgstr":
        def trigger (msg, cat):
            hl = []
            for i in range(len(msg.msgstr)):
                hl.append(("msgstr", i, hook(msgstr)))
            return hl

    return trigger


def _fancyBool (string):

    value = strbool(string)
    if value is None:
        raise SyntaxError, \
              "Cannot ascribe boolean value to '%s'" % string
    return value


_trigger_msgparts = set([
    # For matching in all messages.
    "msgctxt", "msgid", "msgstr",

    # For matching in plural messages part by part.
    "msgid_singular", "msgid_plural",
    "msgstr_0", "msgstr_1", "msgstr_2", "msgstr_3", "msgstr_4", "msgstr_5",
    "msgstr_6", "msgstr_7", "msgstr_8", "msgstr_9", # ought to be enough
])
_trigger_specials = set([
    "hook",
])

_trigger_matchmods = [
    "i",
]

class Rule(object):
    """Represent a single rule"""

    _knownKeywords = set(("env", "cat", "span", "after", "before", "ctx", "msgid", "msgstr", "head", "srcref", "comment"))
    _regexKeywords = set(("span", "after", "before", "ctx", "msgid", "msgstr", "srcref", "comment"))
    _twoRegexKeywords = set(("head",))
    _listKeywords = set(("env", "cat"))

    def __init__(self, pattern, msgpart, hint=None, valid=[],
                       stat=False, casesens=True, ident=None, disabled=False,
                       environ=None, mfilter=None, rfilter=None,
                       trigger=None):
        """Create a rule
        @param pattern: valid regexp pattern that trigger the rule
        @type pattern: unicode
        @param msgpart: part of the message to be matched by C{pattern}
        @type msgpart: string
        @param hint: hint given to user when rule match
        @type hint: unicode
        @param valid: list of cases that should make or not make rule matching
        @type valid: list of unicode key=value
        @param casesens: whether regex matching will be case-sensitive
        @type casesens: bool
        @param ident: rule identifier
        @type ident: unicode or C{None}
        @param disabled: whether rule is disabled
        @type disabled: bool
        @param environ: environment in which the rule applies
        @type environ: string or C{None}
        @param mfilter: filter to apply to message before checking
        @type mfilter: (msg, cat, env) -> <anything>
        @param rfilter: filter to apply to rule strings (e.g. on regex patterns)
        @type rfilter: (string) -> string
        @param trigger: function to act as trigger instead of C{pattern} applied to C{msgpart}
        @type trigger: (msg, cat, env) -> L{highlight<misc.msgreport.report_msg_content>}
        """

        # Define instance variable
        self.pattern=None # Compiled regexp into re.pattern object
        self.msgpart=msgpart # The part of the message to match
        self.valid=None   # Parsed valid definition
        self.hint=hint    # Hint message return to user
        self.ident=ident    # Rule identifier
        self.disabled=disabled # Whether rule is disabled
        self.count=0      # Number of time rule have been triggered
        self.time=0       # Total time of rule process calls
        self.stat=stat    # Wheter to gather stat or not. Default is false (10% perf hit due to time() call)
        self.casesens=casesens # Whether regex matches are case-sensitive
        self.environ=environ # Environment in which to apply the rule
        self.mfilter=mfilter # Function to filter the message before checking
        self.rfilter=rfilter # Function to filter the rule strings
        self.trigger=None # Function to use as trigger instead of pattern

        if trigger is None and msgpart not in _trigger_msgparts:
            raise StandardError, \
                  "Unknown message part '%s' for rule's main pattern" % msgpart

        # Flags for regex compilation.
        self.reflags=re.U|re.S
        if not self.casesens:
            self.reflags|=re.I

        # Setup trigger.
        if not trigger:
            self.setPattern(pattern)
        else:
            self.setTrigger(trigger)

        #Parse valid key=value arguments
        self.setValid(valid)

    def setPattern(self, pattern):
        """Compile pattern
        @param pattern: pattern as an unicode string"""
        try:
            if self.rfilter:
                pattern=self.rfilter(pattern, "pattern")
            self.pattern=re.compile(pattern, self.reflags)
        except Exception, e:
            warning("Invalid pattern '%s', disabling rule\n%s" % (pattern, e))
            self.disabled=True
        self.rawPattern=pattern
        self.trigger=None # invalidate any trigger function
        if self.ident:
            self.displayName="<id=%s>" % self.ident
        else:
            self.displayName="(%s)" % pattern
        
    def setTrigger(self, trigger):
        """
        Use trigger function instead of pattern.

        @param trigger: function to act as trigger
        @type trigger: (msg, cat, env) -> {highlight<misc.msgreport.report_msg_content>}
        """
        self.trigger=trigger
        self.pattern=None # invalidate any pattern
        self.rawPattern=""
        if self.ident:
            self.displayName="<id=%s>" % self.ident
        else:
            self.displayName="<trigger>"
        
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
                        warning("Invalid keyword '%s' in valid definition. Skipping" % key)
                        continue
                    if self.rfilter:
                        value=self.rfilter(value, "pattern")
                    if bkey in Rule._regexKeywords:
                        # Compile regexp
                        value=re.compile(value, self.reflags)
                    elif bkey in Rule._listKeywords:
                        # List of comma-separated words
                        value=[x.strip() for x in value.split(",")]
                    elif bkey in Rule._twoRegexKeywords:
                        # Split into the two regexes and compile them.
                        frx, vrx=value[1:].split(value[:1])
                        value=(re.compile(frx, self.reflags),
                               re.compile(vrx, self.reflags))
                    entry.append((key, value))
                self.valid.append(entry)
            except Exception, e:
                warning("Invalid 'Valid' definition '%s'. Skipping\n%s" % (item, e))
                continue

    #@timed_out(TIMEOUT)
    def process (self, msg, cat, env=None, nofilter=False):
        """
        Apply rule to the message.

        If the rule matches, I{highlight specification} of offending spans is
        returned (see L{report_msg_content<misc.msgreport.report_msg_content>});
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

        if self.pattern is None and self.trigger is None:
            warning("Trigger not defined, skipping rule.")
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
            msg = self._filter_message(msg, cat, env)

        if self.pattern:
            failed_spans = self._processWithPattern(msg, cat, env)
        else:
            failed_spans = self._processWithTrigger(msg, cat, env)

        # Update stats for matched rules.
        self.count += 1
        if self.stat:
            self.time += time() - begin

        return failed_spans


    def _create_text_spec (self, msgpart, msg):

        if 0: pass
        elif msgpart == "msgid":
            text_spec = [("msgid", 0, msg.msgid),
                         ("msgid_plural", 0, msg.msgid_plural)]
        elif msgpart == "msgstr":
            text_spec = [("msgstr", i, msg.msgstr[i])
                         for i in range(len(msg.msgstr))]
        elif msgpart == "msgctxt":
            text_spec = [("msgctxt", 0, msg.msgctxt or u"")]
        elif msgpart == "msgid_singular":
            text_spec = [("msgid", 0, msg.msgid)]
        elif msgpart == "msgid_plural":
            text_spec = [("msgid_plural", 0, msg.msgid_plural)]
        elif msgpart.startswith("msgstr_"):
            item = int(msgpart.split("_")[1])
            text_spec = [("msgstr", item, msg.msgstr[item])]
        else:
            raise StandardError, \
                  "Unknown message part '%s' in rule"

        return text_spec


    def _processWithPattern (self, msg, cat, env):

        text_spec = self._create_text_spec(self.msgpart, msg)

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
                    if self._is_valid(pmatch.group(0),
                                      pmatch.start(), pmatch.end(),
                                      text, entry, msg, cat, env):
                        cancel = True
                        break
                if not cancel:
                    # Record the span of problematic segment.
                    skey = (part, item)
                    if skey not in failed_spans:
                        failed_spans[skey] = (part, item, [], text)
                    failed_spans[skey][2].append(pmatch.span())

        return failed_spans.values()


    def _processWithTrigger (self, msg, cat, env):

        # Apply trigger.
        possibly_failed_spans = self.trigger(msg, cat)

        # Try to clear spans with validity tests.
        failed_spans = {}
        for spanspec in possibly_failed_spans:
            part, item, spans = spanspec[:3]
            ftext = None
            if len(spanspec) > 3:
                ftext = spanspec[3]
            part_item = part
            if part == "msgstr":
                part_item = part + "_" + str(item)
            text_spec = self._create_text_spec(part_item, msg)
            if ftext is None: # the trigger didn't do any own filtering
                ftext = text_spec[0][2] # message field which contains the span
            for span in spans:
                mstart, mend = span[:2] # may contain 3rd element, error text
                pmatch = ftext[mstart:mend]
                cancel = False
                for entry in self.valid:
                    if self._is_valid(pmatch, mstart, mend,
                                      ftext, entry, msg, cat, env):
                        cancel = True
                        break
                if not cancel:
                    # Record the span of problematic segment.
                    skey = (part, item)
                    if skey not in failed_spans:
                        failed_spans[skey] = (part, item, [], ftext)
                    failed_spans[skey][2].append(span)

        return failed_spans.values()


    def _filter_message (self, msg, cat, env):

        fmsg = msg
        if self.mfilter is not None:
            fmsg = MessageUnsafe(msg)
            self.mfilter(fmsg, cat, env)

        return fmsg


    def _is_valid (self, match, mstart, mend, text, ventry, msg, cat, env):

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

            elif bkey == "head":
                frx, vrx = value
                match = False
                for name, value in cat.header.field:
                    match = frx.search(name) and vrx.search(value)
                    if match:
                        break
                if invert: match = not match
                if not match:
                    valid = False
                    break

            elif bkey == "span":
                found = value.search(match) is not None
                if invert: found = not found
                if not found:
                    valid = False
                    break

            elif bkey == "after":
                # Search up to the match to avoid need for lookaheads.
                afterMatches = value.finditer(text, 0, mstart)
                found = False
                for afterMatch in afterMatches:
                    if afterMatch.end() == mstart:
                        found = True
                        break
                if invert: found = not found
                if not found:
                    valid = False
                    break

            elif bkey == "before":
                # Search from the match to avoid need for lookbehinds.
                beforeMatches = value.finditer(text, mend)
                found = False
                for beforeMatch in beforeMatches:
                    if beforeMatch.start() == mend:
                        found = True
                        break
                if invert: found = not found
                if not found:
                    valid = False
                    break

            elif bkey == "ctx":
                match = value.search(msg.msgctxt or u"")
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

            elif bkey == "srcref":
                match = False
                for file, lno in msg.source:
                    if value.search(file):
                        match = True
                        break
                if invert: match = not match
                if not match:
                    valid = False
                    break

            elif bkey == "comment":
                match = False
                all_cmnt = []
                all_cmnt.extend(msg.manual_comment)
                all_cmnt.extend(msg.auto_comment)
                for cmnt in all_cmnt:
                    if value.search(cmnt):
                        match = True
                        break
                if invert: match = not match
                if not match:
                    valid = False
                    break

        return valid


def _parseRuleLine (lines, lno):
    """
    Split a rule line into fields as list of (name, value) pairs.

    If a field name is followed by '=' or '=""', the field value will be
    an empty string. If there is no equal sign, the value will be C{None}.

    If the line is the trigger pattern, the name of the first field
    is going to be the "*", and its value the keyword of the message part
    to be matched; the name of the second field is going to be
    the pattern itself, and its value the string of match modifiers.
    """

    # Compose line out or backslash continuations.
    line = lines[lno - 1]
    while line.endswith("\\\n"):
        line = line[:-2]
        if lno >= len(lines):
            break
        lno += 1
        line += lines[lno - 1]

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
                raise SyntaxError, \
                      "Unbalanced '%s' in shorthand trigger pattern" % bropn
            fields.append((_rule_start, fname))
            fields.append((line[p1:p], ""))

            p += 1
            in_modifiers = True

        elif len(fields) == 0 and line[p] == _rule_start:
            # Verbose trigger.
            p += 1
            while p < llen and line[p].isspace():
                p += 1
            if p >= llen:
                raise SyntaxError, \
                      "Missing match keyword in rule trigger"

            # Collect the match keyword.
            p1 = p
            while line[p].isalnum() or line[p] == "_":
                p += 1
                if p >= llen:
                    raise SyntaxError, \
                          "Malformed rule trigger"
            tkeyw = line[p1:p]
            fields.append((_rule_start, tkeyw))

            if tkeyw in _trigger_msgparts:
                # Collect the pattern.
                while line[p].isspace():
                    p += 1
                    if p >= llen:
                        raise SyntaxError, \
                            "No pattern after trigger keyword '%s'" % tkeyw
                quote = line[p]
                p1 = p + 1
                p = _findEndQuote(line, p)
                fields.append((line[p1:p], ""))
                p += 1 # skip quote
                in_modifiers = True
            else:
                # Special trigger, go on reading fields.
                pass

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
                raise SyntaxError, "Invalid field name: %s" % fname

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

    return fields, lno


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
        raise SyntaxError, "Non-terminated quoted string: %s" % line[pos:]

    return epos

