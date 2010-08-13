# -*- coding: UTF-8 -*-

"""
Fetch Pology modules, functions, data, etc. by various handles.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import sys
import os
import re

from pology import PologyError, _, n_
from pology.report import error, warning


def get_module (modpath, lang=None, proj=None, abort=False, wpath=False):
    """
    Import a Pology module.

    Module is specified by its dotted path in Pology's package structure
    relative to (optional) language and project.
    For example::

        get_module("remove")

    will try to import the L{pology.remove}, while::

        get_module("wconv", lang="sr")

    will try to import the C{pology.lang.sr.wconv} module, and::

        get_module("header", proj="kde")

    will try to import the C{pology.proj.kde.header} module.

    Elements of the relative path can also contain hyphens, which will
    be converted into underscores when looking for the module.

    If the module cannot be imported, if C{abort} is C{True} the execution
    will abort with an error message; otherwise an exception is raised.

    If C{wpath} is C{True}, the resolved module path is returned as well.

    @param modpath: relative module location
    @type modpath: string
    @param lang: language code
    @type lang: string
    @param lang: project code
    @type lang: string
    @param abort: whether to abort execution if the module cannot be imported
    @type abort: bool
    @param wpath: whether to also return resolve module path
    @type wpath: bool

    @returns: imported module, possibly with its path
    @rtype: module or (module, string)
    """

    modpath = modpath.replace("-", "_")
    if lang and proj:
        modpath = "pology.lang.%s.proj.%s" % (lang, proj, modpath)
    elif lang:
        modpath = "pology.lang.%s.%s" % (lang, modpath)
    elif proj:
        modpath = "pology.proj.%s.%s" % (proj, modpath)
    else:
        modpath = "pology.%s" % (modpath)
    try:
        module = __import__(modpath, globals(), locals(), [""])
    except ImportError:
        _raise_or_abort(_("@info",
                          "Cannot import module '%(mod)s'.",
                          mod=modpath), abort)

    # TODO: Make more detailed analysis why importing fails:
    # is there such a language or project, is there such a file, etc.

    return module if not wpath else (module, modpath)


_valid_lang_rx = re.compile(r"^[a-z]{2,3}(_[A-Z]{2})?(@\w+)?$")
_valid_proj_rx = re.compile(r"^[a-z_]+$")
_valid_path_rx = re.compile(r"^([a-z][\w-]*(\.|$))+", re.I)
_valid_item_rx = re.compile(r"^[a-z][\w-]+$", re.I)

def split_ireq (ireq, abort=False):
    """
    Split item request string into distinct elements.

    The item request is a string of the form
    C{[lang:][proj%]path[/item][~args]} (or C{[proj%][lang:]...}),
    which this function parses into C{(path, lang, proj, item, args)} tuple.
    If language, project, item or argument strings are not not stated,
    their value in the tuple will be C{None}.
    The language should be a proper language code,
    the project an identifier-like string,
    the path a sequence of identifier-like strings connected by dots
    (though hyphens are accepted an taken as synonymous to underscores),
    item an identifier-like string,
    and arguments can be an arbitrary string.

    If the item request cannot be parsed,
    either the execution is aborted with an error message,
    or an exception is raised, depending on value of C{abort}.

    @param ireq: item request
    @type ireq: string
    @param abort: whether to abort execution or if the request cannot be parsed
    @type abort: bool

    @returns: parsed request elements
    @rtype: (string, string or C{None}, string or C{None}, string or C{None},
             string or C{None})
    """

    rest = ireq

    lst = rest.split("~", 1)
    if len(lst) == 1:
        rest, args = lst + [None]
    else:
        rest, args = lst

    lst = rest.split("/", 1)
    if len(lst) == 1:
        rest, item = lst + [None]
    else:
        rest, item = lst

    lang = None
    proj = None
    plang = rest.find(":")
    pproj = rest.find("%")
    if plang >= 0 and pproj >= 0:
        p1, p2 = min(plang, pproj), max(plang, pproj)
        c1, c2, rest = rest[:p1], rest[p1 + 1:p2], rest[p2 + 1:]
        if plang < pproj:
            lang, proj = c1, c2
        else:
            lang, proj = c2, c1
    elif plang >= 0:
        lang, rest = rest[:plang], rest[plang + 1:]
    elif pproj >= 0:
        proj, rest = rest[:pproj], rest[pproj + 1:]

    path = rest

    if not _valid_path_rx.search(path):
        _raise_or_abort(_("@info",
                          "Invalid path '%(path)s' in item request '%(req)s'.",
                          path=path, req=ireq), abort)
    if lang is not None and not _valid_lang_rx.search(lang):
        _raise_or_abort(_("@info",
                          "Invalid language code '%(code)s' "
                          "in item request '%(req)s.'",
                          code=lang, req=ireq), abort)
    if proj is not None and not _valid_proj_rx.search(proj):
        _raise_or_abort(_("@info",
                          "Invalid project code '%(code)s' "
                          "in item request '%(req)s.'",
                          code=proj, req=ireq), abort)
    if item is not None and not _valid_item_rx.search(item):
        _raise_or_abort(_("@info",
                          "Invalid item '%(item)s' in item request '%(req)s'.",
                          item=item, req=ireq), abort)

    path = path.replace("-", "_")
    if item:
        item = item.replace("-", "_")

    return path, lang, proj, item, args


def get_hook (modpath, lang=None, proj=None, func=None, args=None, abort=False):
    """
    Fetch a hook function.

    Loads a hook function from a module obtained by applying L{get_module}
    to C{modpath}, C{lang}, and C{proj} parameters.
    If C{func} is C{None}, the function name defaults to module name;
    if C{func} is not C{None}, but function of that name is not found,
    then the function named C{<modname>_<func>} is additionally tried
    (where C{<modname>} is the last element in C{modpath}).
    If C{args} is not C{None}, then the loaded function is considered
    a hook factory, and the hook is created by calling it with C{args} string
    as argument list (it should have no surrounding parenthesis).

    @param modpath: hook module
    @type modpath: string
    @param lang: language code
    @type lang: string
    @param proj: project code
    @type proj: string
    @param func: function name of hook or hook factory
    @type func: string
    @param args: argument string to hook factory
    @type args: string
    @param abort: whether to abort execution or raise exception if the hook
        cannot be loaded
    @type abort: bool

    @returns: the hook
    """

    lmod, modpath = get_module(modpath, lang, proj, abort, wpath=True)
    modname = modpath.rsplit(".", 1)[-1]
    if func is None:
        func = modname
        func2 = "\0"
    else:
        func2 = "%s_%s" % (modname, func)
    call = getattr(lmod, func, None) or getattr(lmod, func2, None)
    if call is None:
        _raise_or_abort(_("@info",
                          "Module '%(mod)s' does not define "
                          "'%(func)s' function.",
                          mod=modpath, func=func), abort)
    if args is not None:
        try:
            call = eval("call(%s)" % args)
        except Exception, e:
            fspec = "%s.%s" % (modpath, func)
            _raise_or_abort(_("@info",
                              "Cannot create hook by applying function "
                              "'%(func)s' to argument list %(args)s; "
                              "reported error:\n%(msg)s",
                              func=fspec, args=repr(args), msg=e.args[0]),
                            abort)

    return call


def get_hook_ireq (ireq, abort=False):
    """
    Like L{get_hook}, but the hook is specified by
    L{item request<split_ireq>}.

    For a module C{pology.FOO} which defines the C{FOO()} hook function,
    the hook specification is simply C{FOO}.
    If the hook function is named C{BAR()} instead of C{FOO()},
    the hook specification is given as C{FOO/BAR};
    if the hook function is named C{FOO_BAR()}, i.e. the specification
    would be C{FOO/FOO_BAR}, it can be folded to C{FOO/BAR}.
    Language-specific hooks (C{pology.lang.LANG.FOO}) are aditionally
    preceded by the language code and colon, as C{LANG:FOO} or C{LANG:FOO/BAR}.
    Project-specific hooks (C{pology.proj.PROJ.FOO}) are aditionally
    preceded by the project code and percent, as C{PROJ%FOO} or C{LANG%FOO/BAR}.
    If the hook is both language- and project- specific, language and project
    qualifiers can both be added: C{LANG:PROJ%FOO} or C{LANG:PROJ%FOO/BAR};
    ordering, C{LANG:PROJ%...} or C{PROJ%LANG:...}, is not significant.

    If the hook is not a plain hook, but a hook factory function,
    the factory arguments are supplied after the basic hook specification,
    separated by tilde: C{LANG:PROJ%FOO/BAR~ARGLIST}
    (where C{LANG:}, C{PROJ%} and C{/BAR} may be omitted under previously
    listed conditions).
    Argument list is formatted just like it would be passed in Python code
    to the factory function, omitting the surrounding parenthesis.
    """

    return _by_ireq(ireq, get_hook, abort=abort)


def _by_ireq (ireq, getter, abort=False):
    """
    Get item using C{getter(path, lang, proj, item, abort)}
    method, by applying it to parsed item request string.
    """

    path, lang, proj, item, args = split_ireq(ireq, abort)
    return getter(path, lang, proj, item, args, abort)


def _raise_or_abort (errmsg, abort, exc=PologyError):
    """
    Raise an exception or abort execution with given error message,
    based on the value of C{abort}.
    """

    if abort:
        error(errmsg)
    else:
        raise exc(errmsg)


def get_result (modpath, lang=None, proj=None, func=None, args="", abort=False):
    """
    Fetch the result of a function evaluation.

    Executes function from the module loaded by applying L{get_module}
    to C{modpath}, C{lang}, and C{proj} parameters.
    If C{func} is not given, the function name defaults to module name.
    C{args} is the string representing the argument list
    to the function call (without surrounding parenthesis).

    @param modpath: function module
    @type modpath: string
    @param lang: language code
    @type lang: string
    @param proj: project code
    @type proj: string
    @param func: function name within the module
    @type func: string
    @param args: argument string to function call
    @type args: string
    @param abort: if the function is not found, abort or report C{None}
    @type abort: bool

    @returns: the value returned by the function call
    """

    fmod, modpath = get_module(modpath, lang, proj, abort, wpath=True)
    modname = modpath.rsplit(".", 1)[-1]
    if func is None:
        func = modname
    call = getattr(fmod, modname, None)
    if call is None:
        _raise_or_abort(_("@info",
                          "Module '%(mod)s' does not define "
                          "function '%(func)s'.",
                          mod=modpath, func=func), abort)
    try:
        res = eval("call(%s)" % args)
    except Exception, e:
        fspec = "%s.%s" % (modpath, func)
        _raise_or_abort(_("@info",
                          "Evaluating function '%(func)s' "
                          "with argument list %(args)s failed; "
                          "reported error:\n%(msg)s",
                          func=fspec, args=repr(args), msg=e.args[0]),
                          abort)

    return res


def get_result_ireq (ireq, abort=False):
    """
    Like L{get_result}, but the function is specified by
    L{item request<split_ireq>}.
    """

    return _by_ireq(ireq, get_result, abort=abort)

