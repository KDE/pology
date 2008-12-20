# -*- coding: UTF-8 -*-

"""
Set elements of the PO header.

Sometimes a certain header field needs to be updated throught all POs,
and this sieve serves that purpose.

For the moment, the only available operation is to set a certain field
to a given value. More operation modes may be implemented in the future.

Sieve options for setting a field:
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

Field value strings may contain %-directives, which are expanded to
catalog-dependent substrings prior to setting the value. These are:
  - C{%poname}: catalog name (equal to file name without C{.po} extension)

If literal %-sign is needed, it can be escaped by entering C{%%}.
The directive can also be given with braces, as C{%{...}},
if its use would be ambiguous otherwise.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import re
import time

from pology.misc.report import error, warning
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


class Sieve (object):

    def __init__ (self, params, options):

        # Parse field setting specifications.
        self.fields_values = []
        for field_value_str in (params.field or []):
            field_value = field_value_str.split(":", 1)
            if len(field_value) != 2:
                error("invalid specification of header field and value: %s"
                      % field_value_str)
            self.fields_values.append(field_value)
        # Set fields in reverse, so that 'after' and 'before' parameters
        # are followed by the order of appearance of fields in command line.
        self.fields_values.reverse()

        self.p = params


    def process_header (self, hdr, cat):

        pvars = {"poname" : cat.name}
        for field, value in self.fields_values:
            if self.p.create or hdr.select_fields(field):
                hdr.set_field(field, expand_vars(value, pvars),
                              after=self.p.after, before=self.p.before,
                              reorder=self.p.reorder)

