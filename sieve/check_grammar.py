# -*- coding: UTF-8 -*-

"""
Check language of translation using LanguageTool.

Documented in C{doc/user/sieving.docbook}.

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
from pology.sieve import add_param_langenv, add_param_filter


_REQUEST="/?language=%s&%s"

def setup_sieve (p):

    p.set_desc(_("@info sieve discription",
    "Check language of translation using LanguageTool."
    "\n\n"
    "LanguageTool (http://www.languagetool.org) is an open source "
    "language checker, which may be used as a standalone application, "
    "or in server-client mode. "
    "This sieve runs in client-server mode, so make sure Language Tool "
    "is running before this sieve is run."
    ))

    add_param_langenv(p,
        envappx=_("@info sieve parameter discription",
        "(Currently not used, for future compatibility.)"
        ))
    add_param_filter(p,
        intro=_("@info sieve parameter discription",
        "The F1A or F3A/C hook through which to filter the translation "
        "before passing it to grammar checking."
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

        self.pfilters = [[get_hook_ireq(x, abort=True), x]
                         for x in (params.filter or [])]


    def process_header (self, hdr, cat):

        self.lang=(self.setLang or cat.language())
        if not self.lang:
            raise SieveCatalogError(
                _("@info",
                  "Cannot determine language for catalog '%(file)s'.",
                  file=cat.filename))

        # Force explicitly given accelerators and markup.
        if self.accel is not None:
            cat.set_accelerator(self.accel)
        if self.markup is not None:
            cat.set_markup(self.markup)


    def process (self, msg, cat):

        if msg.obsolete:
            return

        try:
            for msgstr in msg.msgstr:

                # Apply precheck filters.
                for pfilter, pfname in self.pfilters:
                    try: # try as type F1A hook
                        msgstr = pfilter(msgstr)
                    except TypeError:
                        try: # try as type F3* hook
                            msgstr = pfilter(msgstr, msg, cat)
                        except TypeError:
                            raise SieveError(
                                _("@info",
                                  "Cannot execute filter '%(filt)s'.",
                                  filt=pfname))

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
                     "Detected %(num)d problem in grammar and style.",
                     "Detected %(num)d problems in grammar and style.",
                     num=self.nmatch)
            report("===== " + msg)

