# -*- coding: UTF-8 -*-

"""
Operations with environment, file system and external commands.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import codecs
import locale
import os
import re
import subprocess
import sys

from pology import PologyError, _, n_
from pology.report import report, error, warning


def collect_files (paths,
                   recurse=True, sort=True, unique=True, relcwd=True,
                   selectf=None):
    """
    Collect list of files from given directory and file paths.

    C{paths} can be any sequence of strings, or a single string.
    Directories can be searched for files recursively or non-resursively,
    as requested by the C{recurse} parameter.
    Parameters C{sort} and C{unique} determine if the resulting paths
    are sorted alphabetically increasing and if duplicate paths are removed.
    If C{relcwd} is set to C{True}, absolute file paths which point to files
    within the current working directory are made relative to it.

    Only selected files may be collected by supplying
    a selection function through C{selectf} parameter.
    It takes a file path as argument and returns a boolean,
    C{True} to select the file or C{False} to discard it.

    @param paths: paths to search for files
    @type paths: string or iter(string*)
    @param recurse: whether to search for files recursively
    @type recurse: bool
    @param sort: whether to sort collected paths
    @type sort: bool
    @param unique: whether to eliminate duplicate collected paths
    @type unique: bool
    @param relcwd: whether to make collected absolute paths within
        current working directory relative to it
    @param relcwd: bool
    @param selectf: test to select or discard a file path
    @type selectf: (string)->bool

    @returns: collected file paths
    @rtype: [string...]
    """

    if isinstance(paths, basestring):
        paths = [paths]

    filepaths = []
    for path in paths:
        if os.path.isdir(path):
            for root, dirs, files in os.walk(path):
                for file in files:
                    filepath = os.path.normpath(os.path.join(root, file))
                    if not selectf or selectf(filepath):
                        filepaths.append(filepath)
                if not recurse:
                    dirs[:] = []
        elif os.path.isfile(path):
            if not selectf or selectf(path):
                filepaths.append(path)
        elif not os.path.exists(path):
            raise PologyError(
                _("@info",
                  "Path '%(path)s' does not exist.",
                  path=path))
        else:
            raise PologyError(
                _("@info",
                  "Path '%(path)s' is neither a file nor a directory.",
                  path=path))

    if sort:
        if unique:
            filepaths = list(set(filepaths))
        filepaths.sort()
    elif unique:
        # To preserve the order, reinsert paths avoiding duplicates.
        seen = {}
        ufilepaths = []
        for filepath in filepaths:
            if filepath not in seen:
                seen[filepath] = True
                ufilepaths.append(filepath)
        filepaths = ufilepaths

    if relcwd:
        filepaths = map(join_ncwd, filepaths)

    return filepaths


def collect_files_by_ext (paths, extension,
                          recurse=True, sort=True, unique=True, relcwd=True,
                          selectf=None):
    """
    Collect list of files having given extension from given paths.

    The C{extension} parameter can be a single extension or
    a sequence of extensions, without the leading dot.
    Files with empty extension (i.e. dot at the end of path)
    are collected by supplying empty string for C{extension},
    and files with no extension by supplying another empty sequence.

    Other parameters behave in the same way as in L{collect_files}.

    @param extension: extension of files to collect
    @type extension: string or sequence of strings

    @see: L{collect_files}
    """

    if isinstance(extension, basestring):
        extensions = [extension]
    else:
        extensions = extension

    def selectf_mod (fpath):

        ext = os.path.splitext(fpath)[1]
        if ext not in ("", "."):
            hasext = ext[1:] in extensions
        elif ext == ".":
            hasext = extensions == ""
        else: # ext == ""
            hasext = not extensions
        if selectf and hasext:
            return selectf(fpath)
        else:
            return hasext

    return collect_files(paths, recurse, sort, unique, relcwd, selectf_mod)


def collect_catalogs (paths,
                      recurse=True, sort=True, unique=True, relcwd=True,
                      selectf=None):
    """
    Collect list of catalog file paths from given paths.

    Applies C{collect_files_by_ext} with extensions set to C{("po", "pot")}.
    """

    catexts = ("po", "pot")

    return collect_files_by_ext(paths, catexts,
                                recurse, sort, unique, relcwd, selectf)


def collect_catalogs_by_env (catpathenv,
                             recurse=True, sort=True, unique=True, relcwd=True,
                             selectf=None):
    """
    Collect list of catalog file paths from directories given
    by an environment variable.

    Other parameters behave in the same way as in L{collect_catalogs}.

    @param catpathenv: environment variable name
    @type catpathenv: string
    """

    catpath = os.getenv(catpathenv)
    if catpath is None:
        return []

    catdirs = catpath.split(":")

    return collect_catalogs(catdirs,
                            recurse, sort, unique, relcwd, selectf)


def mkdirpath (dirpath):
    """
    Make all the directories in the path which do not exist yet.

    Like shell's C{mkdir -p}.

    @param dirpath: the directory path to create
    @type dirpath: string

    @returns: the path of topmost created directory, if any
    @rtype: string or C{None}
    """

    toppath = None
    incpath = ""
    for subdir in os.path.normpath(dirpath).split(os.path.sep):
        if not subdir:
            subdir = os.path.sep
        incpath = os.path.join(incpath, subdir)
        if not os.path.isdir(incpath):
            os.mkdir(incpath)
            if toppath is None:
                toppath = incpath
    return toppath


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

    cwd = getucwd()
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
        report(cmdline)
    if wdir is not None:
        cwd = getucwd()
        os.chdir(wdir)
    ret = os.system(unicode_to_str(cmdline))
    if wdir is not None:
        os.chdir(cwd)
    if ret:
        if echo:
            error(_("@info",
                    "Non-zero exit from the previous command."))
        else:
            error(_("@info",
                    "Non-zero exit from the command:\n%(cmdline)s",
                    cmdline=cmdline))


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

    @returns: stdout, stderr, and exit code
    @rtype: (string, string, int)
    """

    if echo:
        report(cmdline)
    if wdir is not None:
        cwd = getucwd()
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
            sys.stdout.write(
                _("@info ^^^ points to the earlier output in the terminal",
                  "===== stdout from the command above =====") + "\n")
            sys.stdout.write(strout)
        if strerr:
            sys.stderr.write(
                _("@info ^^^ points to the earlier output in the terminal",
                  "***** stderr from the command ^^^ *****") + "\n")
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
    @rtype: [string...]
    """

    if encoding is None:
        encoding = locale.getpreferredencoding()

    try:
        ifl = codecs.open(filepath, "r", encoding)
    except:
        warning(_("@info",
                  "Cannot open '%(file)s' for reading.",
                  file=filepath))
        raise
    try:
        content = ifl.read()
    except:
        warning(_("@info",
                  "Cannot read content of '%(file)s' using %(enc)s encoding.",
                  file=filepath, enc=encoding))
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
    cwd = getucwd() + os.path.sep
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
    @rtype: [string...]
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


def term_width (stream=sys.stdout, default=None):
    """
    Get number of columns in the terminal of output stream.

    If the output stream is not linked to the terminal, 0 is returned.
    If the output stream is linked to the terminal, but the number of columns
    cannot be determined, the supplied default value is returned instead.

    @param stream: output stream for which the terminal is looked up
    @type stream: file
    @param default: value to return if width cannot be determined
    @type default: int

    @returns: width of the terminal in columns
    @rtype: int
    """

    if not stream.isatty():
        return 0

    try:
        import curses
        curses.setupterm()
    except:
        return default

    ncols = curses.tigetnum("cols")

    return ncols if ncols >= 0 else default


def build_path_selector (incnames=None, incpaths=None,
                         excnames=None, excpaths=None,
                         ormatch=False):
    """
    Build a path selection function based on inclusion-exclusion condition.

    Frequently a collection of paths needs to be filtered,
    to pass only specific paths (inclusion),
    or to block only specific paths (exclusion), or both.
    Filtering conditions are normally posed on full paths,
    but frequently file base names without extensions are really tested.

    This function builds a selector function which takes a path and
    returns C{True} to select the path or C{False} to discard it,
    based on four sets of conditions: inclusions by base name without
    extension (C{incnames}), inclusion by full path (C{incpaths}),
    exclusions by base name without extension (C{excnames}), and
    exclusions by full path (C{excpaths}).
    Each condition in each of the sets can be a regular expression string,
    an object with C{search(string)} method returning true or false value
    (e.g. compiled regular expression), or a general function taking string
    and returning true or false value.

    If C{ormatch} is C{False}, the path is included if there are
    no inclusion conditions or all inclusion conditions match;
    the path is excluded if there is at least one exclusion condition
    and all exclusion conditions match.
    If C{ormatch} is C{True}, the path is included if there are
    no inclusion conditions or at least one of them matches;
    the path is excluded if at least one exclusion condition match.

    @param incnames: conditions for inclusion by base name without extension
    @type incnames: sequence (see description)
    @param incpaths: conditions for inclusion by full path
    @type incpaths: sequence (see description)
    @param excnames: conditions for exclusion by base name without extension
    @type excnames: sequence (see description)
    @param excpaths: conditions for exclusion by full path
    @type excpaths: sequence (see description)
    @param ormatch: whether conditions are linked with OR
    @type ormatch: bool

    @returns: path selection function
    @rtype: (string)->bool
    """

    # Shortcut to avoid complicated selector function.
    if not incnames and not incpaths and not excnames and not excpaths:
        return lambda x: x

    incnames_tf = _build_path_selector_type(incnames)
    incpaths_tf = _build_path_selector_type(incpaths)
    excnames_tf = _build_path_selector_type(excnames)
    excpaths_tf = _build_path_selector_type(excpaths)
    sumf = any if ormatch else all

    def selector (path):
        path = os.path.abspath(path)
        name = None
        if incnames_tf or excnames_tf:
            name = os.path.basename(os.path.normpath(path))
            p = name.rfind(".")
            if p > 0:
                name = name[:p]
        incargs = (  zip(incnames_tf, [name] * len(incnames_tf))
                   + zip(incpaths_tf, [path] * len(incpaths_tf)))
        incress = [x(y) for x, y in incargs]
        excargs = (  zip(excnames_tf, [name] * len(excnames_tf))
                   + zip(excpaths_tf, [path] * len(excpaths_tf)))
        excress = [x(y) for x, y in excargs]
        return (    (not incress or sumf(incress))
                and (not excress or not sumf(excress)))

    return selector


def _build_path_selector_type (sels):

    sels_tf = []
    if not sels:
        return sels_tf
    def tofunc (sel):
        if hasattr(sel, "search"):
            return lambda x: bool(sel.search(x))
        elif isinstance(sel, basestring):
            sel_rx = re.compile(sel, re.U)
            return lambda x: bool(sel_rx.search(x))
        elif callable(sel):
            return sel
        else:
            raise PologyError(
                _("@info",
                  "Cannot convert object '%(obj)s' into a string matcher.",
                  obj=sel))
    sels_tf = map(tofunc, sels)

    return sels_tf


_dhead = ":"
_dincname = "+"
_dincpath = "/+"
_dexcname = "-"
_dexcpath = "/-"

def collect_paths_from_file (fpath, cmnts=True, incexc=True, respathf=None,
                             getsel=False, abort=False):
    """
    Collect list of paths from the file.

    In general, non-empty lines in the file are taken to be paths,
    and empty lines are skipped.
    If C{cmnts} is C{True}, then also the lines starting with C{'#'}
    are skipped as comments.

    The C{respathf} parameter provides a function to be applied to each path
    and return a list of paths, which then substitute the original path.
    This function can be used, for example, to recursively collect files
    from listed directories, or to exclude paths by an external condition.

    If C{incexc} is C{True}, then the lines starting with C{':'}
    define directives by which files and directories are included
    or excluded from the final list.
    Inclusion-exclusion directives are mostly useful when some of the paths
    are directories, and C{respathf} parameter is used to provide
    a function to collect subpaths from listed directories;
    the inclusion-exclusion directives are applied to those subpaths too.
    The directives are as follows:
      - C{:-REGEX}: excludes path if its base name without extension
            matches the regular expression
      - C{:/-REGEX}: excludes path if it matches the regular expression
      - C{:+REGEX}: includes path only if its base name without extension
            matches the regular expression
      - C{:/+REGEX}: includes path only if it matches the regular expression
    The path is included if there are no inclusion directives,
    or it matches at least one inclusion directive;
    the path is excluded if it matches at least one exclusion directive.
    Inclusion-exclusion directives are given to L{build_path_selector}
    to create the path selection function (with C{ormatch} set to C{True}),
    which is then used to filter collected paths
    (after application of C{respathf}, if given).

    If C{getsel} is set to C{True}, the selection function is returned
    instead of being applied to read paths immediately.
    This is useful in case the C{respathf} parameter is not sufficient
    to resolve paths, but more complex processing is required.
    from directories externally, instead with C{respathf}).
    If there were no inclusion-exclusion directives in the file,
    the resulting selection function will return C{True} for any path.

    @param fpath: the path to file which contains paths
    @type fpath: string
    @param cmnts: whether the file can contain comments
    @type cmnts: bool
    @param incexc: whether the file can contain inclusion-exclusion directives
    @type incexc: boolean
    @param respathf: function to resolve collected paths
    @type respathf: (string)->[string...]
    @param getsel: whether to return constructed path selection function
        instead of applying it
    @type getsel: bool
    @param abort: whether to abort the execution on exceptions from
        path resolution or selection functions
    @type abort: bool

    @returns: collected paths, possibly with path selection function
    @rtype: [string...] or ([string...], (string)->bool)
    """

    if abort:
        def abort_or_raise (e):
            error(unicode(e))
    else:
        def abort_or_raise (e):
            raise

    paths = []
    incnames = []
    incpaths = []
    excnames = []
    excpaths = []
    lines = open(fpath).read().split("\n")
    lno = 0
    for line in lines:
        lno += 1
        if not line or (cmnts and line.startswith("#")):
            continue

        if incexc and line.startswith(_dhead):
            line = line[len(_dhead):]
            dstr = None
            for sels, shead in (
                (incnames, _dincname), (incpaths, _dincpath),
                (excnames, _dexcname), (excpaths, _dexcpath),
            ):
                if line.startswith(shead):
                    dstr = line[len(shead):]
                    try:
                        rx = re.compile(dstr, re.U)
                    except:
                        raise PologyError(
                            _("@info",
                              "Invalid regular expression in inclusion/"
                              "exclusion directive at %(file)s:%(line)d.",
                              file=fpath, line=lno))
                    sels.append(rx)
                    break
            if dstr is None:
                raise PologyError(
                    _("@info",
                      "Unknown inclusion/exclusion directive "
                      "at %(file)s:%(line)d.",
                      file=fpath, line=lno))
        else:
            paths.append(line)

    if respathf:
        try:
            paths = sum(map(respathf, paths), [])
        except Exception, e:
            abort_or_raise(e)

    selectf = build_path_selector(incnames=incnames, incpaths=incpaths,
                                  excnames=excnames, excpaths=excpaths,
                                  ormatch=True)
    if getsel:
        return paths, selectf
    else:
        try:
            paths = filter(selectf, paths)
        except Exception, e:
            abort_or_raise(e)
        return paths


def collect_paths_cmdline (rawpaths=None,
                           incnames=None, incpaths=None,
                           excnames=None, excpaths=None,
                           ormatch=False,
                           filesfrom=None, cmnts=True, incexc=True,
                           elsecwd=False, respathf=None,
                           getsel=False,
                           abort=False):
    """
    Collect list of paths from usual sources given on command line.

    Scripts that process paths will in general get paths directly
    (as free command line arguments or on standard input),
    or indirectly from files containing lists of paths
    (usually given by a command line option).
    Sometimes input directory paths will be searched for
    paths of all files in them, possibly of certain type.
    Especially when searching directory paths, the script may take
    options to exclude or include only paths that match something.
    This function conveniently wraps up these possibilities,
    to fetch all possible paths in single statement.

    The C{rawpaths} parameter provides a list of directly supplied
    paths, e.g. from command line arguments.
    C{incnames}, C{incpaths}, C{excnames}, and C{excpaths} are
    lists of inclusion and exclusion conditions out of which
    single path selection function is constructed,
    with C{ormatch} determining how conditions are linked,
    see L{build_path_selector} for details.
    C{filesfrom} is a list of files containing lists of paths,
    C{cmnts} and C{incexc} are options for the file format,
    see L{collect_paths_from_file} for details.
    If both C{rawpaths} and C{filesfrom} are not given or empty,
    C{elsecwd} determines if current working directory is added
    to list of paths (C{True}) or not (C{False}).
    C{respathf} is a function which takes a path and returns
    list of paths, see description of the same parameter in
    L{collect_paths_from_file}.

    The order of path collection is as follows.
    First all paths from C{rawpaths} are added, applying C{respathf}.
    Then all paths from all files given by C{fromfiles}
    are added, by applying L{collect_paths_from_file} on each file
    (C{respathf} is applied by sending it to L{collect_paths_from_file}).
    If both C{rawpaths} and C{fromfiles} were C{None} or empty,
    current working directory is added, possibly applying C{respathf}.
    Finally, all paths are filtered through inclusion-exclusion tests;
    if no inclusion tests are given, then all files are included
    unless excluded by an exclusion test.

    If C{getsel} is set to C{True}, the path selection function
    is returned instead of being applied to collected paths.
    This function will also include path selection functions
    constructed from inclusion-exclusion directives found in C{filesfrom},
    linked with the top conditions according to C{ormatch}.

    @param respathf: function to resolve collected paths
    @type respathf: (string)->[string...]
    @param getsel: whether to return constructed path selection function
        instead of applying it
    @type getsel: bool
    @param abort: whether to abort the execution on exceptions from
        path resolution or selection functions
    @type abort: bool

    @returns: collected paths, possibly with path selection function
    @rtype: [string...] or ([string...], (string)->bool)
    """

    paths = []

    if abort:
        def abort_or_raise (e):
            error(unicode(e))
    else:
        def abort_or_raise (e):
            raise

    # First add paths given directly, then add paths read from files.
    if rawpaths:
        rawpaths2 = rawpaths
        if respathf:
            try:
                rawpaths2 = sum(map(respathf, rawpaths), [])
            except Exception, e:
                abort_or_raise(e)
        paths.extend(rawpaths2)
    ffselfs = []
    if filesfrom:
        for ffpath in filesfrom:
            res = collect_paths_from_file(ffpath, cmnts, incexc,
                                          respathf, getsel=getsel,
                                          abort=abort)
            if getsel:
                cpaths, cself = res
                paths.extend(cpaths)
                ffselfs.append(cself)
            else:
                paths.extend(res)
    # If neither direct paths nor files to read paths from were given,
    # add current working directory if requested.
    if elsecwd and not rawpaths and not filesfrom:
        cwd = getucwd()
        if respathf:
            try:
                paths.extend(respathf(cwd))
            except Exception, e:
                abort_or_raise(e)
        else:
            paths.append(cwd)

    selectf = build_path_selector(incnames=incnames, incpaths=incpaths,
                                  excnames=excnames, excpaths=excpaths,
                                  ormatch=ormatch)
    if ffselfs:
        if ormatch:
            selftot = lambda p: selectf(p) or any([x(p) for x in ffselfs])
        else:
            selftot = lambda p: selectf(p) and all([x(p) for x in ffselfs])
    else:
        selftot = selectf

    if getsel:
        return paths, selftot
    else:
        try:
            paths = filter(selftot, paths)
        except Exception, e:
            abort_or_raise(e)
        return paths


def getucwd ():
    """
    Get path of current working directory as Unicode string.

    C{os.getcwd()} returns a raw byte sequence, to which
    the L{str_to_unicode} function is applied to make best guess
    at decoding it into a unicode string.

    @returns: path of current working directory
    @rtype: string
    """

    rawcwd = os.getcwd()
    cwd = str_to_unicode(rawcwd)
    return cwd

