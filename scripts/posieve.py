#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Sieve messages in collections of PO files.

Frequently there is a need to visit every message, either in a single catalog
or collection of catalogs, and perform some operations on each. The operations
may be checks, modifications, data collection, etc. This script is intended
to ease this process, both from users' point of view and that of preparing
new custom operations.

The bundle of operations to be performed on a message is called a "sieve".
C{posieve} does conceptually a simple thing: it runs each message in each
catalog given to it, through sieves that the user has specified.

Pology comes with many internal sieves, but users can write their own too.
For example, here is how one could run the internal L{C{stats}<sieve.stats>}
sieve, to collect statistics on all PO files in C{frobaz} directory::

    $ posieve.py stats frobaz/
    ... (after some time, a table with stats appears) ...

Assuming that C{frobaz} contains a lot of PO files, user would wait some time
until all the messages are pushed through the sieve, and then C{stats} would
present its findings in a table.

After the sieve name, any number of directory or file paths can be specified.
C{posieve} will consider file paths as catalog files to open, and search
recursively through directory paths for all files ending with C{.po} or C{.pot}.

Sieves need not only collect data (such as the C{stats} above) or do checks,
but may also modify messages. Whenever a message is modified, the catalog
with changes will be saved over old catalog, and the user will be informed
by an exclamation mark followed by the catalog path. An example of such
internal sieve is L{tag-incomplete<sieve.tag_incomplete>}, which will add
C{incomplete} flag to each fuzzy or untranslated message::

    $ posieve.py tag-incomplete frobaz/
    ! frobaz/alfa.po
    ! frobaz/bravo.po
    ! frobaz/charlie.po
    Total incomplete tagged: 42

C{posieve} itself monitors and informs about changed catalogs, whereas the
final line in the example above has been output by the C{tag-incomplete} sieve.
Sieves will frequently issue such final reports.

More than one sieve can be applied to the catalog collection in one pass.
This is called the "sieve chain", and is specified as comma-separated list
of sieve names instead of a lone sieve name. Each message is passed through
the sieves in the given order, in a pipeline fashion -- the output from the
previous sieve is input to the next -- before moving to the next message.
This order is important to bear in mind when two sieves in the chain can both
modify a message. For example::

    $ posieve.py stats,tag-incomplete frobaz/
    ! frobaz/alfa.po
    ! frobaz/bravo.po
    ! frobaz/charlie.po
    ... (table with stats) ...
    Total incomplete tagged: 42

If the order were C{tag-incomplete,stats} in this case the effect on the
catalogs would be the same, but number of tagged messages would be the first
in output, followed by the table with statistics.

C{posieve} takes a few options, which you can list with the usual C{--help}
option. However, more interesting is that sieves themselves can be sent some
options. These sieve options are sent to sieve by the C{-s} option, which
takes as argument a C{key:value} pair. As many of these as needed can be given.
For example, C{stats} sieve could be instructed to take into account only
messages with at most 5 words, like this::

    $ posieve.py stats -s maxwords:5 frobaz/

Sieve options can also be switches, when only the key is given. C{stats} can
be instructed to show statistics in greater detail like this::

    $ posieve.py stats -s detail frobaz/

In case a sieve chain is specified, sieve options are routed to sieves as they
will accept them. If two sieves in the chain have a same-named option, when
given on the command line it will be sent to both.

Pology also collects language-specific internal sieves. These are run by
prefixing sieve name with the language code and a colon. For example, there is
a sieve for the French language that replaces ordinary with non-breaking spaces
in some interpunction scenarios, the L{setUbsp<l10n.fr.sieve.setUbsp>},
which is invoked like this::

    $ posieve.py fr:setUbsp frobaz-fr/

In case the user has written a custom sieve, it can be run by simply stating
its path as sieve name. For C{posieve} to acknowledge it as external sieve,
the file name has to end in C{.py}. Custom sieves can be chained as any other. For example::

    $ posieve.py ../custom/my_count.py frobaz/
    $ posieve.py stats,../custom/my_count.py frobaz/

The list of all internal sieves is given within the L{sieve} module, as well
as instructions on how to write custom sieves. The list of internal language-specific sieves can be found within C{l10n.<lang>.sieve} module of
the languages that have them.

If an internal sieve contains underscores in its name, they can be replaced
with dashes in the C{posieve} command line. The dashes will be converted back
to underscores before trying to resolve the location of the internal sieve.

