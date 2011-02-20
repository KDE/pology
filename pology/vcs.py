# -*- coding: UTF-8 -*-

"""
Version control operations.

Collections of PO files are frequently kept under some sort of version control.
This module provides typical version control operations, abstracted across
various version control systems.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import os
import re
import shutil
import tempfile

from pology import PologyError, _, n_
from pology.fsops import collect_system, system_wd, unicode_to_str
from pology.report import report, warning


_vcskeys_by_pkey = {}
_vcstypes_by_akey = {}

def _register_vcs ():

    register = (
        # First keyword is primary.
        (("none", "noop", "dummy"),
         VcsNoop),
        (("svn", "subversion"),
         VcsSubversion),
        (("git",),
         VcsGit),
    )
    for vcskeys, vcstype in register:
        _vcskeys_by_pkey[vcskeys[0]] = vcskeys
        _vcstypes_by_akey.update([(x, vcstype) for x in vcskeys])


def available_vcs (flat=False):
    """
    Get keywords of all available version control systems.

    Some VCS have more than one keyword identifying them.
    If C{flat} is C{False}, a dictionary with primary keyword per VCS
    as keys, and tuple of all alternatives (including the main keyword)
    as values, is returned.
    If C{flat} is C{True}, all keywords are returned in a flat tuple.

    @return: VCS keywords, as dictionary by primary or as a flat list of all
    @rtype: {(string, string)*} or [string*]
    """

    if flat:
        return _vcstypes_by_akey.keys()
    else:
        return _vcskeys_by_pkey.copy()


def make_vcs (vcskey):
    """
    Factory for version control systems.

    Desired VCS is identified by a keyword. Currently available:
      - dummy noop (C{none}, C{noop}, C{dummy})
      - Subversion (C{svn}, C{subversion})
      - Git (C{git})

    @param vcskey: keyword identifier of the VCS
    @type vcskey: string

    @return: version control object
    @rtype: instance of L{VcsBase}
    """

    nkey = vcskey.strip().lower()
    vcstype = _vcstypes_by_akey.get(nkey)
    if not vcstype:
        raise PologyError(
            _("@info",
              "Unknown version control system requested by key '%(key)s'.",
              key=vcskey))
    return vcstype()


class VcsBase (object):
    """
    Abstract base for VCS objects.
    """

    def add (self, paths, repadd=False):
        """
        Add paths to version control.

        It depends on the particular VCS what adding means,
        but in general it should be the point where the subsequent L{commit()}
        on the same path will record addition in the repository history.

        Also a single path can be given instead of sequence of paths.

        Actually added paths may be different from input paths,
        e.g. if an input path is already version controlled,
        or input path's parent directory was added as well.
        List of added paths can be requested with C{repadd} parameter,
        and it will become the second element of return value.

        @param paths: paths to add
        @type paths: <string*> or string
        @param repadd: whether to report which paths were actually added
        @type repadd: bool

        @return: C{True} if addition successful, possibly list of added paths
        @rtype: bool or (bool, [string*])
        """
        raise PologyError(
            _("@info",
              "Selected version control system does not define adding."))


    def remove (self, path):
        """
        Remove path from version control and from disk.

        It depends on the particular VCS what removing means,
        but in general it should be the point where the subsequent L{commit()}
        on the same path will record removal in the repository history.

        @param path: path to remove
        @type path: string

        @return: C{True} if removal successful
        @rtype: bool
        """

        raise PologyError(
            _("@info",
              "Selected version control system does not define removing."))


    def move (self, spath, dpath):
        """
        Move versioned file or directory within the repository.

        It depends on the particular VCS what moving means,
        but in general it should be the point where the subsequent L{commit()}
        on source and destination path (or their common parent directory)
        will record the move in the repository history.

        @param spath: source path
        @type spath: string
        @param dpath: destination path
        @type dpath: string

        @return: C{True} if moving successful
        @rtype: bool
        """

        raise PologyError(
            _("@info",
              "Selected version control system does not define moving."))



    def revision (self, path):
        """
        Get current revision ID of the path.

        @param path: path to query for revision
        @type path: string

        @return: revision ID
        @rtype: string
        """

        raise PologyError(
            _("@info",
              "Selected version control system does not define "
              "revision query."))


    def is_clear (self, path):
        """
        Check if the path is in clear state.

        Clear state means none of: not version-controlled, modified, added...

        @param path: path to check the state of
        @type path: string

        @return: C{True} if clear
        @rtype: bool
        """

        raise PologyError(
            _("@info",
              "Selected version control system does not define state query."))


    def is_versioned (self, path):
        """
        Check if path is under version control.

        @param path: path to check
        @type path: string

        @return: C{True} if versioned
        @rtype: bool
        """

        raise PologyError(
            _("@info",
              "Selected version control system does not define "
              "checking whether a path is version controlled."))


    def export (self, path, rev, dstpath, rewrite=None):
        """
        Export a versioned file or directory.

        Makes a copy of versioned file or directory pointed to by
        local path C{path}, in the revision C{rev}, to destination C{dstpath}.
        If C{rev} is C{None}, the clean version of C{path} according
        to current local repository state is copied to C{dstpath}.

        Final repository path, as determined from C{path}, can be filtered
        through an external function C{rewrite} before being used.
        The function takes as arguments the path and revision strings.
        This can be useful, for example, to reroute remote repository URL.

        @param path: path of the versioned file or directory in local repository
        @type path: string
        @param rev: revision to export
        @type rev: string or C{None}
        @param dstpath: file path to export to
        @type dstpath: string
        @param rewrite: function to filter resolved repository path
        @type rewrite: (string, string)->string or None

        @return: C{True} if fetching succeeded, C{False} otherwise
        @rtype: bool
        """

        raise PologyError(
            _("@info",
              "Selected version control system does not define "
              "fetching of a versioned path."))


    def commit (self, paths, message=None, msgfile=None, incparents=True):
        """
        Commit paths to the repository.

        Paths can include any number of files and directories.
        Also a single path string can be given instead of a sequence.
        It depends on the particular VCS what committing means,
        but in general it should be the earliest level at which
        modifications are recorded in the repository history.

        Commit message can be given either directly, through C{message}
        parameter, or read from a file with path given by C{msgfile}.
        If both C{message} and C{msgfile} are given,
        C{message} takes precedence and C{msgfile} is ignored.
        If the commit message is not given, VCS should ask for one as usual
        (pop an editor window, or whatever the user has configured).

        Some VCS require that the parent directory of a path to be committed
        has been committed itself or included in the commit list if not.
        If that is the case, C{incparents} parameter determines if
        this function should assure that non-committed parents are included
        into the commit list too. This may be expensive to check,
        so it is good to disable it if all parents are known to be
        committed or included in the input paths.

        @param paths: paths to commit
        @type paths: <string*> or string
        @param message: commit message
        @type message: string
        @param msgfile: path to file with the commit message
        @type msgfile: string
        @param incparents: whether to automatically include non-committed
            parents in the commit list
        @type incparents: bool

        @return: C{True} if committing succeeded, C{False} otherwise
        @rtype: bool
        """

        raise PologyError(
            _("@info",
              "Selected version control system does not define "
              "committing of paths."))


    def log (self, path, rev1=None, rev2=None):
        """
        Get revision log of the path.

        Revision log entry consists of revision ID, commiter name,
        date string, and commit message.
        Except the revision ID, any of these may be empty strings,
        depending on the particular VCS.
        The log is ordered from earliest to newest revision.

        A section of entries between revisions C{rev1} (inclusive)
        and C{rev2} (exclusive) can be returned instead of the whole log.
        If C{rev1} is C{None}, selected IDs start from the first in the log.
        If C{rev2} is C{None}, selected IDs end with the last in the log.

        If either C{rev1} or C{rev2} is not C{None} and does not exist in
        the path's log, or the path is not versioned, empty log is returned.

        @param path: path to query for revisions
        @type path: string
        @param rev1: entries starting from this revision (inclusive)
        @type rev1: string
        @param rev2: entries up to this revision (exclusive)
        @type rev2: string

        @return: revision ID, committer name, date string, commit message
        @rtype: [(string*4)*]
        """

        raise PologyError(
            _("@info",
              "Selected version control system does not define "
              "revision history query."))


    def to_commit (self, path):
        """
        Get paths which need to be committed within the given path.

        Input path can be either a file or directory.
        If it is a directory, it depends on VCS whether it will
        only report files within it that need to be committed,
        or subdirectories too (including the given directory).

        @param path: path to query for non-committed paths
        @type path: string

        @return: non-committed paths
        @rtype: [string*]
        """

        raise PologyError(
            _("@info",
              "Selected version control system does not define "
              "listing of non-committed paths."))


    def diff (self, path, rev1=None, rev2=None):
        """
        Get diff between revisions of the given path.

        Unified diff is computed and reported as list of 2-tuples,
        where the first element is a tag, and the second the payload.
        For tags C{" "}, C{"+"}, and C{"-"}, the payload is the line
        (without newline) which was equal, added or removed, respectively.
        Payload for tag C{":"} is the path of the diffed file,
        and for C{"@"} the 4-tuple of old start line, old number of lines,
        new start line, and new number of lines, which are represented
        by the following difference segment.

        Diffs can be requested between specific revisions.
        If both C{rev1} and C{rev2} are C{None},
        diff is taken from last known commit to working copy.
        If only C{rev2} is C{None} diff is taken from C{rev1} to working copy.

        @param path: path to query for modified lines
        @type path: string
        @param rev1: diff from this revision
        @type rev1: string
        @param rev2: diff to this revision
        @type rev2: string

        @return: tagged unified diff
        @rtype: [(string, string or (int, int, int, int))*]
        """

        raise PologyError(
            _("@info",
              "Selected version control system does not define diffing."))


    def revert (self, path):
        """
        Revert a versioned file or directory.

        The path is reverted to the clean version of itself according
        to current local repository state.

        @param path: path of the versioned file or directory in local repository
        @type path: string

        @return: C{True} if reverting succeeded, C{False} otherwise
        @rtype: bool
        """

        raise PologyError(
            _("@info",
              "Selected version control system does not define "
              "reverting a versioned path."))


class VcsNoop (VcsBase):
    """
    VCS: Dummy VCS which perform only file system operations.
    """

    def add (self, paths, repadd=False):
        # Base override.

        return True if not repadd else [True, paths]


    def remove (self, path):
        # Base override.

        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)
        return True


    def move (self, spath, dpath):
        # Base override.

        shutil.move(spath, dpath)
        return True


    def revision (self, path):
        # Base override.

        return ""


    def is_clear (self, path):
        # Base override.

        return True


    def is_versioned (self, path):
        # Base override.

        return True


    def export (self, path, rev, dstpath, rewrite=None):
        # Base override.

        if rev is not None:
            return False

        try:
            os.shutil.copyfile(path, dstpath)
        except:
            return False
        return True


    def commit (self, paths, message=None, msgfile=None, incparents=True):
        # Base override.

        return True


    def log (self, path, rev1=None, rev2=None):
        # Base override.

        return []


    def to_commit (self, path):
        # Base override.

        return []


    def revert (self, path):
        # Base override.

        return True


class VcsSubversion (VcsBase):
    """
    VCS: Subversion.
    """

    def __init__ (self):

        # Environment to cancel any localization in output of operations,
        # for methods which need to parse the output.
        self._env = os.environ.copy()
        self._env["LC_ALL"] = "C"


    def add (self, paths, repadd=False):
        # Base override.

        if isinstance(paths, basestring):
            paths = [paths]
        if not paths:
            return True

        tmppath = _temp_paths_file(paths)
        res = collect_system("svn add --parents --targets %s" % tmppath,
                             env=self._env)
        success = (res[2] == 0)
        os.remove(tmppath)

        if repadd:
            apaths = []
            for line in res[0].split("\n"):
                if line.startswith("A"):
                    apaths.append(line[1:].strip())
            return success, apaths
        else:
            return success


    def remove (self, path):
        # Base override.

        if collect_system("svn remove %s" % path)[2] != 0:
            return False

        return True


    def move (self, spath, dpath):
        # Base override.

        if collect_system("svn move %s %s" % (self._ep(spath), dpath))[2] != 0:
            return False
        return True


    def revision (self, path):
        # Base override.

        res = collect_system("svn info %s" % self._ep(path), env=self._env)
        rx = re.compile(r"^Last Changed Rev: *([0-9]+)", re.I)
        revid = ""
        for line in res[0].split("\n"):
            m = rx.search(line)
            if m:
                revid = m.group(1)
                break

        return revid


    def is_clear (self, path):
        # Base override.

        res = collect_system("svn status %s" % path, env=self._env)
        clear = not re.search(r"^\S", res[0])

        return clear


    def is_versioned (self, path):
        # Base override.

        res = collect_system("svn info %s" % self._ep(path), env=self._env)
        if res[-1] != 0:
            return False

        rx = re.compile(r"^Repository", re.I)
        for line in res[0].split("\n"):
            if rx.search(line):
                return True

        return False


    def export (self, path, rev, dstpath, rewrite=None):
        # Base override.

        if rev is None:
            cmdline = "svn export %s -r BASE %s" % (self._ep(path), dstpath)
            if collect_system(cmdline)[-1] != 0:
                return False
            return True

        res = collect_system("svn info %s" % self._ep(path), env=self._env)
        if res[-1] != 0:
            return False
        rx = re.compile(r"^URL:\s*(\S+)", re.I)
        rempath = None
        for line in res[0].split("\n"):
            m = rx.search(line)
            if m:
                rempath = m.group(1)
                break
        if not rempath:
            return False

        if rewrite:
            rempath = rewrite(rempath, rev)

        cmdline = "svn export %s -r %s %s" % (self._ep(rempath), rev, dstpath)
        if collect_system(cmdline)[-1] != 0:
            return False

        return True


    def commit (self, paths, message=None, msgfile=None, incparents=True):
        # Base override.

        if isinstance(paths, basestring):
            paths = [paths]
        if not paths:
            return True

        if incparents:
            # Move up any path that needs its parent committed too.
            paths_up = []
            for path in paths:
                path_up = path
                while not self.revision(path_up):
                    path_up = os.path.dirname(path_up)
                    if not path_up or not self.is_versioned(path_up):
                        # Let simply Subversion complain.
                        path_up = path
                        break
                paths_up.append(path_up)
            paths = paths_up

        cmdline = "svn commit "
        if message is not None:
            cmdline += "-m \"%s\" " % message.replace("\"", "\\\"")
        elif msgfile is not None:
            cmdline += "-F \"%s\" " % msgfile.replace("\"", "\\\"")
        tmppath = _temp_paths_file(paths)
        cmdline += "--targets %s " % tmppath

        # Do not use collect_system(), user may need to input stuff.
        #report(cmdline)
        success = (os.system(unicode_to_str(cmdline)) == 0)
        os.remove(tmppath)

        return success


    def log (self, path, rev1=None, rev2=None):
        # Base override.

        res = collect_system("svn log %s" % self._ep(path), env=self._env)
        if res[-1] != 0:
            return []
        rev = ""
        next_rev, next_cmsg = range(2)
        entries = []
        next = -1
        for line in res[0].strip().split("\n"):
            if line.startswith("----------"):
                if rev:
                    cmsg = "\n".join(cmsg).strip("\n")
                    entries.append((rev, user, dstr, cmsg))
                cmsg = []
                next = next_rev
            elif next == next_rev:
                lst = line.split("|")
                rev, user, dstr = [x.strip() for x in lst[:3]]
                rev = rev[1:] # strip initial "r"
                next = next_cmsg
            elif next == next_cmsg:
                cmsg += [line]

        entries.reverse()

        return _crop_log(entries, rev1, rev2)


    def to_commit (self, path):
        # Base override.

        res = collect_system("svn status %s" % path, env=self._env)
        if res[-1] != 0:
            return []

        ncpaths = []
        for line in res[0].split("\n"):
            if line[:1] in ("A", "M"):
                path = line[1:].strip()
                ncpaths.append(path)

        return ncpaths


    def diff (self, path, rev1=None, rev2=None):
        # Base override.

        if rev1 is not None and rev2 is not None:
            rspec = "-r %s:%s" % (rev1, rev2)
        elif rev1 is not None:
            rspec = "-r %s" % rev1
        elif rev2 is not None:
            raise PologyError(
                _("@info \"Subversion\" is a version control system",
                  "Subversion cannot diff from working copy "
                  "to a named revision."))
        else:
            rspec = ""

        res = collect_system("svn diff %s %s" % (path, rspec), env=self._env)
        if res[-1] != 0:
            warning(_("@info",
                      "Subversion reports it cannot diff path '%(path)s':\n"
                       "%(msg)s",
                       path=path, msg=res[1]))
            return []

        udiff = []
        nskip = 0
        for line in res[0].split("\n"):
            if nskip > 0:
                nskip -= 1
                continue

            if line.startswith("Index:"):
                udiff.append((":", line[line.find(":") + 1:].strip()))
                nskip = 3
            elif line.startswith("@@"):
                m = re.search(r"-(\d+),(\d+) *\+(\d+),(\d+)", line)
                spans = tuple(map(int, m.groups())) if m else (0, 0, 0, 0)
                udiff.append(("@", spans))
            elif line.startswith(" "):
                udiff.append((" ", line[1:]))
            elif line.startswith("-"):
                udiff.append(("-", line[1:]))
            elif line.startswith("+"):
                udiff.append(("+", line[1:]))

        return udiff


    def revert (self, path):
        # Base override.

        res = collect_system("svn revert -R %s" % path, env=self._env)
        if res[-1] != 0:
            warning(_("@info",
                      "Subversion reports it cannot revert path '%(path)s':\n"
                      "%(msg)s",
                      path=path, msg=res[1]))
            return False

        return True


    def _ep (self, path):
        #if "@" in os.path.basename(os.path.normpath(path)):
        if "@" in path:
            path = "%s@" % path
        return path


class VcsGit (VcsBase):
    """
    VCS: Git.
    """

    def __init__ (self):

        # Environment to cancel any localization in output of operations,
        # for methods which need to parse the output.
        self._env = os.environ.copy()
        self._env["LC_ALL"] = "C"


    def _gitroot (self, paths):

        single = False
        if isinstance(paths, basestring):
            paths = [paths]
            single = True

        # Take first path as referent.
        path = os.path.abspath(paths[0])

        root = None
        if os.path.isfile(path):
            pdir = os.path.dirname(path)
        else:
            pdir = path
        while True:
            gitpath = os.path.join(pdir, ".git")
            if os.path.isdir(gitpath):
                root = pdir
                break
            pdir_p = pdir
            pdir = os.path.dirname(pdir)
            if pdir == pdir_p:
                break

        if root is None:
            raise PologyError(
                _("@info \"Git\" is a version control system",
                  "Cannot find Git repository for '%(path)s'.",
                  path=path))

        rpaths = []
        for path in paths:
            path = os.path.abspath(path)
            path = path[len(root) + len(os.path.sep):]
            rpaths.append(path)

        if single:
            return root, rpaths[0]
        else:
            return root, rpaths


    def add (self, paths, repadd=False):
        # Base override.

        if isinstance(paths, basestring):
            paths = [paths]
        if not paths:
            return True

        root, paths = self._gitroot(paths)

        success = True
        apaths = []
        for path in paths:
            if collect_system("git add %s" % path, wdir=root)[2] != 0:
                success = False
                break
            apaths.append(path)

        return success if not repadd else [success, apaths]


    def remove (self, path):
        # Base override.

        if os.path.isdir(path):
            warning(_("@info",
                      "Git cannot remove directories (tried on '%(path)s').",
                      path=path))
            return False

        root, path = self._gitroot(path)

        if collect_system("git rm %s" % path, wdir=root)[2] != 0:
            return False

        return True


    def move (self, spath, dpath):
        # Base override.

        root1, spath = self._gitroot(spath)
        root2, dpath = self._gitroot(dpath)
        if root1 != root2:
            warning(_("@info",
                      "Trying to move paths between different repositories."))
            return False

        if collect_system("git mv %s %s" % (spath, dpath), wdir=root1)[2] != 0:
            return False

        return True


    def revision (self, path):
        # Base override.

        root, path = self._gitroot(path)

        res = collect_system("git log %s" % path, wdir=root, env=self._env)
        rx = re.compile(r"^commit\s*([0-9abcdef]+)", re.I)
        revid = ""
        for line in res[0].split("\n"):
            m = rx.search(line)
            if m:
                revid = m.group(1)
                break

        return revid


    def is_clear (self, path):
        # Base override.

        root, path = self._gitroot(path)

        res = collect_system("git status %s" % path, wdir=root, env=self._env)
        rx = re.compile(r"\bmodified:\s*(\S.*)", re.I)
        for line in res[0].split("\n"):
            m = rx.search(line)
            if m:
                mpath = m.group(1)
                if os.path.isfile(path):
                    if mpath == path:
                        return False
                else:
                    if not path or mpath[len(path):].startswith(os.path.sep):
                        return False

        return True


    def is_versioned (self, path):
        # Base override.

        root, path = self._gitroot(path)
        if not path:
            return True

        res = collect_system("git status", wdir=root, env=self._env)
        rx = re.compile(r"untracked.*?:", re.I)
        m = rx.search(res[0])
        if m:
            for line in res[0][m.end():].split("\n"):
                line = line.lstrip("#").strip()
                if line == path:
                    print "here!"
                    return False

        return True


    def export (self, path, rev, dstpath, rewrite=None):
        # Base override.

        root, path = self._gitroot(path)
        ret = True

        if rev is None:
            rev = "HEAD"

        if rewrite:
            path = rewrite(path, rev)

        # FIXME: Better temporary location."
        tarpdir = "/tmp"
        tarbdir = "git-archive-tree%d" % os.getpid()
        res = collect_system("  git archive --prefix=%s/ %s %s "
                             "| (cd %s && tar xf -)"
                             % (tarbdir, rev, path, tarpdir),
                             wdir=root)
        if res[2] == 0:
            tardir = os.path.join(tarpdir, tarbdir)
            tarpath = os.path.join(tardir, path)
            try:
                shutil.move(tarpath, dstpath)
            except:
                ret = False
            if os.path.isdir(tardir):
                shutil.rmtree(tardir)
        else:
            ret = False

        return ret


    def commit (self, paths, message=None, msgfile=None, incparents=True):
        # Base override.

        if isinstance(paths, basestring):
            paths = [paths]
        if not paths:
            return True

        opaths = paths
        root, paths = self._gitroot(paths)

        # Check if all paths are versioned.
        # Add to index any modified paths that have not been added.
        for opath in opaths:
            if not self.is_versioned(opath):
                warning(_("@info"
                          "Git cannot commit non-versioned path '%(path)s'.",
                          path=opath))
                return False
            if os.path.exists(opath) and not self.add(opath):
                warning(_("@info"
                          "Git cannot add path '%(path)s' to index.",
                          path=opath))
                return False

        # Reset all paths in index which have not been given to commit.
        ipaths = self._paths_to_commit(root)
        rpaths = list(set(ipaths).difference(paths))
        if rpaths:
            warning(_("@info",
                      "Git is resetting paths in index which are "
                      "not to be committed."))
            cmdline = "git reset %s" % " ".join(rpaths)
            system_wd(unicode_to_str(cmdline), root)
            # ...seems to return != 0 even if it did what it was told to.

        # Commit the index.
        cmdline = "git commit "
        if message is not None:
            cmdline += "-m \"%s\" " % message.replace("\"", "\\\"")
        elif msgfile is not None:
            cmdline += "-F \"%s\" " % msgfile.replace("\"", "\\\"")

        # Do not use collect_system(), user may need to input stuff.
        #report(cmdline)
        if system_wd(unicode_to_str(cmdline), root) != 0:
            return False

        return True


    def log (self, path, rev1=None, rev2=None):
        # Base override.

        root, path = self._gitroot(path)

        res = collect_system("git log %s" % path, wdir=root, env=self._env)
        if res[-1] != 0:
            return []
        rev = ""
        next_auth, next_date, next_cmsg = range(3)
        next = -1
        entries = []
        lines = res[0].split("\n")
        for i in range(len(lines) + 1):
            if i < len(lines):
                line = lines[i]
            if i == len(lines) or line.startswith("commit"):
                if rev:
                    cmsg = "\n".join(cmsg).strip("\n")
                    entries.append((rev, user, dstr, cmsg))
                rev = line[line.find(" ") + 1:].strip()
                cmsg = []
                next = next_auth
            elif next == next_auth:
                user = line[line.find(":") + 1:].strip()
                next = next_date
            elif next == next_date:
                dstr = line[line.find(":") + 1:].strip()
                next = next_cmsg
            elif next == next_cmsg:
                cmsg += [line[4:]]

        entries.reverse()

        return _crop_log(entries, rev1, rev2)


    def to_commit (self, path):
        # Base override.

        root, path = self._gitroot(path)

        ncpaths = self._paths_to_commit(root, path or ".")

        return ncpaths


    def _paths_to_commit (self, root, path=None):

        if path:
            cmdline = "git status %s" % path
        else:
            cmdline = "git status"
        res = collect_system(cmdline, wdir=root, env=self._env)

        sect_rx = re.compile(r"^# (\S.*):$", re.I)
        file_rx = re.compile(r"^#\s+.*\w:\s*(.+?)\s*$", re.I)
        inlist = False
        ipaths = []
        for line in res[0].split("\n"):
            m = sect_rx.search(line)
            if m:
                if (   m.group(1).endswith("to be committed") # git 1.6.x
                    or m.group(1).endswith("but not updated") # git 1.7.x
                ):
                    inlist = True
                else:
                    break
            if not inlist:
                continue
            m = file_rx.search(line)
            if m:
                ipaths.append(m.group(1))

        return ipaths


    def diff (self, path, rev1=None, rev2=None):
        # Base override.

        root, path = self._gitroot(path)

        if rev1 is not None and rev2 is not None:
            rspec = "%s..%s" % (rev1, rev2)
        elif rev1 is not None:
            rspec = "%s" % rev1
        elif rev2 is not None:
            raise PologyError(
                _("@info"
                  "Git cannot diff from non-staged paths to a commit."))
        else:
            rspec = ""

        res = collect_system("git diff %s %s" % (rspec, path),
                             wdir=root, env=self._env)
        if res[-1] != 0:
            warning(_("@info"
                      "Git reports it cannot diff path '%(path)s':\n"
                      "%(msg)s",
                      path=path, msg=res[1]))
            return []

        udiff = []
        nskip = 0
        for line in res[0].split("\n"):
            if nskip > 0:
                nskip -= 1
                continue

            if line.startswith("diff"):
                m = re.search(r"a/(.*?) *b/", line)
                udiff.append((":", m.group(1) if m else ""))
                nskip = 3
            elif line.startswith("@@"):
                m = re.search(r"-(\d+),(\d+) *\+(\d+),(\d+)", line)
                spans = tuple(map(int, m.groups())) if m else (0, 0, 0, 0)
                udiff.append(("@", spans))
            elif line.startswith(" "):
                udiff.append((" ", line[1:]))
            elif line.startswith("-"):
                udiff.append(("-", line[1:]))
            elif line.startswith("+"):
                udiff.append(("+", line[1:]))

        return udiff


    def revert (self, path):
        # Base override.

        res = collect_system("git checkout %s" % path,
                             wdir=root, env=self._env)
        if res[-1] != 0:
            warning(_("@info"
                      "Git reports it cannot revert path '%(path)s':\n"
                      "%(msg)s",
                      path=path, msg=res[1]))
            return []

        return True


def _crop_log (entries, rev1, rev2):

    start = 0
    if rev1 is not None:
        while start < len(entries):
            if entries[start][0] == rev1:
                break
            start += 1

    end = len(entries)
    if rev2 is not None:
        while end > 0:
            end -= 1
            if entries[end][0] == rev2:
                break

    return entries[start:end]


def _temp_paths_file (paths):

    content = unicode_to_str("\n".join(paths) + "\n")
    tmpf, tmppath = tempfile.mkstemp()
    os.write(tmpf, content)
    os.close(tmpf)
    return tmppath


_register_vcs()
