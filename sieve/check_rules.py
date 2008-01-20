# -*- coding: UTF-8 -*-

import sys, os, locale
from os.path import abspath, basename, dirname, exists, expandvars, isdir, isfile, join
from codecs import open
from time import strptime, mktime

from pology.misc.rules import loadRules, Rule
from pology.misc.colors import BOLD, RED, RESET
from pology.misc.timeout import TimedOutException

reload(sys)
encoding = locale.getdefaultlocale()[1]
sys.setdefaultencoding(encoding)

MARSHALL="+++"
#TODO: use $HOME and expand variable
CACHEDIR=expandvars("$HOME/.pology-check_rules-cache/") 

def error (msg, code=1):

    cmdname = os.path.basename(sys.argv[0])
    sys.stderr.write("%s: error: %s\n" % (cmdname, msg))
    sys.exit(code)


class Sieve (object):
    """Find messages matching given rules."""

    def __init__ (self, options, global_options):

        self.nmatch = 0 # Number of match for finalize
        self.rules=[]   # List of rules objects loaded in memory
        self.xmlFile=None # File handle to write XML output
        self.cacheFile=None # File handle to write XML cache
        self.cachePath=None # Path to cache file
        self.filename=""     # File name we are processing
        self.cached=False    # Flag to indicate if process result is already is cache
        
        ruleFiles=[]    # List of rule files used
        ruleDir=""
        baseRuleDir=join(dirname(sys.argv[0]), "rules")

        # Detect language
        if "lang" in options:
            options.accept("lang")
            ruleDir=join(baseRuleDir, options["lang"])
            print "Using %s rules" % options["lang"]
        else:
            # Try to autodetect language
            languages=[d for d in os.listdir(baseRuleDir) if isdir(join(baseRuleDir, d))]
            print "Rules availables in the following languages: %s" % ", ".join(languages)
            for language in languages:
                if language in sys.argv[-1] or language in locale.getdefaultlocale()[0]:
                    print "Autodetecting %s language" % language
                    ruleDir=join(baseRuleDir, language)
                    break
        # Identify rule files (overide language option)
        if "rule" in options:
            options.accept("rule")
            if isdir(options["rule"]):
                ruleFiles=[f for f in options["rule"] if isfile(f)]
        
        if not ruleFiles:
            if not ruleDir:
                print "Using default rule files (french)..."
                ruleDir=join(baseRuleDir, "fr")
            if isdir(ruleDir):
                ruleFiles=[join(ruleDir, f) for f in os.listdir(ruleDir) if f.endswith(".rules")]
            else:
                print "The rule directory is not a directory or is not accessible"
        
        # Load rules
        for filePath in ruleFiles:
            self.rules.extend(loadRules(filePath))
        
        print "Load %s rules from %s rule file" % (len(self.rules), len(ruleFiles))
        
        # Also output in XML file ?
        if "xml" in options:
            options.accept("xml")
            xmlPath=options["xml"]
            if os.access(dirname(abspath(xmlPath)), os.W_OK):
                self.xmlFile=open(xmlPath, "w", "utf-8")
                self.xmlFile.write('<?xml version="1.0" encoding="UTF-8"?>\n')
                self.xmlFile.write('<pos>\n')
            else:
                print "Cannot open %s file. XML output disabled" % xmlPath

        if not exists(CACHEDIR) and self.xmlFile:
            #Create cache dir (only if we want wml output)
            try:
                os.mkdir(CACHEDIR)
            except IOError, e:
                print "Cannot create cache directory (%s):\n%s" % (CACHEDIR, e)
                sys.exit(1)
 
        # Indicators to the caller:
        self.caller_sync = False # no need to sync catalogs
        self.caller_monitored = False # no need for monitored messages

    def process (self, msg, cat):

        if msg.obsolete:
            return

        filename=basename(cat.filename)
  
        # New file handling
        if self.xmlFile and self.filename!=filename:
            print "(Processing %s)" % filename
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
            # No need to analyse message, close cache if needed and return immediatly
            if self.cacheFile:
                self.xmlFile.write("</po>")
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
                print "Using cache"
                self.xmlFile.writelines(open(self.cachePath, "r", "utf-8").readlines())
                self.cached=True
        
        # No cache available, create it for next time
        if self.xmlFile and newFile and not self.cached:
            print "No cache available, processing file"
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

        msgstr=u"".join(msg.msgstr)
        msgtext=msg.to_string()
        msgtext=msgtext[0:msgtext.find('msgstr "')].rstrip()

        for word in ("msgid", "msgctxt"):
            msgtext=msgtext.replace(word, BOLD+word+RESET)
        for rule in self.rules:
            try:
                match=rule.process(msgstr, msg.msgid, msg.msgctxt, filename)
            except TimedOutException:
                print BOLD+RED+"Rule %s timed out. Skipping." % rule.rawPattern + RESET
                continue
            if match:
                self.nmatch += 1
                if self.xmlFile:
                    # Now, write to XML file if defined
                    error=[]
                    error.append("\t<error>\n")
                    error.append("\t\t<line>%s</line>\n" % msg.refline)
                    error.append("\t\t<refentry>%s</refentry>\n" % msg.refentry)
                    error.append("\t\t<msgctxt><![CDATA[%s]]></msgctxt>\n" % msg.msgctxt)
                    error.append("\t\t<msgid><![CDATA[%s]]></msgid>\n" % msg.msgid)
                    error.append("\t\t<msgstr><![CDATA[%s]]></msgstr>\n" % msgstr)
                    error.append("\t\t<start>%s</start>\n" % rule.span[0])
                    error.append("\t\t<end>%s</end>\n" % rule.span[1])
                    error.append("\t\t<pattern><![CDATA[%s]]></pattern>\n" % rule.rawPattern)
                    error.append("\t\t<hint><![CDATA[%s]]></hint>\n" % rule.hint)
                    error.append("\t</error>\n")
                    self.xmlFile.writelines(error)
                    if not self.cached:
                        # Write result in cache
                        self.cacheFile.writelines(error)
                else:
                    # Text format
                    print "-"*(len(msgstr)+8)
                    print BOLD+"%s:%d(%d)" % (cat.filename, msg.refline, msg.refentry)+RESET
                    try:
                        print msgtext
                        print BOLD+'msgstr'+RESET+' "%s"' % (msgstr[0:rule.span[0]]+BOLD+RED+
                                              msgstr[rule.span[0]:rule.span[1]]+RESET+
                                              msgstr[rule.span[1]:])
                        print "("+rule.rawPattern+")"+BOLD+RED+"==>"+RESET+BOLD+rule.hint+RESET
                    except UnicodeEncodeError, e:
                        print "UnicodeEncodeError, cannot print message (%s)" % e
                #print "(debug) raw pattern: '%s'" % rule.rawPattern

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
        if self.nmatch:
            print "----------------------------------------------------"
            print "Total matching: %d" % (self.nmatch,)
            print "Rules stat (raw_pattern, calls, average time (ms)"
            stat=list(((r.rawPattern, r.count, r.time/r.count) for r in self.rules if r.count!=0))
            stat.sort(lambda x, y: cmp(x[2], y[2]))
            for p, c, t in stat:
                print "%-20s %6d %6.1f" % (p, c, t)
