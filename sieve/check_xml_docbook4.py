# -*- coding: UTF-8 -*-

"""
Lightweight validity checking of POs containing Docbook XML.

Docbook is a complex XML application, and nothing short of full validation
of XML files generated from translated POs can show it correct for sure.
This sieve just checks for well-formedness and mere existance of a tag in
Docbook subset, and on a single PO entry level.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import sys
import os
import re
import locale
import xml.parsers.expat
from pology.misc.report import report_on_msg
from pology import rootdir

# ----------------------------------------
# Informal Docbook specification.

# Collect tags and attributes from the companion file.
specfile = os.path.join(rootdir(), "sieve", "check_xml_docbook4-spec.txt")
ifl = open(specfile, "r")
stripc_rx = re.compile(r"#.*")
specstr = "".join([stripc_rx.sub('', x) for x in ifl.readlines()])
ifl.close()
docbook_tagattrs = {}
for elspec in specstr.split(";"):
    lst = elspec.split(":")
    tag = lst.pop(0).strip()
    docbook_tagattrs[tag] = {}
    if lst:
        attrs = lst[0].split()
        docbook_tagattrs[tag] = dict([(attr, True) for attr in attrs])

# Add dummy top tag.
dummy_top = "dummytop123"
docbook_tagattrs[dummy_top] = {}

# Add common attributes to each tag.
cattrs = docbook_tagattrs.pop("pe-common-attrib")
for attrs in docbook_tagattrs.itervalues():
    attrs.update(cattrs)

# ----------------------------------------
# Check well-formedness and existence of tags.

# Links to current state for the handlers.
_c_cat = None
_c_msg = None
_c_quiet = False
_c_errcnt = 0


# Handler to check existence of tags.
def _handler_start_element (name, attrs):

    global _c_errcnt

    # Check existence of tag.
    if name not in docbook_tagattrs:
        _c_errcnt += 1
        if not _c_quiet:
            report_on_msg("unrecognized Docbook tag: %s" % name, _c_msg, _c_cat)
        return

    # Check applicability of attributes.
    for attr in attrs:
        if attr not in docbook_tagattrs[name]:
            _c_errcnt += 1
            if not _c_quiet:
                report_on_msg(  "invalid attribute for Docbook tag <%s>: %s"
                              % (name, attr), _c_msg, _c_cat)


# Check current msgstr.
def check_xml_docbook (cat, msg, msgstr, quiet=False):

    # Link current state for handlers.
    global _c_cat; _c_cat = cat
    global _c_msg; _c_msg = msg
    global _c_quiet; _c_quiet = quiet
    global _c_errcnt; _c_errcnt = 0

    text = msgstr

    # Make sure the text has a top tag, for the parser not to bitch.
    text = "<%s>%s</%s>" % (dummy_top, text, dummy_top)

    # Parse the text.
    p = xml.parsers.expat.ParserCreate()
    p.UseForeignDTD() # not to barf on non-default XML entities
    p.StartElementHandler = _handler_start_element

    try:
        p.Parse(text.encode("UTF-8"), True)
    except xml.parsers.expat.ExpatError, inst:
        if not quiet:
            report_on_msg("Docbook parsing: %s" % inst, _c_msg, _c_cat)
        return False

    return _c_errcnt == 0

# ----------------------------------------
# The checker sieve.

class Sieve (object):
    """Weakly check validity of Docbook XML."""

    def __init__ (self, options, global_options):

        self.nbad = 0

        # Indicators to the caller:
        self.caller_sync = False # no need to sync catalogs to the caller
        self.caller_monitored = False # no need for monitored messages


    def process (self, msg, cat):

        # Check only translated messages.
        if not msg.translated:
            return

        # Check XML in translation.
        for msgstr in msg.msgstr:
            if not check_xml_docbook(cat, msg, msgstr):
                self.nbad += 1


    def finalize (self):

        if self.nbad > 0:
            print "Total translations with invalid Docbook: %d" % self.nbad

