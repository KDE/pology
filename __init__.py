# -*- coding: UTF-8 -*-
# pology.__init__

"""
Pology is a framework for custom processing of PO files in field environments,
and a collection of tools based on its foundation, including many smaller
scripts and subscripts which can be used to perform various precision tasks.

Core Pology objects -- abstractions of PO catalog and its entries -- are
designed to allow quick writing of robust scripts. By default, the correctness
of processed objects is strictly enforced, but such that the user may easily
switch it off for better performance. Modifications to PO files on disk are
always explicit, and Pology tries to change as few lines as possible to be
friendly to version control systems.

For typical processing needs of different kinds of data in PO files, Pology
defines many utility functions, such as for word-splitting, markup handling,
wrapping, comment parsing, summary reporting, rule matching, etc.

Pology encourages addition of tools that are not necessarily applicable to PO
files in general, but are intended to support the features and conventions of
specific translation environments. For another, "orthogonal" level of diversity,
Pology also contains language-specific tools, grouped by language under a
dedicated top-level module.

As a design intent, Pology includes tools which have overlapping or even
duplicate functionality. This is to allow for tools better suited to
particular needs, by their collection of features and levels of complexity.

I{"Pology -- the study of POs."}

Requirements
============

Minimum Python version is 2.5.

Required external Python modules:
  - none

Required general software:
  - Gettext >= 0.17

Optional external Python packages:
  - C{python-dbus}: communication with various external applications
        (e.g. U{Lokalize<http://userbase.kde.org/Lokalize>} CAT tool)
  - C{python-enchant}: frontend to various spell-checkers
        (used by most of Pology's spell checking functionality)

Optional general software:
  - LanguageTool (U{http://www.languagetool.org/}): open source language checker
        (used by the L{check-grammar<sieve.check_grammar>} sieve)
  - Apertium (U{http://www.apertium.org/}): a free/open-source machine
        translation platform (used by the L{pomtrans<scripts.pomtrans>} script)

Setup
=====

Although already useful for many day-to-day needs, Pology is currently
in experimental stage of development, and therefore lacks packaging or
any release versioning. But this does not make it difficult to set up.

Pology can be checked out from KDE's Subversion repository::

    $ cd <parent_dir>
    $ svn co svn://anonsvn.kde.org/home/kde/trunk/l10n-support/pology

and set up for use by exporting environment variables::

    $ export PYTHONPATH=<parent_dir>:$PYTHONPATH
    $ export PATH=<parent_dir>/pology/bin:$PATH

(if the intent is only to use Pology's scripts, and they remain in their
default location within Pology's directory tree, C{PYTHONPATH} actually
needs not be exported).

Later on, Pology can be updated to the latest repository version by running::

    $ cd <parent_dir>/pology
    $ svn up

In addition to general scripts, Pology comes with scripts specific to
certain languages. These are made available by::

    $ export PATH=<parent_dir>/pology/l10n/LANG/bin:$PATH

where C{LANG} should be replaced by desired language code.

Custom shell completion for Pology scripts is also available::

    $ . <parent_dir>/pology/completion/bash/pology # Bash


@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@author: Sébastien Renard <sebastien.renard@digitalfox.org>
@author: Nicolas Ternisien <nicolas.ternisien@gmail.com>
@author: Goran Rakic (Горан Ракић) <grakic@devbase.net>
@author: Nick Shaforostoff (Николай Шафоростов) <shaforostoff@kde.ru>

@license: GPLv3
"""

import gettext
import locale
import os


def rootdir ():
    """
    Get root directory of Pology installation.

    @return: absolute directory path
    @rtype: string
    """

    return __path__[0]


def version ():
    """
    Get Pology version string.

    @return: version string
    @rtype: string
    """

    return "0.0.0"


# Collect data paths.
# Either as installed, when the _paths.py module will be available,
# or assume locations within the repository.
try:
    import pology._paths as _paths
    _mo_dir = _paths.mo
except ImportError:
    _mo_dir = os.path.join(rootdir(), "mo")


# Setup translations.
try:
    _tr = gettext.translation("pology", _mo_dir)
except IOError:
    _tr = gettext.NullTranslations()


def _ (_ctxt_, _text_, **kwargs):
    """
    Get translation of the text into user's language.

    If there are any formatting directives in the text,
    they should be named;
    the arguments which substitute them are given
    as keyword values following the text.

    @param _ctxt_: the context in which the text is used
    @type _ctxt_: string
    @param _text_: the text to translate
    @type _text_: string
    @return: translated text if available, otherwise original
    @rtype: string
    """

    ts = TextTrans()
    ts._init(_ctxt_, _text_, None, kwargs)
    return ts.to_string()


