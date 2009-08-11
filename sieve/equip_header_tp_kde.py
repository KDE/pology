# -*- coding: UTF-8 -*-

"""
Equip catalog headers within KDE Translation Project with extra information.

The following header fields are set:
  - C{Language}: the language code of translation;
        set only if the language can be determined
  - C{X-Environment}: linguistic subset of the language of translation
        (team choices on terminology, ortography...); set to C{kde}
  - C{X-Accelerator-Marker}: accelerator marker character which may
        be encountered in text
  - C{X-Text-Markup}: text markups (e.g. Qt rich text, Docbook...) which
        may be encountered in text, as keywords

For the sieve to function properly, the local checkout of language catalogs
must match the repository structure up to a certain level.
See the documentation on L{check-tp-kde<sieve.check_tp_kde>} sieve for
details.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import os
import re

from pology.sieve.check_tp_kde import is_qt_cat, is_txt_cat, is_docbook_cat
from pology.sieve.check_tp_kde import _get_catalog_project_subdir


def setup_sieve (p):

    p.set_desc(
    "Equip catalog headers within KDE Translation Project "
    "with extra information."
    )


class Sieve (object):

    def __init__ (self, params):

        pass


    def process_header (self, hdr, cat):

        cname = cat.name
        csubdir = _get_catalog_project_subdir(cat.filename)

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
            (u"Language", unicode(lang), "Language-Team"),
            (u"X-Environment", u"kde", None),
            (u"X-Accelerator-Marker", unicode(accmark), None),
            (u"X-Text-Markup", u", ".join(mtypes), None),
        ]
        for fnam, fval, fnamaft in fvs:
            if fval is None:
                continue
            if len(hdr.select_fields(fnam)) > 1:
                hdr.remove_field(fnam)
            hdr.set_field(fnam, fval, after=fnamaft)

