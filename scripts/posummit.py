#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import copy
from difflib import SequenceMatcher
import filecmp
import hashlib
import imp
import locale
import os
import re
import shutil
import sys
import time

try:
    import fallback_import_paths
except:
    pass

from pology import version, _, n_, t_, PologyError
from pology.ascript import collect_ascription_associations
from pology.ascript import collect_ascription_history
from pology.ascript import make_ascription_selector
from pology.catalog import Catalog
from pology.header import Header, format_datetime
from pology.message import Message, MessageUnsafe
from pology.colors import ColorOptionParser
from pology.fsops import str_to_unicode
from pology.fsops import mkdirpath, assert_system, collect_system
from pology.fsops import getucwd, join_ncwd
from pology.fsops import collect_paths_cmdline, build_path_selector
from pology.fsops import exit_on_exception
from pology.merge import merge_pofile
from pology.monitored import Monpair, Monlist
from pology.msgreport import report_on_msg
from pology.report import report, error, warning, format_item_list
from pology.report import init_file_progress
from pology.stdcmdopt import add_cmdopt_incexc, add_cmdopt_filesfrom
from pology.vcs import make_vcs
from pology.wrap import select_field_wrapping


SUMMIT_ID = "+" # must not start with word-character (\w)


def main ():

    locale.setlocale(locale.LC_ALL, "")

    # Setup options and parse the command line.
    usage = _("@info command usage",
        "\n"
        "  %(cmd)s [OPTIONS] CFGFILE LANG OPMODE [PARTIAL...]\n"
        "    (if there is no '%(cfgfile)s' file in a parent directory)\n"
        "  %(cmd)s [OPTIONS] OPMODE [PARTIAL...]\n"
        "    (if there is a '%(cfgfile)s' file in a parent directory)",
        cmd="%prog", cfgfile="summit-config")
    desc = _("@info command description",
        "Translate PO files spread across different branches "
        "in a unified fashion.")
    ver = _("@info command version",
        u"%(cmd)s (Pology) %(version)s\n"
        u"Copyright © 2007, 2008, 2009, 2010 "
        u"Chusslove Illich (Часлав Илић) &lt;%(email)s&gt;",
        cmd="%prog", version=version(), email="caslav.ilic@gmx.net")

    opars = ColorOptionParser(usage=usage, description=desc, version=ver)
    opars.add_option(
        "-a", "--asc-filter",
        action="store", dest="asc_filter", default=None,
        help=_("@info command line option description",
               "Apply a non-default ascription filter on scatter."))
    opars.add_option(
        "--create",
        action="store_true", dest="create", default=False,
        help=_("@info command line option description",
               "Allow creation of new summit catalogs."))
    opars.add_option(
        "--force",
        action="store_true", dest="force", default=False,
        help=_("@info command line option description",
               "Force some operations that are normally not advised."))
    opars.add_option(
        "-q", "--quiet",
        action="store_true", dest="quiet", default=False,
        help=_("@info command line option description",
               "Output less detailed progress info."))
    opars.add_option(
        "-v", "--verbose",
        action="store_true", dest="verbose", default=False,
        help=_("@info command line option description",
               "Output more detailed progress info"))
    add_cmdopt_filesfrom(opars)
    add_cmdopt_incexc(opars)

    options, free_args = opars.parse_args(str_to_unicode(sys.argv[1:]))

    # Look for the config file through parent directories.
    parent = getucwd()
    cfgpath = None
    while True:
        for cfgname in ("summit-config",):
            cfgpath1 = os.path.join(parent, cfgname)
            if os.path.isfile(cfgpath1):
                cfgpath = cfgpath1
                break
        if cfgpath:
            break
        pparent = parent
        parent = os.path.dirname(parent)
        if parent == pparent:
            break

    # If config file not found, expect it and language as arguments.
    if not cfgpath:
        if len(free_args) < 1:
            error(_("@info",
                    "Summit configuration file neither found "
                    "as '%(cfgfile)s' in parent directories, "
                    "nor given in command line.",
                    cfgfile="summit-config"))
        cfgpath = free_args.pop(0)
        if not os.path.isfile(cfgpath):
            error(_("@info",
                    "Summit configuration file '%(file)s' does not exist.",
                    file=cfgpath))

        if len(free_args) < 1:
            error(_("@info",
                    "Language code not given."))
        lang = free_args.pop(0)
    else:
        lang = None
        # ...will be read from config file.

    if len(free_args) < 1:
        error(_("@info", "Operation mode not given."))
    opmodes = free_args.pop(0).split(",")
    opmodes_uniq = []
    for opmode in opmodes:
        if opmode not in opmodes_uniq:
            if opmode not in ("gather", "scatter", "merge", "deps"):
                error(_("@info",
                        "Unknown operation mode '%(mode)s'.",
                        mode=opmode))
            opmodes_uniq.append(opmode)
    opmodes = opmodes_uniq

    # Could use some speedup.
    try:
        import psyco
        psyco.full()
    except ImportError:
        pass

    # Read project definition.
    project = Project(lang, opmodes, options)
    project.include(cfgpath)

    # In summit-over-templates mode, determine if templates are dynamic.
    project.templates_dynamic = (    project.over_templates
                                 and not project.summit.get("topdir_templates"))

    # If config file was found in parent directories,
    # it should have defined the language itself.
    # Otherwise, its language is set to language given in command line.
    if not lang:
        if not project.lang:
            error(_("@info",
                    "Language code not set in configuration file."))
        lang = project.lang
    else:
        project.lang = lang

    # In summit-over-templates mode, derive special project data
    # for implicitly gathering templates on merge.
    if project.templates_dynamic and "merge" in project.opmodes:
        project.toptions = copy.copy(options)
        project.toptions.quiet = True
        project.tproject = Project(project.templates_lang, ["gather"],
                                   project.toptions)
        project.tproject.include(cfgpath)
        project.tproject.templates_dynamic = False
        project.tproject.summit_version_control = "none"
        project.tproject.summit_wrap = False # performance
        project.tproject.summit_fine_wrap = False # performance
        tpd = project.tproject.summit.get("topdir_templates")
        if tpd is None:
            # FIXME: Portability.
            tpd = "/tmp/summit-templates-%d" % os.getpid()
        project.tproject.summit["topdir"] = tpd
        for tb in project.tproject.branches:
            tbpd = tb.get("topdir_templates")
            if tbpd is not None:
                tb["topdir"] = tbpd
        project.tproject.lang = project.templates_lang
        project.tproject = derive_project_data(project.tproject,
                                               project.toptions,
                                               project.summit["topdir"])
        project.summit["topdir_templates"] = tpd

    # Explicit gathering in summit-over-templates mode
    # may be useful to check if gathering works.
    # Make some adjustments for this to go smoothly.
    if (    project.templates_dynamic and "gather" in project.opmodes
        and project.lang == project.templates_lang
    ):
        options.create = True
        project.summit["topdir"] = project.summit["topdir_templates"]
        project.summit_version_control = "none"

    # Derive project data.
    project = derive_project_data(project, options)

    # Collect partial processing specs and inclusion-exclusion test.
    specargs, ffself = collect_paths_cmdline(rawpaths=free_args,
                                             filesfrom=options.files_from,
                                             getsel=True, abort=True)
    options.partspecs, options.partbids = collect_partspecs(project, specargs)
    cmdself = build_path_selector(incnames=options.include_names,
                                  incpaths=options.include_paths,
                                  excnames=options.exclude_names,
                                  excpaths=options.exclude_paths)
    options.selcatf = lambda x: cmdself(x) and ffself(x)

    # Invoke the appropriate operations on collected bundles.
    for opmode in opmodes:
        if options.verbose:
            report(_("@info:progress",
                     "-----> Processing mode: %(mode)s",
                     mode=opmode))
        if opmode == "gather":
            summit_gather(project, options)
        elif opmode == "scatter":
            summit_scatter(project, options)
        elif opmode == "merge":
            summit_merge(project, options)
        elif opmode == "deps":
            summit_deps(project, options)


class Project (object):

    def __init__ (self, lang, opmodes, options):

        self.__dict__.update({
            "lang" : lang,
            "opmodes" : opmodes,
            "options" : options,

            "summit" : "",
            "branches" : [],
            "mappings" : [],
            "subdir_mappings" : [],

            "over_templates" : False,
            "templates_lang" : "templates",

            "summit_wrap" : False,
            "summit_fine_wrap" : True,
            "summit_fuzzy_merging" : True,
            "branches_wrap" : True,
            "branches_fine_wrap" : True,
            "branches_fuzzy_merging" : True,

            "version_control" : "",
            "summit_version_control" : "",
            "branches_version_control" : "",

            "hook_on_scatter_msgstr" : [],
            "hook_on_scatter_msg" : [],
            "hook_on_scatter_cat" : [],
            "hook_on_scatter_file" : [],
            "hook_on_scatter_branch": [],
            "hook_on_gather_msg" : [],
            "hook_on_gather_msg_branch" : [],
            "hook_on_gather_cat" : [],
            "hook_on_gather_cat_branch" : [],
            "hook_on_gather_file" : [],
            "hook_on_gather_file_branch" : [],
            "hook_on_merge_msg" : [],
            "hook_on_merge_head" : [],
            "hook_on_merge_cat" : [],
            "hook_on_merge_file" : [],

            "header_propagate_fields" : [],
            "header_skip_fields_on_scatter" : [],

            "vivify_on_merge" : False,
            "vivify_w_translator" : "Simulacrum",
            "vivify_w_langteam" : "Nevernessian",
            "vivify_w_language" : "",
            "vivify_w_charset" : "UTF-8",
            "vivify_w_plurals" : "",

            "compendium_on_merge" : "",
            "compendium_fuzzy_exact" : False,
            "compendium_min_words_exact" : 0,

            "merge_min_adjsim_fuzzy" : 0.0,
            "merge_rebase_fuzzy" : False,

            "scatter_min_completeness" : 0.0,
            "scatter_acc_completeness" : 0.0,

            "ascription_filters" : [],
            "ascription_history_filter" : None,
        })
        self.__dict__["locked"] = False

        self.inclusion_trail = []


    def __setattr__ (self, att, val):

        # TODO: Do extensive checks.
        if self.locked and att not in self.__dict__:
            error(_("@info",
                    "Unknown summit configuration field '%(field)s'.",
                    field=att))
        self.__dict__[att] = val


    def relpath (self, path):

        rootdir = os.path.dirname(self.inclusion_trail[-1])
        if not os.path.isabs(path):
            path = join_ncwd(rootdir, path)

        return path


    # FIXME: Temporary for backward compatibility, remove at some point.
    def resolve_path_rooted (self, path):

        return self.relpath(path)


    def include (self, path):

        path = os.path.abspath(path)
        if path in self.inclusion_trail:
            error(_("@info",
                    "Circular inclusion of '%(file)s' attempted "
                    "in summit configuration.",
                    file=path))
        self.inclusion_trail.append(path)
        self.locked = True
        exec open(path) in {"S" : self}
        self.locked = False
        self.inclusion_trail.pop()


