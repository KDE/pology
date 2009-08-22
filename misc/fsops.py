# -*- coding: UTF-8 -*-

"""
Operations with file system and external commands.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import sys
import os
import codecs
import re
import locale
import subprocess

from pology.misc.report import error, warning


def collect_files_by_ext (dirpath, extension,
                          recurse=True, sort=True, unique=True):
    """
    Collect list of files having given extension from given directory path.

    Single path or a sequence of paths may be given as C{dirpath} parameter.
    Similarly, a single extension or sequence of extensions may be given
    in place of C{extension} parameter. If extensions are given as empty
    sequence, then files with no extensions are collected.
    Directories can be searched for files recursively or non-resursively,
    as requested by the C{recurse} parameter.

    Collected file paths are by default sorted and any duplicates eliminated,
    but this can be controlled using the C{sort} and C{unique} parameters.

    @param dirpath: path to search for files
    @type dirpath: string or sequence of strings
    @param extension: extension of files to collect
    @type extension: string or sequence of strings
    @param recurse: whether to search for files recursively
    @type recurse: bool
    @param sort: whether to sort collected paths
    @type sort: bool
    @param unique: whether to eliminate duplicates from collected paths
    @type unique: bool

    @returns: list of collected file paths
    @rtype: list of strings
    """

    if isinstance(dirpath, basestring):
        dirpaths = [dirpath]
    else:
        dirpaths = dirpath

    if isinstance(extension, basestring):
        extensions = [extension]
    else:
        extensions = extension
    # Tuple for matching file paths with str.endswith().
    dot_exts = tuple(["." + x for x in extensions])

    filepaths = []
    for dirpath in dirpaths:
        if not os.path.isdir(dirpath):
            warning("path '%s' is not a directory path" % dirpath)
            continue
        for root, dirs, files in os.walk(dirpath):
            for file in files:
                if (   file.endswith(dot_exts)
                    or (not dot_exts and "." not in file)
                ):
                    filepath = os.path.normpath(os.path.join(root, file))
                    filepaths.append(filepath)

    if sort:
        if unique:
            filepaths = list(set(filepaths))
        filepaths.sort()
    elif unique:
        # To preserve the order, reinsert catalogs avoiding duplicates.
        seen = {}
        unique = []
        for filepath in filepaths:
            if filepath not in seen:
                seen[filepath] = True
                unique.append(filepath)
        filepaths = unique

    return filepaths


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
    @rtype: string or list of strings
    """

    if isinstance(file_or_dir_paths, (str, unicode)):
        file_or_dir_paths = [file_or_dir_paths]

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


def collect_catalogs_by_env (catpathenv, sort=True, unique=True, relcwd=True):
    """
    Collect list of catalog file paths from directories given
    by an environment variable.

    @param sort: whether to sort the list of collected paths
    @type sort: bool
    @param unique: whether to eliminate duplicates among collected paths
    @type unique: bool
    @param relcwd: whether to make paths relative to current working directory
        when they point to a file within it
    @param relcwd: bool

    @returns: collected catalog paths
    @rtype: list of strings
    """

    catpath = os.getenv(catpathenv)
    if catpath is None:
        warning("environment variable with catalog paths '%s' "
                "not set" % catpath)
        return []

    catdirs = catpath.split(":")
    catfiles = collect_catalogs(catdirs, sort, unique)

    if relcwd:
        cwd = os.getcwd()
        catfiles_rel = []
        for catfile in catfiles:
            if catfile.startswith(cwd):
                catfile = catfile[len(cwd):]
                while catfile.startswith(os.path.sep):
                    catfile = catfile[len(os.path.sep):]
            catfiles_rel.append(catfile)
        catfiles = catfiles_rel

    return catfiles


def mkdirpath (dirpath):
    """
    Make all the directories in the path which do not exist yet.

    Like shell's C{mkdir -p}.

    @param dirpath: the directory path to create
    @type dirpath: string
    """

    incpath = ""
    for subdir in os.path.normpath(dirpath).split(os.path.sep):
        if not subdir:
            subdir = os.path.sep
        incpath = os.path.join(incpath, subdir)
        if not os.path.isdir(incpath):
            os.mkdir(incpath)


