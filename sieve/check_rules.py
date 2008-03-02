# -*- coding: UTF-8 -*-

"""
Sieves messages with rules and warn when a rule triggers.

@author: Sébastien Renard <sebastien.renard@digitalfox.org>
@license: GPLv3
"""

import sys, os, locale
from os.path import abspath, basename, dirname, exists, expandvars, join
from codecs import open
from time import strptime, mktime

from pology.misc.rules import loadRules, printErrorMsg, printStat, xmlErrorMsg
from pology.misc.colors import BOLD, RED, RESET
from pology.misc.timeout import TimedOutException

reload(sys)
encoding = locale.getdefaultlocale()[1]
sys.setdefaultencoding(encoding) #pylint: disable-msg=E1101

# Pattern used to marshall path of cached files
MARSHALL="+++"
# Cache directory (for xml processing only)
CACHEDIR=expandvars("$HOME/.pology-check_rules-cache/") 

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
        
        if "lang" in options:
            options.accept("lang")
            lang=options["lang"]
        else:
            lang=None
        
        if "stat" in options:
            options.accept("stat")
            stat=True
        else:
            stat=False

        # Load rules
        self.rules=loadRules(lang, stat)
        
        if len(self.rules)==0:
            print "No rule loaded. Exiting"
            sys.exit(1)

        print "Load %s rules" % (len(self.rules))
        
        # Also output in XML file ?
        if "xml" in options:
            options.accept("xml")
            xmlPath=options["xml"]
            if os.access(dirname(abspath(xmlPath)), os.W_OK):
                #TODO: create nice api to manage xml file and move it to misc/rules.py
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
            # No need to analyze message, close cache if needed and return immediately
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
        
        # Now the sieve itself. Check message with every rules
        for rule in self.rules:
            id=0 # Count msgstr plural forms
            for msgstr in msg.msgstr:
                try:
                    match=rule.process(msgstr, msg.msgid, msg.msgctxt, filename)
                except TimedOutException:
                    print BOLD+RED+"Rule %s timed out. Skipping." % rule.rawPattern + RESET
                    id+=1
                    continue
                if match:
                    self.nmatch+=1
                    if self.xmlFile:
                        # Now, write to XML file if defined
                        error=xmlErrorMsg(msg, cat, rule, id)
                        self.xmlFile.writelines(error)
                        if not self.cached:
                            # Write result in cache
                            self.cacheFile.writelines(error)
                    else:
                        # Text format
                        printErrorMsg(msg, cat, rule, id)
                id+=1 # Increase msgstr id count

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