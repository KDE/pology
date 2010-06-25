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

    $ posieve stats frobaz/
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
internal sieve is L{tag-untranslated<sieve.tag_untranslated>}, which will add
the C{untranslated} flag to each untranslated message::

    $ posieve tag-untranslated frobaz/
    ! frobaz/alfa.po
    ! frobaz/bravo.po
    ! frobaz/charlie.po
    Total untranslated messages tagged: 42

C{posieve} itself monitors and informs about changed catalogs, whereas the
final line in the example above has been output by the C{tag-untranslated}
sieve. Sieves will frequently issue such final reports.

More than one sieve can be applied to the catalog collection in one pass.
This is called the "sieve chain", and is specified as comma-separated list
of sieve names instead of a lone sieve name. Each message is passed through
the sieves in the given order, in a pipeline fashion -- the output from the
previous sieve is input to the next -- before moving to the next message.
This order is important to bear in mind when two sieves in the chain can both
modify a message. For example::

    $ posieve stats,tag-untranslated frobaz/
    ! frobaz/alfa.po
    ! frobaz/bravo.po
    ! frobaz/charlie.po
    ... (table with stats) ...
    Total untranslated messages tagged: 42

If the order were C{tag-untranslated,stats} in this case the effect on the
catalogs would be the same, but number of tagged messages would be the first
in output, followed by the table with statistics.

Frequently it is necessary to modify a message before doing a check on it,
such that an earlier sieve in the chain does the modification,
and a later sieve does the check.
If the modifications are performed only for the sake of the checks,
C{--no-sync} option can be used to prevent actually writing out
any modifications back to catalogs on disk.
This option is likewise useful for making "dry runs" when testing sieves.

C{posieve} takes a few options, which can be listed with the usual C{--help}
option. However, more interesting is that sieves themselves can be sent some
I{parameters}, using the C{-s} option, which takes as argument a
C{parameter:value} pair. As many of these as needed can be given.
For example, C{stats} sieve could be instructed to take into account only
messages with at most 5 words, like this::

    $ posieve stats -s maxwords:5 frobaz/

Sieve parameters can also be switches, when only the parameter name is given.
C{stats} can be instructed to show statistics in greater detail like this::

    $ posieve stats -s detail frobaz/

In case a sieve chain is specified, sieve parameters are routed to sieves as they
will accept them. If two sieves in the chain have a same-named parameters, when
given on the command line it will be sent to both.

Some sieves have the capability to prevent further sieving of a message in
a sieve chain. They may do this by default, or when requested by a parameter.
For example, L{C{find-messages}<sieve.find_messages>} sieve will by default
prevent further sieving of messages which do not match the condition;
statistics on all messages which have the number C{42} in original text
can be computed using::

    $ posieve find-messages,stats -smsgid:'\\b42\\b'

Pology also collects language-specific internal sieves. These are run by
prefixing sieve name with the language code and a colon. For example, there is
a sieve for the French language that replaces ordinary with non-breaking spaces
in some interpunction scenarios, the L{setUbsp<l10n.fr.sieve.setUbsp>},
which is invoked like this::

    $ posieve fr:setUbsp frobaz-fr/

In case the user has written a custom sieve, it can be run by simply stating
its path as sieve name. For C{posieve} to acknowledge it as external sieve,
the file name has to end in C{.py}. Custom sieves can be chained as any other. For example::

    $ posieve ../custom/my_count.py frobaz/
    $ posieve stats,../custom/my_count.py frobaz/

The list of all internal sieves is given within the L{sieve} module, as well
as instructions on how to write custom sieves. The list of internal language-specific sieves can be found within C{l10n.<lang>.sieve} module of
the languages that have them.

If an internal sieve contains underscores in its name, they can be replaced
with dashes in the C{posieve} command line. The dashes will be converted back
to underscores before trying to resolve the location of the internal sieve.

The following L{user configuration<misc.config>} fields are considered
(they may be overridden by command line options):
  - C{[posieve]/skip-on-error}: whether to skip current catalog on
        processing error and go to next, if possible (default C{yes})
  - C{[posieve]/msgfmt-check}: whether to check catalog file by C{msgfmt -c}
        before sieving (default C{no})
  - C{[posieve]/skip-obsolete}: whether to avoid sending obsolete messages
        to sieves (default C{no})

