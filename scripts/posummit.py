#!/usr/bin/env python
# -*- coding: UTF-8 -*-

from difflib import SequenceMatcher
import filecmp
import imp
import locale
from optparse import OptionParser
import os
import re
import shutil
import sys
import time

import fallback_import_paths

from pology.file.catalog import Catalog
from pology.file.header import Header
from pology.file.message import Message, MessageUnsafe
from pology.misc.fsops import str_to_unicode
from pology.misc.fsops import mkdirpath, assert_system, collect_system
from pology.misc.fsops import join_ncwd
from pology.misc.fsops import collect_paths_cmdline
from pology.misc.merge import merge_pofile
from pology.misc.monitored import Monpair, Monlist
from pology.misc.msgreport import report_on_msg
from pology.misc.report import report, error, warning
from pology.misc.report import init_file_progress
from pology.misc.stdcmdopt import add_cmdopt_incexc, add_cmdopt_filesfrom
from pology.misc.vcs import make_vcs
import pology.scripts.poascribe as ASC
import pology.scripts.porewrap as REW


SUMMIT_ID = "+" # must not start with word-character (\w)


def main ():

    locale.setlocale(locale.LC_ALL, "")

    # Setup options and parse the command line.
    usage = u"""
%prog [options] project_file lang_code op_mode [part_spec...]
""".strip()
    description = u"""
Handle PO catalogs spread across different branches in an integral fashion.
""".strip()
    version = u"""
%prog (Pology) experimental
Copyright © 2007 Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
""".strip()

    opars = OptionParser(usage=usage, description=description, version=version)
    opars.add_option(
        "--create",
        action="store_true", dest="do_create", default=False,
        help="allow creation of new summit catalogs")
    opars.add_option(
        "--force",
        action="store_true", dest="force", default=False,
        help="force some operations that are normally not advised")
    opars.add_option(
        "-v", "--verbose",
        action="store_true", dest="verbose", default=False,
        help="output more detailed progress info")
    opars.add_option(
        "-q", "--quiet",
        action="store_true", dest="quiet", default=False,
        help="output less detailed progress info")
    opars.add_option(
        "-a", "--asc-filter",
        action="store", dest="asc_filter", default=None,
        help="select a non-default ascription filter on scatter")
    add_cmdopt_filesfrom(opars)
    add_cmdopt_incexc(opars)

    (options, free_args) = opars.parse_args(str_to_unicode(sys.argv[1:]))

    if len(free_args) < 1:
        opars.error("must provide project file name")
    options.fproj = free_args.pop(0)
    if not os.path.isfile(options.fproj):
        error("file '%s' does not exist" % options.fproj)

    if len(free_args) < 1:
        opars.error("must provide language code")
    options.lang = free_args.pop(0)

    if len(free_args) < 1:
        opars.error("must provide operation mode")
    options.modes = free_args.pop(0).split(",")
    for mode in options.modes:
        if mode not in ("gather", "scatter", "merge"):
            error("unknown mode '%s'" % mode)

    # Could use some speedup.
    try:
        import psyco
        psyco.full()
    except ImportError:
        pass

    # Read project definition.
    project = Project(options)
    project.include(options.fproj)

    # Derive some project data.
    project = derive_project_data(project, options)

    # Collect partial processing specs and inclusion-exclusion test.
    res = collect_paths_cmdline(rawpaths=free_args,
                                incnames=options.include_names,
                                incpaths=options.include_paths,
                                excnames=options.exclude_names,
                                excpaths=options.exclude_paths,
                                filesfrom=options.files_from,
                                getsel=True)
    options.partspecs, options.partbids = collect_partspecs(project, res[0])
    options.selcatf = res[1]

    # Invoke the appropriate operations on collected bundles.
    for mode in options.modes:
        if options.verbose:
            report("-----> Processing mode: %s" % mode)
        if mode == "gather":
            summit_gather(project, options)
        elif mode == "scatter":
            summit_scatter(project, options)
        elif mode == "merge":
            summit_merge(project, options)


