# -*- coding: UTF-8 -*-

"""
Apply language- and project-dependent validation rules to messages.

Documented in C{doc/user/sieving.docbook}.

@author: Sébastien Renard <sebastien.renard@digitalfox.org>
@author: Chusslove Illich <caslav.ilic@gmx.net>
@license: GPLv3
"""

from codecs import open
from locale import getpreferredencoding
import os
from os.path import abspath, basename, dirname, exists, expandvars, join
import re
import sys
from time import strftime, strptime, mktime

from pology import _, n_
from pology.colors import cjoin
from pology.comments import manc_parse_list, parse_summit_branches
from pology.fsops import collect_files_by_ext
from pology.message import MessageUnsafe
from pology.msgreport import multi_rule_error, rule_xml_error
from pology.msgreport import report_msg_to_lokalize
from pology.report import report, warning, format_item_list
from pology.rules import loadRules, printStat
from pology.sieve import add_param_lang, add_param_env, add_param_poeditors
from pology.timeout import TimedOutException
from pology.sieve import SieveError, SieveCatalogError, SieveMessageError


# Pattern used to marshall path of cached files
_MARSHALL = "+++"
# Cache directory (for xml processing only)
# FIXME: More portable location of cache.
_CACHEDIR = expandvars("$HOME/.pology-check_rules-cache/")

# Flag to add to failed messages, if requested.
_flag_mark = u"failed-rule"


def setup_sieve (p):

    p.set_desc(_("@info sieve discription",
    "Apply rules to messages and report those that do not pass."
    ))

    add_param_lang(p, appx=_("@info sieve parameter discription",
        "If the language is left undefined for a given catalog, "
        "it will be skipped and a warning may be output."
        ))
    add_param_env(p, appx=_("@info sieve parameter discription",
        "If the environment is left undefined for a given catalog, "
        "only environment-agnostic rules will be applied."
        ))
    p.add_param("stat", bool, defval=False,
                desc=_("@info sieve parameter discription",
    "Output statistics on application of rules."
    ))
    p.add_param("envonly", bool, defval=False,
                desc=_("@info sieve parameter discription",
    "Load only rules explicitly belonging to environment given by '%(par)s'.",
    par="env"
    ))
    p.add_param("accel", unicode, multival=True,
                metavar=_("@info sieve parameter value placeholder", "CHAR"),
                desc=_("@info sieve parameter discription",
    "Character which is used as UI accelerator marker in text fields. "
    "If a catalog defines accelerator marker in the header, "
    "this value overrides it."
    ))
    p.add_param("markup", unicode, seplist=True,
                metavar=_("@info sieve parameter value placeholder", "KEYWORD"),
                desc=_("@info sieve parameter discription",
    "Markup that can be expected in text fields, as special keyword "
    "(see documentation to pology.catalog, Catalog.set_markup(), "
    "for markup keywords currently known to Pology). "
    "If a catalog defines markup type in the header, "
    "this value overrides it."
    "Several markups can be given as comma-separated list."
    ))
    p.add_param("rfile", unicode, multival=True,
                metavar=_("@info sieve parameter value placeholder", "PATH"),
                desc=_("@info sieve parameter discription",
    "Load rules from a file, rather than internal Pology rules. "
    "Several rule files can be given by repeating the parameter."
    ))
    p.add_param("rdir", unicode, multival=True,
                metavar=_("@info sieve parameter value placeholder", "DIRPATH"),
                desc=_("@info sieve parameter discription",
    "Load rules from a directory, rather than internal Pology rules."
    "Several rule directories can be given by repeating the parameter."
    ))
    p.add_param("showfmsg", bool, defval=False,
                desc=_("@info sieve parameter discription",
    "Show filtered message too when reporting message failed by a rule."
    ))
    p.add_param("nomsg", bool, attrname="showmsg", defval=True,
                desc=_("@info sieve parameter discription",
    "Do not show message content at all when reporting failures."
    ))
    p.add_param("rule", unicode, seplist=True,
                metavar=_("@info sieve parameter value placeholder", "RULEID"),
                desc=_("@info sieve parameter discription",
    "Apply only the rule given by this identifier. "
    "Several identifiers can be given as comma-separated list."
    ))
    p.add_param("rulerx", unicode, multival=True,
                metavar=_("@info sieve parameter value placeholder", "REGEX"),
                desc=_("@info sieve parameter discription",
    "Apply only the rules with identifiers matching this regular expression. "
    "Several patterns can be given by repeating the parameter."
    ))
    p.add_param("norule", unicode, seplist=True,
                metavar=_("@info sieve parameter value placeholder", "RULEID"),
                desc=_("@info sieve parameter discription",
    "Do not apply rule given by this identifier. "
    "Several identifiers can be given as comma-separated list."
    ))
    p.add_param("norulerx", unicode, multival=True,
                metavar=_("@info sieve parameter value placeholder", "REGEX"),
                desc=_("@info sieve parameter discription",
    "Do not apply the rules with identifiers matching this regular expression. "
    "Several patterns can be given by repeating the parameter."
    ))
    p.add_param("branch", unicode, seplist=True,
                metavar=_("@info sieve parameter value placeholder", "BRANCH"),
                desc=_("@info sieve parameter discription",
    "In summit catalogs, consider only messages belonging to given branch. "
    "Several branches can be given as comma-separated list."
    ))
    p.add_param("xml", unicode,
                metavar=_("@info sieve parameter value placeholder", "PATH"),
                desc=_("@info sieve parameter discription",
    "Write rule failures into an XML file instead of stdout."
    ))
    p.add_param("mark", bool, defval=False,
                desc=_("@info sieve parameter discription",
    "Add '%(flag)s' flag to each message failed by a rule.",
    flag=_flag_mark
    ))
    p.add_param("byrule", bool, defval=False,
                desc=_("@info sieve parameter discription",
    "Output failed messages ordered by sorted rule identifiers."
    ))
    add_param_poeditors(p)