def derive_project_data (project, options, nwgrefpath=None):

    p = project # shortcut

    # Create summit object from summit dictionary.
    class Summit: pass
    s = Summit()
    sd = p.summit
    s.id = SUMMIT_ID
    s.by_lang = False
    s.topdir = sd.pop("topdir", None)
    s.topdir_templates = sd.pop("topdir_templates", None)
    # Assert that there are no misnamed keys in the dictionary.
    if sd:
        error(_("@info",
                "Unknown keys in summit configuration: %(keylist)s.",
                keylist=format_item_list(sd.keys())))
    # Assert that all necessary fields in summit specification exist.
    if s.topdir is None:
        error(_("@info",
                "Top directory not set in summit configuration."))
    s.split_path = None # needed only on some checks later
    p.summit = s

    # Create branch objects from branch dictionaries.
    class Branch: pass
    branches = []
    for bd in p.branches:
        b = Branch()
        branches.append(b)

        b.id = bd.pop("id", None)
        b.topdir = bd.pop("topdir", None)
        b.topdir_templates = bd.pop("topdir_templates", None)
        b.by_lang = bd.pop("by_lang", False)
        if b.by_lang and isinstance(b.by_lang, bool):
            b.by_lang = project.lang
        b.scatter_create_filter = bd.pop("scatter_create_filter", None)
        b.skip_version_control = bd.pop("skip_version_control", False)
        # FIXME: merge_locally retained for backward compatibility,
        # replace at some point with b.merge = bd.pop("merge", False).
        b.merge = bd.pop("merge", None)
        if b.merge is None:
            b.merge = bd.pop("merge_locally", False)
        b.split_path, b.join_path = bd.pop("transform_path", (None, None))

        # Assemble include-exclude functions.
        includes = bd.pop("includes", [])
        excludes = bd.pop("excludes", [])

        def regex_to_func (rxstr):
            try:
                rx = re.compile(rxstr, re.U)
            except:
                error(_("@info",
                        "Invalid regular expression '%(regex)s' "
                        "in include-exclude specification "
                        "of branch '%(branch)s'.",
                        branch=b.id, regex=rxstr))
            return lambda x: bool(rx.search(x))

        def chain_tests (tests):
            testfs = []
            for test in tests:
                if isinstance(test, basestring):
                    testfs.append(regex_to_func(test))
                elif callable(test):
                    testfs.append(test)
                else:
                    error(_("@info",
                            "Invalid test type '%(type)s' "
                            "in include-exclude specification "
                            "of branch '%(branch)s'.",
                            branch=b.id, type=type(test)))
            return lambda x: reduce(lambda s, y: s or y(x), testfs, False)

        if includes:
            includef = chain_tests(includes)
        if excludes:
            excludef = chain_tests(excludes)
        if includes and excludes:
            b.ignored = lambda x: not includef(x) or excludef(x)
        elif includes:
            b.ignored = lambda x: not includef(x)
        elif excludes:
            b.ignored = lambda x: excludef(x)
        else:
            b.ignored = lambda x: False

        # Assert that there are no misnamed keys in the dictionary.
        if bd:
            error(_("@info",
                    "Unknown keys in specification of branch '%(branch)s': "
                    "%(keylist)s.",
                    branch=b.id, keylist=format_item_list(bd.keys())))
    p.branches = branches

    # Assert that all necessary fields in branch specifications exist.
    p.branch_ids = []
    for branch in p.branches:
        if branch.id is None:
            error(_("@info",
                    "Branch with undefined ID."))
        if branch.id in p.branch_ids:
            error(_("@info",
                    "Non-unique branch ID '%(branch)s'.",
                    branch=branch.id))
        p.branch_ids.append(branch.id)
        if branch.topdir is None:
            error(_("@info",
                    "Top directory not set for branch '%(branch)s'.",
                    branch=branch.id))

    # Dictionary of branches by branch id.
    p.bdict = dict([(x.id, x) for x in p.branches])

    # Create version control operators if given.
    p.summit_vcs = None
    p.branches_vcs = None
    if p.summit_version_control:
        p.summit_vcs = make_vcs(p.summit_version_control.lower())
    if p.branches_version_control:
        p.branches_vcs = make_vcs(p.branches_version_control.lower())
    if p.version_control:
        if p.summit_vcs is None:
            p.summit_vcs = make_vcs(p.version_control.lower())
        if p.branches_vcs is None:
            p.branches_vcs = make_vcs(p.version_control.lower())

    # Decide wrapping policies.
    class D: pass
    dummyopt = D()
    dummyopt.do_wrap = p.summit_wrap
    dummyopt.do_fine_wrap = p.summit_fine_wrap
    p.summit_wrapping = select_field_wrapping(cmlopt=dummyopt)
    dummyopt.do_wrap = p.branches_wrap
    dummyopt.do_fine_wrap = p.branches_fine_wrap
    p.branches_wrapping = select_field_wrapping(cmlopt=dummyopt)

    # Decide the extension of catalogs.
    if p.over_templates and p.lang == p.templates_lang:
        catext = ".pot"
    else:
        catext = ".po"

    # Collect catalogs from branches.
    p.catalogs = {}
    for b in p.branches:
        p.catalogs[b.id] = collect_catalogs(b.topdir, catext,
                                            b.by_lang, b.ignored, b.split_path,
                                            project, options)
    # ...and from the summit.
    p.catalogs[SUMMIT_ID] = collect_catalogs(p.summit.topdir, catext,
                                             None, None, None,
                                             project, options)
    if (    p.lang == p.templates_lang and "gather" in p.opmodes
        and nwgrefpath is not None
    ):
        # Also add summit templates which do not actually exist,
        # but are going to be created on gather without warnings,
        # by reflecting the catalogs found in the given path.
        refcats = collect_catalogs(nwgrefpath, ".po",
                                   None, None, None, project, options)
        for name, spec in refcats.iteritems():
            if name not in p.catalogs[SUMMIT_ID]:
                path, subdir = spec[0] # all summit catalogs unique
                tpath = join_ncwd(p.summit.topdir, subdir, name + ".pot")
                p.catalogs[SUMMIT_ID][name] = [(tpath, subdir)]

    # Resolve ascription filter.
    project.ascription_filter = None
    for afname, afspec in project.ascription_filters:
        if options.asc_filter is None or afname == options.asc_filter:
            if isinstance(afspec, basestring):
                afcall = make_ascription_selector([afspec])
            elif isinstance(afspec, (tuple, list)):
                afcall = make_ascription_selector(afspec)
            elif callable(afspec):
                afcall = afspec
            else:
                error(_("@info",
                        "Unknown type of definition for "
                        "ascription filter '%(filt)s'.",
                        filt=afname))
            project.ascription_filter = afcall
            break
    if options.asc_filter is not None and project.ascription_filter is None:
        error(_("@info",
                "Summit configuration does not define "
                "ascription filter '%(filt)s'.",
                filt=options.asc_filter))

    # Link summit and ascription catalogs.
    if project.ascription_filter:
        tmp0 = [(x, y[0][0]) for x, y in p.catalogs[SUMMIT_ID].items()]
        tmp1 = [x[0] for x in tmp0]
        tmp2 = collect_ascription_associations([x[1] for x in tmp0])
        tmp3 = zip([tmp2[0][0]] * len(tmp1), [x[1] for x in tmp2[0][1]])
        p.aconfs_acatpaths = dict(zip(tmp1, tmp3))

    # Assure that summit catalogs are unique.
    for name, spec in p.catalogs[SUMMIT_ID].items():
        if len(spec) > 1:
            fstr = "\n".join([x[0] for x in spec])
            error(_("@info",
                    "Non-unique summit catalog '%(name)s', found as:\n"
                    "%(filelist)s",
                    name=name, filelist=fstr))

    # At scatter in summit-over-static-templates mode, add to the collection
    # of branch catalogs any that should be newly created.
    p.add_on_scatter = {}
    if (    p.over_templates and p.lang != p.templates_lang
        and "scatter" in p.opmodes):

        # Go through all mappings and collect branch names mapped to
        # summit catalogs per branch id and summit name, and vice versa.
        mapped_summit_names = {}
        mapped_branch_names = {}
        for mapping in p.mappings:
            branch_id = mapping[0]
            branch_name = mapping[1]
            summit_names = mapping[2:]
            if not branch_id in mapped_summit_names:
                mapped_summit_names[branch_id] = {}
            if not branch_id in mapped_branch_names:
                mapped_branch_names[branch_id] = {}
            for summit_name in summit_names:
                if not summit_name in mapped_summit_names[branch_id]:
                    mapped_summit_names[branch_id][summit_name] = []
                mapped_summit_names[branch_id][summit_name].append(branch_name)
                if not branch_name in mapped_branch_names[branch_id]:
                    mapped_branch_names[branch_id][branch_name] = []
                mapped_branch_names[branch_id][branch_name].append(summit_name)

        # Go through all branches.
        bt_cache = {}
        for branch in p.branches:
            # Skip this branch if no templates.
            if not branch.topdir_templates:
                continue

            # Collect all templates for this branch.
            branch_templates = bt_cache.get(branch.topdir_templates)
            if branch_templates is None:
                branch_templates = collect_catalogs(branch.topdir_templates,
                                                    ".pot", branch.by_lang,
                                                    branch.ignored,
                                                    branch.split_path,
                                                    project, options)
                bt_cache[branch.topdir_templates] = branch_templates

            # Go through all summit catalogs.
            for summit_name in p.catalogs[SUMMIT_ID]:

                # Collect names of any catalogs in this branch mapped to
                # the current summit catalog.
                branch_names = []
                if (    branch.id in mapped_summit_names
                    and summit_name in mapped_summit_names[branch.id]):
                    branch_names = mapped_summit_names[branch.id][summit_name]
                # Unconditionally add summit name as one possible branch name,
                # since otherwise a mapped branch catalog could shadow
                # a direct branch catalog.
                branch_names.append(summit_name)

                # For each collected branch name, check if there are some
                # branch templates for which the corresponding branch path
                # does not exit and (in case of explicit mapping) whether
                # all summit catalogs needed for scattering are available.
                # If this is the case, set missing paths for scattering.
                for branch_name in branch_names:

                    if (    branch_name in branch_templates
                        and all(map(lambda x: x in p.catalogs[SUMMIT_ID],
                                    mapped_branch_names.get(branch.id, {})
                                                       .get(branch_name, [])))
                    ):
                        # Assemble all branch catalog entries.
                        for template in branch_templates[branch_name]:
                            # Compose the branch catalog subdir and path.
                            subdir = template[1]
                            if branch.join_path:
                                subpath = branch.join_path(branch_name, subdir,
                                                           branch.by_lang)
                            elif branch.by_lang:
                                subpath = os.path.join(subdir, branch_name,
                                                       branch.by_lang + ".po")
                            else:
                                subpath = os.path.join(subdir,
                                                       branch_name + ".po")
                            path = join_ncwd(branch.topdir, subpath)

                            # Skip this catalog if excluded from creation on
                            # scatter, by filter on catalog name and subdir
                            # (False -> excluded).
                            scf = branch.scatter_create_filter
                            if scf and not scf(branch_name, subdir):
                                continue

                            # If not there already, add this path
                            # to branch catalog entry,
                            # and record later initialization from template.
                            brcats = p.catalogs[branch.id].get(branch_name)
                            if brcats is None:
                                brcats = []
                                p.catalogs[branch.id][branch_name] = brcats
                            if (path, subdir) not in brcats:
                                brcats.append((path, subdir))
                                p.add_on_scatter[path] = template[0]

    # In summit-over-dynamic-templates mode,
    # automatic vivification of summit catalogs must be active.
    if p.templates_dynamic:
        p.vivify_on_merge = True

    # At merge in summit-over-templates mode,
    # if automatic vivification of summit catalogs requested,
    # add to the collection of summit catalogs any that should be created.
    p.add_on_merge = {}
    if (    p.over_templates and p.lang != p.templates_lang
        and "merge" in p.opmodes and (p.vivify_on_merge or options.create)
    ):
        # Collect all summit templates.
        if not p.templates_dynamic:
            summit_templates = collect_catalogs(p.summit.topdir_templates,
                                                ".pot", None, None, None,
                                                project, options)
        else:
            summit_templates = p.tproject.catalogs[SUMMIT_ID]

        # Go through all summit templates, recording missing summit catalogs.
        for name, spec in summit_templates.iteritems():
            tpath, tsubdir = spec[0] # all summit catalogs unique
            if name not in p.catalogs[SUMMIT_ID]:
                # Compose the summit catalog path.
                spath = join_ncwd(p.summit.topdir, tsubdir, name + ".po")
                # Add this file to summit catalog entries.
                p.catalogs[SUMMIT_ID][name] = [(spath, tsubdir)]
                # Record later initialization from template.
                p.add_on_merge[spath] = tpath

    # Convenient dictionary views of mappings.
    # - direct: branch_id->branch_name->summit_name
    # - part inverse: branch_id->summit_name->branch_name
    # - full inverse: summit_name->branch_id->branch_name
    p.direct_map = {}
    p.part_inverse_map = {}
    p.full_inverse_map = {}

    # Initialize mappings by branch before the main loop for direct mappings,
    # because an explicit mapping may name a branch before it was processed
    # in the main loop.
    for branch_id in p.branch_ids:
        p.direct_map[branch_id] = {}
        for branch_name in p.catalogs[branch_id]:
            p.direct_map[branch_id][branch_name] = []

    # Add direct mappings.
    # - explicit
    for mapping in p.mappings:
        branch_id, branch_name = mapping[:2]
        if (    "gather" in p.opmodes
            and (   branch_id not in p.catalogs
                 or branch_name not in p.catalogs[branch_id])
        ):
            warning(_("@info",
                      "No branch catalog corresponding to mapping %(mapping)s "
                      "set by the summit configuration.",
                      mapping=("('%s', '%s', ...)" % (branch_id, branch_name))))
            continue
        summit_names = mapping[2:]
        p.direct_map[branch_id][branch_name] = summit_names
    # - implicit
    for branch_id in p.branch_ids:
        for branch_name in p.catalogs[branch_id]:
            if p.direct_map[branch_id][branch_name] == []:
                p.direct_map[branch_id][branch_name].append(branch_name)

    # Convert subdir mappings into dictionary by branch ID and subdir.
    p.subdir_map = {}
    for bid, bsubdir, ssubdir in p.subdir_mappings:
        p.subdir_map[(bid, bsubdir)] = ssubdir

    # Collect missing summit catalogs.
    needed_additions = []
    for branch_id in p.branch_ids:
        for branch_name in p.catalogs[branch_id]:
            summit_names = p.direct_map[branch_id][branch_name]
            for summit_name in summit_names:
                if summit_name not in p.catalogs[SUMMIT_ID]:
                    # Compose the path for the missing summit catalog.
                    # Default the subdir to that of the current branch,
                    # as it is the primary branch for this catalog.
                    # Or use explicit subdir mapping if given.
                    branch_path, branch_subdir = \
                        p.catalogs[branch_id][branch_name][0]
                    dmkey = (branch_id, branch_subdir)
                    summit_subdir = p.subdir_map.get(dmkey) or branch_subdir
                    summit_path = join_ncwd(p.summit.topdir, summit_subdir,
                                            summit_name + catext)
                    if "gather" == p.opmodes[0] and options.create:
                        # Add summit catalog into list of existing catalogs;
                        # it will be created for real on gather.
                        p.catalogs[SUMMIT_ID][summit_name] = [(summit_path,
                                                               summit_subdir)]
                    elif ["merge"] != p.opmodes:
                        needed_additions.append((branch_path, summit_path))

    # Initialize inverse mappings.
    # - part inverse:
    for branch_id in p.branch_ids:
        p.part_inverse_map[branch_id] = {}
        for summit_name in p.catalogs[SUMMIT_ID]:
            p.part_inverse_map[branch_id][summit_name] = []
    # - full inverse:
    for summit_name in p.catalogs[SUMMIT_ID]:
        p.full_inverse_map[summit_name] = {}
        for branch_id in p.branch_ids:
            p.full_inverse_map[summit_name][branch_id] = []

    # Add existing inverse mappings.
    for branch_id in p.branch_ids:
        for branch_name in p.catalogs[branch_id]:
            for summit_name in p.direct_map[branch_id][branch_name]:
                if summit_name in p.full_inverse_map:
                    # - part inverse:
                    pinv = p.part_inverse_map[branch_id][summit_name]
                    if branch_name not in pinv:
                        pinv.append(branch_name)
                    # - full inverse:
                    finv = p.full_inverse_map[summit_name][branch_id]
                    if branch_name not in finv:
                        finv.append(branch_name)

    # Collect superfluous summit catalogs.
    needed_removals = []
    for summit_name in p.catalogs[SUMMIT_ID]:
        src_branch_ids = []
        for branch_id in project.branch_ids:
            if project.full_inverse_map[summit_name][branch_id]:
                src_branch_ids.append(branch_id)
        if not src_branch_ids:
            if (    not ("gather" == p.opmodes[0] and options.create)
                and ["merge"] != p.opmodes and ["deps"] != p.opmodes
            ):
                summit_path = p.catalogs[SUMMIT_ID][summit_name][0][0]
                needed_removals.append(summit_path)

    # Collect summit catalogs that should be moved.
    needed_moves = []
    for summit_name in p.catalogs[SUMMIT_ID]:
        branch_subdirs = []
        for branch_id in p.full_inverse_map[summit_name]:
            for branch_name in p.full_inverse_map[summit_name][branch_id]:
                branch_subdirs_1 = []
                for bpath, bsubdir in p.catalogs[branch_id][branch_name]:
                    dmkey = (branch_id, bsubdir)
                    branch_subdirs_1.append(p.subdir_map.get(dmkey) or bsubdir)
                branch_subdirs_1.sort()
                branch_subdirs.extend(branch_subdirs_1)
        if branch_subdirs:
            summit_subdir = p.catalogs[SUMMIT_ID][summit_name][0][1]
            if summit_subdir not in branch_subdirs:
                summit_path = p.catalogs[SUMMIT_ID][summit_name][0][0]
                dpaths = []
                for bsubdir in branch_subdirs:
                    dpath = join_ncwd(p.summit.topdir, bsubdir,
                                      summit_name + catext)
                    dpaths.append(dpath)
                if (    not ("gather" == p.opmodes[0] and options.create)
                    and ["merge"] != p.opmodes
                ):
                    needed_moves.append((summit_path, dpaths))

    # If catalog creation is not allowed,
    # complain about needed additions, removals, and moves.
    if needed_additions or needed_removals or needed_moves:
        if needed_additions:
            fmtlist = "\n".join("%s --> %s" % x
                                for x in sorted(needed_additions))
            warning(_("@info",
                      "Some branch catalogs have no "
                      "associated summit catalog "
                      "(expected summit path given):\n"
                      "%(filelist)s",
                      filelist=fmtlist))
        if needed_removals:
            fmtlist = "\n".join(sorted(needed_removals))
            warning(_("@info",
                      "Some summit catalogs have no "
                      "associated branch catalogs:\n"
                      "%(filelist)s",
                      filelist=fmtlist))
        if needed_moves:
            fmtlist = "\n".join("%s --| %s" % (x, " | ".join(y))
                                for x, y in sorted(needed_moves))
            warning(_("@info",
                      "Some summit catalogs should be "
                      "moved to another subdirectory:\n"
                      "%(filelist)s",
                      filelist=fmtlist))
        if "gather" in p.opmodes:
            error(_("@info",
                    "Halting because catalog creation is not allowed "
                    "(consider issuing %(opt)s option).", opt="--create"))

    # Fill in defaults for missing fields in hook specs.
    for attr in p.__dict__:
        if attr.startswith("hook_"):
            p.__dict__[attr] = hook_fill_defaults(p.__dict__[attr])

    return p


