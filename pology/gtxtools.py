# -*- coding: UTF-8 -*-

"""
Wrappers for commands from Gettext tools.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import os

from pology import _, n_
from pology.report import warning


def msgfilter (filtr, options=""):
    """
    Pass PO file through C{msgfilter(1)} [hook factory].

    Wrappers modify PO files in place; the executed command is::

        msgfilter <options> -i <filepath> -o <filepath> <filtr>

    where C{options} parameter may be used to pass any
    extra options to C{msgfilter}.

    @param filtr: filter to use (e.g. C{cat} for no-op)
    @type filtr: string
    @param options: additional options to pass to C{msgfilter}
    @type options string

    @return: type F6A hook
    @rtype: C{(filepath) -> numerr}

    @note: In case C{msgfilter} does not finish without errors,
        wrapper always reports number of errors as 1.
    """

    # FIXME: Check availability and version of msgfilter.

    base_cmdline = "msgfilter " + options + " "

    def wrapper (filepath):
        cmdline = base_cmdline + "-i %s -o %s " % (filepath, filepath) + filtr
        ret = os.system(cmdline)
        if ret:
            warning(_("@info",
                      "%(file)s: %(cmd)s failed with exit code %(num)d "
                      "(filter: '%(filter)s', options: '%(options)s')",
                      file=filepath, cmd="msgfilter", num=ret, filter=filtr,
                      options=options))
            return 1
        return 0

    return wrapper


def msgfmt (options=""):
    """
    Pass PO file through C{msgfmt(1)} [hook factory].

    The file is not modified; the executed command is::

        msgfilter <options> -o/dev/null <filepath>

    where C{options} parameter may be used to pass any
    extra options to C{msgfmt}.

    @param options: additional options to pass to C{msgfmt}
    @type options: string

    @return: type S6A hook
    @rtype: C{(filepath) -> numerr}

    @note: In case C{msgfmt} does not finish without errors,
        wrapper always reports number of errors as 1.
    """

    # FIXME: Check availability and version of msgfmt.

    base_cmdline = "msgfmt " + options + " -o/dev/null "

    def wrapper (filepath):
        cmdline = base_cmdline + filepath
        ret = os.system(cmdline)
        if ret:
            warning(_("@info",
                      "%(file)s: %(cmd)s failed with exit code %(num)d "
                      "(options: '%(options)s')",
                      file=filepath, cmd="msgfmt", num=ret, options=options))
            return 1
        return 0

    return wrapper
