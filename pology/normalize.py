# -*- coding: UTF-8 -*-

"""
Various normalizations for strings and PO elements.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import os
import re
import unicodedata

from pology import _, n_
from pology.message import MessageUnsafe
from pology.monitored import Monlist, Monpair
from pology.report import warning


_wsseq_rx = re.compile(r"[ \t\n]+", re.U)

def simplify (s):
    """
    Simplify ASCII whitespace in the string.

    All leading and trailing ASCII whitespace are removed,
    all inner ASCII whitespace sequences are replaced with space.

    @param s: string to normalize
    @type s: string

    @returns: normalized string
    @rtype: string
    """

    return _wsseq_rx.sub(" ", s.strip())


_uwsseq_rx = re.compile(r"\s+", re.U)

def usimplify (s):
    """
    Simplify whitespace in the string.

    Like L{simplify}, but takes into account all whitespace defined by Unicode.

    @param s: string to normalize
    @type s: string

    @returns: normalized string
    @rtype: string
    """

    return _uwsseq_rx.sub(" ", s.strip())


def shrink (s):
    """
    Remove all whitespace from the string.

    @param s: string to normalize
    @type s: string

    @returns: normalized string
    @rtype: string
    """

    return _uwsseq_rx.sub("", s)


def tighten (s):
    """
    Remove all whitespace and lowercase the string.

    @param s: string to normalize
    @type s: string

    @returns: normalized string
    @rtype: string
    """

    return _uwsseq_rx.sub("", s.lower())


_non_ascii_ident_rx = re.compile(r"[^a-z0-9_]", re.U|re.I)

def identify (s):
    """
    Construct an uniform-case ASCII-identifier out of the string.

    ASCII-identifier is constructed in the following order:
      - string is decomposed into Unicode NFKD
      - string is lowercased
      - every character that is neither an ASCII alphanumeric nor
        the underscore is removed
      - if the string starts with a digit, underscore is prepended

    @param s: string to normalize
    @type s: string

    @returns: normalized string
    @rtype: string
    """

    ns = s

    # Decompose.
    ns = unicodedata.normalize("NFKD", ns)

    # Lowercase.
    ns = ns.lower()

    # Remove non-identifier chars.
    ns = _non_ascii_ident_rx.sub("", ns) 

    # Prefix with underscore if first char is digit.
    if ns[0:1].isdigit():
        ns = "_" + ns

    return ns


def xentitize (s):
    """
    Replace characters having default XML entities with the entities.

    The replacements are:
      - C{&amp;} for ampersand
      - C{&lt} and C{&gt;} for less-than and greater-then signs
      - C{&apos;} and C{&quot;} for ASCII single and double quotes

    @param s: string to normalize
    @type s: string

    @returns: normalized string
    @rtype: string
    """

    ns = s
    ns = ns.replace("&", "&amp;") # must come first
    ns = ns.replace("<", "&lt;")
    ns = ns.replace(">", "&gt;")
    ns = ns.replace("'", "&apos;")
    ns = ns.replace('"', "&quot;")

    return ns


def demangle_srcrefs (collsrcs=None, collsrcmap=None, truesrcheads=None,
                      compexts=None):
    """
    Resolve source references in message created by intermediate extraction
    [hook factory].

    Sometimes the messages from a source file in the format not known
    to C{xgettext(1)} are first extracted by a preextraction tool into
    a format known to C{xgettext}, and then by C{xgettext} to PO template.
    This is the intermediate extraction, and the files that C{xgettext}
    gets to operate on are intermediate files.

    When intermediate extraction is performed, the source references in
    the resulting PO template are going to be "mangled", pointing to
    the intermediate files rather than to the true source files.
    This hook factory will produce a function that will resolve
    intermediate into true source reference, "demangle" them, where possible.

    One mode of intermediate extraction is to extract multiple sources
    into a collective intermediate file. This file may have standardized
    name throughout a collection of catalogs, or it may be special
    by catalog. For demangling to be possible in this case,
    the preextraction tool has to provide true source references
    in the extracted comments (C{#.}) of the messages.
    When that is the case, parameter C{collsrcs} is used to specify
    the sequence of names of generally known intermediate files,
    parameter C{collsrcmap} of those specific by catalog
    (as dictionary of catalog name to sequence of intermediate file names),
    and parameter C{truesrcheads} specifies the sequence of initial strings
    in extracted comments which are followed by the true source reference.
    (If C{truesrcheads} is C{None} or empty, this mode of demangling
    is disabled.)

    For example, collective-intermediate extraction::

        #. file: apples.clt:156
        #: resources.cpp:328
        msgid "Granny Smith"
        msgstr ""

        #. file: peaches.clt:49
        #: resources.cpp:2672
        msgid "Redhaven"
        msgstr ""

    is demangled by setting C{collsrcs=["resources.cpp"]}
    and C{truesrcheads=["file:"]}.

    Another mode of intermediate extraction is to for each source file
    to be extracted into a single paired intermediate file,
    which is named same as the true source plus an additional extension.
    In this mode, parameter C{compexts} specifies the list of known
    composite extensions (including the leading dot), which
    will be demangled by stripping the final extension from the path.

    For example, paired-intermediate extraction::

        #: apples.clt.h:156
        msgid "Granny Smith"
        msgstr ""

        #: peaches.clt.h:49
        msgid "Redhaven"
        msgstr ""

    is demangled by setting C{compexts=[".clt.h"]}.

    @param collsrcs: general intermediate file names
    @type collsrcs: <string*>
    @param collsrcmap: catalog-specific intermediate file names
    @type collsrcmap: {string: <string*>*}
    @param truesrcheads: prefixes to true file references in comments
    @type truesrcheads: <string*>
    @param compexts: composite intermediate file extensions
    @type compexts: <string*>

    @return: type F4A hook
    @rtype: C{(cat, msg) -> numerr}
    """

    def hook (msg, cat):

        numerr = 0

        truerefs = []

        # Demangle source references in collective-intermediate mode
        if truesrcheads:
            # Collect source references from extracted comments.
            cmnts = []
            for cmnt in msg.auto_comment:
                hasrefs = False
                for head in truesrcheads:
                    if cmnt.startswith(head):
                        refs = [x.split(":")
                                for x in cmnt[len(head):].split()]
                        hasrefs = all((len(x) == 2 and x[1].isdigit)
                                        for x in refs)
                        if not hasrefs:
                            numerr += 1
                        break
                if hasrefs:
                    refs = [(path, int(lno)) for path, lno in refs]
                    truerefs.extend(refs)
                else:
                    cmnts.append(cmnt)
            msg.auto_comment[:] = cmnts

            # Exclude intermediates from source references.
            for path, lno in msg.source:
                bname = os.path.basename(path)
                if (not (   (collsrcs and bname in collsrcs)
                         or (    collsrcmap
                             and bname in collsrcmap.get(cat.name, {})))
                ):
                    truerefs.append((path, lno))

        # Demangle source references in paired-intermediate mode
        if compexts:
            for path, lno in msg.source:
                for ext in compexts:
                    if path.endswith(ext):
                        p = path.rfind(".")
                        if p > 0:
                            path = path[:p]
                        else:
                            numerr += 1
                        break
                truerefs.append((path, lno))

        if isinstance(msg, MessageUnsafe):
            msg.source = truerefs
        else:
            msg.source = Monlist(map(Monpair, truerefs))

        return numerr

    return hook


def uniq_source (msg, cat):
    """
    Make message source references unique [type F4A hook].

    Sometimes source references of a message can be non-unique
    due to particularities of extraction or later processing.
    This hook makes them unique, while preserving the ordering.
    """

    uniqrefs = []
    for path, line in msg.source:
        ref = (os.path.normpath(path), line)
        if ref not in uniqrefs:
            uniqrefs.append(ref)

    if isinstance(msg, MessageUnsafe):
        msg.source = uniqrefs
    else:
        msg.source = Monlist(map(Monpair, uniqrefs))



def uniq_auto_comment (onlyheads=None):
    """
    Remove non-unique automatic comment lines in message [hook factory].

    Sometimes the message extraction tool adds automatic comments
    to provide more context for the message
    (for example, XML tag path to the current message).
    If the message is found more than once in the same context,
    such comment lines get repeated.
    This hook can be used to make auto comment lines unique;
    either fully, or only those with certain prefixes given
    by C{onlyheads} parameter.

    @param onlyheads: prefixes of comment lines which should be made unique
    @type onlyheads: <string*>

    @return: type F4A hook
    @rtype: C{(cat, msg) -> numerr}
    """

    if onlyheads is not None and not isinstance(onlyheads, tuple):
        onlyheads = tuple(onlyheads)

    def hook (msg, cat):

        seen_cmnts = set()
        cmnts = []
        for cmnt in msg.auto_comment:
            if onlyheads is None or cmnt.startswith(onlyheads):
                if cmnt not in seen_cmnts:
                    cmnts.append(cmnt)
                    seen_cmnts.add(cmnt)
            else:
                cmnts.append(cmnt)
        msg.auto_comment[:] = cmnts

    return hook


def canonical_header (hdr, cat):
    """
    Check and rearrange content of a PO header into canonical form
    [type F4B hook].

    @return: number of errors
    @rtype: int
    """

    nerr = 0

    nerr += _fix_authors(hdr, cat)

    return nerr


_yr1_rx = re.compile(ur"^\s*(\d{4}|\d{2})\s*$")
_yr2_rx = re.compile(ur"^\s*(\d{4}|\d{2})\s*[-—–]\s*(\d{4}|\d{2})\s*$")

def _fix_authors (hdr, cat):

    nerr = 0

    # Parse authors data from the header.
    authors = {}
    problems = False
    pos = 0
    for a in hdr.author:
        pos += 1

        m = re.search(r"(.*?)<(.*?)>(.*)$", a)
        if not m:
            warning(_("@info",
                      "%(file)s: Cannot parse name and email address "
                      "from translator comment '%(cmnt)s'.",
                      file=cat.filename, cmnt=a))
            problems = True
            nerr += 1
            continue
        name, email, rest = m.groups()
        name = simplify(name)
        email = simplify(email)

        m = re.search(r"^\s*,(.+?)\.?\s*$", rest)
        if not m:
            warning(_("@info",
                      "%(file)s: Missing years in "
                      "translator comment '%(cmnt)s'.",
                      file=cat.filename, cmnt=a))
            problems = True
            nerr += 1
            continue
        yearstr = m.group(1)

        years = []
        for yspec in yearstr.split(","):
            m = _yr1_rx.search(yspec) or _yr2_rx.search(yspec)
            if not m:
                warning(_("@info",
                          "%(file)s: Cannot parse years in "
                          "translator comment '%(cmnt)s'.",
                          file=cat.filename, cmnt=a))
                problems = True
                nerr += 1
                break
            if len(m.groups()) == 1:
                ystr = m.group(1)
                if len(ystr) == 2:
                    ystr = (ystr[0] == "9" and "19" or "20") + ystr
                years.append(int(ystr))
            else:
                years.extend(range(int(m.group(1)), int(m.group(2)) + 1))
        if not years:
            continue

        if name not in authors:
            authors[name] = {"email": "", "pos": 0, "years": set()}
        authors[name]["email"] = email
        authors[name]["pos"] = pos
        authors[name]["years"].update(years)

    # If there were any problems, do not touch author comments.
    if problems:
        return nerr

    # Post-process authors data.
    authlst = []
    for name, adata in authors.items():
        adata["years"] = list(adata["years"])
        adata["years"].sort()
        adata["years"] = map(str, adata["years"])
        adata["name"] = name
        authlst.append(adata)

    authlst.sort(key=lambda x: (min(x["years"]), x["pos"]))

    # Construct new author comments.
    authcmnts = Monlist()
    for a in authlst:
        acmnt = u"%s <%s>, %s." % (a["name"], a["email"],
                                    ", ".join(a["years"]))
        authcmnts.append(acmnt)

    hdr.author = authcmnts

    return nerr