def split_path_in_project (project, path):

    if os.path.isfile(path):
        if not path.endswith((".po", ".pot")):
            error(_("@info",
                    "Non-PO file '%(file)s' given as catalog.",
                    file=path))

    splits = []
    for b in [project.summit] + project.branches:
        broot = os.path.abspath(b.topdir)
        apath = os.path.abspath(path)
        if apath.startswith(broot + os.path.sep) or apath == broot:
            subpath = apath[len(broot + os.path.sep):]
            # Split the path into catalog name and subdirectory.
            if os.path.isfile(apath):
                if b.split_path:
                    catname, subdir = b.split_path(subpath)
                else:
                    subdir = os.path.dirname(subpath)
                    basename = os.path.basename(subpath)
                    catname = basename[:basename.rfind(".")]
                    if b.by_lang:
                        # If this is by-language mode,
                        # catalog path can be split only if of proper language,
                        # and subdirectory and catalog name should backtrack.
                        if catname != b.by_lang:
                            continue
                        catname = os.path.basename(subdir)
                        subdir = os.path.dirname(subdir)
            elif os.path.isdir(apath):
                if b.split_path:
                    catname = None
                    dummy_subpath = os.path.join(subpath, "__dummy__.po")
                    subdir = b.split_path(dummy_subpath)[1]
                else:
                    subdir = subpath
                    catname = None
                    if b.by_lang:
                        # If this is a leaf directory in by-language mode,
                        # then actually a catalog has been selected,
                        # and subdirectory and catalog name should backtrack.
                        apath2 = os.path.join(subdir, b.by_lang + ".po")
                        if os.path.isfile(apath2):
                            catname = os.path.basename(subdir)
                            subdir = os.path.dirname(subdir)
            # Collect the splitting.
            # Catalog name being None means that a subdirectory is selected,
            # and if subdirectory too is None, the whole branch is selected.
            if not catname and not subdir:
                subdir = None
            splits.append((b.id, subdir, catname))
    if not splits:
        error(_("@info",
                "Path '%(path)s' is not covered by the summit configuration.",
                path=path))

    return splits


def collect_partspecs (project, specargs):

    partbids = []
    partspecs = {}
    for specarg in specargs:
        # If the partial specification is a valid path,
        # convert it to operation target.
        optargets = []
        if os.path.exists(specarg):
            splits = split_path_in_project(project, specarg)
            for bid, breldir, catname in splits:
                if catname:
                    optarget = bid + ":" + catname
                elif breldir:
                    optarget = bid + ":" + breldir + os.path.sep
                else:
                    optarget = bid + ":"
                optargets.append(optarget)
        else:
            optargets = [specarg]

        for optarget in optargets:
            lst = optarget.split(":", 1)
            if len(lst) < 2:
                fdname, = lst
                bid = None
            else:
                bid, fdname = lst
                if bid not in project.branch_ids and bid != SUMMIT_ID:
                    error(_("@info",
                            "Branch '%(branch)s' is not defined "
                            "in the summit configuration.",
                            branch=bid))
            if bid and bid not in partbids:
                partbids.append(bid)
            if fdname:
                bsid = bid or SUMMIT_ID
                if bsid not in partspecs:
                    partspecs[bsid] = []
                partspecs[bsid].append(fdname)

    return partspecs, partbids


# Fill in defaults for missing fields in hook specs.
def hook_fill_defaults (specs):

    new_specs = []
    for spec in specs:
        call = spec[0]
        branch_rx = r""
        if len(spec) > 1: branch_rx = spec[1]
        name_rx = r""
        if len(spec) > 2: name_rx = spec[2]
        new_specs.append((call, branch_rx, name_rx))

    return new_specs


# Each catalog is represented by a dictionary entry: the key is the catalog
# name, the value is the list of tuples of file path and subdirectory
# relative to top (list in case there are several same-named catalogs in
# different subdirectories).
def collect_catalogs (topdir, catext, by_lang, ignored, split_path,
                      project, options):

    catalogs = {}
    topdir = os.path.normpath(topdir)
    for root, dirs, files in os.walk(topdir):
        for file in files:
            catn = ""
            if file.endswith(catext):
                if not by_lang:
                    fpath = os.path.abspath(os.path.join(root, file))
                    if split_path:
                        catn, spath = split_path(fpath[len(topdir) + 1:])
                    else:
                        catn = file[0:file.rfind(".")]
                        spath = root[len(topdir) + 1:]
                elif file == by_lang + ".po" or catext == ".pot":
                    fpath = os.path.abspath(os.path.join(root, file))
                    if split_path:
                        catn, spath = split_path(fpath[len(topdir) + 1:])
                    else:
                        catn = os.path.basename(root)
                        spath = os.path.dirname(root)[len(topdir) + 1:]

            if catn:
                if not ignored or not ignored(fpath):
                    if catn not in catalogs:
                        catalogs[catn] = []
                    fpath = join_ncwd(fpath)
                    spath = os.path.normpath(spath)
                    catalogs[catn].append((fpath, spath))

    for catpaths in catalogs.values():
        catpaths.sort(key=lambda x: x[0])

    return catalogs


def summit_gather (project, options):

    if (    project.over_templates and project.lang != project.templates_lang
        and not options.force):
        error(_("@info",
                "Gathering catalogs is normally not allowed "
                "in summit-over-static-templates mode. "
                "If this is the initial creation of summit catalogs, "
                "or externally injected branch catalogs need to be gathered, "
                "run with options %(opts)s.",
                opts="--create --force"))
    elif (    project.templates_dynamic
          and project.lang == project.templates_lang and not options.force):
        warning(_("@info",
                  "Gathering templates is superfluous in "
                  "summit-over-templates mode. "
                  "If this is done to check whether gathering works, "
                  "to supress this message run with option %(opt)s.",
                  opt="--force"))

    # Collect names of summit catalogs to gather.
    summit_names = select_summit_names(project, options)

    # Setup progress indicator.
    upprog = lambda x: x
    if not options.verbose:
        catpaths = [project.catalogs[SUMMIT_ID][x][0][0] for x in summit_names]
        upprog = init_file_progress(catpaths,
                                    addfmt=t_("@info:progress",
                                              "Gathering: %(file)s"))

    # Gather all selected catalogs.
    for name in summit_names:
        catpath = project.catalogs[SUMMIT_ID][name][0][0]
        if options.verbose:
            report(_("@info:progress",
                     "Gathering %(file)s...",
                     file=catpath))
        upprogc = lambda: upprog(catpath)
        summit_gather_single(name, project, options, update_progress=upprogc)
    upprog()


