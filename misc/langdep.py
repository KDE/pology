# -*- coding: UTF-8 -*-

"""
Fetch language-dependent modules, functions, data, etc.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import sys
import os
import re

from pology.misc.report import error, warning


def get_module (lang, path, abort=False):
    """
    Import a language-dependent module.

    Module is specified by the language code, and the elements of
    the relative path in Pology's package for that language.
    Language can also be C{None}, in which case a language-independent
    module is looked for. For example::

        get_module("sr", ["hook", "cyr2lat"])

    will try to import the C{pology.l10n.sr.cyr2lat} module, while::

        get_module(None, ["hook", "normctx-ooo"])

    will try to import the C{pology.hook.normctx_ooo}.

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
        _raise_or_abort("cannot import module '%s'" % modpath, abort)

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
    C{[lang:]path[/item]}, which is to be parsed into
    C{(lang, path, item)} tuple; if language is not stated,
    its value in the tuple will be C{None}, and likewise for the item.
    The language should be a proper language code, path a sequence of
    identifier-like strings connected by dots, and item also an
    identifier-like string.

    If the item request cannot be parsed,
    either the execution is aborted with an error message,
    or an exception is raised, depending on value of C{abort}.

    @param langreq: request specification
    @type langreq: string
    @param abort: whether to abort execution or if the request cannot be parsed
    @type abort: bool

    @returns: parsed language and request
    @rtype: (string or C{None}, string, string or C{None})
    """

    lst = langreq.split(":")
    if len(lst) > 2:
        _raise_or_abort("cannot parse item request '%s'" % langreq, abort)
    if len(lst) == 1:
        lang, path = [None] + lst
    else:
        lang, path = lst

    lst = path.rsplit("/", 1)
    if len(lst) == 1:
        item = None
    else:
        path, item = lst

    if lang and not _valid_lang_rx.search(lang):
        _raise_or_abort("invalid language '%s' in item request '%s'"
                        % (lang, langreq), abort)
    if not _valid_path_rx.search(path):
        _raise_or_abort("invalid path '%s' in item request '%s'"
                        % (path, langreq), abort)
    if item and not _valid_item_rx.search(item):
        _raise_or_abort("invalid item '%s' in item request '%s'"
                        % (item, langreq), abort)

    path = path.replace("-", "_")
    if item:
        item = item.replace("-", "_")

    return (lang, path, item)


def get_hook (lang, filtr, func=None, abort=False):
    """
    Fetch a language-dependent hook function.

    Loads the hook function from C{pology.l10n.<lang>.hook.<filtr>} module.
    If C{func} is C{None}, the function name defaults to C{process}.

    @param lang: language code
    @type lang: string
    @param filtr: hook module
    @type filtr: string
    @param func: hook function
    @type func: string of C{None}
    @param abort: if the hook is not loadable, abort or report C{None}
    @type abort: bool

    @returns: the hook
    """

    path = ["hook"] + filtr.split(".")
    lmod = get_module(lang, path, abort)
    if func is None:
        func = "process"
    call = getattr(lmod, func, None)
    if call is None:
        _raise_or_abort("hook module '%s:%s' does not define '%s' function"
                        % (lang, filtr, func), abort)

    return call


def get_hook_lreq (langreq, abort=False):
    """
    Like L{get_hook}, but the hook is specified as
    L{language request<split_req>}.
    """

    return _by_lreq(langreq, get_hook, abort)


def _by_lreq (langreq, getter, abort=False):
    """
    Get language-dependent item using C{getter(lang, path, item, abort)}
    method, by applying it to parsed language request string.
    """

    lang, path, item = split_req(langreq, abort)
    return getter(lang, path, item, abort)


def _raise_or_abort (errmsg, abort, exc=StandardError):
    """
    Raise an exception or abort execution with given error message,
    based on the value of C{abort}.
    """

    if abort:
        error(errmsg)
    else:
        raise exc, errmsg

