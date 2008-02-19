# -*- coding: UTF-8 -*-

"""
Pipe PO files through Gettext commands.
"""

import os

def msgfilter (filtr, options=""):
    """Factory of hooks to pass PO files through msgfilter.

    Produces hooks with (filepath) signature, returning True on success.
    Hooks modify the given file in place.
    The default command line to msgfilter is::

        msgfilter <options> -i <filepath> -o <filepath> <filtr>

    where options argument to the factory may be used to pass any
    extra options to msgfilter.
    """

    # FIXME: Check availability and version of msgfilter.

    base_cmdline = "msgfilter " + options + " "

    def hook (filepath):
        cmdline = base_cmdline + "-i %s -o %s " % (filepath, filepath) + filtr
        ret = os.system(cmdline)
        if ret:
            print   "%s: msgfilter failed (filter: '%s', options: '%s')" \
                  % (filepath, filtr, options)
            return False
        return True

    return hook


def msgfmt (options=""):
    """Factory of hooks to pass PO files through msgfmt.

    Produces hooks with (filepath) signature, returning True on success.
    Hooks do not modify the given file.
    The default command line to msgfmt is::

        msgfilter <options> -o/dev/null <filepath>

    where options argument to the factory may be used to pass any
    extra options to msgfmt.
    """

    # FIXME: Check availability and version of msgfmt.

    base_cmdline = "msgfmt " + options + " -o/dev/null "

    def hook (filepath):
        cmdline = base_cmdline + filepath
        ret = os.system(cmdline)
        if ret:
            print "%s: msgfmt failed (options: '%s')" % (filepath, options)
            return False
        return True

    return hook
