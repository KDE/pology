# -*- coding: UTF-8 -*-

"""
Try to fail messages by rules and warn when that happens.

This sieve applies a collection of L{special rules<misc.rules>} to
messages, reporting whenever a rule "fails" a message --
rules are usually written to detect messages faulty, or possibly such,
in a certain sense.

By default, the sieve reads rules from Pology's internal C{l10n/<lang>/rules/}
directories, i.e. written for specific languages, and possibly specific
translation environments within a given language. Read about how to write
rules and create rule files in the L{misc.rules} module documentation.

The sieve parameters are:
   - C{lang:<language>}: language for which to fetch and apply the rules
   - C{env:<environment>}: specific environment within the given language;
        if not given, only environment-agnostic rules are applied
   - C{envonly}: when a specific environment is given, apply only the rules
        explicitly belonging to it (ignoring environment-agnostic ones)
   - C{rule}: comma-separated list of specific rules to apply, containing
        rule identifiers; if not given, all rules for given language and
        environment are applied
   - C{stat}: show statistics of rule matching at the end
   - C{accel:<characters>}: characters to consider as accelerator markers
   - C{markup:<mkeywords>}: markup types by keyword (comma separated)
   - C{xml:<filename>}: output results of the run in XML format file
   - C{rfile:<filename>}: read rules from this file, instead of from
        Pology's internal rule files
   - C{showfmsg}: show filtered message too when a rule fails a message
   - C{nomsg}: do not show message content, only problem descriptions

Parameters C{accel} and C{markup} set accelerator markers (e.g. C{_}, C{&},
etc.) and markup types by keyword (e.g. C{xml}, C{qtrich}, etc.) that may
be present in sieved catalogs. However, providing this information by itself
does nothing, it is only forced on catalogs (overriding what their headers
state, if anything) such that filter and validation hooks can properly
process messages. See documentation to L{rules<misc.rules>} for setting
up these in rule files.

Certain rules may be selectively disabled on a given message, by listing
their identifiers (C{id=} rule property) in C{skip-rule:} embedded list::

    # skip-rule: ruleid1, ruleid1, ...

@author: Sébastien Renard <sebastien.renard@digitalfox.org>
@license: GPLv3
"""

import sys, os
from os.path import abspath, basename, dirname, exists, expandvars, join
from codecs import open
from time import strftime, strptime, mktime
from locale import getpreferredencoding

from pology.misc.rules import loadRules, printStat
from pology.misc.report import report, error, warning
from pology.misc.msgreport import rule_error, rule_xml_error, report_msg_content
from pology.misc.colors import BOLD, RED, RESET
from pology.misc.timeout import TimedOutException
from pology.misc.comments import manc_parse_list
from pology.file.message import MessageUnsafe

# Pattern used to marshall path of cached files
MARSHALL="+++"
# Cache directory (for xml processing only)
CACHEDIR=expandvars("$HOME/.pology-check_rules-cache/") 


def setup_sieve (p):

    p.set_desc(
    "Apply rules to messages and report those that do not pass."
    "\n\n"
    "See documentation to pology.sieve.check_rules for details."
    % dict(par1="or")
    )

    p.add_param("lang", unicode,
                metavar="CODE",
                desc=
    "Load rules for this language "
    "(if not given, a language is automatically guessed)."
    )
    p.add_param("env", unicode,
                metavar="CODE",
                desc=
    "Load rules for this environment within language "
    "(if not given, only environment-agnostic rules are loaded)."
    )
    p.add_param("stat", bool, defval=False,
                desc=
    "Output some statistics on application of rules."
    )
    p.add_param("envonly", bool, defval=False,
                desc=
    "Load only rules explicitly belonging to environment given by '%(par)s'."
    % dict(par="env")
    )
    p.add_param("accel", unicode, multival=True,
                metavar="CHAR",
                desc=
    "Character which is used as UI accelerator marker in text fields. "
    "If a catalog defines accelerator marker in the header, "
    "this value overrides it."
    )
    p.add_param("markup", unicode, seplist=True,
                metavar="KEYWORD",
                desc=
    "Markup that can be expected in text fields, as special keyword "
    "(see documentation to pology.file.catalog, Catalog.set_markup(), "
    "for markup keywords currently known to Pology). "
    "If a catalog defines markup type in the header, "
    "this value overrides it."
    "Several markups can be given as comma-separated list."
    )
    p.add_param("rfile", unicode, multival=True,
                metavar="PATH",
                desc=
    "Load rules from a file, rather than internal Pology rules. "
    "Several rule files can be given by repeating the parameter."
    )
    p.add_param("showfmsg", bool, defval=False,
                desc=
    "Show filtered message too when reporting message failed by a rule."
    )
    p.add_param("nomsg", bool, attrname="showmsg", defval=True,
                desc=
    "Do not show message content at all when reporting failures."
    )
    p.add_param("rule", unicode, seplist=True,
                metavar="RULEID",
                desc=
    "Apply only the rule given by this identifier. "
    "Several identifiers can be given as comma-separated list."
    )
    p.add_param("xml", unicode,
                metavar="PATH",
                desc=
    "Write rule failures into an XML file instead of stdout."
    )


