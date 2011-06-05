# -*- coding: UTF-8 -*-

"""
Match messages by rules of arbitrary specificity.

A message-matching rule, represented by L{Rule} object, is a series of
pattern matches to be applied to the message, leading to the decision
of whether or not the rule as whole matches the message.
Patterns can be of different kinds, act on different parts of the message,
and be applied in a boolean-like combinations.

See C{doc/user/lingo.docbook#sec-lgrules} for detailed discussion of rules.

@author: Sébastien Renard <sebastien.renard@digitalfox.org>
@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

from codecs import open
from locale import getlocale
from os.path import dirname, basename, isdir, join, isabs
from os import listdir
import re
import sys
from time import time

from pology import PologyError, datadir, _, n_
from pology.message import MessageUnsafe
from pology.config import strbool
from pology.getfunc import get_hook_ireq, split_ireq
from pology.report import report, warning, format_item_list
from pology.tabulate import tabulate
from pology.timeout import timed_out

TIMEOUT=8 # Time in sec after which a rule processing is timeout


def printStat(rules):
    """Print rules match statistics
    @param rules: list of rule files
    """
    statRules=[r for r in rules if r.count!=0 and r.stat is True]
    if statRules:
        statRules.sort(key=lambda x: x.time)
        data=[]
        rown=[r.displayName for r in statRules]
        data.append([r.count for r in statRules])
        data.append([r.time/r.count*1000 for r in statRules])
        totTimeMsg=sum(data[-1])/1000
        data.append([r.time for r in statRules])
        totTime=sum(data[-1])
        data.append([r.time/totTime*100 for r in statRules])
        report(_("@label", "Rule application statistics:"))
        coln=[_("@title:column", "calls"),
              _("@title:column avg = average", "avg-time [ms]"),
              _("@title:column tot = total", "tot-time [s]"),
              _("@title:column", "time-share")]
        dfmt=[   "%d",           "%.3f",          "%.1f",     "%.2f%%"]
        report(tabulate(data, rown=rown, coln=coln, dfmt=dfmt, colorize=True))
        report(_("@info statistics",
                 "Total application time [s]: %(num).1f",
                 num=totTime))
        report(_("@info statistics",
                 "Average application time per message [ms]: %(num).1f",
                 num=totTimeMsg*1000))


def loadRules(lang, envs=[], envOnly=False, ruleFiles=None, stat=False):
    """Load rules for a given language
    @param lang: lang as a string in two caracter (i.e. fr). If none or empty, try to autodetect language
    @param envs: also load rules applicable in these environments
    @param envOnly: load only rules applicable in given environments
    @param ruleFiles: a list of rule files to load instead of internal
    @param stat: stat is a boolean to indicate if rule should gather count and time execution
    @return: list of rules objects or None if rules cannot be found (with complaints on stdout)
    """
    ruleDir=""             # Rules directory
    rules=[]               # List of rule objects
    langDir=join(datadir(), "lang") # Base of rule files per language

    # Collect rule files.
    if ruleFiles is not None:
        report(_("@info:progress", "Using external rules."))
    else:
        ruleDir=join(langDir, lang, "rules")
        if not isdir(ruleDir):
            raise PologyError(
                _("@info",
                  "There are no internal rules for language '%(langcode)s'.",
                  langcode=lang))
        report(_("@info:progress",
                 "Using internal rules for language '%(langcode)s'.",
                 langcode=lang))
        ruleFiles=[join(ruleDir, f) for f in listdir(ruleDir) if f.endswith(".rules")]

    # Parse rules.
    seenMsgFilters = {}
    for ruleFile in ruleFiles:
        rules.extend(loadRulesFromFile(ruleFile, stat, set(envs), seenMsgFilters))

    # Remove rules with specific but different to given environments,
    # or any rule not in given environments in environment-only mode.
    # FIXME: This should be moved to loadRulesFromFile.
    srules=[]
    for rule in rules:
        if envOnly and rule.environ not in envs:
            continue
        elif rule.environ and rule.environ not in envs:
            continue
        srules.append(rule)
    rules=srules

    # When operating in specific environments, for rules with
    # equal identifiers eliminate all but the one in the last environment.
    if envs:
        envsByIdent={}
        for rule in rules:
            if rule.ident:
                if rule.ident not in envsByIdent:
                    envsByIdent[rule.ident]=set()
                envsByIdent[rule.ident].add(rule.environ)
        srules=[]
        for rule in rules:
            eliminate=False
            if rule.ident and len(envsByIdent[rule.ident])>1:
                iEnv=((rule.environ is None and -1) or envs.index(rule.environ))
                for env in envsByIdent[rule.ident]:
                    iEnvOther=((env is None and -1) or envs.index(env))
                    if iEnv<iEnvOther:
                        eliminate=True
                        break
            if not eliminate:
                srules.append(rule)
        rules=srules

    return rules


_rule_start = "*"

class _IdentError (Exception): pass
class _SyntaxError (Exception): pass


def loadRulesFromFile(filePath, stat, envs=set(), seenMsgFilters={}):
    """Load rule file and return list of Rule objects
    @param filePath: full path to rule file
    @param stat: stat is a boolean to indicate if rule should gather count and time execution
    @param envs: environments in which the rules are to be applied
    @param seenMsgFilters: dictionary of previously encountered message
        filter functions, by their signatures; to avoid constructing
        same filters over different files
    @return: list of Rule object"""

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
                            raise _SyntaxError(
                                _("@info",
                                  "Unknown match modifier '%(mod)s' "
                                  "in trigger pattern.",
                                  mod=mmod))
                    casesens=("i" not in fields[1][1])
                elif keyword in _trigger_specials:
                    casesens, rest = _triggerParseGeneral(fields[1:])
                    if keyword == "hook":
                        triggerFunc = _triggerFromHook(rest)
                else:
                    raise _SyntaxError(
                        _("@info",
                          "Unknown keyword '%(kw)s' in rule trigger.",
                          kw=keyword))

            # valid line (for rule ou validGroup)
            elif fields[0][0]=="valid":
                if not inRule and not inGroup:
                    raise _SyntaxError(
                        _("@info",
                          "Directive '%(dir)s' outside of rule or "
                          "validity group.",
                          dir="valid"))
                valid.append(fields[1:])
            
            # Rule hint
            elif fields[0][0]=="hint":
                if not inRule:
                    raise _SyntaxError(
                        _("@info",
                          "Directive '%(dir)s' outside of rule.",
                          dir="hint"))
                hint=fields[0][1]
            
            # Rule identifier
            elif fields[0][0]=="id":
                if not inRule:
                    raise _SyntaxError(
                        _("@info",
                          "Directive '%(dir)s' outside of rule.",
                          dir="id"))
                ident=fields[0][1]
                if ident in identLines:
                    (prevLine, prevEnviron)=identLines[ident]
                    if prevEnviron==globalEnviron:
                        raise _IdentError(ident, prevLine)
                identLines[ident]=(lno, globalEnviron)
            
            # Whether rule is disabled
            elif fields[0][0]=="disabled":
                if not inRule:
                    raise _SyntaxError(
                        _("@info",
                          "Directive '%(dir)s' outside of rule.",
                          dir="disabled"))
                disabled=True
            
            # Validgroup 
            elif fields[0][0]=="validGroup":
                if inGroup:
                    raise _SyntaxError(
                        _("@info",
                          "Directive '%(dir)s' inside validity group.",
                          dir="validGroup"))
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
                    raise _SyntaxError(
                        _("@info",
                          "Directive '%(dir)s' inside validity group.",
                          dir="environment"))
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
                        raise _SyntaxError(
                            _("@info",
                              "Unknown filter directive '%(dir)s'.",
                              dir=fields[0][0]))
                    msgParts = set(parts).difference(_filterKnownRuleParts)
                    if msgParts:
                        totFunc, totSig = _msgFilterSetOnParts(msgParts, func, sig)
                        currentMsgFilters.append([handles, fenvs, totFunc, totSig])
                    ruleParts = set(parts).difference(_filterKnownMsgParts)
                    if ruleParts and (not envs or envs.intersection(fenvs)):
                        totFunc, totSig = _ruleFilterSetOnParts(ruleParts, func, sig)
                        currentRuleFilters.append([handles, fenvs, totFunc, totSig])

                elif fields[0][0] == ("removeFilter"):
                    _filterRemove(fields[1:],
                                  (currentMsgFilters, currentRuleFilters), envs)

                else: # remove all filters
                    if len(fields) != 1:
                        raise _SyntaxError(
                            _("@info",
                              "Expected no fields in "
                              "all-filter removal directive."))
                    # Must not loose reference to the selected lists.
                    while currentMsgFilters:
                        currentMsgFilters.pop()
                    while currentRuleFilters:
                        currentRuleFilters.pop()

            # Include another file
            elif fields[0][0] == "include":
                if inRule or inGroup:
                    raise _SyntaxError(
                        _("@info",
                          "Directive '%(dir)s' inside a rule or group.",
                          dir="include"))
                fileStack.append((lines, filePath, lno))
                lines, filePath, lno = _includeFile(fields[1:], filePath)

            else:
                raise _SyntaxError(
                    _("@info",
                      "Unknown directive '%(dir)s'.",
                      dir=fields[0][0]))

    except _IdentError, e:
        raise PologyError(
            _("@info",
              "Identifier '%(id)s' at %(file)s:%(line)d "
              "previously encountered at %(pos)s.",
              id=e.args[0], file=filePath, line=lno, pos=e.args[1]))
    except IOError, e:
        raise PologyError(
            _("@info",
              "Cannot read rule file '%(file)s'. The error was: %(msg)s",
              file=filePath, msg=e.args[0]))
    except _SyntaxError, e:
        raise PologyError(
            _("@info",
              "Syntax error at %(file)s:%(line)d:\n%(msg)s",
              file=filePath, line=lno, msg=e.args[0]))

    return rules


def _checkFields (directive, fields, knownFields, mandatoryFields=set(),
                  unique=True):

    fieldDict = dict(fields)
    if unique and len(fieldDict) != len(fields):
        raise _SyntaxError(
            _("@info",
              "Duplicate fields in '%(dir)s' directive.",
              dir=directive))

    if not isinstance(knownFields, set):
        knownFields = set(knownFields)
    unknownFields = set(fieldDict).difference(knownFields)
    if unknownFields:
        raise _SyntaxError(
            _("@info",
              "Unknown fields in '%(dir)s' directive: %(fieldlist)s.",
              dir=directive, fieldlist=format_item_list(unknownFields)))

    for name in mandatoryFields:
        if name not in fieldDict:
            raise _SyntaxError(
                _("@info",
                  "Mandatory field '%(field)s' missing in '%(dir)s' directive.",
                  field=name, dir=directive))


def _includeFile (fields, includingFilePath):

    _checkFields("include", fields, ["file"], ["file"])
    fieldDict = dict(fields)

    relativeFilePath = fieldDict["file"]
    if isabs(relativeFilePath):
        filePath = relativeFilePath
    else:
        filePath = join(dirname(includingFilePath), relativeFilePath)

    if filePath.endswith(".rules"):
        warning(_("@info",
                  "Including one rule file into another, "
                  "'%(file1)s' from '%(file2)s'.",
                  file1=filePath, file2=includingFilePath))

    lines=open(filePath, "r", "UTF-8").readlines()
    lines.append("\n") # sentry line

    return lines, filePath, 0


def _filterRemove (fields, filterLists, envs):

    _checkFields("removeFilter", fields, ["handle", "env"], ["handle"])
    fieldDict = dict(fields)

    handleStr = fieldDict["handle"]

    fenvStr = fieldDict.get("env")
    if fenvStr is not None:
        fenvs = [x.strip() for x in fenvStr.split(",")]
        if not envs or not envs.intersection(fenvs):
            # We are operating in no environment, or no operating environment
            # is listed among the selected; skip removal.
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
        raise PologyError(
            _("@info",
              "No filters with these handles to remove: %(handlelist)s.",
              handlelist=format_item_list(unseenHandles)))


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
                raise _SyntaxError(
                    _("@info",
                      "Unknown message parts for the filter to act on: "
                      "%(partlist)s.",
                      partlist=format_item_list(unknownParts)))
        elif name == "env":
            envs = [x.strip() for x in value.split(",")]
        else:
            rest.append(field)

    if not parts:
        raise _SyntaxError(
            _("@info",
              "No message parts specified for the filter to act on."))

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

    def composition (msg, cat, envs):

        for fenvs, func in fenvs_funcs:
            # Apply filter if environment-agnostic or in an operating environment.
            if fenvs is None or envs.intersection(fenvs):
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
        if msg.msgid_plural is not None:
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
        if msg.msgid_plural is not None:
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
            raise PologyError(
                _("@info",
                  "Unknown rule part '%(part)s' for the filter to act on.",
                  part=part))

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


_filterRegexKnownFields = set(["match", "repl", "casesens"])

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


def _filterCreateHook (fields):

    _checkFields("addFilterHook", fields, ["name"], ["name"])
    fieldDict = dict(fields)

    hookSpec = fieldDict["name"]
    hook = get_hook_ireq(hookSpec, abort=False)

    sigSegs = []
    for el in split_ireq(hookSpec):
        if el is not None:
            sigSegs.append(el)
        else:
            sigSegs.append("\x00")
    sig = "\x04".join(sigSegs)

    return hook, sig


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

    _checkFields("hook", fields, ["name", "on"], ["name", "on"])
    fieldDict = dict(fields)

    hook = get_hook_ireq(fieldDict["name"], abort=False)

    msgpart = fieldDict["on"].strip()
    if msgpart not in _triggerKnownMsgParts:
        raise PologyError(
            _("@info",
              "Unknown message part '%(part)s' for trigger to act on.",
              part=msgpart))

    if msgpart == "msg":
        def trigger (msg, cat):
            return hook(msg, cat)
    elif msgpart == "msgid":
        def trigger (msg, cat):
            hl = []
            hl.append(("msgid", 0, hook(msg.msgid, msg, cat)))
            if msg.msgid_plural is not None:
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
            if msg.msgid_plural is not None:
                hl.append(("msgid_plural", 0, hook(msg.msgid_plural)))
            return hl
    elif msgpart == "pmsgstr":
        def trigger (msg, cat):
            hl = []
            for i in range(len(msg.msgstr)):
                hl.append(("msgstr", i, hook(msg.msgstr[i])))
            return hl

    return trigger


def _fancyBool (string):

    value = strbool(string)
    if value is None:
        raise PologyError(
            _("@info",
              "Cannot convert '%(val)s' to a boolean value.",
              val=string))
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

    _knownKeywords = set(("env", "cat", "catrx", "span", "after", "before", "ctx", "msgid", "msgstr", "head", "srcref", "comment"))
    _regexKeywords = set(("catrx", "span", "after", "before", "ctx", "msgid", "msgstr", "srcref", "comment"))
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
        @type mfilter: (msg, cat, envs) -> <anything>
        @param rfilter: filter to apply to rule strings (e.g. on regex patterns)
        @type rfilter: (string) -> string
        @param trigger: function to act as trigger instead of C{pattern} applied to C{msgpart}
        @type trigger: (msg, cat, envs) -> L{highlight<msgreport.report_msg_content>}
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
            raise PologyError(
                _("@info",
                  "Unknown message part '%(part)s' set for the rule's "
                  "trigger pattern.",
                  part=msgpart))

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
            warning(_("@info",
                      "Invalid pattern '%(pattern)s', disabling rule:\n"
                      "%(msg)s",
                      pattern=pattern, msg=e))
            self.disabled=True
        self.rawPattern=pattern
        self.trigger=None # invalidate any trigger function
        if self.ident:
            self.displayName=_("@item:intext",
                               "[id=%(rule)s]",
                               rule=self.ident)
        else:
            self.displayName=_("@item:intext",
                               "[pattern=%(pattern)s]",
                               pattern=self.rawPattern)
        
    def setTrigger(self, trigger):
        """
        Use trigger function instead of pattern.

        @param trigger: function to act as trigger
        @type trigger: (msg, cat, envs) -> {highlight<msgreport.report_msg_content>}
        """
        self.trigger=trigger
        self.pattern=None # invalidate any pattern
        self.rawPattern=""
        if self.ident:
            self.displayName=_("@item:intext",
                               "[id=%(rule)s]",
                               rule=self.ident)
        else:
            self.displayName=_("@item:intext",
                               "[function]")
        
        
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
                        warning(_("@info",
                                  "Invalid keyword '%(kw)s' in "
                                  "validity definition, skipped.",
                                  kw=key))
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
                warning(_("@info",
                          "Invalid validity definition '%(dfn)s', skipped. "
                          "The error was:\n%(msg)s",
                          dfn=item, msg=e))
                continue

    #@timed_out(TIMEOUT)
    def process (self, msg, cat, envs=set(), nofilter=False):
        """
        Apply rule to the message.

        If the rule matches, I{highlight specification} of offending spans is
        returned (see L{report_msg_content<msgreport.report_msg_content>});
        otherwise an empty list.

        Rule will normally apply its own filters to the message before
        matching (on a local copy, the original message will not be affected).
        If the message is already appropriately filtered, this self-filtering
        can be prevented by setting C{nofilter} to {True}.

        @param msg: message to which the texts belong
        @type msg: instance of L{Message_base}
        @param cat: catalog to which the message belongs
        @type cat: L{Catalog}
        @param envs: environments in which the rule is applied
        @type envs: set
        @param nofilter: avoid filtering the message if C{True}
        @type nofilter: bool

        @return: highlight specification (may be empty list)
        """

        if self.pattern is None and self.trigger is None:
            warning(_("@info",
                      "Rule trigger not defined, rule skipped."))
            return []

        # If this rule belongs to a specific environment,
        # and it is not among operating environments,
        # cancel the rule immediately.
        if self.environ and self.environ not in envs:
            return []

        # Cancel immediately if the rule is disabled.
        if self.disabled:
            return []

        if self.stat:
            begin=time()

        # Apply own filters to the message if not filtered already.
        if not nofilter:
            msg = self._filter_message(msg, cat, envs)

        if self.pattern:
            failed_spans = self._processWithPattern(msg, cat, envs)
        else:
            failed_spans = self._processWithTrigger(msg, cat, envs)

        # Update stats for matched rules.
        self.count += 1
        if self.stat:
            self.time += time() - begin

        return failed_spans


    def _create_text_spec (self, msgpart, msg):

        if 0: pass
        elif msgpart == "msgid":
            text_spec = [("msgid", 0, msg.msgid)]
            if msg.msgid_plural is not None:
                text_spec += [("msgid_plural", 0, msg.msgid_plural)]
        elif msgpart == "msgstr":
            text_spec = [("msgstr", i, msg.msgstr[i])
                         for i in range(len(msg.msgstr))]
        elif msgpart == "msgctxt":
            text_spec = []
            if msg.msgctxt is not None:
                text_spec = [("msgctxt", 0, msg.msgctxt)]
        elif msgpart == "msgid_singular":
            text_spec = [("msgid", 0, msg.msgid)]
        elif msgpart == "msgid_plural":
            text_spec = []
            if msg.msgid_plural is not None:
                text_spec += [("msgid_plural", 0, msg.msgid_plural)]
        elif msgpart.startswith("msgstr_"):
            item = int(msgpart.split("_")[1])
            text_spec = [("msgstr", item, msg.msgstr[item])]
        else:
            raise PologyError(
                _("@info",
                  "Unknown message part '%(part)s' referenced in the rule.",
                  part=msgpart))

        return text_spec


    def _processWithPattern (self, msg, cat, envs):

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
                                      text, entry, msg, cat, envs):
                        cancel = True
                        break
                if not cancel:
                    # Record the span of problematic segment.
                    skey = (part, item)
                    if skey not in failed_spans:
                        failed_spans[skey] = (part, item, [], text)
                    failed_spans[skey][2].append(pmatch.span())

        return failed_spans.values()


    def _processWithTrigger (self, msg, cat, envs):

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
                                      ftext, entry, msg, cat, envs):
                        cancel = True
                        break
                if not cancel:
                    # Record the span of problematic segment.
                    skey = (part, item)
                    if skey not in failed_spans:
                        failed_spans[skey] = (part, item, [], ftext)
                    failed_spans[skey][2].append(span)

        return failed_spans.values()


    def _filter_message (self, msg, cat, envs):

        fmsg = msg
        if self.mfilter is not None:
            fmsg = MessageUnsafe(msg)
            self.mfilter(fmsg, cat, envs)

        return fmsg


    def _is_valid (self, match, mstart, mend, text, ventry, msg, cat, envs):

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
                match = envs.intersection(value)
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

            elif bkey == "catrx":
                match = bool(value.search(cat.name))
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
                match = False
                if msg.msgctxt:
                    match = value.search(msg.msgctxt)
                if invert: match = not match
                if not match:
                    valid = False
                    break

            elif bkey == "msgid":
                match = False
                for msgid in (msg.msgid, msg.msgid_plural):
                    if msgid is not None:
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
                raise _SyntaxError(
                    _("@info",
                      "Unbalanced '%(delim)s' in shorthand trigger pattern.",
                      delim=bropn))
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
                raise _SyntaxError(
                    _("@info",
                      "Missing '%(kw)s' keyword in the rule trigger.",
                      kw="match"))

            # Collect the match keyword.
            p1 = p
            while line[p].isalnum() or line[p] == "_":
                p += 1
                if p >= llen:
                    raise _SyntaxError(
                        _("@info",
                          "Malformed rule trigger."))
            tkeyw = line[p1:p]
            fields.append((_rule_start, tkeyw))

            if tkeyw in _trigger_msgparts:
                # Collect the pattern.
                while line[p].isspace():
                    p += 1
                    if p >= llen:
                        raise _SyntaxError(
                            _("@info",
                              "No pattern after the trigger keyword '%(kw)s'.",
                              kw=tkeyw))
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
                raise _SyntaxError(
                    _("@info",
                      "Invalid field name '%(field)s'.",
                      field=fname))

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
        raise _SyntaxError(
            _("@info",
              "Non-terminated quoted string '%(snippet)s'.",
              snippet=line[pos:]))

    return epos

