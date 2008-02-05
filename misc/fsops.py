# -*- coding: UTF-8 -*-

"""
File system operations concerning PO files.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import os


def collect_catalogs (file_or_dir_paths, sort=True, unique=True):
    """
    Collect list of catalog file paths from given file/directory paths.

    When the given path is a directory path, the directory is recursively
    searched for C{.po} and C{.pot} files. Otherwise, the path is taken
    verbatim as single catalog file path (even if it does not exist).

    Collected paths are by default sorted and any duplicates eliminated,
    but this can be controlled using the C{sort} and C{unique} parameters.

    @param file_or_dir_paths: paths to search for catalogs
    @type file_or_dir_paths: list of strings

    @param sort: whether to sort the list of collected paths
    @type sort: bool

    @param unique: whether to eliminate duplicates among collected paths
    @type unique: bool

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
        if unique:
            catalog_files = list(set(catalog_files))
        catalog_files.sort()
    elif unique:
        # To preserve the order, reinsert catalogs avoiding duplicates.
        seen = {}
        unique = []
        for catalog_file in catalog_files:
            if catalog_file not in seen:
                seen[catalog_file] = true
                unique.append(catalog_file)
        catalog_files = unique

    return catalog_files