User configuration can also be used to issue sieve parameters.
For example, to issue parameters C{transl} (a switch) and C{accel} (valued)
for all sieves that accept them::

    [posieve]
    param-transl = yes
    param-accel = &

To issue parameters only for certain sieves, parameter name is followed
by C{/sieve1,sieve2,...}; to avoid issuing parameter for certain sieves,
a tilde is prepended to sieve list. For example::

    [posieve]
    param-transl/find-messages = yes   # only for find-messages
    param-accel/~stats = &             # not for stats

Same-named fields cannot be used in configuration to provide several values
(they override each other), so several same-named parameters are issued by
appending a dot and a unique string (within the sequence) to parameter name::

    [posieve]
    param-accel.0 = &
    param-accel.1 = _

If a sieve parameter is set to be issued from configuration,
option C{-S} followed by parameter name can be used to leave out
that parameter for one particular sieve run.
To see which parameters will be issued after both the command line and
the configuration have been considered, use C{--issued-params} option.

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

from pology import rootdir, version, _, n_, t_
from pology.file.catalog import Catalog
from pology.misc.colors import set_coloring_globals
import pology.misc.config as pology_config
from pology.misc.escape import escape_sh
from pology.misc.fsops import str_to_unicode
from pology.misc.fsops import collect_catalogs, collect_system
from pology.misc.fsops import build_path_selector, collect_paths_from_file
from pology.misc.fsops import collect_paths_cmdline
from pology.misc.msgreport import report_on_msg, warning_on_msg, error_on_msg
from pology.misc.report import error, warning, report, encwrite
from pology.misc.report import init_file_progress
from pology.misc.report import list_options
from pology.misc.report import format_item_list
from pology.misc.stdcmdopt import add_cmdopt_filesfrom, add_cmdopt_incexc
from pology.misc.stdcmdopt import add_cmdopt_colors
from pology.misc.subcmd import ParamParser
from pology.sieve import SieveMessageError, SieveCatalogError


