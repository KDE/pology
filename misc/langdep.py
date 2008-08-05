# -*- coding: UTF-8 -*-

"""
Fetch language-dependent modules, functions, data, etc.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import sys
import os

from pology.misc.report import error, warning


def get_module (lang, path, abort=False):
    """
    Import a language-dependent module.

    For example::

        lmod = _import_lang_mod("sr", ["filter", "cyr2lat"])

    will try to import the module C{pology.l10n.sr.cyr2lat.py}.
    The elements of the module path can also contain hyphens, which will
    be converted into underscores when looking for the module.

    If the module cannot be loaded, if C{abort} is C{True} the execution
    will abort with an error message;
    if C{abort} is C{False}, an exception is thrown.

    @param lang: language code
    @type lang: string
    @param path: relative module location within language
    @type path: list of strings
    @param abort: whether to abort execution if the module cannot be loaded
    @type abort: bool

    @returns: imported module
    @rtype: module or C{None}
    """

    subname = ".".join(path)
    subname = subname.replace("-", "_")
    try:
        lmod = __import__("pology.l10n.%s.%s" % (lang, subname),
                          globals(), locals(), [""])
    except ImportError:
        _raise_or_abort("cannot load language module '%s.%s'"
                        % (lang, subname), abort)

    # TODO: Make more detailed analysis why the loading fails: is there
    # such a language, is there such a file, etc.

    return lmod


def split_req (langreq, abort=False):
    """
    Split string of the language-dependent request.

    The language-dependent request is string of the form C{lang:request},
    This is parsed into a tuple of C{(lang, request)} strings. If the
    language cannot be determined, and the execution aborts with a message,
    or C{None} is returned, depending on value of C{abort}

    @param langreq: request specification
    @type langreq: string
    @param abort: if the request cannot be parsed, abort or report C{None}
    @type abort: bool

    @returns: parsed language and request
    @rtype: (string, string)
    """

    lst = langreq.split(":", 1)
    if len(lst) != 2:
        _raise_or_abort("cannot parse language request '%s'" % langreq, abort)

    return tuple(lst)


def get_filter (lang, filtr, abort=False):
    """
    Fetch a language-dependent text filter function.

    Loads the filter function from C{pology.l10n.<lang>.filter.<filtr>} module.
    This module must have the C{process(string) -> string} method defined.

    @param lang: language code
    @type lang: string
    @param filtr: filter name
    @type filtr: string
    @param abort: if the filter is not loadable, abort or report C{None}
    @type abort: bool

    @returns: the filter
    @rtype: (string)->string
    """

    lmod = get_module(lang, ["filter", filtr], abort)
    if not lmod:
        _raise_or_abort("cannot load language filter '%s:%s'" % (lang, filtr),
                        abort)

    if not hasattr(lmod, "process"):
        _raise_or_abort("language filter '%s:%s' does not have the "
                        "process() method" % (lang, filtr), abort)

    # TODO: Check if process() is (string)->string function.

    return lmod.process


def get_filter_lreq (langreq, abort=False):
    """
    Like L{get_filter}, but the filter is specified as
    L{language request<split_req>}.
    """

    return _by_lreq(langreq, get_filter, abort)


def _by_lreq (langreq, getter, abort=False):
    """
    Get language-dependent item using C{getter(lang, request, abort)} method,
    by applying it to parsed language request string.
    """

    lst = split_req(langreq, abort)
    if not lst:
        return None
    lang, request = lst
    return getter(lang, request, abort)


def _raise_or_abort (errmsg, abort, exc=StandardError):
    """
    Raise an exception or abort execution with given error message,
    based on the value of C{abort}.
    """

    if abort:
        error(errmsg)
    else:
        raise exc, errmsg