class Project (object):

    def __init__ (self, options):

        self.__dict__.update({
            "options" : options,

            "summit" : "",
            "branches" : [],
            "mappings" : [],

            "templates_lang" : "",

            "summit_wrap" : False,
            "summit_fine_wrap" : True,
            "summit_fuzzy_merging" : True,
            "branches_wrap" : True,
            "branches_fine_wrap" : True,
            "branches_fuzzy_merging" : True,

            "version_control" : "",

            "hook_on_scatter_msgstr" : [],
            "hook_on_scatter_msg" : [],
            "hook_on_scatter_cat" : [],
            "hook_on_scatter_file" : [],
            "hook_on_scatter_branch": [],
            "hook_on_gather_msg" : [],
            "hook_on_gather_cat" : [],
            "hook_on_gather_file" : [],
            "hook_on_gather_file_branch" : [],
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

        # Root dir for path resolution:
        # all paths considered relative to project file location.
        self._rootdir = os.path.dirname(self.options.fproj)

    def __setattr__ (self, att, val):

        # TODO: Do extensive checks.
        if self.locked and att not in self.__dict__:
            error("unknown project field '%s'" % att)
        self.__dict__[att] = val

    def resolve_path (self, path):

        new_path = path

        # Substitute language code.
        new_path = interpolate(new_path, {"lang" : self.options.lang})

        return new_path

    def resolve_path_rooted (self, path):

        new_path = path

        # Ordinary resolve.
        new_path = self.resolve_path(new_path)

        # Resolve relative paths as relative to current root dir.
        if not os.path.isabs(path):
            new_path = join_ncwd(self._rootdir, new_path)

        return new_path

    def include (self, path):

        backup_rootdir = self._rootdir
        self._rootdir = os.path.dirname(path)
        self.locked = True
        ifs = open(path)
        execdict = {"S" : self}
        exec ifs in execdict
        ifs.close()
        self.locked = False
        self._rootdir = backup_rootdir


def interpolate (text, dict):

    new_text = text
    for name, value in dict.items():
        new_text = new_text.replace("@%s@" % name, value)

    return new_text


def derive_project_data (project, options):

    p = project # shortcut

    # Create summit object from summit dictionary.
    class Summit: pass
    s = Summit()
    sd = p.summit
    s.id = SUMMIT_ID
    s.topdir = sd.pop("topdir", None)
    s.topdir_templates = sd.pop("topdir_templates", None)
    # Assert that there are no misnamed keys in the dictionary.
    if sd:
        error(  "unknown keys in specification of summit: %s"
              % ", ".join(sd.keys()))
    # Assert that all necessary fields in summit specification exist.
    if s.topdir is None:
        error("topdir not given for summit")
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
        b.by_lang = bd.pop("by_lang", None)
        if b.by_lang:
            b.by_lang = interpolate(b.by_lang, {"lang" : options.lang})
        b.scatter_create_filter = bd.pop("scatter_create_filter", None)
        b.skip_version_control = bd.pop("skip_version_control", False)
        b.merge_locally = bd.pop("merge_locally", False)

        ignores = bd.pop("ignores", [])

        def ignrx_to_func (rxstr):
            try:
                rx = re.compile(rxstr, re.U)
            except:
                error("invalid ignoring regular expression "
                      "in branch '%s': %s" % (b.id, rxstr))
            return lambda x: bool(rx.search(x))

        def chain_ignores ():
            ignfs = []
            for ign in ignores:
                if isinstance(ign, basestring):
                    ignfs.append(ignrx_to_func(ign))
                elif callable(ign):
                    ignfs.append(ign)
                else:
                    error("invalid ignoring type "
                        "in branch '%s': %s" % (b.id, ign))
            return lambda x: reduce(lambda s, y: s or y(x), ignfs, False)

        b.ignored = chain_ignores()

        # Assert that there are no misnamed keys in the dictionary.
        if bd:
            error(  "unknown keys in specification of branch '%s': %s"
                  % (b.id, ", ".join(bd.keys())))
    p.branches = branches

    # Assert that all necessary fields in branch specifications exist.
    p.branch_ids = []
    for branch in p.branches:
        if branch.id is None:
            error("branch with undefined id")
        if branch.id in p.branch_ids:
            error("non-unique branch id: %s" % branch.id)
        p.branch_ids.append(branch.id)
        if branch.topdir is None:
            error("topdir not given for branch '%s'" % branch.id)

    # Dictionary of branches by branch id.
    p.bdict = dict([(x.id, x) for x in p.branches])

    # Create the version control operator if given.
    if p.version_control:
        p.vcs = make_vcs(p.version_control.lower())
    else:
        p.vcs = None

    # Decide wrapping policies.
    class D: pass
    dummyopt = D()
    dummyopt.do_wrap = p.summit_wrap
    dummyopt.do_fine_wrap = p.summit_fine_wrap
    p.summit_wrapping = REW.select_field_wrapping(cmlopt=dummyopt)
    dummyopt.do_wrap = p.branches_wrap
    dummyopt.do_fine_wrap = p.branches_fine_wrap
    p.branches_wrapping = REW.select_field_wrapping(cmlopt=dummyopt)

    # Decide the extension of catalogs.
    if p.templates_lang and options.lang == p.templates_lang:
        options.catext = ".pot"
    else:
        options.catext = ".po"

    # Collect catalogs from branches.
    p.catalogs = {}
    for b in p.branches:
        p.catalogs[b.id] = collect_catalogs(b.topdir, options.catext,
                                            b.by_lang, b.ignored,
                                            project, options)
    # ...and from the summit.
    p.catalogs[SUMMIT_ID] = collect_catalogs(p.summit.topdir, options.catext,
                                             None, None, project, options)

    # Resolve ascription filter calls.
    for i in range(len(project.ascription_filters)):
        afname, afspec = project.ascription_filters[i]
        if isinstance(afspec, basestring):
            afcall = ASC.build_selector([afspec])
        elif isinstance(afspec, (tuple, list)):
            afcall = ASC.build_selector(afspec)
        elif callable(afspec):
            afcall = afspec
        else:
            error("Unknown type of definition for ascription filter '%s'."
                  % afname)
        project.ascription_filters[i] = (afname, afcall)

    # Link summit and ascription catalogs.
    if project.ascription_filters:
        tmp0 = [(x, y[0][0]) for x, y in p.catalogs[SUMMIT_ID].items()]
        tmp1 = [x[0] for x in tmp0]
        tmp2 = ASC.collect_configs_catpaths([x[1] for x in tmp0])
        tmp3 = zip([tmp2[0][0]] * len(tmp1), [x[1] for x in tmp2[0][1]])
        p.asc_configs_acatpaths = dict(zip(tmp1, tmp3))

    # Resolve non-default ascription filters from name to index.
    if options.asc_filter is not None:
        if not project.ascription_filters:
            error("project does not define any ascription filters")
        for i in range(len(project.ascription_filters)):
            if project.ascription_filters[i][0] == options.asc_filter:
                options.asc_filter = i
                break
        if i == len(project.ascription_filters):
            error("project does not define ascription filter '%s'"
                  % options.asc_filter)
    else:
        options.asc_filter = 0

    # Assure that summit catalogs are unique.
    for name, spec in p.catalogs[SUMMIT_ID].items():
        if len(spec) > 1:
            fstr = " ".join([x[0] for x in spec])
            error("non-unique summit catalog '%s': %s" % (name, fstr))

    # At scatter in template-summit mode, add to the collection of branch
    # catalogs any that should be newly created.
    p.add_on_scatter = {}
    if (    p.templates_lang and options.lang != p.templates_lang
        and "scatter" in options.modes):

        # Go through all mappings and collect branch names mapped to
        # summit catalogs per branch id and summit name.
        mapped_summit_names = {}
        for mapping in p.mappings:
            branch_id = mapping[0]
            branch_name = mapping[1]
            summit_names = mapping[2:]
            if not branch_id in mapped_summit_names:
                mapped_summit_names[branch_id] = {}
            for summit_name in summit_names:
                if not summit_name in mapped_summit_names[branch_id]:
                    mapped_summit_names[branch_id][summit_name] = []
                mapped_summit_names[branch_id][summit_name].append(branch_name)

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
                # If no mapped catalogs, use summit name as the branch name.
                if not branch_names:
                    branch_names.append(summit_name)

                # For each collected branch name, check if it exists in
                # branch templates and collect if not already collected.
                for branch_name in branch_names:

                    if (    branch_name not in p.catalogs[branch.id]
                        and branch_name in branch_templates):
                        # Assemble all branch catalog entries.
                        branch_catalogs = []
                        for template in branch_templates[branch_name]:
                            # Compose the branch catalog subdir and path.
                            subdir = template[1]
                            if branch.by_lang:
                                poname = branch.by_lang + ".po"
                            else:
                                poname = branch_name + ".po"
                            path = join_ncwd(branch.topdir, subdir, poname)

                            # Skip this catalog if excluded from creation on
                            # scatter, by filter on catalog name and subdir
                            # (False -> excluded).
                            scf = branch.scatter_create_filter
                            if scf and not scf(branch_name, subdir):
                                continue

                            # Add this file to catalog entry.
                            branch_catalogs.append((path, subdir))
                            # Record later initialization from template.
                            p.add_on_scatter[path] = template[0]

                        # Add branch catalog entry.
                        p.catalogs[branch.id][branch_name] = branch_catalogs

    # At merge in template-summit mode,
    # if automatic vivification of summit catalogs requested,
    # add to the collection of summit catalogs any that should be created.
    p.add_on_merge = {}
    if (    p.templates_lang and options.lang != p.templates_lang
        and "merge" in options.modes and p.vivify_on_merge
    ):
        # Collect all summit templates.
        summit_templates = collect_catalogs(p.summit.topdir_templates,
                                            ".pot", False, None,
                                            project, options)

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
    for branch_id in p.branch_ids:
        # - explicit
        for mapping in p.mappings:
            bid, bname = mapping[:2]
            summit_names = mapping[2:]
            p.direct_map[bid][bname] = summit_names
        # - implicit
        for branch_name in p.catalogs[branch_id]:
            if p.direct_map[branch_id][branch_name] == []:
                p.direct_map[branch_id][branch_name].append(branch_name)

    # Add or complain about missing summit catalogs.
    halting_pairs = []
    for branch_id in p.branch_ids:
        for branch_name in p.catalogs[branch_id]:
            summit_names = project.direct_map[branch_id][branch_name]
            for summit_name in summit_names:
                if summit_name not in p.catalogs[SUMMIT_ID]:
                    # Compose the path for the missing summit catalog.
                    # Default the subdir to that of the current branch,
                    # as it is the primary branch for this catalog.
                    branch_path, branch_dir = \
                        p.catalogs[branch_id][branch_name][0]
                    summit_subdir = branch_dir
                    if p.bdict[branch_id].by_lang:
                        summit_subdir = os.path.dirname(summit_subdir)
                    summit_path = join_ncwd(p.summit.topdir, summit_subdir,
                                            summit_name + options.catext)

                    # Add missing summit catalog if the mode is gather
                    # and creation is enabled.
                    # Record missing summit catalogs as halting the operation
                    # if the mode is gather and creation is not enabled.
                    if "gather" in options.modes:
                        if not options.do_create:
                            halting_pairs.append((branch_path, summit_path))

                        # Add summit catalog into list of existing catalogs;
                        # it will be created for real on gather.
                        p.catalogs[SUMMIT_ID][summit_name] = [(summit_path,
                                                               summit_subdir)]

    if halting_pairs:
        error("missing summit catalogs per branch catalog:\n"
              "%s" % "\n".join("%s --> %s" % x for x in halting_pairs))

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
                else:
                    for bpath, bdir in p.catalogs[branch_id][branch_name]:
                        warning("no summit catalog for branch catalog '%s'"
                                % bpath)

    # Fill in defaults for missing fields in hook specs.
    for attr in p.__dict__:
        if attr.startswith("hook_"):
            p.__dict__[attr] = hook_fill_defaults(p.__dict__[attr])

    return p


def split_path_in_project (project, path):

    # Split the path into directory and catalog name.
    if os.path.isfile(path):
        if not path.endswith((".po", ".pot")):
            error("Non-PO file '%(path)s' given as project catalog."
                  % dict(path=path))
        dirpath = os.path.dirname(path)
        basename = os.path.basename(path)
        catname = basename[:basename.rfind(".")]
    elif os.path.isdir(path):
        dirpath = path
        catname = None

    # Deduce project branch and relative path of the directory within it.
    bid = None
    breldir = None
    dirpath = os.path.abspath(dirpath)
    for b in [project.summit] + project.branches:
        broot = os.path.abspath(b.topdir)
        if dirpath.startswith(broot):
            cbreldir = dirpath[len(broot):]
            if not cbreldir or cbreldir.startswith(os.path.sep):
                if not cbreldir:
                    cbreldir = None
                else:
                    cbreldir = cbreldir[len(os.path.sep):]
                bid = b.id
                breldir = cbreldir
                break
    if not bid:
        error("Path '%(path)s' is not covered by the project."
              % dict(path=path))

    return bid, breldir, catname


def collect_partspecs (project, specargs):

    partbids = []
    partspecs = {}
    for specarg in specargs:
        # If the partial specification is a valid path,
        # convert it to operation target.
        if os.path.exists(specarg):
            bid, breldir, catname = split_path_in_project(project, specarg)
            if catname:
                optarget = bid + ":" + catname
            elif breldir:
                optarget = bid + ":" + breldir + os.path.sep
            else:
                optarget = bid + ":"
        else:
            optarget = specarg

        lst = optarget.split(":", 1)
        if len(lst) < 2:
            fdname, = lst
            bid = None
        else:
            bid, fdname = lst
            if bid not in project.branch_ids and bid != SUMMIT_ID:
                error("Branch '%s' not defined in the project." % bid)
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
def collect_catalogs (topdir, catext, by_lang, ignored, project, options):

    catalogs = {}
    topdir = os.path.normpath(topdir)
    for root, dirs, files in os.walk(topdir):
        for file in files:
            catn = ""
            fpath = join_ncwd(root, file)
            if by_lang is None or catext == ".pot":
                if file.endswith(catext):
                    catn = file[0:file.rfind(".")]
                    spath = root[len(topdir) + 1:]
            else:
                if file == by_lang + ".po": # cannot be .pot, so no catext
                    mroot = root
                    if os.path.basename(root) == "po":
                        mroot = os.path.dirname(root)
                    catn = os.path.basename(mroot)
                    spath = os.path.dirname(mroot)[len(topdir) + 1:]

            if catn:
                fpath = os.path.normpath(fpath)
                spath = os.path.normpath(spath)
                if not ignored or not ignored(fpath):
                    if catn not in catalogs:
                        catalogs[catn] = []
                    catalogs[catn].append((fpath, spath))

    for catpaths in catalogs.values():
        if len(catpaths) > 1:
            catpaths.sort(key=lambda x: x[0])

    return catalogs


def summit_gather (project, options):

    if (    project.templates_lang and options.lang != project.templates_lang
        and not options.force):
        error(  "template summit mode: gathering possible only on '%s' "
                "(if this is the very creation of the '%s' summit, "
                "run with: --create --force)"
              % (project.templates_lang, options.lang))

    # Collect names of summit catalogs to gather.
    summit_names = select_summit_names(project, options)

    # Setup progress indicator.
    upprog = lambda x: x
    if not options.verbose:
        catpaths = [project.catalogs[SUMMIT_ID][x][0][0] for x in summit_names]
        upprog = init_file_progress(catpaths, addfmt="Gathering: %s")

    # Gather all selected catalogs.
    for name in summit_names:
        catpath = project.catalogs[SUMMIT_ID][name][0][0]
        if options.verbose:
            report("Gathering %s ..." % catpath)
        upprogc = lambda: upprog(catpath)
        summit_gather_single(name, project, options, update_progress=upprogc)
    upprog()


def summit_scatter (project, options):

    if project.templates_lang and options.lang == project.templates_lang:
        error(  "template summit mode: scattering not possible on '%s'"
              % project.templates_lang)

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
        error("Missing necessary summit catalogs: %s"
              % " ".join(missing_in_summit))

    # Setup progress indicator.
    upprog = lambda x: x
    if not options.verbose:
        catpaths = [x[3] for x in scatter_specs if x[1]]
        upprog = init_file_progress(catpaths, addfmt="Scattering: %s")

    # Scatter to branch catalogs.
    for scatter_spec in scatter_specs:
        branch_id, catpath = scatter_spec[0], scatter_spec[3]
        if catpath is not None:
            if options.verbose:
                report("Scattering to %s ..." % catpath)
            upprogc = lambda: upprog(catpath)
            summit_scatter_single(*(scatter_spec + (project, options, upprogc)))
        else:
            # Apply post-scatter hooks.
            if options.verbose:
                report("Applying post-hook to branch %s ..." % branch_id)
            exec_hook_branch(branch_id, project.hook_on_scatter_branch)
    upprog()


def summit_merge (project, options):

    if project.templates_lang and options.lang == project.templates_lang:
        error(  "template summit mode: merging not possible on '%s'"
              % project.templates_lang)

    merge_specs = []

    # Select branches to merge.
    if not options.partbids:
        branch_ids = project.branch_ids + [SUMMIT_ID]
    else:
        branch_ids = options.partbids

    # Merge template summit selected and exists.
    if SUMMIT_ID in branch_ids and project.summit.topdir_templates:
        branch_ids.remove(SUMMIT_ID)

        # Collect names of summit catalogs to merge.
        summit_names = select_summit_names(project, options)

        # Collect template catalogs to use.
        template_catalogs = collect_catalogs(project.summit.topdir_templates,
                                             ".pot", None, None,
                                             project, options)

        # Collect data for summit catalogs to merge.
        for name in summit_names:
            if name not in template_catalogs:
                warning("no template for summit catalog '%s'" % name)
                continue
            summit_path, summit_subdir = project.catalogs[SUMMIT_ID][name][0]
            template_path = template_catalogs[name][0][0]
            merge_specs.append((SUMMIT_ID, name, summit_subdir,
                                summit_path, template_path,
                                project.summit_wrapping,
                                project.summit_fuzzy_merging))

    # Merge selected branches.
    for branch_id in branch_ids:
        branch = project.bdict[branch_id]

        # Skip branch if local merging not desired, or no templates defined.
        if (not branch.merge_locally or branch.topdir_templates is None):
            continue

        # Collect branch catalogs to merge.
        branch_catalogs = select_branch_catalogs(branch_id, project, options)

        # Collect template catalogs to use.
        template_catalogs = collect_catalogs(branch.topdir_templates, ".pot",
                                             branch.by_lang, branch.ignored,
                                             project, options)

        # Collect data for branch catalogs to merge.
        for name, branch_path, branch_subdir in branch_catalogs:
            if not os.path.isfile(branch_path):
                # Catalog has been selected due to another operation mode,
                # which can create catalogs from scratch.
                continue
            if not name in template_catalogs:
                warning("no template for branch catalog '%s'" % branch_path)
                continue
            exact = False
            for template_path, template_subdir in template_catalogs[name]:
                if template_subdir == branch_subdir:
                    exact = True
                    break
            if not exact:
                warning("no exact template for branch catalog '%s'" % branch_path)
                continue
            merge_specs.append((branch_id, name, branch_subdir,
                                branch_path, template_path,
                                project.branches_wrapping,
                                project.branches_fuzzy_merging))

    # Setup progress indicator.
    upprog = lambda x: x
    if not options.verbose:
        catpaths = [x[3] for x in merge_specs]
        upprog = init_file_progress(catpaths, addfmt="Merging: %s")

    # Merge catalogs.
    for merge_spec in merge_specs:
        catpath = merge_spec[3]
        if options.verbose:
            report("Merging %s ..." % catpath)
        upprogc = lambda: upprog(catpath)
        summit_merge_single(*(merge_spec + (project, options, upprogc)))
    upprog()


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
                        error(  "no catalogs in branch '%s' subdir '%s'" \
                              % (branch_id, sel_subdir))
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
                        error(  "no catalog named '%s' in branch '%s'" \
                            % (sel_name, branch_id))

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
                        error("no summit catalog named '%s'" % sel_name)
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
                            error("no summit directory named '%s'" % sel_subdir)
                    else: # single name
                        sel_name = part_spec
                        spec = project.catalogs[SUMMIT_ID].get(sel_name)
                        if not sel_name:
                            error("no summit catalog named '%s'" % sel_name)
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
                            error("no directory named '%s' in branch '%s'"
                                  % (sel_subdir, branch_id))
                    else: # single name
                        sel_name = part_spec
                        spec = project.catalogs[branch_id].get(sel_name)
                        if not spec:
                            error("no catalog named '%s' in branch '%s'"
                                  % (sel_name, branch_id))
                        for path, subdir in spec:
                            if options.selcatf(path):
                                summit_names.extend(
                                    project.direct_map[branch_id][sel_name])
                            break

    # Make names unique and sort by path.
    summit_names = list(set(summit_names))
    summit_names.sort(key=lambda x: project.catalogs[SUMMIT_ID][x][0][0])

    return summit_names


def summit_gather_single (summit_name, project, options,
                          phony=False, pre_summit_names=[],
                          update_progress=(lambda: None)):

    update_progress()

    summit_path = project.catalogs[SUMMIT_ID][summit_name][0][0]
    summit_subdir = project.catalogs[SUMMIT_ID][summit_name][0][1]

    fresh_cat = Catalog("", wrapping=project.summit_wrapping, create=True)
    fresh_cat.filename = summit_path

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
            error("internal: phony-gather on summit catalog to be removed")

        # Remove by version control, if any.
        if project.vcs:
            if not project.vcs.remove(summit_path):
                warning(  "cannot remove '%s' from version control"
                        % summit_path)
        # If not removed by version control, plainly delete.
        if os.path.isfile(summit_path):
            os.unlink(summit_path)
            if os.path.isfile(summit_path):
                warning("cannot remove '%s' from disk" % summit_path)

        if not os.path.isfile(summit_path):
            if options.verbose:
                report("-   (gathered-removed) %s  %s" % summit_path)
            elif not options.quiet:
                report("-    %s" % summit_path)

        # Skip the rest, nothing to gather.
        return fresh_cat

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

                # Apply hooks to all branch catalog messages here,
                # as they may modify message keys.
                if project.hook_on_gather_msg:
                    for msg in branch_cat:
                        update_progress()
                        exec_hook_msg(branch_id, branch_name, subdir,
                                      msg, branch_cat,
                                      project.hook_on_gather_msg)
                    # Sync only message map, do not write catalog on disk.
                    branch_cat.sync_map()

                bcat_pscats[branch_id].append((branch_cat, dep_summit_cats))

    # Select primary branch catalog and list of all catalogs with branch ids.
    prim_branch_cat = None
    branch_ids_cats = []
    for branch_id in src_branch_ids:
        for branch_cat, dep_summit_cats in bcat_pscats[branch_id]:
            if prim_branch_cat is None:
                prim_branch_cat = branch_cat
            branch_ids_cats.append((branch_id, branch_cat))

    # Gather messages through branch catalogs.
    # Add summit messages to a fresh catalog, such that if no
    # summit messages were changed by themselves, but their order changed,
    # the fresh catalog will still replace the original.
    for branch_id in src_branch_ids:
        for branch_cat, dep_summit_cats in bcat_pscats[branch_id]:
            is_primary = branch_cat is prim_branch_cat
            summit_gather_single_bcat(branch_id, branch_cat, branch_ids_cats,
                                      fresh_cat, dep_summit_cats, is_primary,
                                      project, options, update_progress)

    # If phony-gather, stop here and return fresh catalog for reference.
    if phony:
        return fresh_cat

    # If there were any modified messages, or their order changed,
    # replace the original with the fresh catalog.
    summit_cat = Catalog(summit_path, wrapping=project.summit_wrapping,
                         create=True)
    summit_created = summit_cat.created() # preserve created state
    replace = False
    for pos in range(len(fresh_cat)):
        update_progress()
        old_pos = summit_cat.find(fresh_cat[pos])
        if pos != old_pos:
            replace = True
        if old_pos >= 0:
            if fresh_cat[pos] != summit_cat[old_pos]:
                replace = True
            else:
                # Replace newly gathered with old message,
                # to avoid reformatting.
                fresh_cat[pos] = summit_cat[old_pos]
    if replace:
        # Set path and header to that of the original.
        fresh_cat.filename = summit_path
        fresh_cat.header = summit_cat.header
        summit_cat = fresh_cat

    # Update the summit header.
    summit_gather_single_header(summit_cat, prim_branch_cat, branch_ids_cats,
                                project, options)

    # Apply hooks to the summit catalog.
    exec_hook_cat(SUMMIT_ID, summit_cat.name, summit_subdir, summit_cat,
                  project.hook_on_gather_cat)

    # Sync to disk.
    if summit_cat.sync():

        # Apply hooks to summit catalog file.
        exec_hook_file(SUMMIT_ID, summit_cat.name, summit_subdir,
                       summit_cat.filename, project.hook_on_gather_file)

        added = False
        if summit_created:
            added = True
        # Add to version control.
        if project.vcs and not project.vcs.is_versioned(summit_cat.filename):
            if not project.vcs.add(summit_cat.filename):
                warning(  "cannot add '%s' to version control"
                        % summit_cat.filename)
            else:
                added = True

        branch_paths = []
        for branch_id, branch_cat in branch_ids_cats:
            branch_paths.append(branch_cat.filename)
        paths_str = " ".join(branch_paths)

        if options.verbose:
            if added:
                report(">+   (gathered-added) %s  %s" % (summit_cat.filename,
                                                         paths_str))
            else:
                report(">    (gathered) %s  %s" % (summit_cat.filename,
                                                   paths_str))
        elif not options.quiet:
            if added:
                report(">+   %s  %s" % (summit_cat.filename, paths_str))
            else:
                report(">    %s  %s" % (summit_cat.filename, paths_str))

    return summit_cat


def summit_gather_single_bcat (branch_id, branch_cat, branch_ids_cats,
                               summit_cat, dep_summit_cats, is_primary,
                               project, options, update_progress):

    # Go through messages in the branch catalog, merging them with
    # existing summit messages, or collecting for later insertion.
    # Do not insert new messages immediately, as source references may be
    # updated by merging, which reflects on heuristic insertion.
    # Ignore messages present in dependent summit catalogs.
    msgs_to_insert = set()
    for msg in branch_cat:
        update_progress()

        # Do not gather obsolete messages.
        if msg.obsolete:
            continue

        # Normalizations when gathering templates,
        # in case extraction tool needs to have its sanity checked.
        if options.lang == project.templates_lang:
            # There should be no manual comments,
            # convert them to automatic if present.
            if msg.manual_comment:
                for cmnt in msg.manual_comment:
                    msg.auto_comment.append(cmnt)
                msg.manual_comment = type(msg.manual_comment)()
            # There should be no translations, discard if any.
            for i in range(len(msg.msgstr)):
                msg.msgstr[i] = u""

        # Do not gather messages belonging to depending summit catalogs.
        in_dep = False
        for dep_summit_cat in dep_summit_cats:
            if msg in dep_summit_cat:
                in_dep = True
                break
        if in_dep:
            continue

        # Merge the branch message or collect for insertion.
        summit_msg = summit_cat.get(msg)
        if summit_msg is not None:
            # Merge the message.
            gather_merge_msg(summit_msg, msg)
            # Update automatic comments.
            summit_override_auto(summit_msg, msg, branch_id, is_primary)
            # Equip any new summit tags to the merged message.
            summit_set_tags(summit_msg, branch_ids_cats, project)
        else:
            # Record branch message, to insert later.
            msgs_to_insert.add(msg)

    # If there are any messages awaiting insertion, heuristically insert them.
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
        fnsyn = fuzzy_match_source_files(branch_cat, [summit_cat])

        # Prepare messages for insertion into summit.
        summit_msg_by_msg = {}
        for msg in msgs_to_insert:
            update_progress()
            summit_msg = Message(msg)
            summit_set_tags(summit_msg, branch_ids_cats, project)
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
        error("internal: cannot merge messages with different keys")

    # Plural always overrides non-plural, regardless of summit/branch state.
    if summit_msg.msgid_plural is None and msg.msgid_plural is not None:
        if msg.manual_comment:
            summit_msg.manual_comment = Monlist(msg.manual_comment)
        if msg.fuzzy:
            summit_msg.msgctxt_previous = msg.msgctxt_previous
            summit_msg.msgid_previous = msg.msgid_previous
            summit_msg.msgid_plural_previous = msg.msgid_plural_previous
        summit_msg.msgid_plural = msg.msgid_plural
        summit_msg.msgstr = Monlist(msg.msgstr)
        summit_msg.fuzzy = msg.fuzzy

    else:
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


def summit_gather_single_header (summit_cat, prim_branch_cat, branch_ids_cats,
                                 project, options):

    # Update template creation date
    # if there were any changes to the catalog otherwise.
    if summit_cat.modcount:
        summit_cat.header.set_field(u"POT-Creation-Date", ASC.format_datetime())

    # Copy over standard fields from the primary branch catalog.
    for fname in [x[0] for x in Header().field]:
        if fname == "POT-Creation-Date":
            continue # handled specially above
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
    branch_cat = Catalog(branch_path_mod, wrapping=project.branches_wrapping)
    summit_cats = [Catalog(x) for x in summit_paths]

    # Open ascription catalogs.
    if project.ascription_filters:
        aconfs_acats = {}
        for summit_cat in summit_cats:
            aconf, acatpath = project.asc_configs_acatpaths[summit_cat.name]
            acat = Catalog(acatpath, monitored=False, create=True)
            aconfs_acats[summit_cat.name] = (aconf, acat)

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
        if project.hook_on_gather_msg:
            branch_msg_lkp = MessageUnsafe(branch_msg)
            exec_hook_msg(branch_id, branch_name, branch_subdir,
                          branch_msg_lkp, branch_cat,
                          project.hook_on_gather_msg)

        # Find first summit catalog which has this message translated.
        summit_msg = None
        for summit_cat in summit_cats:
            if branch_msg_lkp in summit_cat:
                summit_msg = summit_cat[branch_msg_lkp]
                if summit_msg.obsolete:
                    summit_msg = None
                else:
                    break

        if summit_msg is None:
            report_on_msg("message not in the summit", branch_msg, branch_cat)
            continue

        if (    project.ascription_filters and not options.force
            and do_scatter(summit_msg, branch_msg)
        ):
            aconf, acat = aconfs_acats[summit_cat.name]
            hfilter = project.ascription_history_filter
            ahist = ASC.asc_collect_history(summit_msg, acat, aconf,
                                            nomrg=True, hfilter=hfilter)
            afname, afilter = project.ascription_filters[options.asc_filter]
            if not afilter(summit_msg, summit_cat, ahist, aconf):
                asc_stopped += 1
                continue

        if summit_msg.translated:
            msgs_translated += 1
        msg_links.append((branch_msg, summit_msg, summit_cat))

    if asc_stopped > 0:
        warning("%s: %d messages stopped by ascription filter"
                % (branch_path, asc_stopped))

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
                if (   (summit_msg.msgid_plural is None)
                    == (branch_msg.msgid_plural is None)
                ):
                    # Both messages have same plurality.
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

                elif (    summit_msg.msgid_plural is not None
                      and branch_msg.msgid_plural is None
                ):
                    # Summit is plural, branch is not: means that branch is
                    # singular, so copy plural form for n==1.
                    index = summit_cat.plural_index(1)
                    branch_msg.msgstr[0] = exec_hook_msgstr(
                        branch_id, branch_name, branch_subdir,
                        summit_msg.msgstr[index], summit_msg, summit_cat,
                        project.hook_on_scatter_msgstr)
                    branch_msg.unfuzzy()
                    branch_msg.manual_comment = summit_msg.manual_comment
                    scattered_branch_msgs.add(branch_msg)

                else:
                    # Branch is plural, summit is not: should not happen.
                    report(   "%s: summit message needs plurals: {%s}"
                           % (branch_path, branch_msg.msgid))

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

        # Add to version control if new file.
        if (    new_from_template and project.vcs
            and not project.bdict[branch_id].skip_version_control
        ):
            if not project.vcs.add(branch_cat.filename):
                warning(  "cannot add '%s' to version control"
                        % branch_cat.filename)

        paths_str = " ".join(summit_paths)
        if options.verbose:
            if new_from_template:
                report("<+   (scattered-added) %s  %s" % (branch_cat.filename,
                                                          paths_str))
            else:
                report("<    (scattered) %s  %s" % (branch_cat.filename,
                                                    paths_str))
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


if sys.version_info[:2] >= (2, 5):
    import hashlib
    _makehash = hashlib.md5
else:
    import md5
    _makehash = md5.new

def msg_ident (msg):

    h = _makehash()
    h.update(msg.key.encode("UTF-8"))
    return "_" + h.hexdigest() + "_"


# NOTE: If changed, also change in stats sieve.
#_summit_tag_ident = "+="
_summit_tag_branchid = "+>"
_summit_tags = (
    #_summit_tag_ident,
    _summit_tag_branchid,
)

def summit_set_tags (msg, bids_cats, project):

    ## Add hash ident.
    #ident = msg_ident(msg)
    #set_summit_comment(msg, _summit_tag_ident, ident)

    # Get branch IDs of any branch catalog which contains this message.
    branch_ids = []
    for bid, bcat in bids_cats:
        if msg in bcat:
            branch_ids.append(bid)

    # Order branch IDs by the global order, to preserve priorites.
    ordered_branch_ids = []
    for branch_id in project.branch_ids:
        if branch_id in branch_ids:
            ordered_branch_ids.append(branch_id)

    # Set branch IDs.
    set_summit_comment(msg, _summit_tag_branchid,
                       " ".join(ordered_branch_ids))


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

    tmp_dir = os.path.join("/tmp", "summit-merge-%d" % os.getpid())
    mkdirpath(tmp_dir)
    tmp_path = os.path.join(tmp_dir, os.path.basename(catalog_path))

    # Whether to create pristine catalog from template.
    vivified = catalog_path in project.add_on_merge

    # Skip calling msgmerge if template creation dates are equal.
    do_msgmerge = True
    if not vivified and not options.force:
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
    if otherwrap or project.hook_on_merge_cat:
        do_open = True
    elif header_prop_fields or project.hook_on_merge_head or vivified:
        do_open = True
        headonly = True
    if (   header_prop_fields or vivified
        or project.hook_on_merge_cat or project.hook_on_merge_head
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
        cat = merge_pofile(catalog_path_mod, template_path, outpath=tmp_path,
                           wrapping=wrapping, fuzzymatch=fuzzy_merging,
                           minasfz=minasfz, refuzzy=refuzzy,
                           cmppaths=cmppaths, fuzzex=fuzzex, minwnex=minwnex,
                           getcat=getcat, monitored=monitored,
                           quiet=True, abort=True)
        if not getcat:
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
        if (    project.vcs
            and (    branch_id == SUMMIT_ID or
                 not project.bdict[branch_id].skip_version_control)
            and not project.vcs.is_versioned(catalog_path)
        ):
            if not project.vcs.add(catalog_path):
                warning(  "cannot add '%s' to version control"
                        % catalog_path)

        if options.verbose:
            if added:
                report(".+   (merged-added) %s" % catalog_path)
            else:
                report(".    (merged) %s" % catalog_path)
        elif not options.quiet:
            if added:
                report(".+   %s" % catalog_path)
            else:
                report(".    %s" % catalog_path)
    else:
        # Remove the temporary merged catalog.
        os.unlink(tmp_path)


# FIXME: Export as library function, used by poediff too.
# For each source file mentioned in the test catalog, if it is not mentioned
# in any of the other catalogs, check for any different, but possibly only
# renamed/moved source files from the other catalogs (if the these contain
# the test catalog itself, it is skipped automatically).
# The heuristics uses number of messages common to both files
# to ascertain the possibility. The amount of commonality can be set.
# Return the dictionary of possible "synonyms", i.e. possible other names
# for each of the determined matches.
def fuzzy_match_source_files (cat, other_cats, minshare=0.7):

    syns = {}

    # Collect all own sources, to avoid fuzzy matching for them.
    ownfs = {}
    for msg in cat:
        for file, lno in msg.source:
            ownfs[file] = True

    for ocat in other_cats:
        if cat is ocat:
            continue

        fcnts = {}
        ccnts = {}
        for msg in cat:
            p = ocat.find(msg)
            if p <= 0:
                continue
            omsg = ocat[p]

            for file, lno in msg.source:
                if file not in fcnts:
                    fcnts[file] = 0.0
                    ccnts[file] = {}
                # Weigh each message disproportionally to the number of
                # files it appears in (i.e. the sum of counts == 1).
                fcnts[file] += 1.0 / len(msg.source)
                counted = {}
                for ofile, olno in omsg.source:
                    if ofile not in ownfs and ofile not in counted:
                        if ofile not in ccnts[file]:
                            ccnts[file][ofile] = 0.0
                        ccnts[file][ofile] += 1.0 / len(omsg.source)
                        counted[ofile] = True

        # Select match groups.
        fuzzies = {}
        for file, fcnt in fcnts.iteritems():
            shares = []
            for ofile, ccnt in ccnts[file].iteritems():
                share = ccnt / (fcnt + 1.0) # tip a bit to avoid fcnt of 0.x
                if share >= minshare:
                    shares.append((ofile, share))
            if shares:
                shares.sort(key=lambda x: x[1]) # not necessary atm
                fuzzies[file] = [f for f, s in shares]

        # Update the dictionary of synonyms.
        for file, fuzzfiles in fuzzies.iteritems():
            group = [file] + fuzzfiles
            for file in group:
                if file not in syns:
                    syns[file] = []
                for syn in group:
                    if file != syn and syn not in syns[file]:
                        syns[file].append(syn)
                if not syns[file]:
                    syns.pop(file)

    return syns


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
    main()
