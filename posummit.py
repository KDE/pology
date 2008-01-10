#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import pology.misc.wrap as wrap
from pology.file.catalog import Catalog

import sys, os, imp, shutil, re
from optparse import OptionParser
import md5
import filecmp

SUMMIT_ID = "+"

def main ():

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
        "--no-psyco",
        action="store_false", dest="use_psyco", default=True,
        help="do not try to use Psyco specializing compiler")
    opars.add_option(
        "-v", "--verbose",
        action="store_true", dest="verbose", default=False,
        help="output more detailed progress info")
    (options, free_args) = opars.parse_args()

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
        if mode not in ("gather", "scatter", "purge", "reorder", "merge"):
            error("unknown mode '%s'" % mode)

    # Collect partial processing specs.
    options.branches = []
    options.partspecs = {}
    for part_spec in free_args:
        lst = part_spec.split(":")
        if len(lst) < 2:
            lst.insert(0, SUMMIT_ID)
        branch_id, part_spec = lst
        if branch_id not in options.branches:
            options.branches.append(branch_id)
        if part_spec:
            if not branch_id in options.partspecs:
                options.partspecs[branch_id] = []
            options.partspecs[branch_id].append(part_spec)

    # Could use some speedup.
    if options.use_psyco:
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

    # Invoke the appropriate operations on collected bundles.
    for mode in options.modes:
        if options.verbose:
            print "-----> Processing mode: %s" % mode
        if mode == "gather":
            summit_gather(project, options)
        elif mode == "scatter":
            summit_scatter(project, options)
        elif mode == "purge":
            summit_purge(project, options)
        elif mode == "reorder":
            summit_reorder(project, options)
        elif mode == "merge":
            summit_merge(project, options)


def error (msg, code=1):

    cmdname = os.path.basename(sys.argv[0])
    sys.stderr.write("%s: error: %s\n" % (cmdname, msg))
    sys.exit(code)


