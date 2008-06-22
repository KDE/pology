# -*- coding: UTF-8 -*-

"""
Operations with file system and external commands.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import sys
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
                seen[catalog_file] = True
                unique.append(catalog_file)
        catalog_files = unique

    return catalog_files


def mkdirpath (dirpath):
    """
    Make all the directories in the path which do not exist yet.

    Like shell's C{mkdir -p}.

    @param dirpath: the directory path to create
    @type dirpath: string
    """

    incpath = ""
    for subdir in os.path.normpath(dirpath).split(os.path.sep):
        incpath = os.path.join(incpath, subdir)
        if not os.path.isdir(incpath):
            os.mkdir(incpath)


# Execute command line and assert success.
# In case of failure, report the failed command line if echo is False.
def assert_system (cmdline, echo=False):
    """
    Execute command line and assert success.

    If the command exits with non-zero zero state, the program aborts.

    @param cmdline: command line to execute
    @type cmdline: string
    @param echo: whether to echo the supplied command line
    @type echo: bool
    """

    if echo:
        print cmdline
    ret = os.system(cmdline)
    if ret:
        if echo:
            error("non-zero exit from previous command")
        else:
            error("non-zero exit from:\n%s" % cmdline)


_execid = 0
def collect_system (cmdline, echo=False):
    """
    Execute command line and collect stdout, stderr, and return code.

    @param cmdline: command line to execute
    @type cmdline: string
    @param echo: whether to echo the command line, as well as stdout/stderr
    @type echo: bool
    """

    # Create temporary files.
    global _execid
    tmpout = "/tmp/exec%s-%d-out" % (os.getpid(), _execid)
    tmperr = "/tmp/exec%s-%d-err" % (os.getpid(), _execid)
    _execid += 1

    # Execute.
    if echo:
        print cmdline
    cmdline_mod = cmdline + (" 1>%s 2>%s " % (tmpout, tmperr))
    ret = os.system(cmdline_mod)

    # Collect stdout and stderr.
    strout = "".join(open(tmpout).readlines())
    strerr = "".join(open(tmperr).readlines())
    if echo:
        if strout:
            sys.stdout.write("===== stdout from the command ^^^ =====\n")
            sys.stdout.write(strout)
        if strerr:
            sys.stderr.write("***** stderr from the command ^^^ *****\n")
            sys.stderr.write(strerr)

    # Clean up.
    os.unlink(tmpout)
    os.unlink(tmperr)

    return (strout, strerr, ret)


