# -*- coding: UTF-8 -*-

"""
Summit hooks for passing PO files through Gettext's msgfilter command.
"""

import os

def msgfilter (filtr, options=""):
    """Factory of hooks to pass PO files through msgfilter.

    Produces hooks with (filepath) signature, returning True on success.
    Hooks modify the given file in place.
    The default command line to msgfilter is:
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