def system_wd (cmdline, wdir):
    """
    Execute command line in a specific working directory.

    Like C{os.system}, only switching CWD during execution.

    @param cmdline: command line to execute
    @type cmdline: string
    @param wdir: working directory for the command (CWD if none given)
    @type wdir: path

    @returns: exit code from the command
    @rtype: int
    """

    cwd = os.getcwd()
    try:
        os.chdir(wdir)
        ret = os.system(cmdline)
    except:
        os.chdir(cwd)
        raise

    return ret


# Execute command line and assert success.
# In case of failure, report the failed command line if echo is False.
def assert_system (cmdline, echo=False, wdir=None):
    """
    Execute command line and assert success.

    If the command exits with non-zero zero state, the program aborts.

    @param cmdline: command line to execute
    @type cmdline: string
    @param echo: whether to echo the supplied command line
    @type echo: bool
    @param wdir: working directory for the command (CWD if none given)
    @type wdir: path
    """

    if echo:
        print cmdline
    if wdir is not None:
        cwd = os.getcwd()
        os.chdir(wdir)
    ret = os.system(unicode_to_str(cmdline))
    if wdir is not None:
        os.chdir(cwd)
    if ret:
        if echo:
            error("non-zero exit from previous command")
        else:
            error("non-zero exit from:\n%s" % cmdline)


def collect_system (cmdline, echo=False, wdir=None, env=None, instr=None):
    """
    Execute command line and collect stdout, stderr, and return code.

    Normally the output will 

    @param cmdline: command line to execute
    @type cmdline: string
    @param echo: whether to echo the command line, as well as stdout/stderr
    @type echo: bool
    @param wdir: working directory for the command (CWD if none given)
    @type wdir: path
    @param env: environment for the execution (variable name-value pairs)
    @type env: {string: string}
    @param instr: string to pass to the command stdin
    @type instr: string

    @returns: tuple of stdout, stderr, and exit code
    @rtype: (string, string, int)
    """

    if echo:
        print cmdline
    if wdir is not None:
        cwd = os.getcwd()
        os.chdir(wdir)
    stdin = instr is not None and subprocess.PIPE or None
    p = subprocess.Popen(unicode_to_str(cmdline), shell=True, env=env,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         stdin=stdin)
    if instr is not None:
        p.stdin.write(instr.encode(locale.getpreferredencoding()))
    strout, strerr = map(str_to_unicode, p.communicate())
    ret = p.returncode
    if wdir is not None:
        os.chdir(cwd)

    if echo:
        if strout:
            sys.stdout.write("===== stdout from the command ^^^ =====\n")
            sys.stdout.write(strout)
        if strerr:
            sys.stderr.write("***** stderr from the command ^^^ *****\n")
            sys.stderr.write(strerr)

    return (strout, strerr, ret)


def lines_from_file (filepath, encoding=None):
    """
    Read content of a text file into list of lines.

    Only CR, LF, and CR+LF are treated as line breaks.

    If the given file path is not readable, or text cannot be decoded using
    given encoding, exceptions are raised. If encoding is not given,
    the encoding specified by the environment is used.

    @param filepath: path of the file to read
    @type filepath: string
    @param encoding: text encoding for the file
    @param encoding: string

    @returns: lines
    @rtype: list of strings
    """

    if encoding is None:
        encoding = locale.getpreferredencoding()

    try:
        ifl = codecs.open(filepath, "r", encoding)
    except:
        warning("cannot open '%s' for reading" % filepath)
        raise
    try:
        content = ifl.read()
    except:
        warning("cannot read content of '%s' using %s encoding"
                % (filepath, encoding))
        raise
    ifl.close()

    lines = [x + "\n" for x in re.split(r"\r\n|\r|\n", content)]
    # ...no file.readlines(), it treats some other characters as line breaks.
    if lines[-1] == "\n":
        # If the file ended properly in a line break, the last line will be
        # phony, from the empty element splitted out by the last line break.
        lines.pop()

    return lines


