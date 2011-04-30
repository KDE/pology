# -*- coding: UTF-8 -*-

"""
Wrappers for commands from Gettext tools.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import os
import subprocess

from pology import _, n_
from pology.report import warning
from pology.fsops import unicode_to_str


def msgfilter (filtr, options=[]):
    """
    Pass PO file through C{msgfilter(1)} [hook factory].

    Wrappers modify PO files in place; the executed command is::

        msgfilter <options> -i <filepath> -o <filepath> <filtr>

    where C{options} parameter may be used to pass any
    extra options to C{msgfilter}.
    Both C{filtr} and C{options} are lists of command line arguments
    rather than monolithic strings, to avoid shell quoting problems.
    For example, to rewrap the file at 70 columns::

        msgfilter(["cat"], ["-w", "70"])

    or to replace every C{foo} with C{bar}:

        msgfilter(["sed", "s/foo/bar/g"])

    @param filtr: filter to use
    @type filtr: [string*]
    @param options: additional options to pass to C{msgfilter}
    @type options: [string*]

    @return: type F6A hook
    @rtype: C{(filepath) -> numerr}

    @note: In case C{msgfilter} does not finish without errors,
        wrapper always reports number of errors as 1.
    """

    # FIXME: Check availability and version of msgfilter.

    base_cmdargs = ["msgfilter"] + options

    def wrapper (filepath):
        cmdargs = base_cmdargs + ["-i", filepath, "-o", filepath] + filtr
        cmdargs = map(unicode_to_str, cmdargs)
        ret = subprocess.call(cmdargs)
        if ret:
            warning(_("@info",
                      "%(file)s: %(cmd)s failed with exit code %(num)d "
                      "(filter: '%(filter)s', options: '%(options)s')",
                      file=filepath, cmd="msgfilter", num=ret, filter=filtr,
                      options=options))
            return 1
        return 0

    return wrapper


def msgfmt (options=[]):
    """
    Pass PO file through C{msgfmt(1)} [hook factory].

    The file is not modified; the executed command is::

        msgfilter <options> -o /dev/null <filepath>

    where C{options} parameter may be used to pass any
    extra options to C{msgfmt}.
    C{options} is a list of command line arguments
    rather than a monolithic string, to avoid shell quoting problems.

    @param options: additional options to pass to C{msgfmt}
    @type options: [string*]

    @return: type S6A hook
    @rtype: C{(filepath) -> numerr}

    @note: In case C{msgfmt} does not finish without errors,
        wrapper always reports number of errors as 1.
    """

    # FIXME: Check availability and version of msgfmt.

    base_cmdargs = ["msgfmt"] + options + ["-o", "/dev/null"]

    def wrapper (filepath):
        cmdargs = base_cmdargs + [filepath]
        cmdargs = map(unicode_to_str, cmdargs)
        ret = subprocess.call(cmdargs)
        if ret:
            warning(_("@info",
                      "%(file)s: %(cmd)s failed with exit code %(num)d "
                      "(options: '%(options)s')",
                      file=filepath, cmd="msgfmt", num=ret, options=options))
            return 1
        return 0

    return wrapper