The following user configuration fields are considered
(they may be overridden by command line options):
  - C{[posieve]/wrap}: whether to wrap message fields (default C{yes})
  - C{[posieve]/tag-split}: whether to split mesage fields on tags
        (default C{yes})
  - C{[posieve]/skip-on-error}: whether to skip current catalog on
        processing error, and go to next (default C{yes})
  - C{[posieve]/msgfmt-check}: whether to check catalog file by C{msgfmt -c}
        before sieving (default C{no})
  - C{[posieve]/use-psyco}: whether to use Psyco specializing compiler,
        if available (default C{yes})

@warning: This module is a script for end-use. No exposed functionality
should be considered public API, it is subject to change without notice.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import fallback_import_paths

import sys
import os
import imp
import locale
import re
from optparse import OptionParser
import glob

import pology.misc.wrap as wrap
from pology.misc.fsops import collect_catalogs, collect_system
from pology.file.catalog import Catalog
from pology.misc.report import error, warning, report
import pology.misc.config as pology_config
from pology import rootdir
from pology.misc.subcmd import ParamParser


def main ():

    locale.setlocale(locale.LC_ALL, "")

    # Get defaults for command line options from global config.
    cfgsec = pology_config.section("posieve")
    def_do_wrap = cfgsec.boolean("wrap", True)
    def_do_tag_split = cfgsec.boolean("tag-split", True)
    def_do_skip = cfgsec.boolean("skip-on-error", True)
    def_msgfmt_check = cfgsec.boolean("msgfmt-check", False)
    def_use_psyco = cfgsec.boolean("use-psyco", True)

    # Setup options and parse the command line.
    usage = u"""
%prog [options] sieve [POPATHS...]
""".strip()
    description = u"""
Apply sieves to PO paths, which may be either single PO files or directories
to search recursively for PO files. Some of the sieves only examine PO files,
while other can modify them. The first non-option argument is the sieve name;
a list of several comma-separated sieves can be given too.
""".strip()
    version = u"""
%prog (Pology) experimental
Copyright © 2007 Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
""".strip()

    opars = OptionParser(usage=usage, description=description, version=version)
    opars.add_option(
        "-l", "--list-sieves",
        action="store_true", dest="list_sieves", default=False,
        help="list available internal sieves")
    opars.add_option(
        "-H", "--help-sieves",
        action="store_true", dest="help_sieves", default=False,
        help="show help for applied sieves")
    opars.add_option(
        "-f", "--files-from", metavar="FILE",
        dest="files_from",
        help="get list of input files from FILE (one file per line)")
    opars.add_option(
        "-s", "--sieve-option", metavar="NAME[:VALUE]",
        action="append", dest="sieve_params", default=[],
        help="pass an option to the sieves")
    opars.add_option(
        "--force-sync",
        action="store_true", dest="force_sync", default=False,
        help="force rewrite of all messages, modified or not")
    opars.add_option(
        "--no-wrap",
        action="store_false", dest="do_wrap", default=def_do_wrap,
        help="do not break long unsplit lines into several lines")
    opars.add_option(
        "--no-tag-split",
        action="store_false", dest="do_tag_split", default=def_do_tag_split,
        help="do not break lines on selected tags")
    opars.add_option(
        "--no-psyco",
        action="store_false", dest="use_psyco", default=def_use_psyco,
        help="do not try to use Psyco specializing compiler")
    opars.add_option(
        "--no-skip",
        action="store_false", dest="do_skip", default=def_do_skip,
        help="do not skip catalogs which signal errors")
    opars.add_option(
        "-m", "--output-modified", metavar="FILE",
        action="store", dest="output_modified", default=None,
        help="output names of modified files into FILE")
    opars.add_option(
        "-c", "--msgfmt-check",
        action="store_true", dest="msgfmt_check", default=def_msgfmt_check,
        help="check catalogs by msgfmt and skip those which do not pass")
    opars.add_option(
        "-e", "--exclude-cat", metavar="REGEX",
        dest="exclude_cat",
        help="do not sieve files when their catalog name (file basename "
             "without .po* extension) matches the regular expression")
    opars.add_option(
        "-E", "--exclude-path", metavar="REGEX",
        dest="exclude_path",
        help="do not sieve files when their full path matches "
             "the regular expression")
    opars.add_option(
        "-i", "--include-cat", metavar="REGEX",
        help="sieve files only when their catalog name (file basename "
             "without .po* extension) matches the regular expression")
    opars.add_option(
        "-I", "--include-path", metavar="REGEX",
        dest="include_path",
        help="sieve files only when their full path matches "
             "the regular expression")
    opars.add_option(
        "-v", "--verbose",
        action="store_true", dest="verbose", default=False,
        help="output more detailed progress info")
    (op, free_args) = opars.parse_args()

    if len(free_args) < 1 and not op.list_sieves:
        opars.error("must provide sieve to apply")

    op.raw_sieves = []
    op.raw_paths = []
    if len(free_args) >= 1:
        op.raw_sieves = free_args[0]
        op.raw_paths = free_args[1:]

    # Convert all string values in options to unicode.
    local_encoding = locale.getpreferredencoding()
    for att, val in op.__dict__.items():
        if isinstance(val, str):
            op.__dict__[att] = unicode(val)
        elif isinstance(val, list):
            op.__dict__[att] = [unicode(x, local_encoding) for x in val]

    # Could use some speedup.
    if op.use_psyco:
        try:
            import psyco
            psyco.full()
        except ImportError:
            pass

    # Parse sieve options.
    # FIXME: Temporary, until all sieves are switched to new style.
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
    for swspec in op.sieve_params:
        if swspec.find(":") >= 0:
            sopt, value = swspec.split(":", 1)
        else:
            sopt = swspec
            value = ""
        sopts[sopt] = value

    # Dummy-set all internal sieves as requested if sieve listing required.
    sieves_requested = []
    if op.list_sieves:
        # Global sieves.
        modpaths = glob.glob(os.path.join(rootdir(), "sieve", "[a-z]*.py"))
        modpaths.sort()
        for modpath in modpaths:
            sname = os.path.basename(modpath)[:-3] # minus .py
            sname = sname.replace("_", "-")
            sieves_requested.append(sname)
        # Language-specific sieves.
        modpaths = glob.glob(os.path.join(rootdir(),
                                          "l10n", "*", "sieve", "[a-z]*.py"))
        modpaths.sort()
        for modpath in modpaths:
            sname = os.path.basename(modpath)[:-3] # minus .py
            sname = sname.replace("_", "-")
            lang = os.path.basename(os.path.dirname(os.path.dirname(modpath)))
            sieves_requested.append(lang + ":" + sname)

    # Load sieve modules from supplied names in the command line.
    if not sieves_requested:
        sieves_requested = op.raw_sieves.split(",")
    sieve_modules = []
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
            sieve_path = os.path.join(rootdir(), sieve_path_base)
        else:
            # Sieve name is its path.
            sieve_path = sieve_name
        try:
            sieve_file = open(sieve_path)
        except IOError:
            error("cannot load sieve: %s" % sieve_path)
        # Load file into new module.
        sieve_mod_name = "sieve_" + str(len(sieve_modules))
        sieve_mod = imp.new_module(sieve_mod_name)
        exec sieve_file in sieve_mod.__dict__
        sieve_file.close()
        sys.modules[sieve_mod_name] = sieve_mod # to avoid garbage collection
        sieve_modules.append((sieve_name, sieve_mod))
        if not hasattr(sieve_mod, "Sieve"):
            error("module does not define Sieve class: %s" % sieve_path)
        # FIXME: Check that module has setup_sieve function,
        # once all sieves are switched to new style.

    # Define and parse sieve parameters.
    pp = ParamParser()
    snames = []
    for name, mod in sieve_modules:
        # FIXME: Remove when all sieves are switched to new style.
        if not hasattr(mod, "setup_sieve"):
            continue
        scview = pp.add_subcmd(name)
        if hasattr(mod, "setup_sieve"):
            mod.setup_sieve(scview)
        snames.append(name)
    if op.list_sieves:
        report("Available internal sieves:")
        report(pp.listcmd(snames))
        sys.exit(0)
    if op.help_sieves:
        report("Help for sieves:")
        report("")
        report(pp.help(snames))
        sys.exit(0)
    # FIXME: Abort instead when all sieves are switched to new style.
    sparams, nacc_params = pp.parse(op.sieve_params, snames) #, abort=True)

    # Create sieves.
    sieves = []
    for name, mod in sieve_modules:
        # FIXME: Remove when all sieves are switched to new style.
        if not hasattr(mod, "setup_sieve"):
            sieves.append(mod.Sieve(sopts, op))
            continue
        sieves.append(mod.Sieve(sparams[name], op))

    # Old-style sieves will have marked options that they have accepted.
    # FIXME: Remove when all sieves are switched to new style.
    all_nacc_params = set(sopts.unaccepted().keys())
    all_nacc_params = all_nacc_params.intersection(set(nacc_params))
    if all_nacc_params:
        error("no sieve has accepted these parameters: %s"
              % ", ".join(all_nacc_params))

    # Get the message monitoring indicator from the sieves.
    # Monitor unless all sieves have requested otherwise.
    use_monitored = False
    for sieve in sieves:
        if getattr(sieve, "caller_monitored", True):
            use_monitored = True
            break
    if op.verbose and not use_monitored:
        print "--> Not monitoring messages"

    # Get the sync indicator from the sieves.
    # Sync unless all sieves have requested otherwise.
    do_sync = False
    for sieve in sieves:
        if getattr(sieve, "caller_sync", True):
            do_sync = True
            break
    if op.verbose and not do_sync:
        print "--> Not syncing after sieving"

    # Open in header-only mode if no sieve has message processor.
    # Categorize sieves by the presence of message/header processors.
    use_headonly = True
    header_sieves = []
    message_sieves = []
    for sieve in sieves:
        if hasattr(sieve, "process"):
            use_headonly = False
            message_sieves.append(sieve)
        if hasattr(sieve, "process_header"):
            header_sieves.append(sieve)
    if op.verbose and use_headonly:
        print "--> Opening catalogs in header-only mode"

    # Assemble list of files.
    file_or_dir_paths = op.raw_paths or ["."]
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

    # Prepare selection regexes.
    exclude_cat_rx = None
    if op.exclude_cat:
        exclude_cat_rx = re.compile(op.exclude_cat, re.I|re.U)
    exclude_path_rx = None
    if op.exclude_path:
        exclude_path_rx = re.compile(op.exclude_path, re.I|re.U)
    include_cat_rx = None
    if op.include_cat:
        include_cat_rx = re.compile(op.include_cat, re.I|re.U)
    include_path_rx = None
    if op.include_path:
        include_path_rx = re.compile(op.include_path, re.I|re.U)

    # Sieve the messages throughout the files.
    modified_files = []
    for fname in fnames:
        # Construct catalog name by stripping final .po* from file basename.
        cname = os.path.basename(fname)
        p = cname.rfind(".po")
        if p > 0:
            cname = cname[:p]

        # Check if the catalog should be sieved
        do_sieve = True
        if do_sieve and exclude_cat_rx:
            do_sieve = exclude_cat_rx.search(cname) is None
        if do_sieve and exclude_path_rx:
            do_sieve = exclude_path_rx.search(fname) is None
        if do_sieve and include_cat_rx:
            do_sieve = include_cat_rx.search(cname) is not None
        if do_sieve and include_path_rx:
            do_sieve = include_path_rx.search(fname) is not None
        if not do_sieve:
            if op.verbose:
                print "skipping on request: %s" % (fname,)
            continue

        if op.verbose:
            print "sieving %s ..." % (fname,),

        if op.msgfmt_check:
            # TODO: Make it more portable?
            d1, oerr, ret = collect_system("msgfmt -o/dev/null -c %s" % fname)
            if ret != 0:
                oerr = oerr.strip()
                warning("%s -- skipping, msgfmt check failed:\n"
                        "%s" % (fname, oerr))
                continue

        try:
            cat = Catalog(fname, monitored=use_monitored, wrapf=wrap_func,
                          headonly=use_headonly)
        except KeyboardInterrupt:
            sys.exit(130)
        except StandardError, e:
            if op.do_skip:
                warning("%s -- skipping, parsing failure: %s" % (fname, e))
                continue
            else:
                raise

        if not use_headonly:
            # In normal mode, first run all header sieves on this catalog,
            # then all message sieves on each message.
            for sieve in header_sieves:
                sieve.process_header(cat.header, cat)
            for msg in cat:
                for sieve in message_sieves:
                    sieve.process(msg, cat)
        else:
            # In header-only mode, run only header sieves on this catalog.
            for sieve in header_sieves:
                sieve.process_header(cat.header, cat)

        if do_sync and cat.sync(op.force_sync):
            if op.verbose:
                print "MODIFIED"
            else:
                print "! %s" % (fname,)
            modified_files.append(fname)
        else:
            if op.verbose: print ""

    for sieve in sieves:
        if hasattr(sieve, "finalize"):
            sieve.finalize()

    if op.output_modified:
        ofh = open(op.output_modified, "w")
        ofh.write("\n".join(modified_files))
        ofh.close


if __name__ == '__main__':
    main()