def join_ncwd (*elements):
    """
    Join path and normalize it with respect to current working directory.

    Path elements are joined with C{os.path.join} and the joined path
    normalized by C{os.path.normpath}.
    The normalized path is then made relative to current working directory
    if it points to a location within current working directory.

    @param elements: path elements
    @type elements: varlist

    @returns: normalized joined path
    @rtype: string
    """

    path = os.path.join(*elements)
    cwd = os.getcwd() + os.path.sep
    apath = os.path.abspath(path)
    if apath.startswith(cwd):
        path = apath[len(cwd):]
    else:
        path = os.path.normpath(path)

    return path


def str_to_unicode (strarg):
    """
    Convert a raw string value or sequence of values into Unicode.

    Strings comming in from the environment are frequently raw byte sequences,
    and need to be converted into Unicode strings according to system locale
    (e.g. command-line arguments).
    This function will take either a single raw string or any sequence
    of raw strings and convert it into a Unicode string or list thereof.

    If the input value is not a single raw or unicode string,
    it is assumed to be a sequence of values.
    In case there are values in the input which are not raw strings,
    they will be carried over into the result as-is.

    @param strarg: input string or sequence
    @type strarg: string, unicode, or sequence of objects

    @returns: unicode string or sequence of objects
    @rtype: unicode string or list of objects
    """

    if isinstance(strarg, unicode):
        return strarg

    lenc = locale.getpreferredencoding()

    if isinstance(strarg, str):
        return unicode(strarg, lenc)
    else:
        uargs = []
        for val in strarg:
            if isinstance(val, str):
                val = unicode(val, lenc)
            uargs.append(val)
        return uargs


def unicode_to_str (strarg):
    """
    Convert a unicode string into raw byte sequence.

    Strings goint to the environment should frequently be raw byte sequences,
    and need to be converted from Unicode strings according to system locale
    (e.g. command-line arguments).
    This function will take either a single Unicode string or any sequence
    of Unicode strings and convert it into a raw string or list thereof.

    If the input value is not a single raw or unicode string,
    it is assumed to be a sequence of values.
    In case there are values in the input which are not Unicode strings,
    they will be carried over into the result as-is.

    @param strarg: input string or sequence
    @type strarg: string, unicode, or sequence of objects

    @returns: raw string or sequence of objects
    @rtype: raw string or list of objects
    """

    if isinstance(strarg, str):
        return strarg

    lenc = locale.getpreferredencoding()

    if isinstance(strarg, unicode):
        return strarg.encode(lenc)
    else:
        uargs = []
        for val in strarg:
            if isinstance(val, unicode):
                val = val.encode(lenc)
            uargs.append(val)
        return uargs


def get_env_langs ():
    """
    Guess user's preferred languages from the environment.

    Various environment variables are examined to collect
    the list of languages in which the user may be wanting
    to read or write in in the environment.
    The list is ordered from most to least preferred language,
    and may be empty.
    Languages are given by their ISO-639 codes.

    @returns: preferred languages
    @rtype: list of strings
    """

    langs = []

    # Variables which contain colon-separated language strings.
    for lenv in ["LANGUAGE"]:
        langs.extend((os.getenv(lenv, "")).split(":"))

    # Variables which contain locale string:
    # split into parts, and assemble possible language codes from least to
    for lenv in ["LC_ALL", "LANG"]:
        lval = os.getenv(lenv, "")
        lsplit = []
        for sep in ("@", ".", "_"): # order is important
            p = lval.rfind(sep)
            if p >= 0:
                el, lval = lval[p + len(sep):], lval[:p]
            else:
                el = None
            lsplit.insert(0, el)
        lsplit.insert(0, lval)
        lng, ctr, enc, mod = lsplit

        if lng and ctr and mod:
            langs.append("%s_%s@%s" % (lng, ctr, mod))
        if lng and ctr:
            langs.append("%s_%s" % (lng, ctr))
        if lng and mod:
            langs.append("%s@%s" % (lng, mod))
        if lng:
            langs.append(lng)

    # Normalize codes, remove empty and any duplicates (but keep order).
    langs2 = [x.strip() for x in langs]
    langs2 = [x for x in langs2 if x]
    seen = set()
    langs = []
    for lang in langs2:
        if lang not in seen:
            seen.add(lang)
            langs.append(lang)

    return langs

