# -*- coding: UTF-8 -*-

import os


def collect_catalogs (file_or_dir_paths, sort=True):
    """Collect list of catalog file paths from given file/directory paths.

    If a path in file_or_dir_paths is a directory path, the directory is
    searched for .po and .pot files; otherwise, the path is taken verbatim as
    single catalog file path.

    If sort is true, the collected paths are sorted before returning.
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