def summit_scatter (project, options):

    if project.over_templates and project.lang == project.templates_lang:
        error(_("@info",
                "Scattering not possible on '%(lang)s' "
                "in summit-over-templates mode.",
                lang=project.templates_lang))

    scatter_specs = []

    # Select branches to scatter to.
    if not options.partbids or SUMMIT_ID in options.partbids:
        branch_ids = project.branch_ids
    else:
        branch_ids = options.partbids

    # Collect catalogs to scatter through all selected branches.
    missing_in_summit = []
    for branch_id in branch_ids:

        branch_catalogs = select_branch_catalogs(branch_id, project, options)

        for branch_name, branch_path, branch_subdir in branch_catalogs:

            # Collect names of all the summit catalogs which this branch
            # catalog supplies messages to.
            summit_names = project.direct_map[branch_id][branch_name]

            # Collect paths of selected summit catalogs.
            summit_paths = []
            for summit_name in summit_names:
                if not summit_name in project.catalogs[SUMMIT_ID]:
                    missing_in_summit.append(summit_name)
                    continue
                summit_paths.append(
                    project.catalogs[SUMMIT_ID][summit_name][0][0])

            scatter_specs.append((branch_id, branch_name, branch_subdir,
                                  branch_path, summit_paths))

        # Dummy entry to indicate branch switch.
        scatter_specs.append((branch_id, None, None, None, None))

    # Assure all catalogs to scatter have summit counterparts.
    if missing_in_summit:
        error(_("@info",
                "Missing necessary summit catalogs: %(namelist)s.",
                namelist=format_item_list(missing_in_summit)))

    # Setup progress indicator.
    upprog = lambda x: x
    if not options.verbose:
        catpaths = [x[3] for x in scatter_specs if x[1]]
        upprog = init_file_progress(catpaths,
                                    addfmt=t_("@info:progress",
                                              "Scattering: %(file)s"))

    # Scatter to branch catalogs.
    for scatter_spec in scatter_specs:
        branch_id, catpath = scatter_spec[0], scatter_spec[3]
        if catpath is not None:
            if options.verbose:
                report(_("@info:progress",
                         "Scattering %(file)s...",
                         file=catpath))
            upprogc = lambda: upprog(catpath)
            summit_scatter_single(*(scatter_spec + (project, options, upprogc)))
        else:
            # Apply post-scatter hooks.
            if options.verbose:
                report(_("@info:progress",
                         "Applying post-hook to branch %(branch)s...",
                         branch=branch_id))
            exec_hook_branch(branch_id, project.hook_on_scatter_branch)
    upprog()


def summit_merge (project, options):

    if project.over_templates and project.lang == project.templates_lang:
        error(_("@info",
                "Merging not possible on '%(lang)s' in "
                "summit-over-templates mode.",
                lang=project.templates_lang))

    merge_specs = []

    # Select branches to merge.
    if not options.partbids:
        branch_ids = project.branch_ids + [SUMMIT_ID]
    else:
        branch_ids = options.partbids

    # Setup merging in summit.
    if SUMMIT_ID in branch_ids and project.summit.topdir_templates:
        branch_ids.remove(SUMMIT_ID)

        # Collect names of summit catalogs to merge.
        summit_names = select_summit_names(project, options)

        # Collect template catalogs to use.
        if not project.templates_dynamic:
            template_catalogs = collect_catalogs(project.summit.topdir_templates,
                                                 ".pot", None, None, None,
                                                 project, options)
        else:
            template_catalogs = project.tproject.catalogs[SUMMIT_ID]

        # Collect data for summit catalogs to merge.
        for name in summit_names:
            summit_path, summit_subdir = project.catalogs[SUMMIT_ID][name][0]
            if name not in template_catalogs:
                warning(_("@info",
                          "No template for summit catalog '%(file)s'.",
                          file=summit_path))
                continue
            template_path = template_catalogs[name][0][0]
            merge_specs.append((SUMMIT_ID, name, summit_subdir,
                                summit_path, template_path,
                                project.summit_wrapping,
                                project.summit_fuzzy_merging))

    # Setup merging in branches.
    for branch_id in branch_ids:
        branch = project.bdict[branch_id]

        # Skip branch if local merging not desired, or no templates defined.
        if (not branch.merge or branch.topdir_templates is None):
            continue

        # Collect branch catalogs to merge.
        branch_catalogs = select_branch_catalogs(branch_id, project, options)

        # Collect template catalogs to use.
        template_catalogs = collect_catalogs(branch.topdir_templates, ".pot",
                                             branch.by_lang, branch.ignored,
                                             branch.split_path,
                                             project, options)

        # Collect data for branch catalogs to merge.
        for name, branch_path, branch_subdir in branch_catalogs:
            if not os.path.isfile(branch_path):
                # Catalog has been selected due to another operation mode,
                # which can create catalogs from scratch.
                continue
            if not name in template_catalogs:
                warning(_("@info",
                          "No template for branch catalog '%(file)s'.",
                          file=branch_path))
                continue
            exact = False
            for template_path, template_subdir in template_catalogs[name]:
                if template_subdir == branch_subdir:
                    exact = True
                    break
            if not exact:
                warning(_("@info",
                          "No exact template for branch catalog '%(file)s'.",
                          file=branch_path))
                continue
            merge_specs.append((branch_id, name, branch_subdir,
                                branch_path, template_path,
                                project.branches_wrapping,
                                project.branches_fuzzy_merging))

    # Setup progress indicator.
    upprog = lambda x: x
    if not options.verbose:
        catpaths = [x[3] for x in merge_specs]
        upprog = init_file_progress(catpaths,
                                    addfmt=t_("@info:progress",
                                              "Merging: %(file)s"))

    # Merge catalogs.
    for merge_spec in merge_specs:
        catpath = merge_spec[3]
        if options.verbose:
            report(_("@info:progress",
                     "Merging %(file)s...",
                     file=catpath))
        upprogc = lambda: upprog(catpath)
        summit_merge_single(*(merge_spec + (project, options, upprogc)))
    upprog()

    # Remove template tree in summit-over-dynamic-templates mode.
    if project.templates_dynamic:
        shutil.rmtree(project.tproject.summit.topdir)


def summit_deps (project, options):

    # Collect names of summit catalogs for which to report dependencies.
    summit_names = select_summit_names(project, options)

    # Report dependencies for all selected catalogs.
    for summit_name in summit_names:
        if summit_name not in project.catalogs[SUMMIT_ID]:
            # May happen if there are some missing summit catalogs
            # to current branch catalogs, i.e. gather has not been made.
            continue
        summit_path = project.catalogs[SUMMIT_ID][summit_name][0][0]
        branch_paths = []
        for branch_id in project.branch_ids:
            for branch_name in project.full_inverse_map[summit_name][branch_id]:
                for branch_path, d1 in project.catalogs[branch_id][branch_name]:
                    branch_paths.append(branch_path)
        fmtbpaths = " ".join(branch_paths)
        if options.verbose:
            actype = _("@item:intext action performed on a catalog",
                        "depends")
            report(":    (%s) %s  %s" % (actype, summit_path, fmtbpaths))
        else:
            report(":    %s  %s" % (summit_path, fmtbpaths))


def select_branch_catalogs (branch_id, project, options):

    # Shortcuts.
    pbcats = project.catalogs[branch_id]

    # Select either all catalogs in this branch,
    # or those mentioned in the command line.
    if not options.partspecs:
        branch_catalogs = []
        for name, spec in pbcats.items():
            for path, subdir in spec:
                if options.selcatf(path):
                    branch_catalogs.append((name, path, subdir))
    else:
        # Select branch catalogs by command line specification.
        branch_catalogs = []

        # Process direct specifications (branch->summit).
        if branch_id in options.partspecs:
            for part_spec in options.partspecs[branch_id]:
                # If the catalog specification has path separators,
                # then it selects a complete subdir in the branch.
                branch_catalogs_l = []
                if part_spec.find(os.sep) >= 0:
                    sel_subdir = os.path.normpath(part_spec)
                    one_found = False
                    for name, spec in pbcats.items():
                        for path, subdir in spec:
                            if sel_subdir == subdir:
                                one_found = True
                                if options.selcatf(path):
                                    branch_catalogs_l.append(
                                        (name, path, subdir))
                    if not one_found:
                        error(_("@info",
                                "No catalogs in subdirectory '%(dir)s' "
                                "of branch '%(branch)s'.",
                                dir=sel_subdir, branch=branch_id))
                else:
                    # Otherwise, specific catalog is selected.
                    sel_name = part_spec
                    one_found = False
                    for name, spec in pbcats.items():
                        if sel_name == name:
                            for path, subdir in spec:
                                one_found = True
                                if options.selcatf(path):
                                    branch_catalogs_l.append(
                                        (name, path, subdir))
                            break
                    if not one_found:
                        error(_("@info",
                                "No catalog named '%(name)s' "
                                "in branch '%(branch)s'.",
                                name=sel_name, branch=branch_id))

                # Also select all branch catalogs which contribute to same
                # summit catalogs as the already selected ones.
                branch_catalogs_l2 = []
                dmap = project.direct_map[branch_id]
                pimap = project.part_inverse_map[branch_id]
                for branch_name, d1, d2 in branch_catalogs_l:
                    if branch_name in dmap:
                        for summit_name in dmap[branch_name]:
                            if summit_name in pimap:
                                for name in pimap[summit_name]:
                                    for path, subdir in pbcats[name]:
                                        if options.selcatf(path):
                                            branch_catalogs_l2.append(
                                                (name, path, subdir))

                branch_catalogs.extend(branch_catalogs_l)
                branch_catalogs.extend(branch_catalogs_l2)

        # Process inverse specifications (summit->branch).
        if SUMMIT_ID in options.partspecs:
            for part_spec in options.partspecs[SUMMIT_ID]:
                if part_spec.find(os.sep) >= 0:
                    # Complete subdir.
                    sel_subdir = os.path.normpath(part_spec)
                    cats = []
                    for name, spec in project.catalogs[SUMMIT_ID].items():
                        path, subdir = spec[0] # all summit catalogs unique
                        if sel_subdir == subdir:
                            bnames = project.full_inverse_map[name][branch_id]
                            for bname in bnames:
                                if bname in pbcats:
                                    for bpath, bsubdir in pbcats[bname]:
                                        if options.selcatf(bpath):
                                            cats.append((bname, bpath, bsubdir))
                    branch_catalogs.extend(cats)
                else:
                    # Specific catalog.
                    sel_name = part_spec
                    if not sel_name in project.catalogs[SUMMIT_ID]:
                        error(_("@info",
                                "No summit catalog named '%(name)s'.",
                                name=sel_name))
                    bnames = project.full_inverse_map[sel_name][branch_id]
                    for bname in bnames:
                        if bname in pbcats:
                            for bpath, bsubdir in pbcats[bname]:
                                if options.selcatf(bpath):
                                    branch_catalogs.append(
                                        (bname, bpath, bsubdir))

    # Same catalogs may have been selected multiple times, remove.
    branch_catalogs = list(set(branch_catalogs))

    # Sort by path.
    branch_catalogs.sort(key=lambda x: x[1])
        # ...sorting is not only for looks, but to establish priority of
        # supplying comments to summit messages.

    return branch_catalogs


