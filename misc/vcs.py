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

from pology.misc.report import error, warning


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
        return VcsSubversion()
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


