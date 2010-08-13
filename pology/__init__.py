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
        (used by the C{check-grammar} sieve)
  - Apertium (U{http://www.apertium.org/}): a free/open-source machine
        translation platform (used by the C{pomtrans} script)

Setup
=====

Although already useful for many day-to-day needs, Pology is currently
in experimental stage of development, and therefore lacks packaging or
any release versioning. But this does not make it difficult to set up.

Pology can be checked out from KDE's Subversion repository::

    $ cd <parent_dir>
    $ svn co svn://anonsvn.kde.org/home/kde/trunk/l10n-support/pology

and set up for use by exporting environment variables::

    $ export PYTHONPATH=<parent_dir>/pology:$PYTHONPATH
    $ export PATH=<parent_dir>/pology/bin:$PATH

(if the intent is only to use Pology's scripts, and they remain in their
default location within Pology's directory tree, C{PYTHONPATH} actually
needs not be exported).

Later on, Pology can be updated to the latest repository version by running::

    $ cd <parent_dir>/pology
    $ svn up

In addition to general scripts, Pology comes with scripts specific to
certain languages. These are made available by::

    $ export PATH=<parent_dir>/pology/lang/LANG/bin:$PATH

where C{LANG} should be replaced by desired language code.

Custom shell completion for Pology scripts is also available::

    $ . <parent_dir>/pology/completion/bash/pology # Bash

Hooks
=====

Hooks are functions with specified sets of input parameters, return values,
processing intent, and behavioral constraints. As such, they can be used
as testing and modification plugins in many processing contexts in Pology.
There are three broad categories of hooks: filtering, validation and
side-effect hooks.

Filtering hooks modify some of their inputs; modifications are done in-place
whenever the input is mutable (like a PO message), otherwise the modified input
is provided in a return value (like a PO message text field).

Validation hooks perform certain checks on their inputs, and return
list of I{annotated spans} or I{annotated parts}, which state all the
encountered errors. Annotated spans are reported when the object of checks
is a piece of text; each span is a tuple of start and end index of
the problematic segment in the text, and a note which explains the problem.
A return value of a text-validation hook will thus be a list::

    [(start1, end1, "note1"), (start2, end2, "note1"), ...]

(note can also be C{None}, when there is nothing to say about the problem).
Annotated parts are reported for an object having more than one distinct text,
such as a PO message. Each annotated part is a tuple stating the problematic
part of the object by name (e.g. C{"msgid"}, C{"msgstr"}), the item index
for array-like parts (e.g. for C{msgstr}), and the list of annotated subparts,
describing problem with the given part (for a PO message, this is a list of
annotated spans, as subparts are text fields).
A return value of an PO message-validation hook will look like::

    [("part1", item1, [(start11, end11, "note11"), ...]),
     ("part2", item2, [(start21, end21, "note21"), ...]),
     ...]

Side-effect hooks neither modify the inputs nor report validation info,
but can be used to whatever purpose which is independent of the processing
chain in which the hook is inserted. For example, a checking hook can be
implemented like this, if it is enough that it reports problems to stdout,
or where clients are not set to use full validation info (spans/parts).
The return value of side-effect hooks is an integer, the number of errors
encountered internally by the hook. Clients may use this number to decide
upon further behavior (e.g. if side-effect hook modified a temporary copy
of a file, client may decide to abandon the result and use the original file
if there were some errors).

In the following, each hook type will be presented, and assigned a formal
type keyword. The type keyword is in the form C{<letter1><number><letter2>},
e.g. C{F1A}. The first letter represents the hook category: C{F} for
filtering hooks, C{V} for validation hooks, and C{S} for side-effect hooks.
The number enumerates the input signature by parameter types, and
the final letter the semantic of input parameters for same input signature.
As a more mnemonic reminder, each type will also be given an informal
signature in the form of C{(param1, param2, ...) -> result};
in them, C{spans} stand for annotated spans, C{parts} for annotated parts, and
C{numerr} for number of errors.

Hooks on pure text:

  - C{F1A} = C{(text)->text}: filters the text
  - C{V1A} = C{(text)->spans}: validates the text
  - C{S1A} = C{(text)->numerr}: side-effects on text

Hooks on text fields in a PO message in a catalog:

  - C{F3A} = C{(text, msg, cat)->text}: filters any text field
  - C{V3A} = C{(text, msg, cat)->spans}: validates any text field
  - C{S3A} = C{(text, msg, cat)->numerr}: side-effects on any text field

  - C{F3B} = C{(msgid, msg, cat)->msgid}: filters an original text field;
        original fields are either C{msgid} or C{msgid_plural}
  - C{V3B} = C{(msgid, msg, cat)->spans}: validates an original text field
  - C{S3B} = C{(msgid, msg, cat)->numerr}: side-effects on an original
        text field

  - C{F3C} = C{(msgstr, msg, cat)->msgstr}: filters a translation text field;
        translation fields are the C{msgstr} array
  - C{V3C} = C{(msgstr, msg, cat)->spans}: validates a translation text field
  - C{S3C} = C{(msgstr, msg, cat)->numerr}: side-effects on a translation
        text field

C{*3B} and C{*3C} series are introduced next to C{*3A} for cases when
it does not make sense for text field to be any other but one of the original,
or translation fields. For example, to process the translation sometimes
the original (obtained by C{msg} parameter) must be consulted.
If a C{*3B} or C{*3C} hook is applied on an inappropriate text field,
the results are undefined.

Hooks on PO entries in a catalog:

  - C{F4A} = C{(msg, cat)->numerr}: filters a message, modifying it
  - C{V4A} = C{(msg, cat)->parts}: validates a message
  - C{S4A} = C{(msg, cat)->numerr}: side-effects on a message (no modification)

  - C{F4B} = C{(hdr, cat)->numerr}: filters a header, modifying it
  - C{V4B} = C{(hdr, cat)->parts}: validates a header
  - C{S4B} = C{(hdr, cat)->numerr}: side-effects on a header (no modification)

Hooks on PO catalogs:

  - C{F5A} = C{(cat)->numerr}: filters a catalog, modifying it in any way;
        (either messages themselves, or removing, adding, moving messages)
  - C{S5A} = C{(cat)->numerr}: side-effects on a catalog (no modification)

Hooks on file paths:

  - C{F6A} = C{(filepath)->numerr}: filters a file, modifying it in any way
  - C{S6A} = C{(filepath)->numerr}: side-effects on a file, no modification

C{*2*} series, which would be C{(text, msg)->...} hooks, has been skipped,
as no need for them was observed so far next to C{*3*} hooks.

Hook Factories
--------------

Since hooks have fixed input signatures by type, the way to customize
a given hook behavior is to produce its function by another function.
The hook-producing function is called a I{hook factory}. It works by
preparing anything needed for the hook, and then defining the hook proper
and returning it, thereby creating a lexical closure around it::

    def hook_factory (parfoo, parbar):

        # perhaps use parfoo, parbar to setup hook definition

        def hook (...):

            # perhaps use parfoo, parbar in the hook definition too

        return hook

In fact, most existing hooks are defined through factories.

Notes on Hooks
--------------

General hooks should be defined in top submodules C{<submod>},
language-dependent hooks in C{lang.<lang>.<submod>},
project-dependent in C{proj.<proj>.<submod>},
and both languge- and project-dependent in C{lang.<lang>.proj.<proj>.<submod>}.
In this way they can be fetched by L{getfunc.get_hook_ireq()} in various
non-code contexts, in particular from Pology utilities which enable users to
insert hooks into processing through command line options or configurations.
(If the hook module implements a single hook function named same as module,
users can select it by giving only the hook module name,without the function name.)

Annotated parts for PO messages returned by hooks are a reduced version,
but a valid instance of highlight specifications used by reporting functions,
e.g. L{report_msg_content()<msgreport.report_msg_content>}.
Annotated parts do not have the optional fourth element of a tuple in
highlight specification, which is used to provide the filtered text against
which spans were constructed, instead of the original text.

In connection with the previous, if a validation hook internally filters
the text and constructs list of problematic spans against such text,
just before returning it can use L{adapt_spans()<diff.adapt_spans>}
to reconstruct spans against the original text.

The documentation of each hook should state its type in the short description,
in square brackets at the end as C{[type ??? hook]}. Input parameters should
be named like in the type lists above, and shouldn't be listed as C{@param:};
only the return is given under C{@return:}, again using one of the above
listed return names, to complete the hook signature.

The documentation to a hook factory should have C{[hook factory]} at
the end of short description. It should normally list all the input parameters,
while the return value should be given as C{@return: type ??? hook}, and
hook signature as the C{@rtype:} field.

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


from pology.colors import ColorString


def rootdir ():
    """
    Get root directory of Pology installation.

    @return: absolute directory path
    @rtype: string
    """

    return os.path.dirname(__path__[0])


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
    @rtype: L{ColorString<colors.ColorString>}
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
    @rtype: L{ColorString<colors.ColorString>}
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
    can be supplied at a later point, using L{with_args<TextTrans.with_args>}
    method, and then the translated string obtained
    by L{to_string<TextTrans.to_string>} method.

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
    can be supplied at a later point, using L{with_args<TextTrans.with_args>}
    method, and then the translated string obtained
    by L{to_string<TextTrans.to_string>} method.

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
        @rtype: L{ColorString<colors.ColorString>}
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

        msgstr = ColorString(msgstr) # before substituting arguments
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