def main ():

    locale.setlocale(locale.LC_ALL, "")

    # Get defaults for command line options from global config.
    cfgsec = pology_config.section("posieve")
    def_do_skip = cfgsec.boolean("skip-on-error", True)
    def_msgfmt_check = cfgsec.boolean("msgfmt-check", False)
    def_skip_obsolete = cfgsec.boolean("skip-obsolete", False)

    # Setup options and parse the command line.
    usage = _("@info command usage",
        "%(cmd)s [OPTIONS] SIEVE [POPATHS...]",
        cmd="%prog")
    desc = _("@info command description",
        "Apply sieves to PO paths, which may be either single PO files or "
        "directories to search recursively for PO files. "
        "Some of the sieves only examine PO files, while others "
        "modify them as well. "
        "The first non-option argument is the sieve name; "
        "a list of several comma-separated sieves can be given too.")
    ver = _("@info command version",
        u"%(cmd)s (Pology) %(version)s\n"
        u"Copyright © 2007, 2008, 2009, 2010 "
        u"Chusslove Illich (Часлав Илић) <%(email)s>",
        cmd="%prog", version=version(), email="caslav.ilic@gmx.net")

    opars = OptionParser(usage=usage, description=desc, version=ver)
    opars.add_option(
        "-a", "--announce-entry",
        action="store_true", dest="announce_entry", default=False,
        help=_("@info command line option description",
               "Announce that header or message just about to be sieved."))
    opars.add_option(
        "-b", "--skip-obsolete",
        action="store_true", dest="skip_obsolete", default=def_skip_obsolete,
        help=_("@info command line option description",
               "Do not sieve obsolete messages."))
    opars.add_option(
        "-c", "--msgfmt-check",
        action="store_true", dest="msgfmt_check", default=def_msgfmt_check,
        help=_("@info command line option description",
               "Check catalogs by %(cmd)s and skip those which do not pass.",
               cmd="msgfmt -c"))
    opars.add_option(
        "--force-sync",
        action="store_true", dest="force_sync", default=False,
        help=_("@info command line option description",
               "Force rewriting of all messages, whether modified or not."))
    opars.add_option(
        "-H", "--help-sieves",
        action="store_true", dest="help_sieves", default=False,
        help=_("@info command line option description",
               "Show help for applied sieves."))
    opars.add_option(
        "--issued-params",
        action="store_true", dest="issued_params", default=False,
        help=_("@info command line option description",
               "Show all issued sieve parameters "
               "(from command line and user configuration)."))
    opars.add_option(
        "-l", "--list-sieves",
        action="store_true", dest="list_sieves", default=False,
        help=_("@info command line option description",
               "List available internal sieves."))
    opars.add_option(
        "--list-options",
        action="store_true", dest="list_options", default=False,
        help=_("@info command line option description",
               "List the names of available options."))
    opars.add_option(
        "--list-sieve-names",
        action="store_true", dest="list_sieve_names", default=False,
        help=_("@info command line option description",
               "List the names of available internal sieves."))
    opars.add_option(
        "--list-sieve-params",
        action="store_true", dest="list_sieve_params", default=False,
        help=_("@info command line option description",
               "List the parameters known to issued sieves."))
    opars.add_option(
        "-m", "--output-modified",
        metavar=_("@info command line value placeholder", "FILE"),
        action="store", dest="output_modified", default=None,
        help=_("@info command line option description",
               "Output names of modified files into FILE."))
    opars.add_option(
        "--no-skip",
        action="store_false", dest="do_skip", default=def_do_skip,
        help=_("@info command line option description",
               "Do not try to skip catalogs which signal errors."))
    opars.add_option(
        "--no-sync",
        action="store_false", dest="do_sync", default=True,
        help=_("@info command line option description",
               "Do not write any modifications to catalogs."))
    opars.add_option(
        "-q", "--quiet",
        action="store_true", dest="quiet", default=False,
        help=_("@info command line option description",
               "Do not display any progress info "
               "(does not influence sieves themselves)."))
    opars.add_option(
        "-s",
        metavar=_("@info command line value placeholder", "NAME[:VALUE]"),
        action="append", dest="sieve_params", default=[],
        help=_("@info command line option description",
               "Pass a parameter to sieves."))
    opars.add_option(
        "-S",
        metavar=_("@info command line value placeholder", "NAME[:VALUE]"),
        action="append", dest="sieve_no_params", default=[],
        help=_("@info command line option description",
               "Remove a parameter to sieves "
               "(e.g. if it was issued through user configuration)."))
    opars.add_option(
        "-v", "--verbose",
        action="store_true", dest="verbose", default=False,
        help=_("@info command line option description",
               "Output more detailed progress information."))
    add_cmdopt_filesfrom(opars)
    add_cmdopt_incexc(opars)
    add_cmdopt_colors(opars)

    (op, free_args) = opars.parse_args(str_to_unicode(sys.argv[1:]))

    if op.list_options:
        report(list_options(opars))
        sys.exit(0)

    if len(free_args) < 1 and not (op.list_sieves or op.list_sieve_names):
        opars.error(_("@info", "No sieve to apply given."))

    op.raw_sieves = []
    op.raw_paths = []
    if len(free_args) >= 1:
        op.raw_sieves = free_args[0]
        op.raw_paths = free_args[1:]

    # Could use some speedup.
    try:
        import psyco
        psyco.full()
    except ImportError:
        pass

    set_coloring_globals(ctype=op.coloring_type, outdep=(not op.raw_colors))

    # Dummy-set all internal sieves as requested if sieve listing required.
    sieves_requested = []
    if op.list_sieves or op.list_sieve_names:
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

    # No need to load and setup sieves if only listing sieve names requested.
    if op.list_sieve_names:
        report("\n".join(sieves_requested))
        sys.exit(0)

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
            error(_("@info",
                    "Cannot load sieve '%(file)s'.",
                    file=sieve_path))
        # Load file into new module.
        sieve_mod_name = "sieve_" + str(len(sieve_modules))
        sieve_mod = imp.new_module(sieve_mod_name)
        exec sieve_file in sieve_mod.__dict__
        sieve_file.close()
        sys.modules[sieve_mod_name] = sieve_mod # to avoid garbage collection
        sieve_modules.append((sieve_name, sieve_mod))
        if not hasattr(sieve_mod, "Sieve"):
            error(_("@info",
                    "Module '%(file)s' does not define %(classname)s class.",
                    file=sieve_path, classname="Sieve"))

    # Setup sieves (description, known parameters...)
    pp = ParamParser()
    snames = []
    for name, mod in sieve_modules:
        try:
            scview = pp.add_subcmd(name)
        except Exception, e:
            error(unicode(e))
        if hasattr(mod, "setup_sieve"):
            mod.setup_sieve(scview)
        snames.append(name)

    # If info on sieves requested, report and exit.
    if op.list_sieves:
        report(_("@info", "Available internal sieves:"))
        report(pp.listcmd(snames))
        sys.exit(0)
    elif op.list_sieve_params:
        params = set()
        for scview in pp.cmdviews():
            params.update(scview.params(addcol=True))
        report("\n".join(sorted(params)))
        sys.exit(0)
    elif op.help_sieves:
        report(_("@info", "Help for sieves:"))
        report("")
        report(pp.help(snames))
        sys.exit(0)

    # Prepare sieve parameters for parsing.
    sieve_params = list(op.sieve_params)
    # - append paramaters according to configuration
    sieve_params.extend(read_config_params(pp.cmdviews(), sieve_params))
    # - remove paramaters according to command line
    if op.sieve_no_params:
        sieve_params_mod = []
        for parspec in sieve_params:
            if parspec.split(":", 1)[0] not in op.sieve_no_params:
                sieve_params_mod.append(parspec)
        sieve_params = sieve_params_mod

    # If assembly of issued parameters requested, report and exit.
    if op.issued_params:
        escparams = []
        for parspec in sieve_params:
            if ":" in parspec:
                param, value = parspec.split(":", 1)
                escparam = "%s:%s" % (param, escape_sh(value))
            else:
                escparam = parspec
            escparams.append(escparam)
        fmtparams = " ".join(["-s%s" % x for x in sorted(escparams)])
        if fmtparams:
            report(fmtparams)
        sys.exit(0)

    # Parse sieve parameters.
    try:
        sparams, nacc_params = pp.parse(sieve_params, snames)
    except Exception, e:
        error(unicode(e))
    if nacc_params:
        error(_("@info",
                "Parameters not accepted by any of issued subcommands: "
                "%(paramlist)s.",
                paramlist=format_item_list(nacc_params)))

    # ========================================
    # FIXME: Think of something less ugly.
    # Add as special parameter to each sieve:
    # - root paths from which the catalogs are collected
    # - whether destination independent coloring is in effect
    # - test function for catalog selection
    root_paths = []
    if op.raw_paths:
        root_paths.extend(op.raw_paths)
    if op.files_from:
        for ffpath in op.files_from:
            root_paths.extend(collect_paths_from_file(ffpath))
    if not op.raw_paths and not op.files_from:
        root_paths = ["."]
    is_cat_included = build_path_selector(incnames=op.include_names,
                                          incpaths=op.include_paths,
                                          excnames=op.exclude_names,
                                          excpaths=op.exclude_paths)
    for p in sparams.values():
        p.root_paths = root_paths
        p.raw_colors = op.raw_colors
        p.is_cat_included = is_cat_included
    # ========================================

    # Create sieves.
    sieves = []
    for name, mod in sieve_modules:
        try:
            sieves.append(mod.Sieve(sparams[name]))
        except Exception, e:
            error(unicode(e))

    # Get the message monitoring indicator from the sieves.
    # Monitor unless all sieves have requested otherwise.
    use_monitored = False
    for sieve in sieves:
        if getattr(sieve, "caller_monitored", True):
            use_monitored = True
            break
    if op.verbose and not use_monitored:
        report(_("@info:progress", "--> Not monitoring messages."))

    # Get the sync indicator from the sieves.
    # Sync unless all sieves have requested otherwise,
    # and unless syncing is disabled globally in command line.
    do_sync = False
    for sieve in sieves:
        if getattr(sieve, "caller_sync", True):
            do_sync = True
            break
    if not op.do_sync:
        do_sync = False
    if op.verbose and not do_sync:
        report(_("@info:progress", "--> Not syncing after sieving."))

    # Open in header-only mode if no sieve has message processor.
    # Categorize sieves by the presence of message/header processors.
    use_headonly = True
    header_sieves = []
    header_sieves_last = []
    message_sieves = []
    for sieve in sieves:
        if hasattr(sieve, "process"):
            use_headonly = False
            message_sieves.append(sieve)
        if hasattr(sieve, "process_header"):
            header_sieves.append(sieve)
        if hasattr(sieve, "process_header_last"):
            header_sieves_last.append(sieve)
    if op.verbose and use_headonly:
        report(_("@info:progress", "--> Opening catalogs in header-only mode."))

    # Collect catalog paths.
    fnames = collect_paths_cmdline(rawpaths=op.raw_paths,
                                   incnames=op.include_names,
                                   incpaths=op.include_paths,
                                   excnames=op.exclude_names,
                                   excpaths=op.exclude_paths,
                                   filesfrom=op.files_from,
                                   elsecwd=True,
                                   respathf=collect_catalogs,
                                   abort=True)

    if op.do_skip:
        errwarn = warning
        errwarn_on_msg = warning_on_msg
    else:
        errwarn = error
        errwarn_on_msg = error_on_msg

    # Prepare inline progress indicator.
    if not op.quiet:
        update_progress = init_file_progress(fnames,
            addfmt=t_("@info:progress", "Sieving: %(file)s"))

    # Sieve catalogs.
    modified_files = []
    for fname in fnames:
        if op.verbose:
            report(_("@info:progress", "Sieving %(file)s...", file=fname))
        elif not op.quiet:
            update_progress(fname)

        if op.msgfmt_check:
            # TODO: Make it more portable?
            d1, oerr, ret = collect_system("msgfmt -o/dev/null -c %s" % fname)
            if ret != 0:
                oerr = oerr.strip()
                errwarn(_("@info:progress",
                          "%(file)s: %(cmd)s check failed:\n"
                          "%(msg)s",
                          file=fname, cmd="msgfmt -c", msg=oerr))
                warning(_("@info:progress",
                          "Skipping catalog due to syntax check failure."))
                continue

        try:
            cat = Catalog(fname, monitored=use_monitored, headonly=use_headonly)
        except KeyboardInterrupt:
            sys.exit(130)
        except Exception, e:
            errwarn(_("@info:progress",
                      "%(file)s: Parsing failed: %(msg)s",
                      file=fname, msg=e))
            warning(_("@info:progress",
                      "Skipping catalog due to parsing failure."))
            continue

        skip = False
        # First run all header sieves.
        if header_sieves and op.announce_entry:
            report(_("@info:progress",
                     "Sieving header of %(file)s...", file=fname))
        for sieve in header_sieves:
            try:
                ret = sieve.process_header(cat.header, cat)
            except SieveCatalogError, e:
                errwarn(_("@info:progress",
                          "%(file)s:header: Sieving failed: %(msg)s",
                          file=fname, msg=e))
                skip = True
                break
            except Exception, e:
                error(_("@info:progress",
                        "%(file)s:header: Sieving failed: %(msg)s",
                        file=fname, msg=e))
            if ret not in (None, 0):
                break
        if skip:
            warning(_("@info:progress",
                      "Skipping catalog due to header sieving failure."))
            continue

        # Then run all message sieves on each message,
        # unless processing only the header.
        if not use_headonly:
            for msg in cat:
                if op.skip_obsolete and msg.obsolete:
                    continue

                if not op.quiet:
                    update_progress(fname)

                if op.announce_entry:
                    report(_("@info:progress",
                             "Sieving %(file)s:%(line)d(#%(entry)d)...",
                             file=fname, line=msg.refline, entry=msg.refentry))

                for sieve in message_sieves:
                    try:
                        ret = sieve.process(msg, cat)
                    except SieveMessageError, e:
                        errwarn_on_msg(_("@info:progress",
                                         "Sieving failed: %(msg)s", msg=e),
                                         msg, cat)
                        break
                    except SieveCatalogError, e:
                        errwarn_on_msg(_("@info:progress",
                                         "Sieving failed: %(msg)s", msg=e),
                                         msg, cat)
                        skip = True
                        break
                    except Exception, e:
                        errwarn_on_msg(_("@info:progress",
                                         "Sieving failed: %(msg)s", msg=e),
                                         msg, cat)
                    if ret not in (None, 0):
                        break
                if skip:
                    break
        if skip:
            warning(_("@info:progress",
                      "Skipping catalog due to message sieving failure."))
            continue

        # Finally run all header-last sieves.
        if header_sieves_last and op.announce_entry:
            report(_("@info:progress",
                     "Sieving header (after messages) in %(file)s...",
                     file=fname))
        for sieve in header_sieves_last:
            try:
                ret = sieve.process_header_last(cat.header, cat)
            except SieveCatalogError, e:
                errwarn(_("@info:progress",
                          "%(file)s:header: Sieving (after messages) "
                          "failed: %(msg)s",
                          file=fname, msg=e))
                skip = True
                break
            except Exception, e:
                error(_("@info:progress",
                        "%(file)s:header: Sieving (after messages) "
                        "failed: %(msg)s",
                        file=fname, msg=e))
            if ret not in (None, 0):
                break
        if skip:
            warning(_("@info:progress",
                      "Skipping catalog due to header sieving "
                      "(after messages) failure."))
            continue

        if do_sync and cat.sync(op.force_sync):
            if op.verbose:
                report(_("@info:progress leading ! is a shorthand "
                         "state indicator",
                         "! (MODIFIED) %(file)s",
                         file=fname))
            elif not op.quiet:
                report(_("@info:progress leading ! is a shorthand "
                         "state indicator",
                         "! %(file)s",
                         file=fname))
            modified_files.append(fname)

    if not op.quiet:
        update_progress() # clear last progress line, if any

    for sieve in sieves:
        if hasattr(sieve, "finalize"):
            try:
                sieve.finalize()
            except Exception, e:
                warning(_("@info:progress",
                          "Finalization failed: %(msg)s",
                          msg=e))

    if op.output_modified:
        ofh = open(op.output_modified, "w")
        ofh.write("\n".join(modified_files) + "\n")
        ofh.close


