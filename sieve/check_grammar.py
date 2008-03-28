# -*- coding: UTF-8 -*-

"""
Sieves messages with the LanguageTool grammar checker (http://www.languagetool.org)

@author: Sébastien Renard <sebastien.renard@digitalfox.org>
@license: GPLv3
"""

from httplib import HTTPConnection
from urllib import urlencode
from xml.dom.minidom import parseString
from pology.misc.colors import BOLD, RED, RESET
from pology.misc.report import warning_on_msg

REQUEST="/?language=%s&%s"

class Sieve (object):
    """Process messages through the LanguageTool grammar checker"""
    
    def __init__ (self, options, global_options):
    
        self.nmatch = 0 # Number of match for finalize
        self.connection=None # Connection to LanguageTool server

        if "lang" in options:
            options.accept("lang")
            self.lang=options["lang"]
        else:
            self.lang="fr"
        
        # LanguageTool server hostname
        if "host" in options:
            options.accept("host")
            host=options["host"]
        else:
            host="localhost"
        
        # LanguageTool server tcp port
        if "port" in options:
            options.accept("port")
            host=options["port"]
        else:
            #TODO: autodetect tcp port by reading LanguageTool config file if host is localhost
            port="8081"
        
        # Create connection to the LanguageTool server
        self.connection=HTTPConnection(host, port)
    
    def process (self, msg, cat):

        if msg.obsolete:
            return

        for msgstr in msg.msgstr:
            self.connection.request("GET", REQUEST % (self.lang, urlencode({"text":msgstr})))
            response=self.connection.getresponse()
            if response:
                responseData=response.read()
                if "error" in responseData:
                    self.nmatch+=1
                    dom=parseString(responseData)
                    for error in dom.getElementsByTagName("error"):
                        print "-"*(len(msgstr)+8)
                        print BOLD+"%s:%d(%d)" % (cat.filename, msg.refline, msg.refentry)+RESET
                        #TODO: create a report function in the right place
                        #TODO: color in red part of context that make the mistake
                        print BOLD+"Context: "+RESET+error.getAttribute("context")
                        print "("+error.getAttribute("ruleId")+")"+BOLD+RED+"==>"+RESET+BOLD+error.getAttribute("msg")+RESET
                        print 
                        

    def finalize (self):
        if self.nmatch:
            print "----------------------------------------------------"
            print "Total matching: %d" % self.nmatch
