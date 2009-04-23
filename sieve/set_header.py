# -*- coding: UTF-8 -*-

"""
Set elements of the PO header.

Sometimes a certain header field or comment needs to be updated throughout POs,
and this sieve serves that purpose.

Sieve parameters for setting a field:
  - C{field:<name>:<value>}: set the named field to the given value
  - C{create}: add the field if not present
  - C{after:<name>}: when adding a field, add it after the given field
  - C{before:<name>}: when adding a field, add it before the given field
  - C{reorder}: reinsert the field to match implied order

The C{field} parameter takes the exact name of the header field and
a value to set it to. But, by itself it will set the field only if it
is already present in the header. To create the field if not present,
C{create} option must be given. If the field is being added, parameters
C{after} and C{before} can be used to specify where to insert it;
by default the new field is appended at the end of the header.
If the field is present, using the option C{reorder} it can be moved within
the header to match the order implied by C{after} and C{before}.

Sieve parameters for setting comments:
  - C{title}: set the title comment to the given value
  - C{copyright}: set the copyright comment to the given value
  - C{license}: set the license comment to the given value
  - C{author}: set the author comment to the given value

The C{author} parameter can be repeated to set several authors.
All existing authors are removed before setting the new ones
(regardless of the number of each),
i.e. the new authors are I{not} appended to the old.

Comment values are checked for some minimal consistency,
e.g. author comments must contain email addresses,
licence comments the word 'licence',
etc.

Value strings (both of fields and comments) may contain %-directives,
which are expanded to catalog-dependent substrings prior to setting the value.
These are:
  - C{%poname}: catalog name (equal to file name without C{.po} extension)

If literal %-sign is needed, it can be escaped by entering C{%%}.
The directive can also be given with braces, as C{%{...}},
if its use would be ambiguous otherwise.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import re
import time

from pology.sieve import SieveError
from pology.misc.report import report, warning
from pology.misc.resolve import expand_vars


def setup_sieve (p):

    p.set_desc(
    "Set elements of the PO header."
    "\n\n"
    "Sometimes a certain header field needs to be updated throught many POs, "
    "and this sieve serves that purpose."
    "\n\n"
    "Note that %%-character in the value is used to expand some preset "
    "variables. Currently these are: %%%(poname)s - name of the catalog. "
    "If literal %% is needed (e.g. in plural forms), it can be escaped as %%%%."
    % dict(poname="poname")
    )

    p.add_param("field", unicode, multival=True,
                metavar="FIELD:VALUE",
                desc=
    "Set a header field to the given value. "
    "This parameter can be repeated, to set several fields in single run."
    )
    p.add_param("create", bool, defval=False,
                desc=
    "Add the field if not present "
    "(by default the field is set only if it already exists in the header)."
    )
    p.add_param("after", unicode,
                metavar="FIELD",
                desc=
    "When the new field is being added, add it after this field. "
    "If such field does not exist, the new field is added as the last one."
    )
    p.add_param("before", unicode,
                metavar="FIELD",
                desc=
    "When the new field is being added, add it before this field. "
    "If such field does not exist, the new field is added as the last one."
    )
    p.add_param("reorder", bool, defval=False,
                desc=
    "If the field to be set is present, but not in the order implied by "
    "'%(after)s' and '%(before)s' parameters, reinsert it accordingly."
    % dict(after="after", before="before")
    )
    p.add_param("title", unicode,
                metavar="VALUE",
                desc=
    "Set title comment to the given value."
    )
    p.add_param("copyright", unicode,
                metavar="VALUE",
                desc=
    "Set copyright comment to the given value."
    )
    p.add_param("license", unicode,
                metavar="VALUE",
                desc=
    "Set license comment to the given value."
    )
    p.add_param("author", unicode, multival=True,
                metavar="VALUE",
                desc=
    "Set author comment to the given value. "
    "This parameter can be repeated to set several authors. "
    "All existing authors are removed before setting the new ones."
    )


class Sieve (object):

    def __init__ (self, params):

        # Parse field setting specifications.
        self.fields_values = []
        for field_value_str in (params.field or []):
            field_value = field_value_str.split(":", 1)
            if len(field_value) != 2:
                raise SieveError("invalid specification of header field "
                                 "and value: %s" % field_value_str)
            self.fields_values.append(field_value)
        # Set fields in reverse, so that 'after' and 'before' parameters
        # are followed by the order of appearance of fields in command line.
        self.fields_values.reverse()

        # Check validity of comment values.
        if params.copyright is not None:
            if not re.search("copyright", params.copyright):
                raise SieveError("invalid value for copyright comment "
                                 "(missing word 'copyright'?): %s"
                                 % params.copyright)
        if params.license is not None:
            if not re.search("license", params.license):
                raise SieveError("invalid value for license comment "
                                 "(missing word 'license'?): %s"
                                 % params.license)
        for author in (params.author or []):
            if not re.search("<.*@.*>", author):
                raise SieveError("invalid value for author comment "
                                 "(missing email address?): %s"
                                 % author)
        self.p = params


    def process_header (self, hdr, cat):

        pvars = {"poname" : cat.name}

        for field, value in self.fields_values:
            if self.p.create or hdr.select_fields(field):
                hdr.set_field(field, expand_vars(value, pvars),
                              after=self.p.after, before=self.p.before,
                              reorder=self.p.reorder)

        if self.p.title is not None:
            hdr.title[:] = [expand_vars(self.p.title, pvars)]
        if self.p.copyright is not None:
            hdr.copyright = expand_vars(self.p.copyright, pvars)
        if self.p.license is not None:
            hdr.license = expand_vars(self.p.license, pvars)
        if self.p.author is not None:
            hdr.author[:] = [expand_vars(x, pvars) for x in self.p.author]