class Sieve (object):
    """Find messages matching given rules."""

    def __init__ (self, params):

        self.nmatch = 0 # Number of match for finalize
        self.rules = []   # List of rules objects loaded in memory
        self.xmlFile = None # File handle to write XML output
        self.cacheFile = None # File handle to write XML cache
        self.cachePath = None # Path to cache file
        self.filename = ""     # File name we are processing
        self.cached = False    # Flag to indicate if process result is already is cache

        self.globalLang = params.lang
        self.globalEnvs = params.env
        self.envOnly = params.envonly
        self._rulesCache = {}

        self.accels = params.accel
        self.markup = params.markup

        self.ruleChoice = params.rule
        self.ruleChoiceRx = params.rulerx
        self.ruleChoiceInv = params.norule
        self.ruleChoiceInvRx = params.norulerx

        self.stat = params.stat
        self.showfmsg = params.showfmsg
        self.showmsg = params.showmsg
        self.lokalize = params.lokalize
        self.mark = params.mark
        self.byrule = params.byrule

        self.branches = params.branch and set(params.branch) or None

        # Collect non-internal rule files.
        self.customRuleFiles = None
        if params.rfile or params.rdir:
            self.customRuleFiles = []
            if params.rfile:
                self.customRuleFiles.extend(params.rfile)
            if params.rdir:
                for rdir in params.rdir:
                    rfiles = collect_files_by_ext(rdir, "rules")
                    self.customRuleFiles.extend(rfiles)

        # Also output in XML file ?
        if params.xml:
            xmlPath = params.xml
            if os.access(dirname(abspath(xmlPath)), os.W_OK):
                #TODO: create nice api to manage xml file and move it to rules.py
                self.xmlFile = open(xmlPath, "w", "utf-8")
                self.xmlFile.write('<?xml version="1.0" encoding="UTF-8"?>\n')
                self.xmlFile.write('<pos date="%s">\n' % strftime('%c').decode(getpreferredencoding()))
            else:
                warning(_("@info",
                          "Cannot open file '%(file)s'. XML output disabled.",
                          file=xmlPath))

        if not exists(_CACHEDIR) and self.xmlFile:
            #Create cache dir (only if we want wml output)
            try:
                os.mkdir(_CACHEDIR)
            except IOError, e:
                raise SieveError(_("@info",
                                   "Cannot create cache directory '%(dir)s':\n"
                                   "%(msg)s",
                                   dir=_CACHEDIR, msg=e))

        report("-"*40)

        if self.byrule:
            self.postFailedMessages = {}

        # Unless marking requested, no need to monitor/sync.
        if not self.mark:
            self.caller_sync = False
            self.caller_monitored = False


    def process_header (self, hdr, cat):

        # Force explicitly given accelerators.
        if self.accels is not None:
            cat.set_accelerator(self.accels)

        # Force explicitly given markup.
        if self.markup is not None:
            cat.set_markup(self.markup)

        # Choose (possibly loading) appropriate rules for this catalog.
        self.lang = self.globalLang or cat.language()
        if not self.lang:
            raise SieveCatalogError(
                _("@info",
                  "Cannot determine language for catalog '%(file)s'.",
                  file=cat.filename))
        self.envs = self.globalEnvs or cat.environment() or []
        rkey = (self.lang, tuple(self.envs))
        if rkey not in self._rulesCache:
            self._rulesCache[rkey] = self._loadRules(self.lang, self.envs)
        self.rules, self.ruleFilters = self._rulesCache[rkey]


    def process (self, msg, cat):

        # Apply rules only on translated messages.
        if not msg.translated:
            return

        # Apply rules only to messages from selected branches.
        if self.branches:
            msg_branches = parse_summit_branches(msg)
            if not set.intersection(self.branches, msg_branches):
                return

        filename = basename(cat.filename)

        # New file handling
        if self.xmlFile and self.filename != filename:
            newFile = True
            self.cached = False # Reset flag
            self.cachePath = join(_CACHEDIR, abspath(cat.filename).replace("/", _MARSHALL))
            if self.cacheFile:
                self.cacheFile.close()
            if self.filename != "":
                # close previous
                self.xmlFile.write("</po>\n")
            self.filename = filename
        else:
            newFile = False

        # Current file loaded from cache on previous message. Close and return
        if self.cached:
            # No need to analyze message, return immediately
            if self.cacheFile:
                self.cacheFile = None # Indicate cache has been used and flushed into xmlFile
            return

        # Does cache exist for this file ?
        if self.xmlFile and newFile and exists(self.cachePath):
            poDate = None
            for headerName, headerValue in cat.header.field:
                if headerName == "PO-Revision-Date":
                    poDate = headerValue
                    break

            if poDate:
                #Truncate daylight information
                poDate = poDate.rstrip("GMT")
                poDate = poDate[0:poDate.find("+")]
                #Convert in sec since epoch time format
                poDate = mktime(strptime(poDate, '%Y-%m-%d %H:%M'))
                if os.stat(self.cachePath)[8] > poDate:
                    report(_("@info:progress", "Using cache."))
                    self.xmlFile.writelines(open(self.cachePath, "r", "utf-8").readlines())
                    self.cached = True

        # No cache available, create it for next time
        if self.xmlFile and newFile and not self.cached:
            report(_("@info", "No cache available, processing file."))
            self.cacheFile = open(self.cachePath, "w", "utf-8")

        # Handle start/end of files for XML output (not needed for text output)
        if self.xmlFile and newFile:
            # open new po
            if self.cached:
                # We can return now, cache is used, no need to process catalog
                return
            else:
                poTag = '<po name="%s">\n' % filename
                self.xmlFile.write(poTag) # Write to result
                self.cacheFile.write(poTag) # Write to cache

        # Collect explicitly ignored rules by ID for this message.
        locally_ignored = manc_parse_list(msg, "skip-rule:", ",")

        # Collect explicitly applied rules by ID for this message.
        locally_applied = manc_parse_list(msg, "apply-rule:", ",")

        # Collect ignored/applied rules by switching comment.
        swprefix = "switch-rule:"
        swsep = ">"
        for cmnt in msg.manual_comment:
            if cmnt.strip().startswith(swprefix):
                p1 = cmnt.find(swprefix) + len(swprefix)
                p2 = cmnt.find(swsep, p1)
                if p2 < 0:
                    raise SieveMessageError(
                        _("@info",
                          "Separator  character '%(sep)s' missing in "
                          "'%(prefix)s' comment.",
                          sep=swsep, prefix=swprefix))
                els1 = [x.strip() for x in cmnt[p1:p2].split(",")]
                els2 = [x.strip() for x in cmnt[p2 + len(swsep):].split(",")]
                locally_ignored.extend(x for x in els1 if x)
                locally_applied.extend(x for x in els2 if x)

        # NOTE: It would be nice to warn if an explicitly applied rule
        # is not defined, but this is not generally possible because
        # different rule files may be loaded for different runs.

        # Prepare filtered messages for checking.
        envSet = set(self.envs)
        msgByFilter = {}
        for mfilter in self.ruleFilters:
            if mfilter is not None:
                msgf = MessageUnsafe(msg)
                mfilter(msgf, cat, envSet)
            else:
                msgf = msg
            msgByFilter[mfilter] = msgf

        # Now the sieve itself. Check message with every rules
        failedRules = []
        for rule in self.rules:
            if rule.disabled:
                continue
            if rule.environ and rule.environ not in envSet:
                continue
            if rule.ident in locally_ignored:
                continue
            if rule.manual and not rule.ident in locally_applied:
                continue
            msgf = msgByFilter[rule.mfilter]
            try:
                spans = rule.process(msgf, cat, envs=envSet, nofilter=True)
            except TimedOutException:
                warning(_("@info:progress",
                          "Rule '%(rule)s' timed out, skipping it.",
                          rule=rule.rawPattern))
                continue
            if spans:
                self.nmatch += 1
                if self.xmlFile:
                    # FIXME: rule_xml_error is actually broken,
                    # as it considers matching to always be on msgstr
                    # Multiple span are now supported as well as msgstr index

                    # Now, write to XML file if defined
                    rspans = [x[:2] for x in spans[0][2]]
                    pluid = spans[0][1]
                    xmlError = rule_xml_error(msg, cat, rule, rspans, pluid)
                    self.xmlFile.writelines(xmlError)
                    if not self.cached:
                        # Write result in cache
                        self.cacheFile.writelines(xmlError)
                if not self.showfmsg:
                    msgf = None
                failedRules.append((rule, spans, msgf))

        if failedRules:
            if not self.byrule:
                multi_rule_error(msg, cat, failedRules, self.showmsg)
            else:
                for rule, spans, msgf in failedRules:
                    if rule.ident not in self.postFailedMessages:
                        self.postFailedMessages[rule.ident] = []
                    self.postFailedMessages[rule.ident].append(
                        (msg, cat, ((rule, spans, msgf))))

            if self.mark:
                msg.flag.add(_flag_mark)

            if self.lokalize:
                repls = [_("@label", "Failed rules:")]
                for rule, hl, msgf in failedRules:
                    repls.append(_("@item",
                                "rule %(rule)s ==> %(msg)s",
                                rule=rule.displayName, msg=rule.hint))
                    for part, item, spans, fval in hl:
                        repls.extend([u"↳ %s" % x[2]
                                     for x in spans if len(x) > 2])
                report_msg_to_lokalize(msg, cat, cjoin(repls, "\n"))


    def finalize (self):

        if self.byrule:
            ruleIdents = sorted(self.postFailedMessages.keys())
            for ruleIdent in ruleIdents:
                for msg, cat, failedRule in self.postFailedMessages[ruleIdent]:
                    multi_rule_error(msg, cat, [failedRule], self.showmsg)

        if self.xmlFile:
            # Close last po tag and xml file
            if self.cached and self.cacheFile:
                self.cacheFile.write("</po>\n")
                self.cacheFile.close()
                self.cacheFile = None
            else:
                self.xmlFile.write("</po>\n")
            self.xmlFile.write("</pos>\n")
            self.xmlFile.close()
        if self.nmatch > 0:
            msg = n_("@info:progress",
                     "Rules detected %(num)d problem.",
                     "Rules detected %(num)d problems.",
                     num=self.nmatch)
            report("===== " + msg)
        printStat(self.rules)


    def _loadRules (self, lang, envs):

        # Load rules.
        rules = loadRules(lang, envs,
                        self.envOnly, self.customRuleFiles, self.stat)

        # Perhaps retain only those rules explicitly requested
        # in the command line, by their identifiers.
        selectedRules = set()
        srules = set()
        if self.ruleChoice:
            requestedRules = set([x.strip() for x in self.ruleChoice])
            foundRules = set()
            for rule in rules:
                if rule.ident in requestedRules:
                    srules.add(rule)
                    foundRules.add(rule.ident)
                    rule.disabled = False
            if foundRules != requestedRules:
                missingRules = list(requestedRules - foundRules)
                fmtMissingRules = format_item_list(sorted(missingRules))
                raise SieveError(_("@info",
                                   "Some explicitly selected rules "
                                   "are missing: %(rulelist)s.",
                                   rulelist=fmtMissingRules))
            selectedRules.update(foundRules)
        if self.ruleChoiceRx:
            identRxs = [re.compile(x, re.U) for x in self.ruleChoiceRx]
            for rule in rules:
                if (rule.ident
                    and reduce(lambda s, x: s or x.search(rule.ident),
                               identRxs, False)
                ):
                    srules.add(rule)
                    selectedRules.add(rule.ident)
        if self.ruleChoice or self.ruleChoiceRx:
            rules = list(srules)

        selectedRulesInv = set()
        srules = set(rules)
        if self.ruleChoiceInv:
            requestedRules = set([x.strip() for x in self.ruleChoiceInv])
            foundRules = set()
            for rule in rules:
                if rule.ident in requestedRules:
                    if rule in srules:
                        srules.remove(rule)
                    foundRules.add(rule.ident)
            if foundRules != requestedRules:
                missingRules = list(requestedRules - foundRules)
                fmtMissingRules = format_item_list(sorted(missingRules))
                raise SieveError(_("@info",
                                   "Some explicitly excluded rules "
                                   "are missing: %(rulelist)s.",
                                   rulelist=fmtMissingRules))
            selectedRulesInv.update(foundRules)
        if self.ruleChoiceInvRx:
            identRxs = [re.compile(x, re.U) for x in self.ruleChoiceInvRx]
            for rule in rules:
                if (rule.ident
                    and reduce(lambda s, x: s or x.search(rule.ident),
                               identRxs, False)
                ):
                    if rule in srules:
                        srules.remove(rule)
                    selectedRulesInv.add(rule.ident)
        if self.ruleChoiceInv or self.ruleChoiceInvRx:
            rules = list(srules)

        ntot = len(rules)
        ndis = len([x for x in rules if x.disabled])
        nact = ntot - ndis
        totfmt = n_("@item:intext inserted below as %(tot)s",
                  "Loaded %(num)d rule", "Loaded %(num)d rules",
                  num=ntot)
        if self.envOnly:
            envfmt = _("@item:intext inserted below as %(env)s",
                     "[only: %(envlist)s]",
                     envlist=format_item_list(envs))
        else:
            envfmt = _("@item:intext inserted below as %(env)s",
                     "[%(envlist)s]",
                     envlist=format_item_list(envs))
        actfmt = n_("@item:intext inserted below as %(act)s",
                  "%(num)d active", "%(num)d active",
                  num=nact)
        disfmt = n_("@item:intext inserted below as %(dis)s",
                  "%(num)d disabled", "%(num)d disabled",
                  num=ndis)
        subs = dict(tot=totfmt, env=envfmt, act=actfmt, dis=disfmt)
        if ndis and envs:
            report(_("@info:progress insertions from above",
                     "%(tot)s %(env)s (%(act)s, %(dis)s).", **subs))
        elif ndis:
            report(_("@info:progress insertions from above",
                     "%(tot)s (%(act)s, %(dis)s).", **subs))
        elif envs:
            report(_("@info:progress insertions from above",
                     "%(tot)s %(env)s.", **subs))
        else:
            report(_("@info:progress insertions from above",
                     "%(tot)s.", **subs))

        if selectedRules:
            selectedRules = selectedRules.difference(selectedRulesInv)
            n = len(selectedRules)
            if n <= 10:
                rlst = list(selectedRules)
                report(_("@info:progress",
                         "Selected rules: %(rulelist)s.",
                         rulelist=format_item_list(sorted(rlst))))
            else:
                report(n_("@info:progress",
                          "Selected %(num)d rule.",
                          "Selected %(num)d rules.",
                          num=n))
        elif selectedRulesInv:
            n = len(selectedRulesInv)
            if n <= 10:
                rlst = list(selectedRulesInv)
                report(_("@info:progress",
                         "Excluded rules: %(rulelist)s.",
                         rulelist=format_item_list(sorted(rlst))))
            else:
                report(n_("@info:progress",
                          "Excluded %(num)d rule.",
                          "Excluded %(num)d rules.",
                          num=n))

        # Collect all distinct filters from rules.
        ruleFilters = set()
        for rule in rules:
            if not rule.disabled:
                ruleFilters.add(rule.mfilter)
        nflt = len([x for x in ruleFilters if x is not None])
        if nflt:
            report(n_("@info:progress",
                      "Active rules define %(num)d distinct filter set.",
                      "Active rules define %(num)d distinct filter sets.",
                      num=nflt))

        return rules, ruleFilters

