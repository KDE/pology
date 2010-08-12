# -*- coding: UTF-8 -*-

"""
Helpers for catalog sieves.

Pology's C{posieve} script processes catalogs with "sieves": objects to which
catalog entries are fed one by one, possibly with finalization phase at the end.
This module contains only some common helpers used by many sieves,
and the following passages primarily describe how sieves are written,
and how clients that use them should behave.


Sieve Layout
============

Every sieve module must define the C{Sieve} class, with some mandatory and
some optional interface methods and instance variables. Here is a simple
sieve which just counts the number of translated messages::

    class Sieve (object):

        def __init__ (self, params):

            self.ntranslated = 0

        def process (self, msg, cat):

            if msg.translated:
                self.ntranslated += 1

        def finalize (self):

            report("Total translated: %d" % self.ntranslated)


The constructor takes as argument an object specifying any sieve parameters
(more on that below). The C{process} method is the one
which gets called for each message by the client, and must take the
message (instance of L{Message_base}) and the catalog which contains it
(L{Catalog}). The client calls the C{finalize} method after no more
messages will be fed to the sieve, but this method needs not be defined
(clients should check before placing the call); also, if C{finalize} is
defined, clients are not obligated to call it.

Another optional method is C{process_header}, which is called by the
client for the header entry::

    def process_header (self, hdr, cat):
        # ...

where C{hdr} is an instance of L{Header}, and C{cat} the containing
catalog. Clients should check for the presence of this method, and if
it is defined, should call it prior to any C{process} call on the
messages from the given catalog. I.e. it is illegal for the client to
switch a catalog between two calls to C{process}, without calling
C{process_header} in between if it exists.

There is also the optional C{process_header_last} method, which is just
like C{process_header}, except that, if present, clients call it I{after}
all C{process} calls on the given catalog::

    def process_header_last (self, hdr, cat):
        # ...

Sieve methods should not abort the program execution in case of errors,
but throw an exception instead. In particular, if C{process} method
throws an instance of L{SieveMessageError}, it means that the sieve
can still process other messages in the same catalog;
if it throws L{SieveCatalogError}, then any following messages
in the same catalog must be skipped, but other catalogs may be processed.
Similarly, if C{process_header} throws L{SieveCatalogError},
then other catalogs may be processed. Any other type of exception
means that the sieve should no longer be used.

C{process} and C{process_header} methods should return C{None} or
an integer exit code. Return value which is neither C{None} nor 0
indicates that while processing was successfull (no exception thrown),
the processed entry should not be passed further along in a sieve chain.


Parameter Handling
==================

The C{params} argument to the sieve constructor is an object with
data attributes that specify parameters influencing the sieve operation.
The sieve module
defines C{setup_sieve} function, which the client calls with
L{SubcmdView} object as argument, to fill in the sieve description and
define all mandatory and optional parameters.
Suppose that a sieve takes a parameter named C{checklevel}, stating
the number of the level at which to perform some checks.
Here is how that sieve would define this parameter::

    def setup_sieve (p):

        p.set_desc("An example sieve.")
        p.add_param("checklevel", int, defval=0,
                    desc="Validity checking level.")

    class Sieve (object):

        def __init__ (self, params):

            if params.checklevel >= 1:
                # ...setup some level 1 validity checks...
            if params.checklevel >= 2:
                # ...setup some level 2 validity checks...
            #...

See L{add_param()<subcmd.SubcmdView.add_param>} method for
details on defining sieve parameters.

Client is not obliged to call C{setup_sieve()}, but must
make sure that the C{params} argument it sends to the sieve has
all the instance variable according to defined parameters.


Catalog Regime Indicators
=========================

There are two boolean instance variables that the sieve may define, and
which the client may check for to decide on the regime in which the
catalogs are opened and closed::

    def __init__ (self, params):

        # These are the defaults:
        self.caller_sync = True
        self.caller_monitored = True

C{caller_sync} instructs the client whether the catalog whose messages
were fed to the sieve should be synced to disk afterwards. If the sieve
does not define this variable, the client should assume C{True} and sync
the catalog. This variable is typically set to C{False} by sieves which
do not modify anything, as it is better for client performance not to
sync the catalog.

C{caller_monitored} tells the client whether it should open catalogs in
monitored mode (see L{Catalog} instructor). If not defined, the client
should assume it C{True}. This is another performance enhancer for the
sieves which do not modify entries.

Most usually, the modifying sieve will set neither of these variables
(i.e. catalogs will be monitored and synced by default), while the
checker sieve will set both to C{False}. A modifying sieve which knows
it will modify all messages may set only C{caller_monitored} to C{False},
while leaving C{caller_sync} undefined (i.e. C{True}).

Note that if a sieve requests no monitoring and/or no syncing, the client
is not obliged to satisfy these requests. On the other hand, if a sieve
does request monitoring and/or syncing (either explicitly or by not
defining them), the client must provide catalogs in that regime. This
is because there may be several sieves operating at the same time, and
monitoring and syncing is usually necessary for the proper operation of
sieves that request it.


Miscellaneous Remarks
=====================

Monitored catalogs have modification counters (see L{Catalog}
and L{Message}), which the sieve may use within its C{process} method
to find out if any modification really took place. The proper way to
do this is to recorder the current counter, and check for increase::

    def process (self, msg, cat):

        startcount = msg.modcount

        # ...
        # ... do some stuff
        # ...

        if msg.modcount > startcount:
            self.nmodified += 1

The I{wrong} way to do it would be to merely check if C{msg.modcount > 0},
because several modification sieves may be operating at the same time,
each increasing the counters.

If the sieve wants to remove the message from the catalog, if at all
possible it should use C{remove_on_sync()} (see L{Catalog}) instead of
C{remove()} method. This is because C{remove()} will probably ruin the
client's iteration over the catalog, so if it must be used, the sieve
documentation should state it clearly.

The sieves should be properly documented in their module comment.
The module comment should contain a short one line description of the sieve,
followed by paragraphs explaining its functionality, followed by list of
sieve parameters.
The C{Sieve} class itself should not be documented in general.
Only if C{process} and C{process_header} methods are returning an exit code,
this should be documented in their own comments.

All methods of the C{Sieve} class other than the above stated standard
interface methods should be kept private. If the sieve module contains
some more widely applicable methods, they should be defined at the top
level, outside of the C{Sieve} class, and properly documented.


@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@author: Sébastien Renard <sebastien.renard@digitalfox.org>
@author: Nicolas Ternisien <nicolas.ternisien@gmail.com>

@license: GPLv3
"""