def select_summit_names (project, options):

    # Collect all summit catalogs selected explicitly or implicitly.
    summit_names = []
    if not options.partspecs:
        for name, spec in project.catalogs[SUMMIT_ID].items():
            path, subdir = spec[0] # summit catalogs are unique
            if options.selcatf(path):
                summit_names.append(name)
    else:
        for branch_id in options.partspecs:
            for part_spec in options.partspecs[branch_id]:

                if branch_id == SUMMIT_ID: # explicit by summit reference
                    if part_spec.find(os.sep) >= 0: # whole subdir
                        sel_subdir = os.path.normpath(part_spec)
                        one_found = False
                        for name, spec in project.catalogs[SUMMIT_ID].items():
                            path, subdir = spec[0] # summit catalogs are unique
                            if sel_subdir == subdir:
                                one_found = True
                                if options.selcatf(path):
                                    summit_names.append(name)
                        if not one_found:
                            error(_("@info",
                                    "No summit directory named '%(name)s'.",
                                    name=sel_subdir))
                    else: # single name
                        sel_name = part_spec
                        spec = project.catalogs[SUMMIT_ID].get(sel_name)
                        if not spec:
                            error(_("@info",
                                    "No summit catalog named '%(name)s'.",
                                    name=sel_name))
                        path, subdir = spec[0] # summit catalogs are unique
                        if options.selcatf(path):
                            summit_names.append(sel_name)

                else: # implicit by branch reference
                    if part_spec.find(os.sep) >= 0: # whole subdir
                        sel_subdir = os.path.normpath(part_spec)
                        one_found = False
                        for name, spec in project.catalogs[branch_id].items():
                            for path, subdir in spec:
                                if sel_subdir == subdir:
                                    one_found = True
                                    if options.selcatf(path):
                                        summit_names.extend(
                                            project.direct_map[branch_id][name])
                                    break
                        if not one_found:
                            error(_("@info",
                                    "No directory named '%(name)s' "
                                    "in branch '%(branch)s'.",
                                    name=sel_subdir, branch=branch_id))
                    else: # single name
                        sel_name = part_spec
                        spec = project.catalogs[branch_id].get(sel_name)
                        if not spec:
                            error(_("@info",
                                    "No catalog named '%(name)s' "
                                    "in branch '%(branch)s'.",
                                    name=sel_name, branch=branch_id))
                        for path, subdir in spec:
                            if options.selcatf(path):
                                summit_names.extend(
                                    project.direct_map[branch_id][sel_name])
                            break

    # Make names unique and sort by path.
    summit_names = list(set(summit_names))
    summit_names.sort(key=lambda x: project.catalogs[SUMMIT_ID].get(x, [[""]])[0][0])

    return summit_names


def summit_gather_single (summit_name, project, options,
                          phony=False, pre_summit_names=[],
                          update_progress=(lambda: None)):

    update_progress()

    summit_path = project.catalogs[SUMMIT_ID][summit_name][0][0]
    summit_subdir = project.catalogs[SUMMIT_ID][summit_name][0][1]

    update_from_old = (    os.path.exists(summit_path)
                       and not project.templates_dynamic)

    # Do not overwrite the old summit catalog here if it exists,
    # as it will be needed for comparison later.
    monitored = update_from_old
    summit_cat = Catalog("", monitored=monitored,
                         wrapping=project.summit_wrapping, create=True)
    summit_cat.filename = summit_path

    # Collect branches in which this summit catalog has corresponding
    # branch catalogs, in order of branch priority.
    src_branch_ids = []
    for branch_id in project.branch_ids:
        if project.full_inverse_map[summit_name][branch_id]:
            src_branch_ids.append(branch_id)

    # If there are no branch catalogs,
    # then the current summit catalog is to be removed.
    if not src_branch_ids:
        if phony: # cannot happen
            error(_("@info",
                    "Phony gather on summit catalog which is to be removed."))

        # Remove by version control, if any.
        if project.summit_vcs:
            if not project.summit_vcs.remove(summit_path):
                warning(_("@info",
                          "Cannot remove '%(path)s' from version control.",
                          path=summit_path))
        # If not removed by version control, plainly delete.
        if os.path.isfile(summit_path):
            os.unlink(summit_path)
            if os.path.isfile(summit_path):
                warning(_("@info",
                          "Cannot remove '%(path)s' from disk.",
                          path=summit_path))

        if not os.path.isfile(summit_path):
            if options.verbose:
                actype = _("@item:intext action performed on a catalog",
                           "gathered-removed")
                report("-    (%s) %s" % (actype, summit_path))
            elif not options.quiet:
                report("-    %s" % summit_path)

        # Skip the rest, nothing to gather.
        return summit_cat

    # Open all corresponding branch catalogs.
    # For each branch catalog, also phony-gather any dependent summit
    # catalogs. Phony means not to take into account branch catalogs which
    # map to current summit catalog if it is higher in their queue than
    # the phony-gathered one, and not to sync phony-gathered catalog;
    # this is needed in order that any new messages get inserted
    # uniquely and deterministically in case of split-mappings.
    bcat_pscats = {}
    for branch_id in src_branch_ids:
        bcat_pscats[branch_id] = []
        for branch_name in project.full_inverse_map[summit_name][branch_id]:

            # In phony-gather, do not use branch catalogs with split-mappings
            # which map to one of the summit catalogs among previous.
            phony_skip = False
            for dep_summit_name in project.direct_map[branch_id][branch_name]:
                if dep_summit_name in pre_summit_names:
                    phony_skip = True
                    break
            if phony_skip:
                continue

            # Gather and open dependent summit catalogs.
            dep_summit_cats = []
            pre_summit_names_m = pre_summit_names[:]
            for dep_summit_name in project.direct_map[branch_id][branch_name]:
                if dep_summit_name == summit_name:
                    pre_summit_names_m.append(summit_name)
                    continue
                # FIXME: Can we get into circles here?
                dep_summit_cat = summit_gather_single(dep_summit_name,
                                                      project, options,
                                                      True, pre_summit_names_m,
                                                      update_progress)
                if dep_summit_cat is not None:
                    dep_summit_cats.append(dep_summit_cat)

            # Open all branch catalogs of this name, ordered by path,
            # link them to the same dependent summit catalogs.
            for path, subdir in project.catalogs[branch_id][branch_name]:
                update_progress()

                # Apply hooks to branch catalog file, creating temporaries.
                tmp_path = None
                if project.hook_on_gather_file_branch:
                    # Temporary path should be such as to not modify the
                    # catalog name (e.g. appending ".mod" could make ".po"
                    # a part of the name).
                    tmp_path = path + "~mod"
                    shutil.copyfile(path, tmp_path)
                    exec_hook_file(branch_id, branch_name, subdir, tmp_path,
                                   project.hook_on_gather_file_branch)

                branch_cat = Catalog(tmp_path or path, monitored=False)
                if tmp_path: # as soon as catalog is opened, no longer needed
                    os.unlink(tmp_path)

                # Apply hooks to branch catalog.
                if project.hook_on_gather_cat_branch:
                    exec_hook_cat(branch_id, branch_name, subdir, branch_cat,
                                  project.hook_on_gather_cat_branch)
                    branch_cat.sync_map()

                # Apply hooks to all branch catalog messages here,
                # as they may modify message keys.
                if project.hook_on_gather_msg_branch:
                    for msg in branch_cat:
                        update_progress()
                        exec_hook_msg(branch_id, branch_name, subdir,
                                      msg, branch_cat,
                                      project.hook_on_gather_msg_branch)
                    branch_cat.sync_map()

                bcat_pscats[branch_id].append((branch_cat, dep_summit_cats))

    # On phony gather, in case of split mappings,
    # it may happen that there are no corresponding branch catalogs.
    if phony and not any(bcat_pscats.values()):
        return None

    # Select primary branch catalog.
    prim_branch_cat = bcat_pscats[src_branch_ids[0]][0][0]

    # Gather messages through branch catalogs.
    for branch_id in src_branch_ids:
        for branch_cat, dep_summit_cats in bcat_pscats[branch_id]:
            is_primary = branch_cat is prim_branch_cat
            summit_gather_single_bcat(branch_id, branch_cat, is_primary,
                                      summit_cat, monitored, dep_summit_cats,
                                      project, options, update_progress)

    # Gather the summit header according to primary branch.
    summit_gather_single_header(summit_cat, prim_branch_cat, project, options)

    # Apply hooks to the summit messages.
    if project.hook_on_gather_msg:
        for msg in summit_cat:
            exec_hook_msg(SUMMIT_ID, summit_cat.name, summit_subdir,
                          msg, summit_cat, project.hook_on_gather_msg)

    # Apply hooks to the summit catalog.
    exec_hook_cat(SUMMIT_ID, summit_cat.name, summit_subdir, summit_cat,
                  project.hook_on_gather_cat)

    # If phony-gather, stop here and return summit catalog for reference.
    if phony:
        return summit_cat

    # If the old summit catalog exists, compare with the new.
    # If there were any modified entries, or their order changed,
    # replace the old with the new summit catalog.
    # Copy over unmodified entries from the old catalog,
    # to avoid line reformatting.
    if update_from_old:
        old_cat = Catalog(summit_path, monitored=monitored,
                          wrapping=project.summit_wrapping)
        summit_created = False
        replace = False
        # Compare headers without some insignificant fields.
        if cmpnorm_hdr(summit_cat.header) == cmpnorm_hdr(old_cat.header):
            summit_cat.header = old_cat.header
        else:
            replace = True
        # Compare messages and their positions.
        for pos in range(len(summit_cat)):
            update_progress()
            old_pos = old_cat.find(summit_cat[pos])
            if pos != old_pos:
                replace = True
            if old_pos >= 0:
                if summit_cat[pos] == old_cat[old_pos]:
                    summit_cat[pos] = old_cat[old_pos]
                else:
                    replace = True
        # Compare lengths.
        if len(summit_cat) != len(old_cat):
            replace = True
    else:
        summit_created = True
        replace = True

    # Check if the catalog needs to be moved to another subdirectory.
    branch_subdirs = []
    for branch_id in project.full_inverse_map[summit_name]:
        for branch_name in project.full_inverse_map[summit_name][branch_id]:
            branch_subdirs_1 = []
            for bpath, bsubdir in project.catalogs[branch_id][branch_name]:
                bsubdir = project.subdir_map.get((branch_id, bsubdir), bsubdir)
                branch_subdirs_1.append(bsubdir)
            branch_subdirs_1.sort()
            branch_subdirs.extend(branch_subdirs_1)
    new_summit_path = summit_path
    if branch_subdirs and summit_subdir not in branch_subdirs:
        catext = summit_path[summit_path.rfind("."):]
        new_summit_path = join_ncwd(project.summit.topdir, branch_subdirs[0],
                                    summit_name + catext)

    if replace or summit_cat.filename != new_summit_path:
        added = False
        moved = False

        if replace:
            # Set template creation date for the summit catalog
            # to the current date.
            # Do not try to trust branch template creation dates,
            # e.g. by copying the latest one.
            summit_cat.header.set_field(u"POT-Creation-Date", format_datetime())

            # Sync to disk.
            summit_cat.sync()

            # Apply hooks to summit catalog file.
            exec_hook_file(SUMMIT_ID, summit_cat.name, summit_subdir,
                           summit_cat.filename, project.hook_on_gather_file)

            if summit_created:
                added = True
            # Add to version control.
            if (    project.summit_vcs
                and not project.summit_vcs.is_versioned(summit_cat.filename)
            ):
                if not project.summit_vcs.add(summit_cat.filename):
                    warning(_("@info",
                            "Cannot add '%(file)s' to version control.",
                            file=summit_cat.filename))
                else:
                    added = True

        if summit_cat.filename != new_summit_path:
            if project.summit_vcs:
                if not project.summit_vcs.move(summit_cat.filename,
                                               new_summit_path):
                    warning(_("@info",
                              "Cannot move '%(srcfile)s' to '%(dstfile)s'.",
                              srcfile=summit_cat.filename,
                              dstfile=new_summit_path))
                else:
                    summit_cat.filename = new_summit_path
                    moved = True

        branch_paths = []
        for branch_id in src_branch_ids:
            for branch_cat, dep_summit_cats in bcat_pscats[branch_id]:
                branch_paths.append(branch_cat.filename)
        paths_str = " ".join(branch_paths)
        if options.verbose:
            if added:
                actype = _("@item:intext action performed on a catalog",
                           "gathered-added")
                report(">+   (%s) %s  %s"
                       % (actype, summit_cat.filename, paths_str))
            elif moved:
                actype = _("@item:intext action performed on a catalog",
                           "gathered-moved")
                report(">|   (%s) %s  %s"
                       % (actype, summit_cat.filename, paths_str))
            else:
                actype = _("@item:intext action performed on a catalog",
                           "gathered")
                report(">    (%s) %s  %s"
                       % (actype, summit_cat.filename, paths_str))
        elif not options.quiet:
            if added:
                report(">+   %s  %s" % (summit_cat.filename, paths_str))
            elif moved:
                report(">|   %s  %s" % (summit_cat.filename, paths_str))
            else:
                report(">    %s  %s" % (summit_cat.filename, paths_str))

    return summit_cat


