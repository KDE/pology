#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import pology.misc.wrap as wrap
from pology.misc.fsops import collect_catalogs
from pology.file.catalog import Catalog

import sys, os, imp
from optparse import OptionParser


def error (msg, code=1):
    cmdname = os.path.basename(sys.argv[0])
    sys.stderr.write("%s: error: %s\n" % (cmdname, msg))
    sys.exit(code)


def main ():

    reload(sys)
    sys.setdefaultencoding("utf-8")

    # Setup options and parse the command line.
    usage = u"""
%prog [options] sieve POFILE...
""".strip()
    description = u"""
Apply a sieve to the PO files. Some of the sieves only examine PO files, and some can modify them. The first non-option argument is the sieve name; a list of several comma-separated names can be given too.
""".strip()
    version = u"""
%prog (Pology) experimental
Copyright © 2007 Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
""".strip()

    opars = OptionParser(usage=usage, description=description, version=version)
    opars.add_option(
        "-f", "--files-from", metavar="FILE",
        dest="files_from",
        help="get list of input files from FILE (one file per line)")
    opars.add_option(
        "-s", "--sieve-option", metavar="NAME[:VALUE]",
        action="append", dest="sieve_options", default=[],
        help="pass an option to the sieves")
    opars.add_option(
        "--force-sync",
        action="store_true", dest="force_sync", default=False,
        help="force rewrite of all messages, modified or not")
    opars.add_option(
        "--no-wrap",
        action="store_false", dest="do_wrap", default=True,
        help="do not break long unsplit lines into several lines")
    opars.add_option(
        "--no-tag-split",
        action="store_false", dest="do_tag_split", default=True,
        help="do not break lines on selected tags")
    opars.add_option(
        "--no-psyco",
        action="store_false", dest="use_psyco", default=True,
        help="do not try to use Psyco specializing compiler")
    opars.add_option(
        "-v", "--verbose",
        action="store_true", dest="verbose", default=False,
        help="output more detailed progress info")
    (op, free_args) = opars.parse_args()

    if len(free_args) < 1:
        opars.error("must provide sieve to apply")
    if len(free_args) < 2 and not op.files_from:
        opars.error("must provide at least one input file")

    # Convert all string values in options to unicode.
    for att, val in op.__dict__.items():
        if isinstance(val, str):
            op.__dict__[att] = unicode(val)
        elif isinstance(val, list):
            op.__dict__[att] = [unicode(x) for x in val]

    # Could use some speedup.
    if op.use_psyco:
        try:
            import psyco
            psyco.full()
        except ImportError:
            pass

    # Parse sieve options.
    class _Sieve_options (dict):
        def __init__ (self):
            self._accepted = []
        def accept (self, opt):
            # Sieves should call this method on each accepted option.
            self._accepted.append(opt)
        def unaccepted (self):
            noadm = {}
            for opt, val in dict.items(self):
                if not opt in self._accepted:
                    noadm[opt] = val
            return noadm

    sopts = _Sieve_options()
    for swspec in op.sieve_options:
        if swspec.find(":") >= 0:
            sopt, value = swspec.split(":", 1)
        else:
            sopt = swspec
            value = ""
        sopts[sopt] = value

    # Load sieve modules from supplied names in the command line.
    execdir = os.path.dirname(sys.argv[0])
    sieves_requested = free_args[0].split(",")
    sieves = []
    for sieve_name in sieves_requested:
        # Resolve sieve file.
        if not sieve_name.endswith(".py"):
            # One of internal sieves.
            if ":" in sieve_name:
                # Language-specific internal sieve.
                lang, name = sieve_name.split(":")
                sieve_path_base = os.path.join("l10n", lang, "sieve", name)
            else:
                sieve_path_base = os.path.join("sieve", sieve_name)
            sieve_path_base = sieve_path_base.replace("-", "_") + ".py"
            sieve_path = os.path.join(execdir, sieve_path_base)
        else:
            # Sieve name is its path.
            sieve_path = sieve_name
        try:
            sieve_file = open(sieve_path)
        except IOError:
            error("cannot load sieve: %s\n" % sieve_path)
        # Load file into new module.
        sieve_mod_name = "sieve_" + str(len(sieves))
        sieve_mod = imp.new_module(sieve_mod_name)
        exec sieve_file in sieve_mod.__dict__
        sieve_file.close()
        sys.modules[sieve_mod_name] = sieve_mod # to avoid garbage collection
        # Create the sieve.
        sieves.append(sieve_mod.Sieve(sopts, op))

    # Sieves will have marked options that they have accepted.
    if sopts.unaccepted():
        error("no sieve has accepted these options: %s" % sopts.unaccepted())

    # Get the message monitoring indicator from the sieves.
    # Use monitored if at least one sieve has not requested otherwise.
    use_monitored = False
    for sieve in sieves:
        if getattr(sieve, "caller_monitored", True):
            use_monitored = True
            break
    if op.verbose and not use_monitored:
        print "--> Not monitoring messages"

    # Get the sync indicator from the sieves.
    # Sync if at least one sieve has not requested otherwise.
    do_sync = False
    for sieve in sieves:
        if getattr(sieve, "caller_sync", True):
            do_sync = True
            break
    if op.verbose and not do_sync:
        print "--> Not syncing after sieving"

    # Assemble list of files.
    file_or_dir_paths = free_args[1:]
    if op.files_from:
        flines = open(op.files_from, "r").readlines()
        file_or_dir_paths.extend([f.rstrip("\n") for f in flines])
    fnames = collect_catalogs(file_or_dir_paths)

    # Decide on wrapping policy for modified messages.
    if op.do_wrap:
        if op.do_tag_split:
            wrap_func = wrap.wrap_field_ontag
        else:
            wrap_func = wrap.wrap_field
    else:
        if op.do_tag_split:
            wrap_func = wrap.wrap_field_ontag_unwrap
        else:
            wrap_func = wrap.wrap_field_unwrap

    # Sieve the messages throughout the files.
    for fname in fnames:
        if op.verbose:
            print "Sieving %s ..." % (fname,),

        try:
            cat = Catalog(fname, monitored=use_monitored, wrapf=wrap_func)
        except StandardError, e:
            print "%s (skipping)" % e
            continue
        for msg in cat:
            for sieve in sieves:
                sieve.process(msg, cat)

        if do_sync and cat.sync(op.force_sync):
            if op.verbose:
                print "MODIFIED"
            else:
                print "! %s" % (fname,)
        else:
            if op.verbose: print ""

    for sieve in sieves:
        if hasattr(sieve, "finalize"):
            sieve.finalize()


if __name__ == '__main__':
    main()
