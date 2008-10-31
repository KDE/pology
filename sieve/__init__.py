# -*- coding: UTF-8 -*-
# sieve.__init__

"""
Catalog sieves.

These modules implement different "sieves" for PO catalogs: objects to which
catalog entries are fed one by one, possibly with finalization phase at the end.
The sieves are presently primarely used by the L{scripts.posieve} script,
but may also export public methods for use in other clients. The following
passages describe how sieves are written, but also how clients that use them
should behave.


The Sieve Layout
================

    Every sieve module must define the C{Sieve} class, with some mandatory and
    some optional interface methods and instance variables. Here is a simple
    sieve which just counts the number of translated messages::

        class Sieve (object):

            def __init__ (self, params, options):

                self.ntranslated = 0

            def process (self, msg, cat):

                if msg.translated:
                    self.ntranslated += 1

            def finalize (self):

                print "Total translated: %d" % self.ntranslated


    The C{__init__} method must take two arguments, the sieve parameters and
    global options (more on that below). The C{process} method is the one
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

    The client ignores return values from all sieve methods, C{process},
    C{process_header}, and C{finalize} alike.


Parameter Handling
==================

    The two arguments to the constructor::

        def __init__ (self, params, options):
            # ...

    are as follows:

    C{options} is the object of the command line options as given
    to the client which uses the sieve, where options are its instance
    variables (e.g. the object produced by the C{OptionParser} from the
    C{optparse} standard library module). The sieve may use this object to
    check for some usual options, like verbose or quite mode. Client may
    specify this object as C{None}.

    C{params} is similarly and object with instance variables, but these
    are parameters intended specifically for the sieve. The sieve module
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

            def __init__ (self, params, options):

                if params.checklevel >= 1:
                    # ...setup some level 1 validity checks...
                if params.checklevel >= 2:
                    # ...setup some level 2 validity checks...
                #...

    See L{add_param()<misc.subcmd.SubcmdView.add_param>} method for
    details on defining sieve parameters.
    Client is not obliged to call C{setup_sieve()}, but must
    make sure that the C{params} argument it sends to the sieve has
    all the instance variable according to defined parameters.


Catalog Regime Indicators
=========================

    There are two boolean instance variables that the sieve may define, and
    which the client may check for to decide on the regime in which the
    catalogs are opened and closed::

        def __init__ (self, options, global_options):

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

    The sieves should be properly documented in their module comment, while
    the C{Sieve} class itself should not be documented. The module comment
    should contain the short one line description of the sieve, followed by
    paragraphs explaining its functionality, followed by list of sieve
    options. Check existing sieves for examples.

    All methods of the C{Sieve} class other than the above stated standard
    interface methods should be kept private. If the sieve module contains
    some more widely applicable methods, they should be defined at the top
    level, outside of the C{Sieve} class, and properly documented.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@author: Sébastien Renard <sebastien.renard@digitalfox.org>
@author: Nicolas Ternisien <nicolas.ternisien@gmail.com>

@license: GPLv3
"""
