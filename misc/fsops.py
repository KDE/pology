# -*- coding: UTF-8 -*-

"""
File system operations concerning PO files.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import os


def collect_catalogs (file_or_dir_paths, sort=True):
    """
    Collect list of catalog file paths from given file/directory paths.

    When the given path is a directory path, the directory is recursively
    searched for C{.po} and C{.pot} files. Otherwise, the path is taken
    verbatim as single catalog file path (even if it does not exist).

    The collected paths can also be sorted before returning.

    @param file_or_dir_paths: paths to search for catalogs
    @type file_or_dir_paths: list of strings

    @param sort: whether to sort the list of collected paths
    @type sort: bool

    @returns: collected catalog paths
    @rtype: list of strings
    """

    catalog_files = []
    for path in file_or_dir_paths:
        if os.path.isdir(path):
            for root, dirs, files in os.walk(path):
                for file in files:
                    if file.endswith(".po") or file.endswith(".pot"):
                        catalog_files.append(os.path.join(root, file))
        else:
            catalog_files.append(path)

    if sort:
        catalog_files.sort()

    return catalog_files

