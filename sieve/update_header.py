# -*- coding: UTF-8 -*-

"""
Initialize and update the PO header with own translation data.

Documented in C{doc/user/sieving.docbook}.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import os
import re
import time

from pology import _, n_
import pology.config as config
from pology.report import warning
from pology.resolve import expand_vars
from pology.sieve import SieveError


def setup_sieve (p):

    p.set_desc(_("@info sieve discription",
    "Initialize or update the PO header with own translator data."
    ))
    p.add_param("proj", unicode, mandatory=True,
                metavar=_("@info sieve parameter value placeholder", "ID"),
                desc=_("@info sieve parameter discription",
    "Project ID in Pology configuration file, "
    "which contains the necessary project data to update the header."
    ))
    p.add_param("init", bool, defval=False,
                desc=_("@info sieve parameter discription",
    "Consider header as uninitialized, removing any existing information "
    "before adding own and project data."
    ))
    p.add_param("onmod", bool, defval=False,
                desc=_("@info sieve parameter discription",
    "Update header only if the catalog was otherwise modified "
    "(in sieve chains)."
    ))


class Sieve (object):

    def __init__ (self, params):

        self.p = params

        # Collect user and project configuration.
        prjsect = "project-" + params.proj
        if not config.has_section(prjsect):
            raise SieveError(
                _("@info",
                  "Project '%(id)s' is not defined in user configuration.",
                  id=params.proj))
        self.prjcfg = config.section(prjsect)
        prjcfg = config.section(prjsect)
        usrcfg = config.section("user")

        # Collect project data.
        self.name = prjcfg.string("name") or usrcfg.string("name")
        if not self.name:
            warning(_("@info",
                      "Field '%(field)s' is not set in "
                      "project or user configuration.",
                      field="name"))
        self.email = prjcfg.string("email") or usrcfg.string("email")
        if not self.email:
            warning(_("@info",
                      "Field '%(field)s' is not set in "
                      "project or user configuration.",
                      field="email"))
        self.langteam = prjcfg.string("language-team")
        if not self.langteam:
            warning(_("@info",
                      "Field '%(field)s' is not set in "
                      "project configuration.",
                      field="language-team"))
        self.teamemail = prjcfg.string("team-email") # ok not to be present
        self.langcode = prjcfg.string("language") or usrcfg.string("language")
        if not self.langcode:
            warning(_("@info",
                      "Field '%(field)s' is not set in "
                      "project configuration.",
                      field="language"))
        self.encoding = (   prjcfg.string("encoding")
                         or usrcfg.string("encoding")
                         or u"UTF-8")
        self.plforms = (   prjcfg.string("plural-forms")
                        or usrcfg.string("plural-forms"))
        if not self.plforms:
            warning(_("@info",
                      "Field '%(field)s' is not set in "
                      "project configuration.",
                      field="plural-forms"))
        self.poeditor = (    prjcfg.string("po-editor")
                          or usrcfg.string("po-editor")) # ok not to be present


    def process_header_last (self, hdr, cat):

        if self.p.onmod and cat.modcount == 0:
            return

        if self.p.init:
            # Assemble translation title.
            if self.langteam:
                title = (u"Translation of %(title)s into %(lang)s."
                         % dict(title="%poname", lang="%langname"))
            else:
                title = (u"Translation of %(title)s."
                         % dict(title="%poname"))
            # Remove some placeholders.
            if "YEAR" in hdr.copyright:
                hdr.copyright = None
            if "PACKAGE" in hdr.license:
                hdr.license = None

            cat.update_header(project=cat.name, title=title,
                              name=self.name, email=self.email,
                              teamemail=self.teamemail,
                              langname=self.langteam, langcode=self.langcode,
                              encoding=self.encoding, ctenc="8bit",
                              plforms=self.plforms,
                              poeditor=self.poeditor)
        else:
            cat.update_header(name=self.name, email=self.email,
                              poeditor=self.poeditor)