import locale

from pology import PologyError, _, n_
from pology.comments import manc_parse_flag_list


class SieveError (PologyError):
    """
    Base exception class for sieve errors with special meaning.
    """

    pass


class SieveMessageError (SieveError):
    """
    Exception for single messages.

    If sieve's C{process} method throws it, client is allowed to send
    other messages from the same catalog to the sieve.
    """

    pass


class SieveCatalogError (SieveError):
    """
    Exception for single catalogs.

    If sieve's C{process} or C{process_header} method throw it, client is not
    allowed to send other messages from the same catalog to the sieve,
    but can send messages from other catalogs.
    """

    pass


def parse_sieve_flags (msg):
    """
    Extract sieve flags embedded in manual comments.

    Sieve flags are put into manual comments with the following syntax::

        # |, flag1, flag2, ...

    Some sieves will define certain sieve flags by which their behavior
    can be altered on a particular message.

    @param msg: message to parse
    @type msg: Message

    @returns: parsed flags
    @rtype: set of strings
    """

    return set(manc_parse_flag_list(msg, "|"))


def add_param_filter (p, intro=None):
    """
    Add C{filter} parameter to sieve parameters.

    @param intro: first paragraph for the parameter description
    @type intro: string
    """

    desc = _("@info sieve parameter description",
    "For a module pology.FOO which defines FOO() function, "
    "the hook specification is simply FOO. "
    "If the hook function is named BAR() instead of FOO(), then "
    "the hook specification is FOO/BAR. "
    "Language specific hooks (pology.lang.LANG.FOO) are aditionally "
    "preceded by the language code with colon, as LANG:FOO or LANG:FOO/BAR. "
    "\n\n"
    "If the function is actually a hook factory, the arguments for "
    "the factory are passed separated by tilde: LANG:FOO/BAR~ARGS "
    "(where LANG: and /BAR may be omitted under previous conditions). "
    "The ARGS string is a list of arguments as it would appear "
    "in the function call in Python code, omitting parenthesis. "
    "\n\n"
    "Several hooks can be given by repeating the parameter, "
    "when they are applied in the given order."
    )
    if intro:
        desc = "%s\n\n%s" % (intro, desc)

    p.add_param("filter", unicode, multival=True,
                metavar=_("@info sieve parameter value placeholder",
                          "HOOKSPEC"),
                desc=desc)


