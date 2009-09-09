# -*- coding: UTF-8 -*-

"""
Check and rearrange content of PO header into canonical form.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import re

from pology.misc.report import warning
from pology.misc.monitored import Monlist
from pology.misc.normalize import simplify


def normalize_header (hdr, cat):

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
            warning("%s: cannot parse name and email address "
                    "from translator comment: %s"
                    % (cat.filename, a))
            problems = True
            nerr += 1
            continue
        name, email, rest = m.groups()
        name = simplify(name)
        email = simplify(email)

        m = re.search(r"^\s*,(.+?)\.?\s*$", rest)
        if not m:
            warning("%s: missing years in translator comment: %s"
                    % (cat.filename, a))
            problems = True
            nerr += 1
            continue
        yearstr = m.group(1)

        years = []
        for yspec in yearstr.split(","):
            m = _yr1_rx.search(yspec) or _yr2_rx.search(yspec)
            if not m:
                warning("%s: cannot parse years in translator comment: %s"
                        % (cat.filename, a))
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

    authlst.sort(lambda x, y:    cmp(min(x["years"]), min(y["years"]))
                                or cmp(x["pos"], y["pos"]))

    # Construct new author comments.
    authcmnts = Monlist()
    for a in authlst:
        acmnt = u"%s <%s>, %s." % (a["name"], a["email"],
                                    ", ".join(a["years"]))
        authcmnts.append(acmnt)

    hdr.author = authcmnts

    return nerr