def read_config_params (scviews, cmdline_parspecs):

    # Collect parameters defined in the config.
    cfgsec = pology_config.section("posieve")
    pref = "param-"
    config_params = []
    for field in cfgsec.fields():
        if field.startswith(pref):
            parspec = field[len(pref):]
            only_sieves = None
            inverted = False
            if "/" in parspec:
                param, svspec = parspec.split("/", 1)
                if svspec.startswith("~"):
                    inverted = True
                    svspec = svspec[1:]
                only_sieves = set(svspec.split(","))
            else:
                param = parspec
            if "." in param:
                param, d1 = param.split(".", 1)
            config_params.append((field, param, only_sieves, inverted))

    if not config_params:
        return []

    # Collect parameters known to issued sieves and issued in command line.
    sieves = set([x.name() for x in scviews])
    acc_raw_params = set(sum([x.params(addcol=True) for x in scviews], []))
    acc_params = set([x.rstrip(":") for x in acc_raw_params])
    acc_flag_params = set([x for x in acc_raw_params if not x.endswith(":")])
    cmd_params = set([x.split(":", 1)[0] for x in cmdline_parspecs])

    # Select parameters based on issued sieves.
    sel_params = []
    for field, param, only_sieves, inverted in config_params:
        if param in acc_params and param not in cmd_params:
            if only_sieves is not None:
                overlap = bool(sieves.intersection(only_sieves))
                add_param = overlap if not inverted else not overlap
            else:
                add_param = True
            if add_param:
                if param in acc_flag_params:
                    if cfgsec.boolean(field):
                        sel_params.append(param)
                else:
                    sel_params.append("%s:%s" % (param, cfgsec.string(field)))

    return sel_params


if __name__ == '__main__':
    main()