def add_param_poeditors (p):
    """
    Add parameters for opening messages in editors to sieve parameters.
    """

    p.add_param("lokalize", bool, defval=False,
                desc=_("@info sieve parameter discription",
    "Open catalogs on reported messages in Lokalize."
    ))


def add_param_entdef (p):
    """
    Add C{entdef} parameter to sieve parameters.
    """

    p.add_param("entdef", unicode, multival=True,
                metavar="FILE",
                desc=_("@info sieve parameter discription; "
                       "in the last line only 'entname' and 'entvalue' "
                       "should be translated",
    "File defining the entities used in messages "
    "(parameter can be repeated to add more files). Entity file "
    "defines entities one per line, in the format:"
    "\n\n"
    "&lt;!ENTITY entname 'entvalue'&gt;"
    ))


def add_param_spellcheck (p):
    """
    Add parameters for spell checking to sieve parameters.
    """

    p.add_param("lang", unicode,
                metavar=_("@info sieve parameter value placeholder", "CODE"),
                desc=_("@info sieve parameter discription",
    "The language dictionary to use."
    "If a catalog header specifies language itself, this parameter takes "
    "precedence over it."
    ))
    p.add_param("env", unicode, seplist=True,
                metavar=_("@info sieve parameter value placeholder", "CODE"),
                desc=_("@info sieve parameter discription",
    "Use supplement word lists for this environment within given language. "
    "Pology configuration and catalog headers may also specify environments, "
    "this parameter takes precedence over them. "
    "Several environments can be given as comma-separated list."
    ))
    p.add_param("accel", unicode, multival=True,
                metavar=_("@info sieve parameter value placeholder", "CHAR"),
                desc=_("@info sieve parameter discription",
    "Character which is used as UI accelerator marker in text fields."
    ))
    p.add_param("markup", unicode, seplist=True,
                metavar=_("@info sieve parameter value placeholder", "KEYWORD"),
                desc=_("@info sieve parameter discription",
    "Markup that can be expected in text fields, as special keyword. "
    "Several markups can be given as comma-separated list."
    ))
    p.add_param("skip", unicode,
                metavar=_("@info sieve parameter value placeholder", "REGEX"),
                desc=_("@info sieve parameter discription",
    "Regular expression to eliminate from spell-checking words that match it."
    ))
    p.add_param("filter", unicode, multival=True,
                metavar=_("@info sieve parameter value placeholder", "HOOK"),
                desc=_("@info sieve parameter discription",
    "F1A or F3A/C hook specification, to filter the translation through "
    "before spell-checking it. "
    "Several hooks can be specified by repeating the parameter."
    ))
    p.add_param("suponly", bool, defval=False,
                desc=_("@info sieve parameter discription",
    "Use only internal supplement word lists, and not the system dictionary."
    ))
    p.add_param("list", bool, defval=False,
                desc=_("@info sieve parameter discription",
    "Output only a simple sorted list of unknown words."
    ))
    add_param_poeditors(p)