def cmpnorm_hdr (hdr):

    rhdr = Header(hdr)
    for field in (
        "POT-Creation-Date",
    ):
        rhdr.remove_field(field)
    return rhdr


def extkey_msg (msg):

    # NOTE: If computation of context pad is modified,
    # padded messages in existing summit catalogs will get fuzzy
    # on next merge with newly gathered templates.

    msg = MessageUnsafe(msg)
    if msg.msgid_plural is not None:
        h = hashlib.md5()
        h.update(msg.msgid_plural.encode("UTF-8"))
        ctxtpad = h.hexdigest()
    else:
        # Something that looks like a hex digest but slightly shorter,
        # so that it does not match any real digest.
        ctxtpad = "abcd1234efgh5665hgfe4321dcba"
    msg.auto_comment.append(u"%s msgctxt-pad %s"
                            % (_summit_tag_kwprop, ctxtpad))
    if msg.msgctxt is None:
        msg.msgctxt = u"%s" % ctxtpad
    else:
        msg.msgctxt = u"%s|%s" % (msg.msgctxt, ctxtpad)

    return msg


def summit_gather_single_bcat (branch_id, branch_cat, is_primary,
                               summit_cat, monitored, dep_summit_cats,
                               project, options, update_progress):

    MessageType = (Message if monitored else MessageUnsafe)

    # Go through messages in the branch catalog, merging them with
    # existing summit messages, or collecting for later insertion.
    # Do not insert new messages immediately, as source references may be
    # updated by merging, which reflects on heuristic insertion.
    # Ignore messages present in dependent summit catalogs.
    msgs_to_merge = []
    msgs_to_insert = []
    xkpairs = []
    for msg in branch_cat:
        update_progress()

        # Do not gather obsolete messages.
        if msg.obsolete:
            continue

        # Normalizations when gathering templates,
        # in case extraction tool needs to have its sanity checked,
        # or certain language files stand in for true templates.
        if project.lang == project.templates_lang:
            msg.manual_comment[:] = []
            msg.unfuzzy()
            if msg.msgid_plural is None:
                msg.msgstr[:] = [u""]
            else:
                msg.msgstr[:] = [u"", u""]

        # Construct branch message with extended key.
        xkmsg = extkey_msg(msg)

        # Do not gather messages belonging to depending summit catalogs.
        in_dep = False
        for dep_summit_cat in dep_summit_cats:
            if msg in dep_summit_cat or xkmsg in dep_summit_cat:
                in_dep = True
                break
        if in_dep:
            continue

        # If the summit message for the original branch message exists,
        # but their extended keys do not match,
        # switch to branch message with extended key.
        summit_msg = summit_cat.get(msg)
        if summit_msg and extkey_msg(summit_msg).key != xkmsg.key:
            xkpairs.append((msg, xkmsg))
            msg = xkmsg
            summit_msg = summit_cat.get(msg)

        # Collect the branch message for merging or insertion.
        if summit_msg is not None:
            msgs_to_merge.append((msg, summit_msg))
        else:
            msgs_to_insert.append(msg)

    # If some messages had to have extended keys, update branch catalog.
    if xkpairs:
        for msg, xkmsg in xkpairs:
            branch_cat.remove_on_sync(msg)
            branch_cat.add_last(xkmsg)
        branch_cat.sync_map()

    # Merge messages already in the summit catalog.
    if msgs_to_merge:
        for msg, summit_msg in msgs_to_merge:
            # Merge the message.
            gather_merge_msg(summit_msg, msg)
            # Update automatic comments.
            summit_override_auto(summit_msg, msg, branch_id, is_primary)
            # Equip any new summit tags to the merged message.
            summit_set_tags(summit_msg, branch_id, project)

    # Insert messages not already in the summit catalog.
    if msgs_to_insert:
        # Pair messages to insert from branch with summit messages
        # having common source files.
        # If summit is empty, this is primary branch catalog, so make
        # only one dummy pair to preserve original ordering of messages.
        summit_msgs_by_src_dict = dict(summit_cat.messages_by_source())
        if summit_msgs_by_src_dict:
            msgs_by_src = branch_cat.messages_by_source()
        else:
            msgs_by_src = [("", branch_cat)]

        # Collect possible source file synonyms to those in the summit catalog.
        fnsyn = branch_cat.detect_renamed_sources(summit_cat)

        # Prepare messages for insertion into summit.
        summit_msg_by_msg = {}
        for msg in msgs_to_insert:
            update_progress()
            summit_msg = MessageType(msg)
            summit_set_tags(summit_msg, branch_id, project)
            summit_msg_by_msg[msg] = summit_msg

        # Insert branch messages into summit source by source.
        for src, msgs in msgs_by_src:

            # Assemble collection of summit messages from same source file.
            summit_msgs = []
            for osrc in [src] + fnsyn.get(src, []):
                summit_msgs.extend(summit_msgs_by_src_dict.get(osrc, []))

            # If existing summit messages from same source found,
            # insert branch messages around those summit messages.
            # Otherwise, just append them at the end.
            if summit_msgs:

                # Assemble groups of messages by same msgid and same msgctxt.
                smsgs_by_msgid = {}
                smsgs_by_msgctxt = {}
                for smsg in summit_msgs:
                    if smsg.msgid not in smsgs_by_msgid:
                        smsgs_by_msgid[smsg.msgid] = []
                    smsgs_by_msgid[smsg.msgid].append(smsg)
                    if smsg.msgctxt is not None:
                        if smsg.msgctxt not in smsgs_by_msgctxt:
                            smsgs_by_msgctxt[smsg.msgctxt] = []
                        smsgs_by_msgctxt[smsg.msgctxt].append(smsg)

                insertions = []
                for msg in msgs:
                    update_progress()
                    new_summit_msg = summit_msg_by_msg.get(msg)
                    if new_summit_msg is None:
                        continue

                    # Existing summit message to where (after or before)
                    # current message is to be inserted.
                    summit_msg_ref = None
                    before = False

                    # Try to insert message by similarity.
                    # Similarity is checked by groups,
                    # such that for each group there is a message part
                    # which is compared for similarity.
                    for summit_msgs_group, matt, forceins in (
                        (smsgs_by_msgid.get(msg.msgid), "msgctxt", True),
                        (smsgs_by_msgctxt.get(msg.msgctxt), "msgid", True),
                        (summit_msgs, "key", False),
                    ):
                        if not summit_msgs_group:
                            continue

                        # Shortcut: if only one summit message in the group
                        # and insertion forced, insert after it.
                        if len(summit_msgs_group) == 1 and forceins:
                            summit_msg_ref = summit_msgs_group[-1]
                            break

                        # Does the message have the part to be matched?
                        mval = msg.get(matt)
                        if mval is None:
                            continue

                        # Find existing message with the most similar
                        # matching attribute.
                        seqm = SequenceMatcher(None, mval, "")
                        maxr = 0.0
                        for summit_msg in summit_msgs_group:
                            smval = summit_msg.get(matt)
                            if smval is None:
                                continue
                            seqm.set_seq2(smval)
                            r = seqm.ratio()
                            if maxr <= r:
                                maxr = r
                                maxr_summit_msg = summit_msg

                        # If similar enough message has been found,
                        # set insertion position after it.
                        # Otherwise, insert after last summit message
                        # in the group if insertion forced.
                        if maxr > 0.6:
                            summit_msg_ref = maxr_summit_msg
                            break
                        elif forceins:
                            summit_msg_ref = summit_msgs_group[-1]
                            break

                    # If no similar existing message, set position before
                    # the summit message with first greater source reference
                    # line number, if any such.
                    if summit_msg_ref is None and src:
                        for summit_msg in summit_msgs:
                            if msg.source[0][1] < summit_msg.source[0][1]:
                                summit_msg_ref = summit_msg
                                before = True
                                break

                    # If not insertion by source references, insert last.
                    if summit_msg_ref is None:
                        summit_msg_ref = summit_msgs[-1]

                    # Record insertion.
                    pos = summit_cat.find(summit_msg_ref)
                    if not before:
                        pos += 1
                    insertions.append((new_summit_msg, pos))

                # Insert ordered messages into catalog.
                summit_cat.add_more(insertions)

            else:
                for msg in msgs:
                    update_progress()
                    new_summit_msg = summit_msg_by_msg.get(msg)
                    if new_summit_msg is not None:
                        summit_cat.add_last(new_summit_msg)


def gather_merge_msg (summit_msg, msg):

    if summit_msg.key != msg.key:
        error(_("@info",
                "Cannot gather messages with different keys."))
    if (summit_msg.msgid_plural is None) != (msg.msgid_plural is None):
        error(_("@info",
                "Cannot gather messages with different plurality."))

    if (   (summit_msg.translated and msg.translated)
        or (summit_msg.fuzzy and msg.fuzzy)
        or (summit_msg.untranslated and msg.untranslated)
    ):
        if not summit_msg.manual_comment:
            summit_msg.manual_comment = Monlist(msg.manual_comment)
        if msg.msgid_plural is not None:
            summit_msg.msgid_plural = msg.msgid_plural
        summit_msg.msgstr = Monlist(msg.msgstr)

    elif summit_msg.fuzzy and msg.translated:
        summit_msg.manual_comment = Monlist(msg.manual_comment)
        if summit_msg.msgid_plural is None or msg.msgid_plural is not None:
            if msg.msgid_plural is not None:
                summit_msg.msgid_plural = msg.msgid_plural
            summit_msg.msgstr = Monlist(msg.msgstr)
            if summit_msg.msgid_plural == msg.msgid_plural:
                summit_msg.unfuzzy()

    elif summit_msg.untranslated and (msg.translated or msg.fuzzy):
        summit_msg.manual_comment = Monlist(msg.manual_comment)
        if summit_msg.msgid_plural is None or msg.msgid_plural is not None:
            if msg.fuzzy:
                summit_msg.msgctxt_previous = msg.msgctxt_previous
                summit_msg.msgid_previous = msg.msgid_previous
                summit_msg.msgid_plural_previous = msg.msgid_plural_previous
            if msg.msgid_plural is not None:
                summit_msg.msgid_plural = msg.msgid_plural
            summit_msg.msgstr = Monlist(msg.msgstr)
            summit_msg.fuzzy = msg.fuzzy


def summit_gather_single_header (summit_cat, prim_branch_cat,
                                 project, options):

    # Copy over comments from the primary branch catalog.
    hdr = summit_cat.header
    bhdr = prim_branch_cat.header
    hdr.title = bhdr.title
    hdr.copyright = bhdr.copyright
    hdr.license = bhdr.license
    hdr.author = bhdr.author
    hdr.comment = bhdr.comment

    # Copy over standard fields from the primary branch catalog.
    for fname in [x[0] for x in Header().field]:
        fvalue = prim_branch_cat.header.get_field_value(fname)
        if fvalue is not None:
            summit_cat.header.set_field(fname, fvalue)
        else:
            summit_cat.header.remove_field(fname)

    # Copy over non-standard fields from the primary branch catalog on request.
    bfields = []
    for fname in project.header_propagate_fields:
        bfields.extend(prim_branch_cat.header.select_fields(fname))
    cfields = []
    for fname in project.header_propagate_fields:
        cfields.extend(summit_cat.header.select_fields(fname))
    # Replace old with new set if not equal.
    if bfields != cfields:
        for cfield in cfields:
            summit_cat.header.field.remove(cfield)
        for bfield in bfields:
            summit_cat.header.field.append(bfield)


_asc_check_cache = {}

