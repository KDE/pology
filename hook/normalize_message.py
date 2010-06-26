# -*- coding: UTF-8 -*-

"""
Various normalizations of messages.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import os

from pology.file.message import MessageUnsafe
from pology.misc.monitored import Monlist, Monpair


def demangle_srcrefs (collsrcs=None, collsrcmap=None, truesrcheads=None,
                      compexts=None):
    """
    Resolve source references created by intermediate extraction [hook factory].

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
    Make source references unique [type F4A hook].

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
    Remove non-unique auto comment lines [hook factory].

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