class Project (object):

    def __init__ (self, options):

        self.__dict__.update({
            "options" : options,

            "summit" : "",
            "branches" : [],
            "mappings" : [],

            "templates_lang" : "",
            "templates_summit" : "",

            "summit_unwrap" : True,
            "summit_split_tags" : True,
            "branches_unwrap" : False,
            "branches_split_tags" : True,

            "hook_on_scatter_msgstr" : [],
            "hook_on_scatter_file" : [],
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
            new_path = os.path.normpath(os.path.join(self._rootdir, new_path))

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

    # Decide the template summit path if in template summit mode and
    # the path is not given explicitely.
    if p.templates_lang and not p.templates_summit:
        if options.lang != p.templates_lang:
            # Current operation is for one of particular language summits,
            # derive the template summit path by replacing the language code.
            p.templates_summit = re.sub(r"\b%s\b" % options.lang,
                                        p.templates_lang, p.summit, 1)
        else:
            # Current operation is for the template summit itself,
            # just copy over the language summit path.
            p.templates_summit = p.summit

    # Decide the extension of catalogs.
    if p.templates_lang and options.lang == p.templates_lang:
        options.catext = ".pot"
        # Reroute summit path to template summit path has been set.
        p.summit = p.templates_summit
    else:
        options.catext = ".po"

    # Equip all branches missing by_lang field with by_lang=None.
    # If by_lang is not missing, interpolate for @lang@.
    mod_branches = []
    for branch_spec in p.branches:
        if len(branch_spec) < 3:
            by_lang = None
        else:
            by_lang = interpolate(branch_spec[2], {"lang" : options.lang})
        mod_branches.append((branch_spec[0], branch_spec[1], by_lang))
    p.branches = mod_branches

    # Collect catalogs from branches.
    p.catalogs = {}
    for branch_id, branch_dir, by_lang in p.branches:
        p.catalogs[branch_id] = collect_catalogs(branch_dir, options.catext,
                                                 by_lang, project, options)
    # ...and from the summit.
    p.catalogs[SUMMIT_ID] = collect_catalogs(p.summit, options.catext,
                                             None, project, options)

    # Assure that summit catalogs are unique.
    for name, spec in p.catalogs[SUMMIT_ID].items():
        if len(spec) > 1:
            fstr = " ".join([x[0] for x in spec])
            error("non-unique summit catalog '%s': %s" % (name, fstr))

    # Convenient dictionary views of mappings.
    # - direct: branch_id->branch_name->summit_name
    # - part inverse: branch_id->summit_name->branch_name
    # - full inverse: summit_name->branch_id->branch_name
    p.direct_map = {}
    p.part_inverse_map = {}
    p.full_inverse_map = {}
    branch_ids = [x[0] for x in p.branches]

    # Initialize mappings.
    # - direct:
    for branch_id in branch_ids:
        p.direct_map[branch_id] = {}
        for branch_name in p.catalogs[branch_id]:
            p.direct_map[branch_id][branch_name] = []
    # - part inverse:
    for branch_id in branch_ids:
        p.part_inverse_map[branch_id] = {}
        for summit_name in p.catalogs[SUMMIT_ID]:
            p.part_inverse_map[branch_id][summit_name] = []
    # - full inverse:
    for summit_name in p.catalogs[SUMMIT_ID]:
        p.full_inverse_map[summit_name] = {}
        for branch_id in branch_ids:
            p.full_inverse_map[summit_name][branch_id] = []

    # Add explicit mappings.
    for mapping in p.mappings:
        branch_id = mapping[0]
        branch_name = mapping[1]
        summit_names = mapping[2:]
        # - direct:
        p.direct_map[branch_id][branch_name] = summit_names
        # - part inverse:
        for summit_name in summit_names:
            if summit_name not in p.part_inverse_map[branch_id]:
                p.part_inverse_map[branch_id][summit_name] = []
            p.part_inverse_map[branch_id][summit_name].append(branch_name)
        # - full inverse:
        for summit_name in summit_names:
            if summit_name not in p.full_inverse_map:
                p.full_inverse_map[summit_name] = {}
            if branch_id not in p.full_inverse_map[summit_name]:
                p.full_inverse_map[summit_name][branch_id] = []
            p.full_inverse_map[summit_name][branch_id].append(branch_name)

    # Add implicit mappings.
    # - direct:
    for branch_id in branch_ids:
        for branch_name in p.catalogs[branch_id]:
            if p.direct_map[branch_id][branch_name] == []:
                p.direct_map[branch_id][branch_name].append(branch_name)
    # - part inverse:
    for branch_id in branch_ids:
        for summit_name in p.catalogs[SUMMIT_ID]:
            if p.part_inverse_map[branch_id][summit_name] == [] \
            and summit_name in p.catalogs[branch_id]:
                p.part_inverse_map[branch_id][summit_name].append(summit_name)
    # - full inverse:
    for summit_name in p.catalogs[SUMMIT_ID]:
        for branch_id in branch_ids:
            if p.full_inverse_map[summit_name][branch_id] == [] \
            and summit_name in p.catalogs[branch_id]:
                p.full_inverse_map[summit_name][branch_id].append(summit_name)

    # Fill in defaults for missing fields in hook specs.
    p.hook_on_scatter_msgstr = hook_fill_defaults(p.hook_on_scatter_msgstr)
    p.hook_on_scatter_file = hook_fill_defaults(p.hook_on_scatter_file)

    return p


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
def collect_catalogs (topdir, catext, by_lang, project, options):

    catalogs = {}
    topdir = os.path.normpath(topdir)
    for root, dirs, files in os.walk(topdir):
        for file in files:
            catn = ""
            fpath = os.path.join(root, file)
            if by_lang is None or catext == ".pot":
                if file.endswith(catext):
                    catn = file[0:file.rfind(".")]
                    spath = root[len(topdir) + 1:]
            else:
                if file == by_lang + ".po": # cannot be .pot, so no catext
                    catn = os.path.basename(root)
                    spath = os.path.dirname(root)[len(topdir) + 1:]

            if catn:
                fpath = os.path.normpath(fpath)
                spath = os.path.normpath(spath)
                if catn not in catalogs:
                    catalogs[catn] = []
                catalogs[catn].append((fpath, spath))

    return catalogs


def summit_gather (project, options):

    if (    project.templates_lang and options.lang != project.templates_lang
        and not options.force):
        error(  "template summit mode: gathering possible only on '%s' "
                "(if this is the very creation of the '%s' summit, "
                "run with: --create --force)"
              % (project.templates_lang, options.lang))

    branch_ids = select_branches(project, options)

    # Go through all selected branches.
    primary_sourced = {}
    n_selected_by_summit_subdir = {}
    for branch_id in branch_ids:

        branch_catalogs = select_branch_catalogs(branch_id, project, options,
                                                 n_selected_by_summit_subdir)

        # Go through all selected catalogs in this branch.
        for branch_name, branch_path, branch_subdir in branch_catalogs:
            if options.verbose:
                print "gathering from %s ..." % branch_path

            # Collect names of all the summit catalogs which this branch
            # catalog supplies messages to.
            summit_names = project.direct_map[branch_id][branch_name]

            # If more than one summit catalog has been collected, all of them
            # must already exist (otherwise, how would we split the contents
            # of the branch catalog?)
            if len(summit_names) > 1:
                for summit_name in summit_names:
                    if summit_name not in project.catalogs[SUMMIT_ID]:
                        fstr = "'" + "', '".join(summit_names) + "'"
                        error(  "catalog '%s' from the mapping '%s:%s'->(%s) "
                                "does not exist in the summit"
                              % (summit_name, branch_id, branch_name, fstr))

            # Collect paths of selected summit catalogs.
            if summit_names[0] in project.catalogs[SUMMIT_ID]:
                # If the first exists, all exist (asserted above).
                summit_paths = [project.catalogs[SUMMIT_ID][x][0][0]
                                for x in summit_names]
            else:
                # Set up the creation of a new summit catalog.
                summit_name = summit_names[0]
                summit_subdir = branch_subdir
                summit_path = os.path.join(project.summit, summit_subdir,
                                           summit_name + options.catext)

                if not options.do_create:
                    error("missing summit catalog '%s' for branch "
                          "catalog '%s'" % (summit_path, branch_path))

                add_summit_catalog_implicit(summit_name, summit_path,
                                            summit_subdir, branch_id, project)
                summit_paths = [summit_path]

            # Merge this branch catalog into summit catalogs.
            summit_gather_merge(branch_id, branch_path, summit_paths,
                                project, options, primary_sourced)

    # Assure no empty partial selections by summit subdirs.
    for subdir in n_selected_by_summit_subdir:
        if not n_selected_by_summit_subdir[subdir]:
            error("no catalogs to gather by summit subdir '%s'" % subdir)


def summit_scatter (project, options):

    if project.templates_lang and options.lang == project.templates_lang:
        error(  "template summit mode: scattering not possible on '%s'"
              % project.templates_lang)

    # Select branches to go through.
    branch_ids = select_branches(project, options)

    # Go through all selected branches.
    n_selected_by_summit_subdir = {}
    for branch_id in branch_ids:

        branch_catalogs = select_branch_catalogs(branch_id, project, options,
                                                 n_selected_by_summit_subdir)

        # Go through all selected catalogs in this branch.
        for branch_name, branch_path, branch_subdir in branch_catalogs:
            if options.verbose:
                print "scattering to %s ..." % branch_path

            # Collect names of all the summit catalogs which this branch
            # catalog supplies messages to.
            summit_names = project.direct_map[branch_id][branch_name]

            # Collect paths of selected summit catalogs.
            summit_paths = []
            for summit_name in summit_names:
                if not summit_name in project.catalogs[SUMMIT_ID]:
                    error("catalog '%s' not found in the summit" % summit_name)
                summit_paths.append(
                    project.catalogs[SUMMIT_ID][summit_name][0][0])

            # Merge messages from the summit catalogs into branch catalog.
            summit_scatter_merge(branch_id, branch_name, branch_path,
                                 summit_paths, project, options)

    # Assure no empty partial selections by summit subdirs.
    for subdir in n_selected_by_summit_subdir:
        if not n_selected_by_summit_subdir[subdir]:
            error("no catalogs to scatter by summit subdir '%s'" % subdir)


def summit_purge (project, options):

    if project.templates_lang and options.lang != project.templates_lang:
        error(  "template summit mode: purging possible only on '%s'"
              % project.templates_lang)

    # Collect names of summit catalogs to purge.
    summit_names = select_summit_catalogs(project, options)

    # Purge all selected catalogs.
    for name in summit_names:
        if options.verbose:
            print "purging %s ..." % project.catalogs[SUMMIT_ID][name][0][0]
        summit_purge_single(name, project, options)


def summit_reorder (project, options):

    if project.templates_lang and options.lang != project.templates_lang:
        error(  "template summit mode: reordering possible only on '%s'"
              % project.templates_lang)

    # Collect names of summit catalogs to reorder.
    summit_names = select_summit_catalogs(project, options)

    # Reorder all selected catalogs.
    for name in summit_names:
        if options.verbose:
            print "reordering %s ..." % project.catalogs[SUMMIT_ID][name][0][0]
        summit_reorder_single(name, project, options)


def summit_merge (project, options):

    if project.templates_lang and options.lang == project.templates_lang:
        error(  "template summit mode: merging not possible on '%s'"
              % project.templates_lang)

    # Collect names of summit catalogs to merge.
    summit_names = select_summit_catalogs(project, options)

    # Collect all template catalogs to merge.
    template_catalogs = collect_catalogs(project.templates_summit, ".pot",
                                         None, project, options)

    # Assert that all summit catalogs have templates.
    for name in summit_names:
        if not name in template_catalogs:
            error("no template for summit catalog '%s'" % name)

    # Merge all selected catalogs.
    for name in summit_names:
        for summit_path, summit_subdir in project.catalogs[SUMMIT_ID][name]:
            template_path = template_catalogs[name][0][0]
            summit_merge_single(summit_path, template_path, project, options)


def select_branches (project, options):

    # Select either all branches, or those mentioned in the command line.
    # If any command line spec points to the summit, must take all branches.
    project_branch_ids = [x[0] for x in project.branches]
    if not options.branches or SUMMIT_ID in options.branches:
        branch_ids = project_branch_ids
    else:
        branch_ids = options.branches
        # Assure that these branches actually exist in the project.
        for branch_id in branch_ids:
            if not branch_id in project_branch_ids:
                error("branch '%s' not in the project" % branch_id)

    return branch_ids


def select_branch_catalogs (branch_id, project, options,
                            n_selected_by_summit_subdir):

    # Shortcuts.
    pbcats = project.catalogs[branch_id]

    # Select either all catalogs in this branch,
    # or those mentioned in the command line.
    if not options.partspecs:
        branch_catalogs = []
        for name, spec in pbcats.items():
            for path, subdir in spec:
                branch_catalogs.append((name, path, subdir))
    else:
        # Select branch catalogs by command line specification.
        branch_catalogs = []

        # Process direct specifications (branch->summit).
        if branch_id in options.partspecs:
            for part_spec in options.partspecs[branch_id]:
                # If the catalog specification has path separators,
                # then it selects a complete subdir in the branch.
                if part_spec.find(os.sep) >= 0:
                    sel_subdir = os.path.normpath(part_spec)
                    one_found = False
                    for name, spec in pbcats.items():
                        for path, subdir in spec:
                            if sel_subdir == subdir:
                                one_found = True
                                branch_catalogs.append((name, path, subdir))
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
                                branch_catalogs.append((name, path, subdir))
                                one_found = True
                            break
                    if not one_found:
                        error(  "no catalog named '%s' in branch '%s'" \
                            % (sel_name, branch_id))

                # Also select all branch catalogs which contribute to same
                # summit catalogs as the already selected ones.
                dmap = project.direct_map[branch_id]
                pimap = project.part_inverse_map[branch_id]
                extra_branch_catalogs = []
                for branch_name, d1, d2 in branch_catalogs:
                    if branch_name in dmap:
                        for summit_name in dmap[branch_name]:
                            if summit_name in pimap:
                                for name in pimap[summit_name]:
                                    for path, subdir in pbcats[name]:
                                        extra_branch_catalogs.append(
                                            (name, path, subdir))
                branch_catalogs.extend(extra_branch_catalogs)

        # Process inverse specifications (summit->branch).
        if SUMMIT_ID in options.partspecs:
            for part_spec in options.partspecs[SUMMIT_ID]:
                if part_spec.find(os.sep) >= 0:
                    # Complete subdir.
                    sel_subdir = os.path.normpath(part_spec)
                    if sel_subdir not in n_selected_by_summit_subdir:
                        n_selected_by_summit_subdir[sel_subdir] = 0
                    cats = []
                    for name, spec in project.catalogs[SUMMIT_ID].items():
                        path, subdir = spec[0] # all summit catalogs unique
                        if sel_subdir == subdir:
                            bnames = project.full_inverse_map[name][branch_id]
                            for bname in bnames:
                                if bname in pbcats:
                                    for bpath, bsubdir in pbcats[bname]:
                                        cats.append((bname, bpath, bsubdir))
                    branch_catalogs.extend(cats)
                    n_selected_by_summit_subdir[sel_subdir] += len(cats)
                else:
                    # Specific catalog.
                    sel_name = part_spec
                    if not sel_name in project.catalogs[SUMMIT_ID]:
                        error("no summit catalog named '%s'" % sel_name)
                    bnames = project.full_inverse_map[sel_name][branch_id]
                    for bname in bnames:
                        if bname in pbcats:
                            for bpath, bsubdir in pbcats[bname]:
                                branch_catalogs.append((bname, bpath, bsubdir))

    # Same catalogs may have been selected multiple times, remove.
    branch_catalogs = list(set(branch_catalogs))

    # Sort by path.
    branch_catalogs.sort(cmp=lambda x, y: cmp(x[1], y[1]))
        # ...sorting is not only for looks, but to establish priority of
        # supplying comments to summit messages.

    return branch_catalogs


def select_summit_catalogs (project, options):

    # Collect all summit catalogs selected explicitly or implicitly.
    summit_names = []
    if not options.partspecs:
        for name in project.catalogs[SUMMIT_ID]:
            summit_names.append(name)
    else:
        for branch_id in options.partspecs:
            for part_spec in options.partspecs[branch_id]:

                if branch_id == SUMMIT_ID: # explicit by summit reference
                    if part_spec.find(os.sep) >= 0: # whole subdir
                        sel_subdir = os.path.normpath(part_spec)
                        for name, spec in project.catalogs[SUMMIT_ID].items():
                            path, subdir = spec[0] # summit catalogs are unique
                            if sel_subdir == subdir:
                                summit_names.append(name)
                    else: # single name
                        sel_name = part_spec
                        summit_names.append(sel_name)

                else: # implicit by branch reference
                    if part_spec.find(os.sep) >= 0: # whole subdir
                        sel_subdir = os.path.normpath(part_spec)
                        for name, spec in project.catalogs[branch_id].items():
                            for path, subdir in spec:
                                if sel_subdir == subdir:
                                    summit_names.extend(
                                        project.direct_map[branch_id][name])
                    else: # single name
                        sel_name = part_spec
                        summit_names.extend(
                            project.direct_map[branch_id][sel_name])

    # Make names unique and sort by path.
    summit_names = list(set(summit_names))
    summit_names.sort(
        cmp=lambda x, y: cmp(project.catalogs[SUMMIT_ID][x][0][0],
                             project.catalogs[SUMMIT_ID][y][0][0]))

    return summit_names


# Register new summit catalog to support implicitly mapped branch catalog,
# updating inverse mappings as well.
def add_summit_catalog_implicit (name, path, subdir, branch_id, project):

    project.catalogs[SUMMIT_ID][name] = [(path, subdir)]
    project.part_inverse_map[branch_id][name] = [name]
    if not name in project.full_inverse_map:
        project.full_inverse_map[name] = {}
    project.full_inverse_map[name][branch_id] = [name]


def summit_gather_merge (branch_id, branch_path, summit_paths,
                         project, options, primary_sourced):

    # Decide on wrapping function for message fields in the summit.
    wrapf = get_wrap_func(project.summit_unwrap, project.summit_split_tags)

    # Open branch catalog.
    branch_cat = Catalog(branch_path)

    # Open all summit catalogs;
    # use header of the branch catalog if the summit catalog is newly created.
    summit_cats = []
    for summit_path in summit_paths:
        summit_cat = Catalog(summit_path, create=True, wrapf=wrapf)
        # Copy over branch header for newly created summit catalog.
        if summit_cat.created():
            summit_cat.header = branch_cat.header
        summit_cats.append(summit_cat)

    # Go through messages in the branch catalog:
    # merge with existing messages, collect any new messages.
    # Do not insert new messages immediately, as the merge may update
    # source references, which are necessary for heuristic insertion.
    to_insert = []
    last_merge_pos = None
    last_merge_summit_cat = None
    for msg in branch_cat:
        if msg.obsolete: # do not gather obsolete messages
            continue

        # Merge in all summit catalogs that have this message.
        pos_merged = None
        for summit_cat in summit_cats:
            if msg in summit_cat:
                # Collect the data for heuristic insertion according
                # to the first merge.
                if pos_merged is None:
                    last_merge_pos = pos_merged
                    last_merge_summit_cat = summit_cat

                # Merge the message.
                pos_merged = summit_cat.add(msg)

                # Possibly update automatic comments.
                if summit_cat.filename not in primary_sourced:
                    primary_sourced[summit_cat.filename] = {}
                summit_override_auto(summit_cat[pos_merged], msg, branch_id,
                                     primary_sourced[summit_cat.filename])

                # Equip any new summit tags to the merged message.
                summit_add_tags(summit_cat[pos_merged], branch_id, project)

        # If the message has not been merged anywhere, collect for insertion.
        # Also collect the catalog/position of the latest message merge,
        # needed later for heuristic insertion.
        if pos_merged is None:
            if last_merge_pos is not None:
                to_insert.append((msg, last_merge_summit_cat, last_merge_pos))
            else:
                to_insert.append((msg, summit_cats[0], -1))

    # Go through messages collected for insertion and heuristically insert.
    for msg, last_merge_summit_cat, last_merge_pos in to_insert:
        # Decide in which catalog to insert by the highest greater than zero
        # belonging weight.
        # If no weight greater than zero, default to the same catalog as
        # the last merged message prior to this and after its positon.
        summit_cat_selected = last_merge_summit_cat
        pos_selected = last_merge_pos
        weight_best = 0.0
        for summit_cat in summit_cats:
            # Skip the catalog if it has been newly created
            # (to speed up things, could check anyway).
            if summit_cat.created():
                continue

            pos, weight = summit_cat.insertion_inquiry(msg)
            if weight > weight_best:
                weight_best = weight
                summit_cat_selected = summit_cat
                pos_selected = pos

        if msg in summit_cat_selected:
            error("internal: existing message in insertion pass")

        # Insert the message; the true position is reported back.
        pos_added = summit_cat_selected.add(msg, pos=pos_selected)

        # Equip summit tags to the added message.
        summit_add_tags(summit_cat[pos_added], branch_id, project)


    # Update headers of otherwise modified summit catalogs.
    for summit_cat in summit_cats:
        if summit_cat.modcount:
            if not summit_cat.header.author and branch_cat.header.author:
                # Copy the complete branch header if it has an author and
                # the summit header misses an author.
                summit_cat.header = branch_cat.header
            else:
                # Copy over POT creation date if newer.
                field_name = "POT-Creation-Date"
                branch_field = branch_cat.header.select_fields(field_name)[0]
                summit_field = summit_cat.header.select_fields(field_name)[0]
                # Compare only dates, ignore time (would have to consider
                # timezones otherwise).
                branch_date_cmp = re.sub(r" .*", "", branch_field[1])
                summit_date_cmp = re.sub(r" .*", "", summit_field[1])
                if branch_date_cmp > summit_date_cmp:
                    summit_cat.header.replace_field_value(field_name,
                                                        branch_field[1])

    # Commit changes to summit catalogs.
    for summit_cat in summit_cats:
        if summit_cat.sync():
            if options.verbose:
                print ">    (scattered) %s  %s" % (branch_cat.filename,
                                                   summit_cat.filename)
            else:
                print ">    %s  %s" % (branch_cat.filename, summit_cat.filename)


def summit_scatter_merge (branch_id, branch_name, branch_path, summit_paths,
                          project, options):

    # Decide on wrapping function for message fields in the brances.
    wrapf = get_wrap_func(project.branches_unwrap, project.branches_split_tags)

    # Open the branch catalog and all summit catalogs.
    branch_cat = Catalog(branch_path, wrapf=wrapf)
    summit_cats = [Catalog(x) for x in summit_paths]

    # Go through messages in the branch catalog.
    for branch_msg in branch_cat:
        # Skip obsolete messages.
        if branch_msg.obsolete:
            continue

        # Find first summit catalog which has this message translated.
        summit_cat = None
        summit_msg = None
        for summit_cat in summit_cats:
            if branch_msg in summit_cat:
                summit_cat = summit_cat
                summit_msg = summit_cat[branch_msg]
                break

        if summit_msg is not None:
            if summit_msg.translated:
                if (summit_msg.msgid_plural and branch_msg.msgid_plural) \
                or not (summit_msg.msgid_plural or branch_msg.msgid_plural):
                    # Both messages have same plurality.
                    for i in range(len(summit_msg.msgstr)):
                        piped_msgstr = exec_hook_msgstr(
                            branch_id, branch_name,
                            summit_cat, summit_msg, summit_msg.msgstr[i],
                            project, options)
                        if i < len(branch_msg.msgstr):
                            branch_msg.msgstr[i] = piped_msgstr
                        else:
                            branch_msg.msgstr.append(piped_msgstr)
                    branch_msg.fuzzy = False
                    branch_msg.manual_comment = summit_msg.manual_comment

                elif summit_msg.msgid_plural and not branch_msg.msgid_plural:
                    # Summit is plural, branch is not: means that branch is
                    # singular, so copy plural form for n==1.
                    index = summit_cat.plural_index(1)
                    branch_msg.msgstr[0] = scatter_pipe_msgstr(
                        branch_id, branch_name,
                        summit_cat, summit_msg, summit_msg.msgstr[index],
                        project, options)
                    branch_msg.fuzzy = False
                    branch_msg.manual_comment = summit_msg.manual_comment

                else:
                    # Branch is plural, summit is not: should not happen.
                    print   "%s: summit message needs plurals: {%s}" \
                          % (branch_path, branch_msg.msgid)
        else:
            print   "%s:%d(%d): message not in the summit" \
                  % (branch_path, branch_msg.refline, branch_msg.refentry)

    # Update header only if the branch catalog was otherwise modified.
    if branch_cat.modcount:
        # Give priority to the first summit catalog.
        summit_cat = summit_cats[0]

        # Overwrite everything except these fields.
        preserved_fields = []
        for name in ["Report-Msgid-Bugs-To",
                     "POT-Creation-Date",
                    ]:
            selected_fields = branch_cat.header.select_fields(name)
            if selected_fields:
                preserved_fields.append(selected_fields[0])

        # Overwrite branch with summit header.
        branch_cat.header = summit_cat.header

        # Put back the preserved fields.
        for field in preserved_fields:
            name, value = field
            replaced = branch_cat.header.replace_field_value(name, value)
            if not replaced:
                # Summit catalog didn't contain this field, append it.
                branch_cat.header.field.append(field)

    # Commit changes to the branch catalog.
    if branch_cat.sync():

        # Apply hooks to branch catalog file.
        exec_hook_file(branch_id, branch_name, branch_cat.filename,
                       project, options)

        paths_str = ", ".join(summit_paths)
        if options.verbose:
            print "<    (gathered) %s  %s" % (branch_cat.filename, paths_str)
        else:
            print "<    %s  %s" % (branch_cat.filename, paths_str)


# Pipe msgstr through hook calls,
# for which branch id and catalog name match hook specification.
def exec_hook_msgstr (branch_id, branch_name, cat, msg, msgstr,
                      project, options):

    piped_msgstr = msgstr
    for call, branch_rx, name_rx in project.hook_on_scatter_msgstr:
        if re.search(branch_rx, branch_id) and re.search(name_rx, branch_name):
            piped_msgstr_tmp = call(cat, msg, piped_msgstr)
            if piped_msgstr_tmp is not None:
                piped_msgstr = piped_msgstr_tmp

    return piped_msgstr


# Pipe catalog file through hook calls,
# for which branch id and catalog name match hook specification.
def exec_hook_file (branch_id, branch_name, filepath, project, options):

    # Make temporary backup of the file.
    bckppath = "/tmp/backup%s-%s" % (os.getpid(), os.path.basename(filepath))
    shutil.copyfile(filepath, bckppath)

    # Apply all hooks to the file, but stop if one does not return True.
    failed = False
    for call, branch_rx, name_rx in project.hook_on_scatter_file:
        if re.search(branch_rx, branch_id) and re.search(name_rx, branch_name):
            if not call(filepath):
                failed = True
                break

    # If any hook failed, retrieve the temporary copy.
    if failed:
        shutil.move(bckppath, filepath)
    else:
        os.unlink(bckppath)


# Decide on wrapping policy for messages.
def get_wrap_func (unwrap, split_tags):

    if unwrap:
        if split_tags:
            wrap_func = wrap.wrap_field_ontag_unwrap
        else:
            wrap_func = wrap.wrap_field_unwrap
    else:
        if split_tags:
            wrap_func = wrap.wrap_field_ontag
        else:
            wrap_func = wrap.wrap_field

    return wrap_func


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


def msg_ident (msg):

    h = md5.new()
    h.update(msg.key.encode("UTF-8"))
    return "_" + h.hexdigest() + "_"


# NOTE: If changed, also change in stats sieve.
#_summit_tag_ident = "+="
_summit_tag_branchid = "+>"
_summit_tags = (
    #_summit_tag_ident,
    _summit_tag_branchid,
)

def summit_add_tags (msg, branch_id, project):

    ## Add hash ident.
    #ident = msg_ident(msg)
    #set_summit_comment(msg, _summit_tag_ident, ident)

    # Add branch ID.
    branch_ids = get_summit_comment(msg, _summit_tag_branchid).split()
    if not branch_id in branch_ids:
        # Order branch ids by the global order, to preserve priorites.
        branch_ids.append(branch_id)
        global_branch_ids = [x[0] for x in project.branches]
        ordered_branch_ids = []
        for branch_id in global_branch_ids:
            if branch_id in branch_ids:
                ordered_branch_ids.append(branch_id)
        set_summit_comment(msg, _summit_tag_branchid,
                           " ".join(ordered_branch_ids))


def summit_override_auto (summit_msg, branch_msg, branch_id, primary_sourced):

    branch_ids = get_summit_comment(summit_msg, _summit_tag_branchid).split()

    # Copy auto/source/flag comments only if this is the primary branch
    # for the current message.
    if not branch_ids or branch_id == branch_ids[0]:
        if summit_msg.key not in primary_sourced:
            # This is the primary branch message for the summit message.

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
            summit_msg.source = branch_msg.source

            # Split auto comments of the current summit message into
            # summit and non-summit tagged comments.
            non_summit_comments = []
            summit_comments = []
            for comment in summit_msg.auto_comment:
                wlst = comment.split()
                if wlst and wlst[0] in _summit_tags:
                    summit_comments.append(comment)
                else:
                    non_summit_comments.append(comment)

            # Copy auto comments only if non-summit auto comments of the
            # current summit message are different to the branch message
            # auto comments.
            if non_summit_comments != branch_msg.auto_comment:
                summit_msg.auto_comment = branch_msg.auto_comment
                summit_msg.auto_comment.extend(summit_comments)

            primary_sourced[summit_msg.key] = True

        else:
            # Secondary source message for the summit message.
            # FIXME: Once there is a way to reliably tell the root directory
            # of source references, add missing and remove obsolete source
            # references instead.
            # FIXME: Should this else branch be one level out?
            pass


def summit_purge_single (summit_name, project, options):

    # Decide on wrapping function for message fields in the summit.
    wrapf = get_wrap_func(project.summit_unwrap, project.summit_split_tags)

    # Open the summit catalog and all dependent branch catalogs.
    summit_path = project.catalogs[SUMMIT_ID][summit_name][0][0]
    summit_cat = Catalog(summit_path, wrapf=wrapf)
    branch_cats = {}
    for branch_id in project.full_inverse_map[summit_name]:
        branch_paths = []
        for branch_name in project.full_inverse_map[summit_name][branch_id]:
            for path, subdir in project.catalogs[branch_id][branch_name]:
                branch_paths.append(path)
        branch_paths.sort()
        branch_cats[branch_id] = [Catalog(x) for x in branch_paths]

    # For each message in the summit catalog, check its presence in
    # branch catalogs (consider only non-obsolete messages);
    # update branch IDs, or remove the message if none remaining.
    for summit_msg in summit_cat:
        branch_ids = get_summit_comment(summit_msg,
                                        _summit_tag_branchid).split()
        valid_branch_ids = []
        for branch_id in branch_ids:
            if branch_id in branch_cats:
                for branch_cat in branch_cats[branch_id]:
                    if summit_msg in branch_cat \
                    and not branch_cat[summit_msg].obsolete:
                        valid_branch_ids.append(branch_id)
                        break

        if valid_branch_ids:
            set_summit_comment(summit_msg, _summit_tag_branchid,
                               " ".join(valid_branch_ids))
        else:
            summit_cat.remove_on_sync(summit_msg)

    # Sync to disk, remove afterwards if empty.
    if summit_cat.sync():
        if len(summit_cat) > 0:
            if options.verbose:
                print "!    (purged) %s" % summit_cat.filename
            else:
                print "!    %s" % summit_cat.filename
        else:
            os.remove(summit_cat.filename)
            if options.verbose:
                print "-    (removed) %s" % summit_cat.filename
            else:
                print "-    %s" % summit_cat.filename


def summit_reorder_single (summit_name, project, options):

    # Decide on wrapping function for message fields in the summit.
    wrapf = get_wrap_func(project.summit_unwrap, project.summit_split_tags)

    # Open the summit catalog.
    summit_path = project.catalogs[SUMMIT_ID][summit_name][0][0]
    summit_cat = Catalog(summit_path, wrapf=wrapf)

    # Open the dependent branch catalogs branch catalogs by
    # priority of branches, and sorted by path within one branch.
    branch_cats = []
    global_branch_ids = [x[0] for x in project.branches]
    for branch_id in global_branch_ids:
        full_inv_map = project.full_inverse_map[summit_name]
        if branch_id in full_inv_map:
            branch_paths = []
            for branch_name in full_inv_map[branch_id]:
                for path, subdir in project.catalogs[branch_id][branch_name]:
                    branch_paths.append(path)
            branch_paths.sort()
            branch_cats.extend([Catalog(x) for x in branch_paths])
    if branch_cats is None:
        error("internal: cannot find branch catalogs for reordering")

    # Open a fresh catalog with empty path and copy the original header.
    fresh_cat = Catalog("", create=True, wrapf=wrapf)
    fresh_cat.header = summit_cat.header

    # Go through all branch catalogs which were selected by priority of
    # branches and sorted within branch; at each catalog, go through its
    # messages in order, and insert the matching summit message to the
    # fresh catalog, when not already in it.
    for branch_cat in branch_cats:
        for pos in range(0, len(branch_cat)):
            branch_msg = branch_cat[pos]
            if branch_msg.obsolete: # skip obsolete messages in branch
                continue
            if fresh_cat.find(branch_msg) < 0:
                old_pos = summit_cat.find(branch_msg)
                # NOTE: Not every branch message must be present in this
                # summit catalog: branch catalog may be spread across several
                # other summit catalogs.
                if old_pos >= 0:
                    summit_msg = summit_cat[old_pos]
                    # If the message is in one of existing file references,
                    # this will nicely insert it, otherwise just appends.
                    pos, weight = fresh_cat.insertion_inquiry(summit_msg)
                    fresh_cat.add(summit_msg, pos)

    # Finally reinsert messages not present in any branch catalog
    # (may happen if the summit wasn't purged before reordering).
    for pos in range(0, len(summit_cat)):
        if fresh_cat.find(summit_cat[pos]) < 0:
            fresh_cat.add(summit_cat[pos])

    # Check if the order has actually changed.
    reordered = False
    for pos in range(0, len(summit_cat)):
        if pos != fresh_cat.find(summit_cat[pos]):
            reordered = True
            break

    # Assign the summit path to the fresh catalog and sync if needed.
    fresh_cat.filename = summit_path
    if reordered and fresh_cat.sync():
        if options.verbose:
            print "!    (reordered) %s" % fresh_cat.filename
        else:
            print "!    %s" % fresh_cat.filename


def summit_merge_single (summit_path, template_path, project, options):

    # Call msgmerge to create the temporary merged catalog.
    tmp_path = "/tmp/merge%d-%s" % (os.getpid(), os.path.basename(summit_path))
    cmdline = "msgmerge --quiet --previous %s %s -o %s "
    cmdline %= (summit_path, template_path, tmp_path)
    if project.summit_unwrap: # unwrap if requested
        cmdline += "--no-wrap "
    assert_system(cmdline)

    # Split on tags if requested.
    # NOTE: This could be done unconditionally, but save good time in case no
    # tag splitting is requested; also wrapping in Gettext is much better than
    # current in Pology for CJK languages, so don't ruin it if not necessary.
    if project.summit_split_tags:
        wrapf = get_wrap_func(project.summit_unwrap, project.summit_split_tags)
        cat = Catalog(tmp_path, monitored=False, wrapf=wrapf)
        cat.sync(force=True)

    # If there is any difference between merged and old catalog.
    if not filecmp.cmp(summit_path, tmp_path):
        # Assert correctness of the merged catalog and move over to the summit.
        assert_system("msgfmt -c -o/dev/null %s " % tmp_path)
        shutil.move(tmp_path, summit_path)

        if options.verbose:
            print ".    (merged) %s" % summit_path
        else:
            print ".    %s" % summit_path
    else:
        # Remove the temporary merged catalog.
        os.unlink(tmp_path)


# Execute command line and assert success.
# In case of failure, report the failed command line if echo is False.
def assert_system (cmdline, echo=False):

    if echo:
        print cmdline
    ret = os.system(cmdline)
    if ret:
        if echo:
            error("non-zero exit from previous command")
        else:
            error("non-zero exit from:\n%s" % cmdline)


if __name__ == '__main__':
    main()
