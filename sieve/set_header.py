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

The {field} parameter takes the exact name of the header field and
a value to set it to. But, by itself it will set the field only if it
is already present in the header. To create the field if not present,
C{create} option must be given. If the field is being added, parameters
C{after} and C{before} can be used to specify where to insert it;
by default the new field is appended at the end of the header.
If the field is present, using the option C{reorder} it can be moved within
the header to match the order implied by C{after} and {before}.

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


class Sieve (object):

    def __init__ (self, options, global_options):

        # Setting a field.
        self.field = None
        if "field" in options:
            self.field, self.value = options["field"].split(":", 1)
            options.accept("field")

        # Should the field be created if not present?
        self.create = False
        if "create" in options:
            self.create = True
            options.accept("create")

        # After or before which field to add the new one?
        self.after = None
        if "after" in options:
            self.after = options["after"]
            options.accept("after")
        self.before = None
        if "before" in options:
            self.before = options["before"]
            options.accept("before")

        # Can the field be reordered?
        self.reorder = False
        if "reorder" in options:
            self.reorder = True
            options.accept("reorder")


    def process_header (self, hdr, cat):

        if self.field and (self.create or hdr.select_fields(self.field)):
            pvars = {"poname" : cat.name}
            value = expand_vars(self.value, pvars)
            hdr.set_field(self.field, value,
                          after=self.after, before=self.before,
                          reorder=self.reorder)

