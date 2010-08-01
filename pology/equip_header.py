# -*- coding: UTF-8 -*-

"""
Equip catalog headers with extra information.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import os
import re

from pology import _, n_
from pology.report import warning
from pology.proj.kde.cattype import get_project_subdir
from pology.proj.kde.cattype import is_txt_cat, is_qt_cat, is_docbook_cat


def equip_header_tp_kde (hdr, cat):
    """
    Equip headers in catalogs within KDE Translation Project [type F4B hook].

    The following header fields are set:
      - C{Language}: the language code of translation;
            set only if the language can be determined
      - C{X-Environment}: linguistic subset of the language of translation
            (team choices on terminology, ortography...);
            set to C{kde} if not existing, otherwise left untouched.
      - C{X-Accelerator-Marker}: accelerator marker character which may
            be encountered in text
      - C{X-Text-Markup}: text markups (e.g. Qt rich text, Docbook...) which
            may be encountered in text, as keywords

    For the hook to function properly, the local checkout of language catalogs
    must match the repository structure up to a certain level.
    See the documentation on L{check-tp-kde<sieve.check_tp_kde>} sieve for
    details.
    """

    cname = cat.name
    csubdir = get_project_subdir(cat.filename)
    if not csubdir:
        warning(_("@info TP stands for Translation Project",
                  "Cannot determine KDE TP subdirectory "
                  "of '%(file)s', skipping header updates.",
                  file=cat.filename))
        return 1

    pathels = os.path.abspath(cat.filename).split(os.path.sep)
    lang_rx = re.compile(r"^[a-z]{2}(_[A-Z]{2}|@[a-z]+)?$")
    lang = None
    if len(pathels) >= 5 and pathels[-4] == "summit":
        if lang_rx.search(pathels[-5]):
            lang = pathels[-5]
    elif len(pathels) >= 4:
        if lang_rx.search(pathels[-4]):
            lang = pathels[-4]

    if is_txt_cat(cname, csubdir):
        accmark = ""
        mtypes = [""]
    elif is_qt_cat(cname, csubdir):
        accmark = "&"
        mtypes = ["qtrich"]
    elif is_docbook_cat(cname, csubdir):
        accmark = ""
        mtypes = ["docbook4"]
    else: # default to native KDE4 catalog
        accmark = "&"
        mtypes = ["kde4"]

    # Special handling for particular catalogs.
    if cname == "desktop_kdebase":
        accmark = "&"

    fvs = [
        ("Language", lang, "Language-Team", False),
        ("X-Environment", u"kde", None, True),
        ("X-Accelerator-Marker", accmark, None, False),
        ("X-Text-Markup", ", ".join(mtypes), None, False),
    ]
    for fnam, fval, fnamaft, fkeep in fvs:
        if fval is None:
            continue
        existing = hdr.select_fields(fnam)
        if not (existing and fkeep):
            if len(existing) > 1:
                hdr.remove_field(fnam)
            hdr.set_field(unicode(fnam), unicode(fval), after=fnamaft)

    return 0

