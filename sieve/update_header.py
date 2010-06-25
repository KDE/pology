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

import os
import re
import time

from pology import _, n_
import pology.misc.config as config
from pology.misc.report import warning
from pology.misc.resolve import expand_vars
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
        self.langcode = prjcfg.string("language")
        if not self.langcode:
            warning(_("@info",
                      "Field '%(field)s' is not set in "
                      "project configuration.",
                      field="language"))
        self.encoding = prjcfg.string("encoding", "UTF-8")
        self.plforms = prjcfg.string("plural-forms")
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

            update_header(cat, project=cat.name, title=title,
                          name=self.name, email=self.email,
                          teamemail=self.teamemail,
                          langname=self.langteam, langcode=self.langcode,
                          encoding=self.encoding, ctenc="8bit",
                          plforms=self.plforms,
                          poeditor=self.poeditor)
        else:
            update_header(cat,
                          name=self.name, email=self.email,
                          poeditor=self.poeditor)


def update_header (cat, project=None, title=None, copyright=None, license=None,
                   name=None, email=None, teamemail=None,
                   langname=None, langcode=None, encoding=None, ctenc=None,
                   plforms=None, poeditor=None):
    """
    Update catalog header.

    If a piece of information is not given (i.e. C{None}),
    the corresponding header field is left unmodified.
    If it is given as empty string, the corresponding header field is removed.
    PO revision date is updated always, to current date.

    Some fields (as noted in parameter descriptions) are expanded on variables
    by applying the L{expand_vars<pology.misc.resolve.expand_vars>} function.
    For example::

         title="Translation of %project into %langname."

    The following variables are available:
      - C{%basename}: PO file base name
      - C{%poname}: PO file base name without .po extension
      - C{%project}: value of C{project} parameter (if not C{None}/empty)
      - C{%langname}: value of C{langname} parameter (if not C{None}/empty)
      - C{%langcode}: value of C{langcode} parameter (if not C{None}/empty)

    @param cat: catalog in which the header is to be updated
    @type cat: L{Catalog<pology.file.header.Catalog>}
    @param project: project name
    @type project: string
    @param title: translation title (expanded on variables)
    @type title: string
    @param copyright: copyright notice (expanded on variables)
    @type copyright: string
    @param license: license notice (expanded on variables)
    @type license: string
    @param name: translator's name
    @type name: string
    @param email: translator's email address
    @type email: string
    @param teamemail: language team's email address
    @type teamemail: string
    @param langname: full language name
    @type langname: string
    @param langcode: language code
    @type langcode: string
    @param encoding: text encoding
    @type encoding: string
    @param ctenc: content transfer encoding
    @type ctenc: string
    @param plforms: plural forms expression
    @type plforms: string
    @param poeditor: translator's PO editor
    @type poeditor: string

    @returns: reference to input header
    """

    varmap = {}
    varmap["basename"] = os.path.basename(cat.filename)
    varmap["poname"] = cat.name
    if project:
        varmap["project"] = project
    if langname:
        varmap["langname"] = langname
    if langcode:
        varmap["langcode"] = langcode
    varhead="%"

    hdr = cat.header

    if title:
        title = expand_vars(title, varmap, varhead)
        hdr.title[:] = [unicode(title)]
    elif title == "":
        hdr.title[:] = []

    if copyright:
        copyright = expand_vars(copyright, varmap, varhead)
        hdr.copyright = unicode(copyright)
    elif copyright == "":
        hdr.copyright = None

    if license:
        license = expand_vars(license, varmap, varhead)
        hdr.license = unicode(license)
    elif license == "":
        hdr.license = None

    if project:
        hdr.set_field(u"Project-Id-Version", unicode(project))
    elif project == "":
        hdr.remove_field(u"Project-Id-Version")

    rdate = time.strftime("%Y-%m-%d %H:%M%z")
    hdr.set_field(u"PO-Revision-Date", unicode(rdate))

    if name or email:
        if name and email:
            tr_ident = "%s <%s>" % (name, email)
        elif name:
            tr_ident = "%s" % name
        else:
            tr_ident = "<%s>" % email

        # Remove author placeholder.
        for i in range(len(hdr.author)):
            if u"FIRST AUTHOR" in hdr.author[i]:
                hdr.author.pop(i)
                break

        # Look for current author in the comments,
        # to update only years if present.
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

        hdr.set_field(u"Last-Translator", unicode(tr_ident))

    elif name == "" or email == "":
        hdr.remove_field(u"Last-Translator")

    if langname:
        tm_ident = None
        if langname and teamemail:
            tm_ident = "%s <%s>" % (langname, teamemail)
        elif langname:
            tm_ident = langname
        hdr.set_field(u"Language-Team", unicode(tm_ident))
    elif langname == "":
        hdr.remove_field(u"Language-Team")

    if langcode:
        hdr.set_field(u"Language", unicode(langcode), after="Language-Team")
    elif langcode == "":
        hdr.remove_field(u"Language")

    if encoding:
        ctval = u"text/plain; charset=%s" % encoding
        hdr.set_field(u"Content-Type", ctval)
    elif encoding == "":
        hdr.remove_field(u"Content-Type")

    if ctenc:
        hdr.set_field(u"Content-Transfer-Encoding", unicode(ctenc))
    elif ctenc == "":
        hdr.remove_field(u"Content-Transfer-Encoding")

    if plforms:
        hdr.set_field(u"Plural-Forms", unicode(plforms))
    elif plforms == "":
        hdr.remove_field(u"Plural-Forms")

    if poeditor:
        hdr.set_field(u"X-Generator", unicode(poeditor))
    elif poeditor == "":
        hdr.remove_field(u"X-Generator")

    return hdr

