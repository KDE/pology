# -*- coding: UTF-8 -*-

"""
Set elements of the PO header.

Documented in C{doc/user/sieving.docbook}.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import time
import re

from pology import _, n_
from pology.report import report, warning
from pology.resolve import expand_vars
from pology.sieve import SieveError


def setup_sieve (p):

    p.set_desc(_("@info sieve discription",
    "Set elements of the PO header."
    "\n\n"
    "Sometimes a header field needs to be modified, added or removed "
    "in many catalogs, and this sieve serves that purpose."
    "\n\n"
    "%%-character in the value is used to expand known variables. "
    "Currently these are: %%%(var1)s - name of the catalog. "
    "If literal %% is needed (e.g. in plural forms header), "
    "it can be escaped as %%%%.",
    var1="poname"
    ))

    p.add_param("field", str, multival=True,
                metavar=_("@info sieve parameter value placeholder", 
                          "FIELD:VALUE"),
                desc=_("@info sieve parameter discription",
    "Set a header field to the given value. "
    "This parameter can be repeated, to set several fields in single run."
    ))
    p.add_param("create", bool, defval=False,
                desc=_("@info sieve parameter discription",
    "Add the field if not present "
    "(by default the field value is set only if the field already exists "
    "in the header)."
    ))
    p.add_param("after", str,
                metavar=_("@info sieve parameter value placeholder", "FIELD"),
                desc=_("@info sieve parameter discription",
    "When the new field is being added, add it after this field. "
    "If such field does not exist, the new field is added as the last one."
    ))
    p.add_param("before", str,
                metavar=_("@info sieve parameter value placeholder", "FIELD"),
                desc=_("@info sieve parameter discription",
    "When the new field is being added, add it before this field. "
    "If such field does not exist, the new field is added as the last one."
    ))
    p.add_param("reorder", bool, defval=False,
                desc=_("@info sieve parameter discription",
    "If the field to be set is present, but not in the order implied by "
    "'%(par1)s' and '%(par2)s' parameters, reinsert it accordingly.",
    par1="after", par2="before"
    ))
    p.add_param("remove", str, multival=True,
                metavar=_("@info sieve parameter value placeholder", "FIELD"),
                desc=_("@info sieve parameter discription",
    "Remove the field."
    ))
    p.add_param("removerx", str, multival=True,
                metavar=_("@info sieve parameter value placeholder", "REGEX"),
                desc=_("@info sieve parameter discription",
    "Remove all fields matching the regular expression. "
    "Matching is not case-sensitive."
    ))
    p.add_param("title", str, multival=True,
                metavar=_("@info sieve parameter value placeholder", "VALUE"),
                desc=_("@info sieve parameter discription",
    "Set title comment to the given value."
    "Can be repeated to set several title lines. "
    "All existing title lines are removed before setting the new ones."
    ))
    p.add_param("rmtitle", bool, defval=False,
                desc=_("@info sieve parameter discription",
    "Remove title comments."
    ))
    p.add_param("copyright", str,
                metavar=_("@info sieve parameter value placeholder", "VALUE"),
                desc=_("@info sieve parameter discription",
    "Set copyright comment to the given value."
    ))
    p.add_param("rmcopyright", bool, defval=False,
                desc=_("@info sieve parameter discription",
    "Remove the copyright comment."
    ))
    p.add_param("license", str,
                metavar=_("@info sieve parameter value placeholder", "VALUE"),
                desc=_("@info sieve parameter discription",
    "Set license comment to the given value."
    ))
    p.add_param("rmlicense", bool, defval=False,
                desc=_("@info sieve parameter discription",
    "Remove the license comment."
    ))
    p.add_param("author", str, multival=True,
                metavar=_("@info sieve parameter value placeholder", "VALUE"),
                desc=_("@info sieve parameter discription",
    "Set author comment to the given value. "
    "Can be repeated to set several authors. "
    "All existing authors are removed before setting the new ones."
    ))
    p.add_param("rmauthor", bool, defval=False,
                desc=_("@info sieve parameter discription",
    "Remove author comments."
    ))
    p.add_param("comment", str, multival=True,
                metavar=_("@info sieve parameter value placeholder", "VALUE"),
                desc=_("@info sieve parameter discription",
    "Set free comment to the given value. "
    "Can be repeated to set several free comment lines. "
    "All existing comment lines are removed before setting the new ones."
    ))
    p.add_param("rmcomment", bool, defval=False,
                desc=_("@info sieve parameter discription",
    "Remove free comments."
    ))
    p.add_param("rmallcomm", bool, defval=False,
                desc=_("@info sieve parameter discription",
    "Remove all header comments."
    ))


class Sieve (object):

    def __init__ (self, params):

        # Parse field setting specifications.
        self.fields_values = []
        for field_value_str in (params.field or []):
            field_value = field_value_str.split(":", 1)
            if len(field_value) != 2:
                raise SieveError(
                    _("@info",
                      "Invalid specification '%(spec)s' "
                      "of header field and value.",
                      spec=field_value_str))
            self.fields_values.append(field_value)

        # Set fields in reverse, so that 'after' and 'before' parameters
        # are followed by the order of appearance of fields in command line.
        if params.after or params.before:
            self.fields_values.reverse()

        # Prepare matching for field removal.
        if params.removerx is not None:
            rxs = []
            for rxstr in params.removerx:
                try:
                    rx = re.compile(rxstr, re.U|re.I)
                except:
                    raise SieveError(
                        _("@info",
                          "Invalid regular expression '%(regex)s' "
                          "for removing fields.",
                          regex=rxstr))
                rxs.append(rx)
            params.removerx = rxs

        # Check validity of comment values.
        for title in (params.title or []):
            if re.search(r"copyright|©|\(C\)|license|<.*?@.*?>",
                         title, re.I|re.U):
                raise SieveError(
                    _("@info",
                      "Invalid value '%(val)s' for title comment "
                      "(it contains some elements appropriate "
                      "for other types of comments).",
                      val=title))
        if params.copyright is not None:
            if not re.search(r"copyright|©|\(C\)", params.copyright, re.I|re.U):
                raise SieveError(
                    _("@info",
                      "Invalid value '%(val)s' for copyright comment "
                      "(missing the word 'copyright'?).",
                      val=params.copyright))
        if params.license is not None:
            if not re.search(r"license", params.license, re.I):
                raise SieveError(
                    _("@info",
                      "Invalid value '%(val)s' for license comment "
                      "(missing the word 'license'?).",
                      val=params.license))
        for author in (params.author or []):
            if not re.search(r"<.*?@.*?>", author):
                raise SieveError(
                    _("@info",
                      "Invalid value '%(val)s' for author comment "
                      "(missing the email address?).",
                      val=author))
        self.p = params


    def process_header (self, hdr, cat):

        pvars = {"poname" : cat.name}

        for rmname in self.p.remove or []:
            hdr.remove_field(rmname)
        for rmrx in self.p.removerx or []:
            to_remove = set()
            for name, value in hdr.field:
                if name not in to_remove and rmrx.search(name):
                    to_remove.add(name)
            for name in to_remove:
                hdr.remove_field(name)

        for field, value in self.fields_values:
            if self.p.create or hdr.select_fields(field):
                hdr.set_field(field, expand_vars(value, pvars),
                              after=self.p.after, before=self.p.before,
                              reorder=self.p.reorder)

        if self.p.rmtitle or self.p.rmallcomm:
            hdr.title[:] = []
        if self.p.title is not None:
            hdr.title[:] = [expand_vars(x, pvars) for x in self.p.title]
        if self.p.rmcopyright or self.p.rmallcomm:
            hdr.copyright = None
        if self.p.copyright is not None:
            hdr.copyright = expand_vars(self.p.copyright, pvars)
        if self.p.rmlicense or self.p.rmallcomm:
            hdr.license = None
        if self.p.license is not None:
            hdr.license = expand_vars(self.p.license, pvars)
        if self.p.rmauthor or self.p.rmallcomm:
            hdr.author[:] = []
        if self.p.author is not None:
            hdr.author[:] = [expand_vars(x, pvars) for x in self.p.author]
        if self.p.rmcomment or self.p.rmallcomm:
            hdr.comment[:] = []
        if self.p.comment is not None:
            hdr.comment[:] = [expand_vars(x, pvars) for x in self.p.comment]

