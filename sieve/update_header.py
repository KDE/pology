# -*- coding: UTF-8 -*-

"""
Initialize and update the header of a PO file.

When work on a pristine PO starts, or an existing PO is to be revised with
new translations, this sieve can be used to automatically set PO header
fields to proper values. The revision date is taken as current, while
the rest of the info is pulled from user's configuration (C{~/.pologyrc}).

Sieve options:
  - C{proj:<project_id>}: ID of the project
  - C{nosync}: do not issue sync request

Parameter C{proj} specifies the ID of the project which covers the POs
about to be operated on. This ID is used as the name of configuration
section C{[project-<ID>]}, which contains the project data fields.
Also used are the fields under the C{[user]} section, unless overriden
in the project's section. All the used config fields are:
  - C{[project-*]/name} or C{[user]/name}: user's name
  - C{[project-*]/email} or C{[user]/email}: user's email address
  - C{[project-*]/language}: language code (IS0 639)
  - C{[project-*]/language-team}: human-readable language name
  - C{[project-*]/team-email}: team's email
  - C{[project-*]/encoding}: encoding of PO files
  - C{[project-*]/plural-forms}: the PO plural header (C{nplurals=...; ...;})

Non-default header fields are not touched, except the revision date and
the last translator which are always updated (including the comment
line, where translators are listed with years of contributions).

Option C{nosync} is there for cases when this sieve is used in a chain
with other sieves, to allow modifying the header only if a catalog
got modifed by another sieve that did request syncing.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import re
import time

import pology.misc.config as config
from pology.misc.report import error, warning
from pology.misc.monitored import Monlist


class Sieve (object):

    def __init__ (self, options, global_options):

        # Collect user and project configuration.
        prjsect = ""
        if "proj" in options:
            prjsect = "project-" + options["proj"]
            self.prjcfg = config.section(prjsect)
            options.accept("proj")
        else:
            error("project ID must be provided (-s proj:<ID>)")
        prjcfg = config.section(prjsect)
        usrcfg = config.section("user")

        # Do not issue sync request if told so.
        if "nosync" in options:
            self.caller_sync = False
            options.accept("nosync")

        # Collect project data.
        self.tname = prjcfg.string("name") or usrcfg.string("name")
        if not self.tname:
            warning("'name' not set in project or user configuration")
        self.temail = prjcfg.string("email") or usrcfg.string("email")
        if not self.temail:
            warning("'email' not set in project or user configuration")
        self.language = prjcfg.string("language-team")
        if not self.language:
            warning("'language-team' not set in project configuration")
        self.lang = prjcfg.string("language")
        if not self.lang:
            warning("'language' not set in project configuration")
        self.encoding = prjcfg.string("encoding")
        if not self.encoding:
            warning("'encoding' not set in project configuration")
        self.plforms = prjcfg.string("plural-forms")
        if not self.plforms:
            warning("'plural-forms' not set in project configuration")
        self.lemail = prjcfg.string("team-email") # ok not to be present


    def process_header (self, hdr, cat):

        # ---------------------
        # Fields updated always

        # - compose translator's and team data
        tr_ident = None
        if self.tname and self.temail:
            tr_ident = "%s <%s>" % (self.tname, self.temail)
        elif self.tname:
            tr_ident = self.tname

        tm_ident = None
        if self.language and self.lemail:
            tm_ident = "%s <%s>" % (self.language, self.lemail)
        elif self.language:
            tm_ident = self.language

        # - author comment
        cyear = time.strftime("%Y")
        acfmt = u"%s, %s."
        new_author = True
        for i in range(len(hdr.author)):
            if tr_ident in hdr.author[i]:
                # Parse the current list of years.
                years = re.findall(r"\b(\d{2,4})\s*[,.]", hdr.author[i])
                if cyear not in years:
                    years.append(cyear)
                years.sort()
                hdr.author[i] = acfmt % (tr_ident, ", ".join(years))
                new_author = False
                break
        if new_author:
            hdr.author.append(acfmt % (tr_ident, cyear))

        # - last translator
        hdr.set_field(u"Last-Translator", unicode(tr_ident))

        # - revision date
        rdate = time.strftime("%Y-%m-%d %H:%M%z")
        hdr.set_field(u"PO-Revision-Date", unicode(rdate))

        # ------------------------------------
        # Fields updated only when at defaults

        # - title
        reset_title = False
        for line in hdr.title:
            if "TITLE" in line:
                reset_title = True
                break
        if reset_title:
            if self.language:
                hdr.title = Monlist([  u"Translation of %s into %s." \
                                     % (cat.name, self.language)])
            else:
                hdr.title = Monlist([u"Translation of %s." % (cat.name)])

        # - project ID
        fval = hdr.get_field_value("Project-Id-Version")
        if "PACKAGE" in fval:
            hdr.set_field(u"Project-Id-Version", unicode(cat.name))

        # - language team
        fval = hdr.get_field_value("Language-Team")
        if self.language and "LANGUAGE" in fval:
            hdr.set_field(u"Language-Team", unicode(tm_ident))

        # - language code
        fval = hdr.get_field_value("Language")
        if self.lang and not fval:
            hdr.set_field(u"Language", unicode(self.lang),
                          after="Language-Team")

        # - encoding
        fval = hdr.get_field_value("Content-Type")
        if self.encoding and "CHARSET" in fval:
            ctval = u"text/plain; charset=%s" % self.encoding
            hdr.set_field(u"Content-Type", unicode(ctval))

        # - plural forms
        fval = hdr.get_field_value("Plural-Forms")
        if self.plforms and "INTEGER" in fval:
            hdr.set_field(u"Plural-Forms", unicode(self.plforms))

        # ------------------------------
        # Handle uninitialized defaults

        # - remove author placeholder
        for i in range(len(hdr.author)):
            if u"FIRST AUTHOR" in hdr.author[i]:
                hdr.author.pop(i)
                break

        # - remove copyright placeholder
        if "YEAR" in hdr.copyright:
            hdr.copyright = u""

        # - remove license placeholder
        if "PACKAGE" in hdr.license:
            hdr.license = u""

