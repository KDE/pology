# -*- coding: UTF-8 -*-

"""
Catalog clasification.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import os
import re


def get_project_subdir (catpath):
    """
    Get canonical project subdirectory path for given catalog path.

    @param catpath: catalog path
    @type catpath: string

    @returns: project subdirectory path for this catalog
    @rtype: string
    """

    apath = os.path.abspath(catpath)
    up1dir = os.path.basename(os.path.dirname(apath))
    up2dir = os.path.basename(os.path.dirname(os.path.dirname(apath)))
    if (   not re.search(r"^(kde|koffice|extragear|playground|qt)", up1dir)
        or not re.search(r"^(|doc|wiki)messages$", up2dir)
    ):
        subdir = None
    else:
        subdir = os.path.join(up2dir, up1dir)

    return subdir


def is_txt_cat (catname, subdir):
    """
    Check whether the project catalog covers plain text sources.

    @param catname: catalog domain name
    @type catname: string
    @param subdir: catalog project subdirectory
    @type subdir: string

    @returns: C{True} if plain text catalog, C{False} otherwise
    @rtype: bool
    """

    return catname.startswith("desktop_") or catname.startswith("xml_")


# - pure Qt
_qt_catdirs = (
    "qt",
)
_qt_catnames = (
    "kdgantt1", "kdgantt",
)
_qt_catname_ends = (
    "_qt",
)

def is_qt_cat (catname, subdir):
    """
    Check whether the project catalog covers pure Qt sources.

    @param catname: catalog domain name
    @type catname: string
    @param subdir: catalog project subdirectory
    @type subdir: string

    @returns: C{True} if pure Qt catalog, C{False} otherwise
    @rtype: bool
    """

    up1dir = os.path.basename(subdir)
    if up1dir in _qt_catdirs:
        return True
    if catname in _qt_catnames:
        return True
    for end in _qt_catname_ends:
        if catname.endswith(end):
            return True
    return False


def is_docbook_cat (catname, subdir):
    """
    Check whether the project catalog covers Docbook sources.

    @param catname: catalog domain name
    @type catname: string
    @param subdir: catalog project subdirectory
    @type subdir: string

    @returns: C{True} if Docbook catalog, C{False} otherwise
    @rtype: bool
    """

    up2dir = os.path.basename(os.path.dirname(subdir))

    return (up2dir == "docmessages")

