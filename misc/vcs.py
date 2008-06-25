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

from pology.misc.report import error, warning
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

