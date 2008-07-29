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
    $ export PATH=<parent_dir>/pology/scripts:$PATH

(if the intent is only to use Pology's scripts, and they remain in their
default location within Pology's directory tree, C{PYTHONPATH} actually
needs not be exported).

Later on, Pology can be updated to the latest repository version by running::

    $ cd <parent_dir>/pology
    $ svn up


@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@author: Sébastien Renard <sebastien.renard@digitalfox.org>
@author: Nicolas Ternisien <nicolas.ternisien@gmail.com>

@license: GPLv3
"""

def rootdir():
    """
    Get root directory of Pology installation.

    @return: absolute directory path
    @rtype: string
    """

    return __path__[0]