class Sieve (object):
    """Find messages matching given rules."""

    def __init__ (self, params, options):

        self.nmatch = 0 # Number of match for finalize
        self.rules=[]   # List of rules objects loaded in memory
        self.xmlFile=None # File handle to write XML output
        self.cacheFile=None # File handle to write XML cache
        self.cachePath=None # Path to cache file
        self.filename=""     # File name we are processing
        self.cached=False    # Flag to indicate if process result is already is cache

        lang=params.lang

        self.env=params.env
        envOnly=params.envonly
        if envOnly and params.env is None:
            warning("'envonly' parameter has no effect when 'env' not given")

        self.accels=params.accel
        self.markup=params.markup

        stat=params.stat
        self.showfmsg=params.showfmsg
        self.showmsg=params.showmsg

        # Load rules
        customRuleFiles=params.rfile
        self.rules=loadRules(lang, stat, self.env, envOnly, customRuleFiles)

        # Perhaps retain only those rules explicitly requested
        # in the command line, by their identifiers.
        selectedRules=[]
        if params.rule:
            selectedRules=set([x.strip() for x in params.rule])
            foundRules=set()
            srules=[]
            for rule in self.rules:
                if rule.ident in selectedRules:
                    srules.append(rule)
                    foundRules.add(rule.ident)
                    rule.disabled = False
            if foundRules!=selectedRules:
                missingRules=list(selectedRules-foundRules)
                missingRules.sort()
                error("some explicitly selected rules are missing: %s"
                      % ", ".join(missingRules))
            self.rules=srules
            selectedRules=list(selectedRules)
            selectedRules.sort()

        if len(self.rules)==0:
            warning("No rule loaded. Exiting")
            sys.exit(1)

        ntot=len(self.rules)
        ndis=len([x for x in self.rules if x.disabled])
        nact=ntot-ndis
        if ndis and self.env:
            if envOnly:
                report("Loaded %s rules [only %s] (%d active, %d disabled)" % (ntot, self.env, nact, ndis))
            else:
                report("Loaded %s rules [%s] (%d active, %d disabled)" % (ntot, self.env, nact, ndis))
        elif ndis:
            report("Loaded %s rules (%d active, %d disabled)" % (ntot, nact, ndis))
        elif self.env:
            if envOnly:
                report("Loaded %s rules [only %s]" % (ntot, self.env))
            else:
                report("Loaded %s rules [%s]" % (ntot, self.env))
        else:
            report("Loaded %s rules" % (ntot))

        if selectedRules:
            report("(explicitly selected: %s)" % ", ".join(selectedRules))

        # Collect all distinct filters from rules.
        self.ruleFilters=set()
        for rule in self.rules:
            if not rule.disabled:
                self.ruleFilters.add(rule.mfilter)
        nflt = len([x for x in self.ruleFilters if x is not None])
        if nflt:
            report("Active rules define %s distinct filter sets" % nflt)

        # Also output in XML file ?
        if params.xml:
            xmlPath=params.xml
            if os.access(dirname(abspath(xmlPath)), os.W_OK):
                #TODO: create nice api to manage xml file and move it to misc/rules.py
                self.xmlFile=open(xmlPath, "w", "utf-8")
                self.xmlFile.write('<?xml version="1.0" encoding="UTF-8"?>\n')
                self.xmlFile.write('<pos date="%s">\n' % strftime('%c').decode(getpreferredencoding()))
            else:
                warning("Cannot open %s file. XML output disabled" % xmlPath)

        if not exists(CACHEDIR) and self.xmlFile:
            #Create cache dir (only if we want wml output)
            try:
                os.mkdir(CACHEDIR)
            except IOError, e:
                error("Cannot create cache directory (%s):\n%s" % (CACHEDIR, e))

        report("-"*40)

        # Indicators to the caller:
        self.caller_sync = False # no need to sync catalogs
        self.caller_monitored = False # no need for monitored messages


    def process_header (self, hdr, cat):

        # Force explicitly given accelerators.
        if self.accels is not None:
            cat.set_accelerator(self.accels)

        # Force explicitly given markup.
        if self.markup is not None:
            cat.set_markup(self.markup)


    def process (self, msg, cat):

        # Apply rules only on translated messages.
        if not msg.translated:
            return

        filename=basename(cat.filename)
  
        # New file handling
        if self.xmlFile and self.filename!=filename:
            report("(Processing %s)" % filename)
            newFile=True
            self.cached=False # Reset flag
            self.cachePath=join(CACHEDIR, abspath(cat.filename).replace("/", MARSHALL))
            if self.cacheFile:
                self.cacheFile.close()
            if self.filename!="":
                # close previous
                self.xmlFile.write("</po>\n")
            self.filename=filename
        else:
            newFile=False
        
        # Current file loaded from cache on previous message. Close and return
        if self.cached:
            # No need to analyze message, return immediately
            if self.cacheFile:
                self.cacheFile=None # Indicate cache has been used and flushed into xmlFile
            return
        
        # Does cache exist for this file ?
        if self.xmlFile and newFile and exists(self.cachePath):
            #FIXME: header date getting is quite ugly...
            poDate=cat.header.field[2][1]
            #Truncate daylight information
            poDate=poDate.rstrip("GMT")
            poDate=poDate[0:poDate.find("+")]
            #Convert in sec since epoch time format
            poDate=mktime(strptime(poDate, '%Y-%m-%d %H:%M'))
            if os.stat(self.cachePath)[8]>poDate:
                report("Using cache")
                self.xmlFile.writelines(open(self.cachePath, "r", "utf-8").readlines())
                self.cached=True
        
        # No cache available, create it for next time
        if self.xmlFile and newFile and not self.cached:
            report("No cache available, processing file")
            self.cacheFile=open(self.cachePath, "w", "utf-8")
        
        # Handle start/end of files for XML output (not needed for text output)
        if self.xmlFile and newFile:
            # open new po
            if self.cached:
                # We can return now, cache is used, no need to process catalog
                return
            else:
                poTag='<po name="%s">\n' % filename
                self.xmlFile.write(poTag) # Write to result
                self.cacheFile.write(poTag) # Write to cache
        
        # Collect explicitly ignored rules by ID for this message.
        locally_ignored=manc_parse_list(msg, "skip-rule:", ",")

        # Prepare filtered messages for checking.
        msgByFilter={}
        for mfilter in self.ruleFilters:
            if mfilter is not None:
                msgf=MessageUnsafe(msg)
                mfilter(msgf, cat, self.env)
            else:
                msgf=msg
            msgByFilter[mfilter]=msgf

        # Now the sieve itself. Check message with every rules
        for rule in self.rules:
            if rule.disabled:
                continue
            if rule.environ and rule.environ!=self.env:
                continue
            if rule.ident in locally_ignored:
                continue
            msgf = msgByFilter[rule.mfilter]
            try:
                spans=rule.process(msgf, cat, env=self.env, nofilter=True)
            except TimedOutException:
                warning("Rule %s timed out. Skipping." % rule.rawPattern)
                continue
            if spans:
                self.nmatch+=1
                if self.xmlFile:
                    # FIXME: rule_xml_error is actually broken,
                    # as it considers matching to always be on msgstr
                    # Multiple span are now supported as well as msgstr index

                    # Now, write to XML file if defined
                    xmlError=rule_xml_error(msg, cat, rule, spans[0][2], spans[0][1])
                    self.xmlFile.writelines(xmlError)
                    if not self.cached:
                        # Write result in cache
                        self.cacheFile.writelines(xmlError)
                else:
                    # Text format.
                    if not self.showfmsg:
                        msgf=None
                    rule_error(msg, cat, rule, spans, msgf, self.showmsg)

    def finalize (self):
        
        if self.xmlFile:
            # Close last po tag and xml file
            if self.cached and self.cacheFile:
                self.cacheFile.write("</po>\n")
                self.cacheFile.close()
                self.cacheFile=None
            else:
                self.xmlFile.write("</po>\n")
            self.xmlFile.write("</pos>\n")
            self.xmlFile.close()
        printStat(self.rules, self.nmatch)

