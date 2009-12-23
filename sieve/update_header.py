# -*- coding: UTF-8 -*-

"""
Initialize and update the PO header with own translation data.

When work on a pristine PO starts, or an existing PO is to be revised with
new translations, this sieve can be used to automatically set PO header
fields to proper values. The revision date is taken as current, while
the rest of information is pulled from L{Pology's configuration<misc.config>}.

Sieve options:
  - C{proj:<project_id>}: ID of the project
  - C{init}: treat the header as uninitialized
  - C{onmod}: update header only if the catalog was otherwise modified
        (when the sieve is used in chain)

Parameter C{proj} specifies the ID of the project which covers the POs
about to be operated on. This ID is used as the name of configuration
section C{[project-<ID>]}, which contains the project data fields.
Also used are the fields under the C{[user]} section, unless overriden
in project's section. The configuration fields used are:
  - C{[project-*]/name} or C{[user]/name}: user's name
  - C{[project-*]/email} or C{[user]/email}: user's email address
  - C{[project-*]/language}: language code (IS0 639)
  - C{[project-*]/language-team}: human-readable language name
  - C{[project-*]/team-email}: team's email
  - C{[project-*]/encoding}: encoding of PO files (UTF-8 assumed if not set)
  - C{[project-*]/plural-forms}: the PO plural header (C{nplurals=...; ...;})
  - C{[project-*]/po-editor} or C{[user]/po-editor}: the tool used
        to work on PO files (none assumed if not set)

Non-default header fields are not touched, except the revision date and
the last translator which are always updated (including the comment
line, where translators are listed with years of contributions).
Option C{init} may be used to force setting all fields as if the header
were uninitialized, overwriting any previous content.

An example of configuration appropriate for this sieve would be::

    [user]
    name = Chusslove Illich
    original-name = Часлав Илић
    email = caslav.ilic@gmx.net
    po-editor = Kate

    [project-kde]
    language = sr
    language-team = Serbian
    team-email = kde-i18n-sr@kde.org
    plural-forms = nplurals=4; plural=n==1 ? 3 : n%%10==1 && \\
                   n%%100!=11 ? 0 : n%%10>=2 && n%%10<=4 && \\
                   (n%%100<10 || n%%100>=20) ? 1 : 2;

In C{plural-forms} field, note escaped percent characters by doubling them
(because single C{%} in configuration has special meaning) and splitting
into several lines by trailing C{\\} (for better look only).

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import re
import time

import pology.misc.config as config
from pology.misc.report import warning
from pology.sieve import SieveError


def setup_sieve (p):

    p.set_desc(
    "Initialize or update the PO header with own translator data."
    )
    p.add_param("proj", unicode, mandatory=True,
                metavar="ID",
                desc=
    "Project ID in Pology configuration file, "
    "which contains the necessary project data to update the header."
    )
    p.add_param("init", bool, defval=False,
                desc=
    "Consider header as uninitialized, removing any existing information "
    "before adding own and project data."
    )
    p.add_param("onmod", bool, defval=False,
                desc=
    "Update header only if the catalog was otherwise modified "
    "(in sieve chains)."
    )


class Sieve (object):

    def __init__ (self, params):

        self.p = params

        # Collect user and project configuration.
        prjsect = "project-" + params.proj
        if not config.has_section(prjsect):
            raise SieveError("project '%s' not defined in configuration"
                             % params.proj)
        self.prjcfg = config.section(prjsect)
        prjcfg = config.section(prjsect)
        usrcfg = config.section("user")

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
        self.encoding = prjcfg.string("encoding", "UTF-8")
        self.plforms = prjcfg.string("plural-forms")
        if not self.plforms:
            warning("'plural-forms' not set in project configuration")
        self.lemail = prjcfg.string("team-email") # ok not to be present
        self.poeditor = (    prjcfg.string("po-editor")
                          or usrcfg.string("po-editor")) # ok not to be present


    def process_header (self, hdr, cat):

        if self.p.onmod and cat.modcount == 0:
            return

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

        # - PO editor
        if self.poeditor:
            hdr.set_field(u"X-Generator", unicode(self.poeditor))
        else:
            hdr.remove_field(u"X-Generator")

        # ------------------------------------------------
        # Fields updated only when at defaults (or forced)

        init = self.p.init

        # - title
        reset_title = init is True
        for line in hdr.title:
            if "TITLE" in line:
                reset_title = True
                break
        if not hdr.title or reset_title:
            if self.language:
                hdr.title[:] = [u"Translation of %s into %s."
                                % (cat.name, self.language)]
            else:
                hdr.title[:] = [u"Translation of %s." % (cat.name)]

        # - project ID
        fval = hdr.get_field_value("Project-Id-Version")
        if fval is not None and ("PACKAGE" in fval or init):
            hdr.set_field(u"Project-Id-Version", unicode(cat.name))

        # - language team
        fval = hdr.get_field_value("Language-Team")
        if self.language and fval is not None and ("LANGUAGE" in fval or init):
            hdr.set_field(u"Language-Team", unicode(tm_ident))

        # - language code
        fval = hdr.get_field_value("Language")
        if self.lang and fval is not None and (not fval.strip() or init):
            hdr.set_field(u"Language", unicode(self.lang),
                          after="Language-Team")

        # - encoding
        fval = hdr.get_field_value("Content-Type")
        if self.encoding and fval is not None and ("CHARSET" in fval or init):
            ctval = u"text/plain; charset=%s" % self.encoding
            hdr.set_field(u"Content-Type", unicode(ctval))

        # - transfer encoding
        fval = hdr.get_field_value("Content-Transfer-Encoding")
        if fval is not None and ("ENCODING" in fval or init):
            hdr.set_field(u"Content-Transfer-Encoding", u"8bit")

        # - plural forms
        fval = hdr.get_field_value("Plural-Forms")
        if self.plforms and fval is not None and ("INTEGER" in fval or init):
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