def summit_scatter_single (branch_id, branch_name, branch_subdir,
                           branch_path, summit_paths,
                           project, options, update_progress):

    update_progress()

    # See if the branch catalog is to be newly created from the template.
    new_from_template = False
    branch_path_mod = branch_path
    if branch_path in project.add_on_scatter:
        new_from_template = True
        # Initialize new catalog with messages directly from the template.
        # Later the catalog file name will be switched to branch path,
        # if the catalog satisfies criteria to be created on scatter.
        branch_path_mod = project.add_on_scatter[branch_path]

    # Open the branch catalog and all summit catalogs.
    try:
        branch_cat = Catalog(branch_path_mod, wrapping=project.branches_wrapping)
    except PologyError, e:
        warning(_("@info",
                  "Cannot open the branch catalog '%(file)s' "
                  "to scatter to. The error was:\n"
                  "%(msg)s",
                  file=branch_path_mod, msg=str_to_unicode(str(e))))
        return
    summit_cats = []
    for summit_path in summit_paths:
        try:
            # NOTE: Must be opened monitored to have compatible types
            # when copying message parts to branch message.
            summit_cat = Catalog(summit_path)
        except PologyError, e:
            warning(_("@info",
                      "Cannot open the summit catalog '%(file)s' "
                      "to scatter from. The error was:\n"
                      "%(msg)s",
                      file=summit_path, msg=str_to_unicode(str(e))))
            return
        summit_cats.append(summit_cat)

    # Collect and link ascription catalogs to summit catalogs.
    # (Do not open them here, but only later when a check is not cached.)
    if project.ascription_filter:
        aconfs_acats = {}
        for summit_cat in summit_cats:
            aconf, acatpath = project.aconfs_acatpaths[summit_cat.name]
            aconfs_acats[summit_cat.name] = (aconf, None, acatpath)
            if acatpath not in _asc_check_cache:
                _asc_check_cache[acatpath] = {}

    # Pair branch messages with summit messages.
    msgs_total = 0
    msgs_translated = 0
    msg_links = []
    asc_stopped = 0
    for branch_msg in branch_cat:
        update_progress()

        # Skip obsolete messages.
        if branch_msg.obsolete:
            continue
        msgs_total += 1

        # If there is a hook on branch messages on gather,
        # it must be used here to prepare branch message for lookup
        # in summit catalog, as the hook may modify the key.
        branch_msg_lkp = branch_msg
        if project.hook_on_gather_msg_branch:
            branch_msg_lkp = MessageUnsafe(branch_msg)
            exec_hook_msg(branch_id, branch_name, branch_subdir,
                          branch_msg_lkp, branch_cat,
                          project.hook_on_gather_msg_branch)

        # Construct branch message for lookup with extended key.
        branch_xkmsg_lkp = extkey_msg(branch_msg_lkp)

        # Find first summit catalog which has this message translated.
        summit_msg = None
        for summit_cat in summit_cats:
            # Branch message with extended key must be looked up first.
            for bmsg_lkp in [branch_xkmsg_lkp, branch_msg_lkp]:
                if bmsg_lkp in summit_cat:
                    summit_msg = summit_cat[bmsg_lkp]
                    if summit_msg.obsolete:
                        summit_msg = None
                    else:
                        break
            if summit_msg is not None:
                break

        if summit_msg is None:
            report_on_msg(_("@info:progress",
                            "Message not in the summit."),
                          branch_msg, branch_cat)
            continue

        if (    project.ascription_filter and not options.force
            and do_scatter(summit_msg, branch_msg)
        ):
            aconf, acat, acatpath = aconfs_acats[summit_cat.name]
            if summit_msg.key not in _asc_check_cache[acatpath]:
                if acat is None:
                    acat = Catalog(acatpath, monitored=False, create=True)
                    aconfs_acats[summit_cat.name] = (aconf, acat, acatpath)
                hfilter = project.ascription_history_filter
                ahist = collect_ascription_history(summit_msg, acat, aconf,
                                                   nomrg=True, hfilter=hfilter)
                afilter = project.ascription_filter
                res = afilter(summit_msg, summit_cat, ahist, aconf)
                _asc_check_cache[acatpath][summit_msg.key] = res
            if not _asc_check_cache[acatpath][summit_msg.key]:
                asc_stopped += 1
                continue

        if summit_msg.translated:
            msgs_translated += 1
        msg_links.append((branch_msg, summit_msg, summit_cat))

    if asc_stopped > 0:
        warning(n_("@info:progress",
                   "%(file)s: %(num)d message stopped by ascription filter.",
                   "%(file)s: %(num)d messages stopped by ascription filter.",
                   file=branch_path, num=asc_stopped))

    # If completeness less than minimal acceptable, remove all translations.
    completeness_ratio = float(msgs_translated) / msgs_total
    if (   completeness_ratio < project.scatter_acc_completeness
        and not options.force
    ):
        for branch_msg in branch_cat:
            if branch_msg.obsolete:
                branch_cat.remove_on_sync(branch_msg)
            else:
                clear_msg(branch_msg)

    # If complete enough, scatter from summit to branch messages.
    else:
        scattered_branch_msgs = set()
        for branch_msg, summit_msg, summit_cat in msg_links:
            update_progress()

            if do_scatter(summit_msg, branch_msg):
                exec_hook_msg(branch_id, branch_name, branch_subdir,
                              summit_msg, summit_cat,
                              project.hook_on_scatter_msg)

                # NOTE: Same plurality and equal msgid_plural fields
                # between summit and branch message are enforced,
                # so only assert this for robustness.
                if summit_msg.msgid_plural != branch_msg.msgid_plural:
                    error(_("@info",
                            "Cannot scatter messages with "
                            "different plurality."))

                for i in range(len(summit_msg.msgstr)):
                    piped_msgstr = exec_hook_msgstr(
                        branch_id, branch_name, branch_subdir,
                        summit_msg.msgstr[i], summit_msg, summit_cat,
                        project.hook_on_scatter_msgstr)
                    if i < len(branch_msg.msgstr):
                        branch_msg.msgstr[i] = piped_msgstr
                    else:
                        branch_msg.msgstr.append(piped_msgstr)
                branch_msg.unfuzzy()
                branch_msg.manual_comment = summit_msg.manual_comment
                scattered_branch_msgs.add(branch_msg)

        # Fuzzy all active messages which were not scattered,
        # in order to avoid stale translations in branches.
        for branch_msg in branch_cat:
            if branch_msg.active and branch_msg not in scattered_branch_msgs:
                branch_msg.fuzzy = True

    # Update branch header based on primary summit catalog.
    # Copy over all header parts from summit to branch,
    # except for those copied from template on merging.
    hdr = branch_cat.header
    shdr = summit_cats[0].header
    # Fields to keep due to being copied over on merging.
    keep_fields = [
        "Report-Msgid-Bugs-To",
        "POT-Creation-Date",
    ]
    # Fields to keep if no branch message was modified.
    if not branch_cat.modcount and branch_cat.header.initialized:
        keep_fields.extend([
            "PO-Revision-Date",
            "Last-Translator",
        ])
    # Fields to keep due to explicitly being told to.
    keep_fields.extend(project.header_skip_fields_on_scatter)
    # Update comments.
    hdr.title = shdr.title
    hdr.copyright = shdr.copyright
    hdr.license = shdr.license
    hdr.author = shdr.author
    hdr.comment = shdr.comment
    # Update fields only if normalized lists of fields do not match.
    if normhf(hdr.field, keep_fields) != normhf(shdr.field, keep_fields):
        # Collect branch fields to be preserved.
        preserved_fs = []
        for fnam in keep_fields:
            selected_fs = branch_cat.header.select_fields(fnam)
            preserved_fs.append(selected_fs[0] if selected_fs else (fnam, None))
        # Overwrite branch with summit header fields.
        hdr.field = shdr.field
        # Put back the preserved branch fields.
        for fnam, fval in preserved_fs:
            if fval is not None:
                hdr.set_field(fnam, fval)
            else:
                hdr.remove_field(fnam)

    # Apply hooks to the branch catalog.
    exec_hook_cat(branch_id, branch_name, branch_subdir, branch_cat,
                  project.hook_on_scatter_cat)

    # If the branch catalog has been newly created,
    # see if it is translated enough to be really written out.
    skip_write = False
    if new_from_template and not options.force:
        ntrans = 0
        for msg in branch_cat:
            if msg.translated:
                ntrans += 1
        skip_write = (  float(ntrans) / len(branch_cat) + 1e-6
                      < project.scatter_min_completeness)

    if new_from_template and not skip_write:
        # Create any needed subdirectories and set destination branch path.
        mkdirpath(os.path.dirname(branch_path))
        branch_cat.filename = branch_path

    # Commit changes to the branch catalog.
    if not skip_write and (branch_cat.sync() or options.force):

        # Apply hooks to branch catalog file.
        exec_hook_file(branch_id, branch_name, branch_subdir,
                       branch_cat.filename, project.hook_on_scatter_file)

        # Add to version control.
        if (    project.branches_vcs
            and not project.bdict[branch_id].skip_version_control
        ):
            if not project.branches_vcs.add(branch_cat.filename):
                warning(_("@info",
                          "Cannot add '%(file)s' to version control.",
                          file=branch_cat.filename))

        paths_str = " ".join(summit_paths)
        if options.verbose:
            if new_from_template:
                actype = _("@item:intext action performed on a catalog",
                           "scattered-added")
                report("<+   (%s) %s  %s"
                       % (actype, branch_cat.filename, paths_str))
            else:
                actype = _("@item:intext action performed on a catalog",
                           "scattered")
                report("<    (%s) %s  %s"
                       % (actype, branch_cat.filename, paths_str))
        elif not options.quiet:
            if new_from_template:
                report("<+   %s  %s" % (branch_cat.filename, paths_str))
            else:
                report("<    %s  %s" % (branch_cat.filename, paths_str))


def do_scatter (smsg, bmsg):

    return smsg.translated


def hook_applicable (branch_check, branch_id, name_check, name, subdir):

    if branch_check is not None:
        if hasattr(branch_check, "__call__"):
            if not branch_check(branch_id):
                return False
        else:
            if not re.search(branch_check, branch_id):
                return False

    if name_check is not None:
        if hasattr(name_check, "__call__"):
            if not name_check(name, subdir):
                return False
        else:
            if not re.search(name_check, name):
                return False

    return True


# Pipe msgstr through hook calls,
# for which branch id and catalog name match hook specification.
def exec_hook_msgstr (branch_id, branch_name, branch_subdir,
                      msgstr, msg, cat, hooks):

    piped_msgstr = msgstr
    for call, branch_ch, name_ch in hooks:
        if hook_applicable(branch_ch, branch_id, name_ch,
                           branch_name, branch_subdir):
            piped_msgstr_tmp = call(piped_msgstr, msg, cat)
            if isinstance(piped_msgstr_tmp, basestring):
                piped_msgstr = piped_msgstr_tmp

    return piped_msgstr


# Pipe message through hook calls,
# for which branch id and catalog name match hook specification.
def exec_hook_msg (branch_id, branch_name, branch_subdir, msg, cat, hooks):

    # Apply all hooks to the message.
    for call, branch_ch, name_ch in hooks:
        if hook_applicable(branch_ch, branch_id, name_ch,
                           branch_name, branch_subdir):
            call(msg, cat)


# Pipe header through hook calls,
# for which branch id and catalog name match hook specification.
def exec_hook_head (branch_id, branch_name, branch_subdir, hdr, cat, hooks):

    # Apply all hooks to the header.
    for call, branch_ch, name_ch in hooks:
        if hook_applicable(branch_ch, branch_id, name_ch,
                           branch_name, branch_subdir):
            call(hdr, cat)


# Pipe catalog through hook calls,
# for which branch id and catalog name match hook specification.
def exec_hook_cat (branch_id, branch_name, branch_subdir, cat, hooks):

    # Apply all hooks to the catalog.
    for call, branch_ch, name_ch in hooks:
        if hook_applicable(branch_ch, branch_id, name_ch,
                           branch_name, branch_subdir):
            call(cat)


# Pipe catalog file through hook calls,
# for which branch id and catalog name match hook specification.
def exec_hook_file (branch_id, branch_name, branch_subdir, filepath, hooks):

    # Make temporary backup of the file.
    # FIXME: Portable construction of temporary file.
    bckppath = "/tmp/backup%s-%s" % (os.getpid(), os.path.basename(filepath))
    shutil.copyfile(filepath, bckppath)

    # Apply all hooks to the file, but stop if one returns non-zero status.
    failed = False
    for call, branch_ch, name_ch in hooks:
        if hook_applicable(branch_ch, branch_id, name_ch,
                           branch_name, branch_subdir):
            if call(filepath) != 0:
                failed = True
                break

    # If any hook failed, retrieve the temporary copy.
    if failed:
        shutil.move(bckppath, filepath)
    else:
        os.unlink(bckppath)


