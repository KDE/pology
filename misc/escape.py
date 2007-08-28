# -*- coding: UTF-8 -*-

import re

_escape_seqs = {
    "\n" : "\\n",
    "\t" : "\\t",
    "\"" : "\\\"",
    # do not try to handle \\, ambiguous!
};

_unescp_seqs = dict([(_escape_seqs[x], x) for x in _escape_seqs.keys()])
_rx_unescp_g = re.compile(r"(.*?)(\\.)")
_rx_escapes_g = re.compile(r"(.*?)(" + r"|".join(_escape_seqs.keys()) + r")")

def unescape_strict (s):
    ns = ""
    ie = 0
    for m in _rx_unescp_g.finditer(s):
        ie += len(m.group(1)) + len(m.group(2))
        ns += m.group(1)
        if _unescp_seqs.has_key(m.group(2)):
            ns += _unescp_seqs[m.group(2)]
        else:
            ns += m.group(2)
    ns += s[ie:]
    return ns

def unescape (s):
    """Less strict unescaping.

    This will do wrong thing upon e.g. \\n. Much faster, however, and
    usually enough.
    """
    ns = s;
    ns = ns.replace(r"\"", "\"")
    ns = ns.replace(r"\n", "\n")
    ns = ns.replace(r"\t", "\t")
    return ns;

def escape_strict (s):
    ns = ""
    ie = 0
    for m in _rx_escapes_g.finditer(s):
        ie += len(m.group(1)) + len(m.group(2))
        ns += m.group(1) + _escape_seqs[m.group(2)]
    ns += s[ie:]
    return ns

def escape (s):
    """Less strict escaping.

    Exactly reverse non-strict unescape.
    """
    ns = s;
    ns = ns.replace("\"", r"\"")
    ns = ns.replace("\n", r"\n")
    ns = ns.replace("\t", r"\t")
    return ns;

