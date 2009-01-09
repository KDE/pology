# -*- coding: UTF-8 -*-

"""
Version control operations.

Collections of PO files are usually kept under some sort of version control.
This module provides typical version control operations, abstracted across
various version control systems.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import os
import re
import shutil

from pology.misc.report import report, error, warning
from pology.misc.fsops import collect_system


def make_vcs (vcskey):
    """
    Factory for version control systems.

    Desired VCS is identified by a keyword. Currently available:
      - Subversion (C{svn}, C{subversion})
      - dummy noop (C{none}, C{noop})

    @param vcskey: keyword identifier of the VCS
    @type vcskey: string

    @return: version control object
    @rtype: instance of L{VcsBase}
    """

    nkey = vcskey.lower()
    if nkey in ("none", "noop"):
        return VcsNoop()
    elif nkey in ("svn", "subversion"):
        return VcsSubversion()
    else:
        error("unknown version control system requested by key '%s'" % vcskey)


class VcsBase (object):
    """
    Abstract base for VCS objects.
    """

    def add (self, path):
        """
        Add path to version control.

        @param path: path to add
        @type path: string

        @return: C{True} if addition successful
        @rtype: bool
        """
        error("selected version control system does not define adding")


    def remove (self, path):
        """
        Remove path from version control and from disk.

        @param path: path to remove
        @type path: string

        @return: C{True} if removal successful
        @rtype: bool
        """

        error("selected version control system does not define removing")


    def revision (self, path):
        """
        Get current revision ID of the path.

        @param path: path to query for revision
        @type path: string

        @return: revision ID
        @rtype: string
        """

        error("selected version control system does not define revision query")


    def is_clear (self, path):
        """
        Check if the path is in clear state.

        Clear state means none of: not version-controlled, modified, added...

        @param path: path to check the state of
        @type path: string

        @return: C{True} if clear
        @rtype: bool
        """

        error("selected version control system does not define state query")


    def is_older (self, rev1, rev2):
        """
        Check if revision 1 is older than revision 2.

        @param rev1: revision string
        @type rev1: string
        @param rev2: revision string
        @type rev2: string

        @return: C{True} if first revision older than second
        @rtype: bool
        """

        error("selected version control system does not define "
              "revision age comparison")


    def is_versioned (self, path):
        """
        Check if path is under version control.

        @param path: path to check
        @type path: string

        @return: C{True} if versioned
        @rtype: bool
        """

        error("selected version control system does not define "
              "checking whether a path is version controlled")


    def export (self, path, rev, dstpath, rewrite=None):
        """
        Export a versioned file.

        Makes a copy of versioned file pointed to by local path C{path},
        in the revision C{rev}, to destination path C{dstpath}.
        If C{rev} is C{None}, the clean version of C{path} according
        to current local repository state is copied to C{dstpath}.

        Final repository path, as determined from C{path}, can be filtered
        through an external function C{rewrite} before being used.
        The function takes as arguments the path and revision strings.
        This can be useful, for example, to reroute remote repository URL.

        @param path: path of the versioned file in local repository
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

        error("selected version control system does not define "
              "fetching a versioned file")


    def commit (self, paths, message=None):
        """
        Commit paths to the repository.

        Paths can include any number of files and directories.
        It depends on the particular VCS what committing means,
        but in general it should be the earliest level at which
        modifications are recorded in the repository history.

        If the commit message is not given, VCS should ask for one as usual
        (pop an editor window, or whatever the user has configured).

        @param paths: paths to commit
        @type paths: list of strings
        @param message: commit message
        @type message: string or None

        @return: C{True} if committing succeeded, C{False} otherwise
        @rtype: bool
        """

        error("selected version control system does not define "
              "committing of paths")


class VcsNoop (VcsBase):
    """
    VCS: Dummy VCS which silently passes any operation and does nothing.
    """

    def add (self, path):
        # Base override.

        return True


    def remove (self, path):
        # Base override.

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


    def commit (self, paths, message=None):
        # Base override.

        return True


class VcsSubversion (VcsBase):
    """
    VCS: Subversion.
    """

    def add (self, path):
        # Base override.

        # Try adding by backtracking.
        cpath = path
        while collect_system("svn add %s" % cpath)[2] != 0:
            cpath = os.path.dirname(cpath)
            if not cpath:
                return False

        return True


    def remove (self, path):
        # Base override.

        if collect_system("svn remove %s" % path)[2] != 0:
            return False

        return True


    def revision (self, path):
        # Base override.

        res = collect_system("svn info %s" % path)
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

        res = collect_system("svn status %s" % path)
        clear = not re.search(r"^\S", res[0])

        return clear


    def is_older (self, rev1, rev2):
        # Base override.

        return int(rev1) < int(rev2)


    def is_versioned (self, path):
        # Base override.

        res = collect_system("svn info %s" % path)
        rx = re.compile(r"^Repository", re.I)
        for line in res[0].split("\n"):
            if rx.search(line):
                return True

        return False


    def export (self, path, rev, dstpath, rewrite=None):
        # Base override.

        if rev is None:
            cmdline = "svn export %s %s" % (path, dstpath)
            if collect_system(cmdline)[-1] != 0:
                return False
            return True

        res = collect_system("svn info %s" % path)
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

        cmdline = "svn export %s -r %s %s" % (rempath, rev, dstpath)
        if collect_system(cmdline)[-1] != 0:
            return False

        return True


    def commit (self, paths, message=None):
        # Base override.

        cmdline = "svn commit "
        if message is not None:
            cmdline += "-m \"%s\" " % message.replace("\"", "\\\"")
        cmdline += " ".join(paths)

        # Do not use collect_system(), user may need to input stuff.
        #report(cmdline)
        if os.system(cmdline) != 0:
            return False

        return True

