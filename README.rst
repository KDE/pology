Pology
======

Pology is a collection of command-line tools and a Python library
for in-depth processing of PO files, which are the predominant
medium for translation of free software and associated documents.

Pology is licensed under the GNU General Public License, version 3.

Installing
----------

Pology may be already packaged for your operating system distribution,
in which case you can install it as usual through the package system.

If you want to use Pology from the source, you can either install it
or use it directly from the source directory.

To build and install Pology into default installation prefix, execute::

    $ cd <pology-source>
    $ mkdir build && cd build
    $ cmake ..
    $ make && make install

CMake, the build system, will notify you of any missing requirements
and provide notes about the command line options that you can use
to customize the build (e.g. installation prefix, etc).

Note that if you install Pology outside of default installation prefix,
you may need to make modify the environment as listed below.

To use Pology directly from the source directory, you only need to
set some environment variables::

  $ export PYTHONPATH=<pology-source>:$PYTHONPATH
  $ export PATH=<pology-source>/bin:$PATH

To this you may also want to enable translations of command-line messages
from Pology scripts, using::

  $ <pology-source>/po/pology/local.sh build [LANG]

where you can supply the language code LANG when you want to build
translations only for that one language.

For more efficient use of Pology scripts in the command line, there are some
shell completion definitions provided for the Bash shell. If you have installed
Pology, you can activate them with::

  $ . <pology-install-prefix>/share/pology/completion/bash/pology

or, if running from source directory::

  $ . <pology-source>/completion/bash/pology


Documentation
-------------

Pology comes with user and API documentation.

If you installed Pology from operating system packages, you will likely
find the user manual at::

  /usr/share/doc/pology/user/en_US/index.html  (one page by chapter)
  /usr/share/doc/pology/user/en_US/index-mono.html  (everything on one page)

and the API documentation at::

  /usr/share/doc/pology/api/en_US/index.html

There may also be some documentation for language-specific support,
e.g. for language LANG and in language LANG (this may sound a bit weird,
but after all, Pology is a piece of software concerned with languages)::

    /usr/share/doc/pology/lang/LANG/LANG/index.html
    /usr/share/doc/pology/lang/LANG/LANG/index-mono.html

If you built and installed Pology yourself, then look for similar paths
in the installation directory that you set.

If you opted to run Pology from sources, you can also build documentation
within the source directory, by executing::

  $ <pology-source>/doc/user/local.sh build  (user manual)
  $ <pology-source>/doc/api/local.sh build  (API documentation)
  $ <pology-source>/lang/LANG/doc/local.sh build  (language-specific)

These lines will produce the ``<pology-source>/doc-html`` directory,
with similar subpaths as above (user/, api/, etc.)


Source code
-----------

Source releases of Pology can be fetched from http://pology.nedohodnik.net/.

The latest development code can be obtained from https://invent.kde.org/sdk/pology.


Contact
-------

Any inquiries should be directed to the mailing list at:

  pology@lists.nedohodnik.net

To subscribe to the mailing list or view archive, visit:

  http://lists.nedohodnik.net/listinfo.cgi/pology-nedohodnik.net

You do not have to be subscribed to send messages, but expect
some moderation holdup in that case.

Currently there is no dedicated bug tracking system,
so use the mailing list for bug reports and patches as well.


Running the tests
-----------------

To run the automated tests, install pytest_ and use it::

    pytest tests/

.. _pytest: https://docs.pytest.org/en/latest/


Authors
-------

This is a non-exhaustive list of people who contributed various stuff::

    Yukiko Bando <ybando@k6.dion.ne.jp>
    Josep Ma. Ferrer <txemaq@gmail.com>
    Karl Ove Hufthammer <karl@huftis.org>
    Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
    Fumiaki Okushi <fumiaki@okushi.com>
    Cristian Oneț <onet.cristian@gmail.com>
    Alexander Potashev (Александр Поташев) <aspotashev@gmail.com>
    Goran Rakic (Горан Ракић) <grakic@devbase.net>
    Sébastien Renard <sebastien.renard@digitalfox.org>
    Nick Shaforostoff (Николай Шафоростов) <shaforostoff@kde.ru>
    Nicolas Ternisien <nicolas.ternisien@gmail.com>
    Marcelino Villarino Aguiar <mvillarino@gmail.com>
    Javier Viñal <fjvinal@gmail.com>
    Manfred Wiese <m.j.wiese@web.de>

Current maintainer is Chusslove Illich <caslav.ilic@gmx.net>.