# Pipe branch through hook calls,
# for which branch id and matches hook specification.
def exec_hook_branch (branch_id, hooks):

    # Apply all hooks to the branch, but stop if one returns non-zero status.
    failed = False
    for call, branch_ch, d1 in hooks:
        if hook_applicable(branch_ch, branch_id, None, None, None):
            if call(branch_id) != 0:
                failed = True
                break


def find_summit_comment (msg, summit_tag):

    i = 0
    for c in msg.auto_comment:
        if c.startswith(summit_tag):
            return i
        i += 1
    return -1


def get_summit_comment (msg, summit_tag, default=u""):

    p = find_summit_comment(msg, summit_tag)
    if p >= 0:
        return msg.auto_comment[p][len(summit_tag):].strip()
    else:
        return default


def set_summit_comment (msg, summit_tag, text):

    ctext = unicode(summit_tag + " " + text.strip())
    p = find_summit_comment(msg, summit_tag)
    if p >= 0:
        msg.auto_comment[p] = ctext
    else:
        msg.auto_comment.append(ctext)


_summit_tag_branchid = "+>"
_summit_tag_kwprop = "+:"
_summit_tags = (
    _summit_tag_branchid,
    _summit_tag_kwprop,
)

def summit_set_tags (msg, branch_id, project):

    # Add branch ID.
    branch_ids = get_summit_comment(msg, _summit_tag_branchid, "").split()
    if branch_id not in branch_ids:
        branch_ids.append(branch_id)
    set_summit_comment(msg, _summit_tag_branchid, " ".join(branch_ids))


def summit_override_auto (summit_msg, branch_msg, branch_id, is_primary):

    # Copy auto/source/flag comments only if this is the primary branch
    # for the current message.
    if is_primary:

        # Equalize flags, except the fuzzy.
        for fl in branch_msg.flag:
            if fl != "fuzzy":
                summit_msg.flag.add(fl)
        for fl in summit_msg.flag:
            if fl != "fuzzy" and fl not in branch_msg.flag:
                summit_msg.flag.remove(fl)

        # Equalize source references.
        # FIXME: Once there is a way to reliably tell the root directory
        # of source references, add missing and remove obsolete source
        # references instead.
        summit_msg.source = Monlist(map(Monpair, branch_msg.source))

        # Split auto comments of the current summit message into
        # summit and non-summit tagged comments.
        # Also of the branch message, in case it has summit-alike comments.
        summit_nscmnts, summit_scmnts = split_summit_comments(summit_msg)
        branch_nscmnts, branch_scmnts = split_summit_comments(branch_msg)

        # Override auto comments only if different overally
        # (which needs not be, due to double fresh/old insertion)
        # and non-summit auto comments of the current summit message
        # are different to the branch message auto comments.
        if (    summit_msg.auto_comment != branch_msg.auto_comment
            and summit_nscmnts != branch_nscmnts
        ):
            summit_msg.auto_comment = Monlist(branch_msg.auto_comment)
            summit_msg.auto_comment.extend(summit_scmnts)


def split_summit_comments (msg):

    non_summit_comments = []
    summit_comments = []
    for comment in msg.auto_comment:
        wlst = comment.split()
        if wlst and wlst[0] in _summit_tags:
            summit_comments.append(comment)
        else:
            non_summit_comments.append(comment)

    return non_summit_comments, summit_comments


def summit_merge_single (branch_id, catalog_name, catalog_subdir,
                         catalog_path, template_path,
                         wrapping, fuzzy_merging,
                         project, options, update_progress):

    update_progress()

    # Gather the summit template in summit-over-dynamic-templates mode.
    if project.templates_dynamic and branch_id == SUMMIT_ID:
        summit_gather_single(catalog_name, project.tproject, project.toptions,
                             update_progress=update_progress)

    # FIXME: Portable construction of temporary file.
    tmp_path = os.path.join("/tmp", (  os.path.basename(catalog_path)
                                     + "~merged-%d" % os.getpid()))

    # Whether to create pristine catalog from template.
    vivified = catalog_path in project.add_on_merge

    # Skip calling msgmerge if template creation dates are equal.
    do_msgmerge = True
    if not vivified and not project.templates_dynamic and not options.force:
        hdr = Catalog(catalog_path, monitored=False, headonly=True).header
        thdr = Catalog(template_path, monitored=False, headonly=True).header
        fname = "POT-Creation-Date"
        do_msgmerge = hdr.get_field_value(fname) != thdr.get_field_value(fname)

    header_prop_fields = project.header_propagate_fields

    # Should merged catalog be opened, and in what mode?
    do_open = False
    headonly = False
    monitored = False
    otherwrap = set(wrapping).difference(["basic"])
    if otherwrap or project.hook_on_merge_msg or project.hook_on_merge_cat:
        do_open = True
    elif header_prop_fields or project.hook_on_merge_head or vivified:
        do_open = True
        headonly = True
    if (   header_prop_fields or vivified
        or project.hook_on_merge_head or project.hook_on_merge_msg
        or project.hook_on_merge_cat
    ):
        monitored = True

    # Should template catalog be opened too?
    do_open_template = False
    if header_prop_fields or vivified:
        do_open_template = True

    cat = None
    if do_msgmerge:
        # Create the temporary merged catalog.
        minasfz, refuzzy = 0.0, False
        cmppaths, fuzzex, minwnex = [], False, 0
        if branch_id == SUMMIT_ID:
            minasfz = project.merge_min_adjsim_fuzzy
            refuzzy = project.merge_rebase_fuzzy
            if project.compendium_on_merge:
                cmppaths.append(project.compendium_on_merge)
                fuzzex = project.compendium_fuzzy_exact
                minwnex = project.compendium_min_words_exact
        catalog_path_mod = catalog_path
        if vivified:
            if cmppaths:
                catalog_path_mod = "/dev/null"
            else:
                catalog_path_mod = tmp_path
                shutil.copyfile(template_path, tmp_path)

        getcat = do_open and not headonly
        ignpotdate = project.templates_dynamic
        cat = merge_pofile(catalog_path_mod, template_path, outpath=tmp_path,
                           wrapping=wrapping, fuzzymatch=fuzzy_merging,
                           minasfz=minasfz, refuzzy=refuzzy,
                           cmppaths=cmppaths, fuzzex=fuzzex, minwnex=minwnex,
                           getcat=getcat, monitored=monitored,
                           ignpotdate=ignpotdate,
                           quiet=True, abort=False)
        if not cat:
            warning(_("@info",
                      "Catalog '%(file1)s' not merged with "
                      "template '%(file2)s' due to errors on merging.",
                      file1=catalog_path_mod, file2=template_path))
            return
        elif not getcat:
            # Catalog not requested, so the return value is True
            # indicating that the merge succedded.
            cat = None

    else:
        # Copy current to temporary catalog, to be processed by hooks, etc.
        shutil.copyfile(catalog_path, tmp_path)

    # Save good time by opening the merged catalog only if necessary,
    # and only as much as necessary.

    # Open catalogs as necessary.
    if do_open:
        update_progress()
        if cat is None:
            cat = Catalog(tmp_path, monitored=monitored, wrapping=wrapping,
                          headonly=headonly)
        if do_open_template:
            tcat = Catalog(template_path, monitored=False, headonly=True)

    # Initialize header if the catalog has been vivified from template.
    if vivified:
        hdr = cat.header
        hdr.title = Monlist()
        hdr.copyright = u""
        hdr.license = u""
        hdr.author = Monlist()
        hdr.comment = Monlist()
        # Get the project ID from template;
        # if it gives default value, use catalog name instead.
        projid = tcat.header.get_field_value("Project-Id-Version")
        if not projid or "PACKAGE" in projid:
            projid = catalog_name
        hdr.set_field(u"Project-Id-Version", unicode(projid))
        rdate = time.strftime("%Y-%m-%d %H:%M%z")
        hdr.set_field(u"PO-Revision-Date", unicode(rdate))
        hdr.set_field(u"Last-Translator", unicode(project.vivify_w_translator))
        hdr.set_field(u"Language-Team", unicode(project.vivify_w_langteam))
        if project.vivify_w_language:
            hdr.set_field(u"Language", unicode(project.vivify_w_language),
                          after="Language-Team", reorder=True)
        hdr.set_field(u"Content-Type",
                      u"text/plain; charset=%s" % project.vivify_w_charset)
        hdr.set_field(u"Content-Transfer-Encoding", u"8bit")
        if project.vivify_w_plurals:
            hdr.set_field(u"Plural-Forms", unicode(project.vivify_w_plurals))
        else:
            hdr.remove_field(u"Plural-Forms")

    # Propagate requested header fields.
    if header_prop_fields:
        # Preserve order of the fields when collecting.
        fields = []
        for field in cat.header.field:
            if field[0] in header_prop_fields:
                fields.append(field)
        tfields = []
        for tfield in tcat.header.field:
            if tfield[0] in header_prop_fields:
                tfields.append(tfield)
        # Replace the field sequence if not equal to that of the template.
        if fields != tfields:
            for field in fields:
                cat.header.field.remove(field)
            for tfield in tfields:
                cat.header.field.append(tfield)

    # Set original instead of temporary file path -- hooks may expect it.
    if cat is not None:
        cat.filename = catalog_path

    # Execute header hooks.
    if project.hook_on_merge_head:
        exec_hook_head(branch_id, catalog_name, catalog_subdir,
                       cat.header, cat, project.hook_on_merge_head)

    # Execute message hooks.
    if project.hook_on_merge_msg:
        for msg in cat:
            exec_hook_msg(branch_id, catalog_name, catalog_subdir,
                          msg, cat, project.hook_on_merge_msg)

    # Execute catalog hooks.
    if project.hook_on_merge_cat:
        exec_hook_cat(branch_id, catalog_name, catalog_subdir,
                      cat, project.hook_on_merge_cat)

    # Synchronize merged catalog if it has been opened.
    if cat is not None:
        cat.filename = tmp_path # not to overwrite original file
        cat.sync(force=otherwrap)

    # Execute file hooks.
    if project.hook_on_merge_file:
        cat_name = os.path.basename(tmp_path)
        cat_name = cat_name[:cat_name.rfind(".po")]
        exec_hook_file(branch_id, cat_name, catalog_subdir, tmp_path,
                       project.hook_on_merge_file)

    # If there is any difference between merged and old catalog.
    if vivified or not filecmp.cmp(catalog_path, tmp_path):
        # Assert correctness of the merged catalog and move over the old.
        assert_system("msgfmt -c -o/dev/null %s " % tmp_path)
        added = False
        if vivified:
            added = True
            mkdirpath(os.path.dirname(catalog_path))
        shutil.move(tmp_path, catalog_path)

        # Add to version control if not already added.
        vcs = project.summit_vcs if SUMMIT_ID else project.branches_vcs
        if (    vcs
            and (    branch_id == SUMMIT_ID or
                 not project.bdict[branch_id].skip_version_control)
            and not vcs.is_versioned(catalog_path)
        ):
            if not vcs.add(catalog_path):
                warning(_("@info",
                          "Cannot add '%(file)s' to version control.",
                          file=catalog_path))

        if options.verbose:
            if added:
                actype = _("@item:intext action performed on a catalog",
                           "merged-added")
                report(".+   (%s) %s" % (actype, catalog_path))
            else:
                actype = _("@item:intext action performed on a catalog",
                           "merged")
                report(".    (%s) %s" % (actype, catalog_path))
        elif not options.quiet:
            if added:
                report(".+   %s" % catalog_path)
            else:
                report(".    %s" % catalog_path)

    # Remove the temporary merged catalog.
    if os.path.exists(tmp_path):
        os.remove(tmp_path)


# Put header fields in canonical form, for equality checking.
# Returns ordered list of (field name, field value).
def normhf (fields, excluded=[]):

    nfs = []

    for fnam, fval in fields:
        if fnam not in excluded:
            nfs.append((fnam, fval))
    nfs.sort()

    return nfs


# Remove all translator-related elements from the message.
def clear_msg (msg):

    msg.unfuzzy()
    msg.msgstr[:] = [u""] * len(msg.msgstr)
    msg.manual_comment[:] = []

    return msg


if __name__ == '__main__':
    exit_on_exception(main)