def n_ (_ctxt_, _stext_, _ptext_, **kwargs):
    """
    Get translation of the singular/plural text into user's language.

    If there are any formatting directives in the text,
    they should be named;
    the arguments which substitute them are given
    as keyword values following the text.

    The plural deciding number is given by the C{num} keyword argument.
    If no such key exists, or its value is not an integer, an error is raised.

    @param _ctxt_: the context in which the text is used
    @type _ctxt_: string
    @param _stext_: the text to translate for the singular case
    @type _stext_: string
    @param _ptext_: the text to translate for the plural case
    @type _ptext_: string
    @return: translated text if available, otherwise original
    @rtype: string
    """

    ts = TextTrans()
    ts._init(_ctxt_, _stext_, _ptext_, kwargs)
    return ts.to_string()


def t_ (_ctxt_, _text_, **kwargs):
    """
    Get delayed translation of the text into user's language.

    Like L{_()<_>}, but returns delayed translation object
    instead of translated text as string.
    In this way some or all arguments for named formatting directives
    can be supplied at a later point, using L{with_args} method,
    and then the translated string obtaned by L{to_string} method.

    @returns: delayed translation
    @rtype: L{TextTrans}
    """

    ts = TextTrans()
    ts._init(_ctxt_, _text_, None, kwargs)
    return ts


def tn_ (_ctxt_, _stext_, _ptext_, **kwargs):
    """
    Get delayed translation of the singular/plural text into user's language.

    Like L{n_()<_>}, but returns delayed translation object
    instead of translated text as string.
    In this way some or all arguments for named formatting directives
    can be supplied at a later point, using L{with_args} method,
    and then the translated string obtaned by L{to_string} method.

    @returns: delayed translation
    @rtype: L{TextTrans}
    """

    ts = TextTrans()
    ts._init(_ctxt_, _stext_, _ptext_, kwargs)
    return ts


class TextTrans:
    """
    Class for intermediate handling of translated user-visible text.

    Objects of this type are not functional if created manually,
    but only through C{t*_()} translation calls.
    """

    def _init (self, msgctxt, msgid, msgid_plural, kwargs):

        self._msgctxt = msgctxt
        self._msgid = msgid
        self._msgid_plural = msgid_plural
        self._kwargs = kwargs


    def _copy (self):

        # Shallow copy all attributes.
        t = TextTrans()
        t._msgctxt = self._msgctxt
        t._msgid = self._msgid
        t._msgid_plural = self._msgid_plural
        t._kwargs = dict(self._kwargs)
        return t


    def with_args (self, **kwargs):
        """
        Add arguments for substitution in the text, creating new object.

        @returns: new delayed translation
        @rtype: L{TextTrans}
        """

        t = self._copy()
        t._kwargs.update(kwargs)
        return t


    def to_string (self):
        """
        Translate the text to get ordinary string.

        @returns: translated text
        @type: string
        """

        if self._msgid_plural is None:
            trf = _tr.ugettext # camouflaged against xgettext
            if self._msgctxt is None:
                msgstr = trf(self._msgid)
            else:
                msgstr = trf("%s\x04%s" % (self._msgctxt, self._msgid))
                if "\x04" in msgstr:
                    msgstr = self._msgid
        else:
            n = self._kwargs.get("num")
            if n is None or not isinstance(n, int):
                raise PologyError(
                    _("@info",
                      "No '%(arg)s' keyword argument to "
                      "plural translation request.",
                      arg="num"))
            trf = _tr.ungettext # camouflaged against xgettext
            if self._msgctxt is None:
                msgstr = trf(self._msgid, self._msgid_plural, n)
            else:
                msgstr = trf("%s\x04%s" % (self._msgctxt, self._msgid),
                             self._msgid_plural, n)
                if "\x04" in msgstr:
                    msgstr = self._msgid

        msgstr = unicode(msgstr)
        msgstr = msgstr % self._kwargs

        return msgstr


class PologyError (Exception):
    """
    Base exception class for errors in Pology.
    """

    def __init__ (self, msg):
        """
        Constructor.

        @param msg: a description of what went wrong
        @type msg: string
        """

        self._msg = msg


    def  __unicode__ (self):

        return unicode(self._msg)


    def  __str__ (self):

        return self.__unicode__().encode(locale.getpreferredencoding())

