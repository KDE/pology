# -*- coding: UTF-8 -*-

"""
Sieves messages with the LanguageTool grammar checker (http://www.languagetool.org)

@author: Sébastien Renard <sebastien.renard@digitalfox.org>
@license: GPLv3
"""

from httplib import HTTPConnection
import socket
import sys
from urllib import urlencode
from xml.dom.minidom import parseString

from pology import _, n_
from pology.misc.colors import colors_for_file
from pology.misc.fsops import get_env_langs
from pology.misc.msgreport import warning_on_msg
from pology.misc.report import report, warning
from pology.sieve import SieveError, SieveCatalogError


_REQUEST="/?language=%s&%s"

def setup_sieve (p):

    p.set_desc(_("@info sieve discription",
    "Check language of translation using the LanguageTool checker."
    "\n\n"
    "LanguageTool (http://www.languagetool.org) is an open source "
    "language checker, which may be used as a standalone application, "
    "or in server-client mode. "
    "This sieve makes use of the latter; the server can easily be "
    "run locally, and can be downloaded from LanguageTools' web site. "
    "Also check the web site for the list of supported languages, "
    "and to which extent they are supported (number of rules)."
    ))

    p.add_param("lang", unicode, defval=None,
                metavar=_("@info sieve parameter value placeholder", "CODE"),
                desc=_("@info sieve parameter discription",
    "Apply rules for this language. "
    "If not given, autodetection of language is attempted based on "
    "catalog headers and environment."
    ))
    p.add_param("host", str, defval="localhost",
                metavar=_("@info sieve parameter value placeholder", "NAME"),
                desc=_("@info sieve parameter discription",
    "Name of the host where the server is running."
    ))
    p.add_param("port", str, defval="8081",
                metavar=_("@info sieve parameter value placeholder", "NUMBER"),
                desc=_("@info sieve parameter discription",
    "TCP port on the host which server uses to listen for queries."
    ))


class Sieve (object):
    
    def __init__ (self, params):
    
        self.nmatch = 0 # Number of match for finalize
        self.connection=None # Connection to LanguageTool server

        self.setLang=params.lang
        self.envLang=(get_env_langs() or [None])[0]

        # LanguageTool server parameters.
        host=params.host
        port=params.port
        #TODO: autodetect tcp port by reading LanguageTool config file if host is localhost
        
        # As LT server does not seem to read disabled rules from his config file, we manage exception here
        #TODO: investigate deeper this problem and make a proper bug report to LT devs.
        self.disabledRules=["UPPERCASE_SENTENCE_START","COMMA_PARENTHESIS_WHITESPACE"] 
        
        # Create connection to the LanguageTool server
        self.connection=HTTPConnection(host, port)

        self.colors = colors_for_file(sys.stdout)


    def process_header (self, hdr, cat):

        self.lang=(self.setLang or cat.language() or self.envLang)
        if not self.lang:
            raise SieveCatalogError(_("@info",
                                      "Cannot guess language for "
                                      "catalog '%(file)s'.")
                                    % dict(file=cat.filename))


    def process (self, msg, cat):

        if msg.obsolete:
            return

        try:
            for msgstr in msg.msgstr:
                self.connection.request("GET", _REQUEST % (self.lang, urlencode({"text":msgstr.encode("UTF-8")})))
                response=self.connection.getresponse()
                if response:
                    responseData=response.read()
                    if "error" in responseData:
                        dom=parseString(responseData)
                        for error in dom.getElementsByTagName("error"):
                            if error.getAttribute("ruleId") in self.disabledRules:
                                continue
                            self.nmatch+=1
                            report("-"*(len(msgstr)+8))
                            report(self.colors.bold("%s:%d(%d)" % (cat.filename, msg.refline, msg.refentry)))
                            #TODO: create a report function in the right place
                            #TODO: color in red part of context that make the mistake
                            report(self.colors.bold(_("@label", "Context:"))+error.getAttribute("context"))
                            report("("+error.getAttribute("ruleId")+")"+self.colors.bold(self.colors.red("==>"))+self.colors.bold(error.getAttribute("msg")))
                            report("")
        except socket.error:
            raise SieveError(_("@info",
                               "Cannot connect to LanguageTool server. "
                               "Did you start it?"))
                        

    def finalize (self):
        if self.nmatch:
            msg = (n_("@info:progress",
                      "Detected %(num)d problem in grammar.",
                      "Detected %(num)d problems in grammar.",
                      self.nmatch)
                   % dict(num=self.nmatch))
            report("===== %s" % msg)

