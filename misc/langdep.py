# -*- coding: UTF-8 -*-

"""
Fetch language-dependent modules, functions, data, etc.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import sys
import os
import re

from pology import _, n_
from pology.misc.report import error, warning


def get_module (lang, path, abort=False):
    """
    Import a language-dependent module.

    Module is specified by the language code, and the elements of
    the relative path in Pology's package for that language.
    Language can also be C{None}, in which case a language-independent
    module is looked for. For example::

        get_module("sr", ["hook", "wconv"])

    will try to import the C{pology.l10n.sr.wconv} module, while::

        get_module(None, ["hook", "remove-subs"])

    will try to import the C{pology.hook.remove_subs}.

    The elements of the module path can also contain hyphens, which will
    be converted into underscores when looking for the module.

    If the module cannot be imported, if C{abort} is C{True} the execution
    will abort with an error message; otherwise an exception is raised.

    @param lang: language code
    @type lang: string or C{None}
    @param path: relative module location
    @type path: list of strings
    @param abort: whether to abort execution if the module cannot be imported
    @type abort: bool

    @returns: imported module
    @rtype: module or C{None}
    """

    modpath = ".".join(path)
    modpath = modpath.replace("-", "_")
    if lang:
        modpath = "pology.l10n.%s.%s" % (lang, modpath)
    else:
        modpath = "pology.%s" % (modpath)
    try:
        module = __import__(modpath, globals(), locals(), [""])
    except ImportError:
        _raise_or_abort(_("@info",
                          "Cannot import module '%(mod)s'.")
                        % dict(mod=modpath), abort)

    # TODO: Make more detailed analysis why importing fails:
    # is there  such a language, is there such a file, etc.

    return module


_valid_lang_rx = re.compile(r"^[a-z]{2,3}(_[A-Z]{2})?(@\w+)?$")
_valid_path_rx = re.compile(r"^([a-z][\w-]*(\.|$))+", re.I)
_valid_item_rx = re.compile(r"^[a-z][\w-]*$", re.I)

def split_req (langreq, abort=False):
    """
    Split string of the language-dependent item request.

    The language-dependent item request is string of the form
    C{[lang:]path[/item][~args]}, which is to be parsed into
    C{(lang, path, item, args)} tuple.
    If language is not stated, its value in the tuple will be C{None},
    and likewise for the item and argument strings.
    The language should be a proper language code,
    the path a sequence of identifier-like strings connected by dots,
    item also an identifier-like string,
    and arguments can be an arbitrary string.

    If the item request cannot be parsed,
    either the execution is aborted with an error message,
    or an exception is raised, depending on value of C{abort}.

    @param langreq: request specification
    @type langreq: string
    @param abort: whether to abort execution or if the request cannot be parsed
    @type abort: bool

    @returns: parsed language and request
    @rtype: (string or C{None}, string, string or C{None}, string or C{None})
    """

    rest = langreq

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

    lst = rest.split(":", 1)
    if len(lst) == 1:
        lang, path = [None] + lst
    else:
        lang, path = lst

    if lang and not _valid_lang_rx.search(lang):
        _raise_or_abort(_("@info",
                          "Invalid language '%(langcode)s' "
                          "in item request '%(req)s.'")
                        % dict(langcode=lang, req=langreq), abort)
    if not _valid_path_rx.search(path):
        _raise_or_abort(_("@info",
                          "Invalid path '%(path)s' in item request '%(req)s'.")
                        % dict(path=path, req=langreq), abort)
    if item and not _valid_item_rx.search(item):
        _raise_or_abort(_("@info",
                          "Invalid item '%(item)s' in item request '%(req)s'.")
                        % dict(item=item, req=langreq), abort)

    path = path.replace("-", "_")
    if item:
        item = item.replace("-", "_")

    return (lang, path, item, args)


def get_hook (lang, hmod, func=None, args=None, abort=False):
    """
    Fetch a language-dependent hook function.

    Loads the hook function from C{pology.l10n.<lang>.hook.<hmod>} module.
    If C{func} is C{None}, the function name defaults to module name;
    if C{func} is not C{None}, but function of that name is not found,
    then the function named C{<hmod>_<func>} is additionally tried.
    If C{args} is not C{None}, then the loaded function is considered
    a hook factory, and the hook is created by calling it with C{args} string
    as argument list (it should have no surrounding parenthesis).

    @param lang: language code
    @type lang: string
    @param hmod: hook module
    @type hmod: string
    @param func: hook of hook factory function name
    @type func: string
    @param args: argument string to hook factory
    @type args: string
    @param abort: if the hook is not loadable, abort or report C{None}
    @type abort: bool

    @returns: the hook
    """

    path = ["hook"] + hmod.split(".")
    lmod = get_module(lang, path, abort)
    if func is None:
        func = hmod
        func2 = "\0"
    else:
        func2 = "%s_%s" % (hmod, func)
    call = getattr(lmod, func, None) or getattr(lmod, func2, None)
    if call is None:
        hmodfmt = "%s:%s" % (lang, hmod) if lang else hmod
        _raise_or_abort(_("@info",
                          "Hook module '%(mod)s' does not define "
                          "'%(func)s' function.")
                        % dict(mod=hmodfmt, func=func), abort)
    if args is not None:
        try:
            call = eval("call(%s)" % args)
        except Exception, e:
            if lang:
                fspec = "%s:%s/%s" % (lang, hmod, func)
            else:
                fspec = "%s/%s" % (hmod, func)
            _raise_or_abort(_("@info",
                              "Cannot create hook by applying function "
                              "'%(func)s' to argument list %(args)s; "
                              "reported error:\n%(msg)s")
                            % dict(func=fspec, args=repr(args), msg=e.message),
                            abort)

    return call


def get_hook_lreq (langreq, abort=False):
    """
    Like L{get_hook}, but the hook is specified as
    L{language request<split_req>}.

    For a module C{pology.hook.FOO} which defines the C{FOO()} hook function,
    the hook specification is simply C{FOO}.
    If the hook function is named C{BAR()} instead of C{FOO()},
    the hook specification is given as C{FOO/BAR};
    if the hook function is named C{FOO_BAR()}, i.e. the specification
    would be C{FOO/FOO_BAR}, it can be folded to C{FOO/BAR}.
    Language-specific hooks (C{pology.l10n.LANG.hook.FOO}) are aditionally
    preceded by the language code with colon, as C{LANG:FOO} or C{LANG:FOO/BAR}.

    If the hook is not a plain hook, but a L{hook factory<hook>} function,
    the factory arguments are supplied after the basic hook specification,
    separated by tilde: C{LANG:FOO/BAR~ARGLIST}
    (where LANG: and /BAR may be omitted under previous conditions).
    Argument list is formatted just like it would be passed in Python code
    to the factory function, omitting the surrounding parenthesis.
    """

    return _by_lreq(langreq, get_hook, abort=abort)


def _by_lreq (langreq, getter, abort=False):
    """
    Get language-dependent item using C{getter(lang, path, item, abort)}
    method, by applying it to parsed language request string.
    """

    lang, path, item, args = split_req(langreq, abort)
    return getter(lang, path, item, args, abort)


def _raise_or_abort (errmsg, abort, exc=StandardError):
    """
    Raise an exception or abort execution with given error message,
    based on the value of C{abort}.
    """

    if abort:
        error(errmsg)
    else:
        raise exc, errmsg


def get_result (lang, mod, func=None, args="", abort=False):
    """
    Fetch a result of language-dependent function evaluation.

    Executes function loaded from a C{pology.l10n.<lang>.<mod>} module
    and returns its result.
    If C{func} is not given, the function name defaults to C{run}.
    C{args} is the string representing the argument list
    to the function call (without surrounding parenthesis).

    @param lang: language code
    @type lang: string
    @param mod: language-dependent module
    @type mod: string
    @param func: function name within the module
    @type func: string
    @param args: argument string to function call
    @type args: string
    @param abort: if the function is not found, abort or report C{None}
    @type abort: bool

    @returns: the value returned by the function call
    """

    path = mod.split(".")
    lmod = get_module(lang, path, abort)
    func = func or "run"
    call = getattr(lmod, func, None)
    if call is None:
        _raise_or_abort(_("@info",
                          "Module '%(mod)s' does not define "
                          "function '%(func)s'.")
                        % dict(mod=lmod, func=func), abort)
    try:
        res = eval("call(%s)" % args)
    except Exception, e:
        fspec = "%s/%s" % (lmod, func)
        _raise_or_abort(_("@info",
                          "Evaluating function '%(func)s' in module '%(mod)s' "
                          "with argument list %(args)s failed; "
                          "reported error:\n%(msg)s")
                        % dict(func=func, mod=lmod, args=repr(args),
                               msg=e.message), abort)

    return res


def get_result_lreq (langreq, abort=False):
    """
    Like L{get_result}, but the function is specified as
    L{language request<split_req>}.
    """

    return _by_lreq(langreq, get_result, abort=abort)

