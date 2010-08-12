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
from pology.msgreport import warning_on_msg
from pology.report import report, warning
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
    "If not given, attempt is made to detect language by catalog headers."
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

        # LanguageTool server parameters.
        host=params.host
        port=params.port
        #TODO: autodetect tcp port by reading LanguageTool config file if host is localhost
        
        # As LT server does not seem to read disabled rules from his config file, we manage exception here
        #TODO: investigate deeper this problem and make a proper bug report to LT devs.
        self.disabledRules=["UPPERCASE_SENTENCE_START","COMMA_PARENTHESIS_WHITESPACE"] 
        
        # Create connection to the LanguageTool server
        self.connection=HTTPConnection(host, port)


    def process_header (self, hdr, cat):

        self.lang=(self.setLang or cat.language())
        if not self.lang:
            raise SieveCatalogError(
                _("@info",
                  "Cannot determine language for catalog '%(file)s'.",
                  file=cat.filename))


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
                            report(_("@info",
                                     "<bold>%(file)s:%(line)d(#%(entry)d)</bold>",
                                     file=cat.filename, line=msg.refline, entry=msg.refentry))
                            #TODO: create a report function in the right place
                            #TODO: color in red part of context that make the mistake
                            report(_("@info",
                                     "<bold>Context:</bold> %(snippet)s",
                                     snippet=error.getAttribute("context")))
                            report(_("@info",
                                     "(%(rule)s) <bold><red>==></red></bold> %(note)s",
                                     rule=error.getAttribute("ruleId"),
                                     note=error.getAttribute("msg")))
                            report("")
        except socket.error:
            raise SieveError(_("@info",
                               "Cannot connect to LanguageTool server. "
                               "Did you start it?"))
                        

    def finalize (self):
        if self.nmatch:
            msg = n_("@info:progress",
                     "Detected %(num)d problem in grammar.",
                     "Detected %(num)d problems in grammar.",
                     num=self.nmatch)
            report("===== " + msg)

