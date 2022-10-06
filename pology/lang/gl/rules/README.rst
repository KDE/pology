=========================
Pology Rules for Galician
=========================

Usage
=====

To check one or more PO files against the Pology rules for Galician:

#.  Install Pology following the instructions on the first sections of the
    `Pology documentation`_.

#.  Run posieve_ with the `check-rules`_ sieve and ``-s lang:gl``, followed by
    the paths of target files and folders.

    It is also recommended to use a regular expression
    (``-s rulerx:<regular expression>``) or multiple rule IDs
    (``-s rule:<rule ID>``) to restrict rules to those in the ``rag.rules`` and
    ``trasno.rules`` files (e.g. ``-s rulerx:^((no)?PT|rag)``), which contains
    rules that enforce the terminology criteria based on resources from
    `Real Academia Galega`_, the official language authority, or published_ by
    `Proxecto Trasno`_ as approved during their annual gatherings.

    These are some other useful parameters to consider:

    -   ``--skip-obsolete`` skips obsolete messages, messages that used to be
        part of the translations, and are kept in PO files in case they are
        used in the translations again in the future.

    -   ``-s lokalize`` opens affected messages in Lokalize.

If a specific message violates a rule but the message should be left as is, and
it makes no sense to update the rule because the message is a rare exception,
you may add ``skip-rule: <rule ID>`` as a translator comment to the message to
let that message skip the ofending rule. Multiple rule IDs may be specified
separated by commas.

.. _check-rules: http://pology.nedohodnik.net/doc/user/en_US/ch-sieve.html#sv-check-rules
.. _Pology documentation: http://pology.nedohodnik.net/doc/user/en_US/ch-about.html
.. _posieve: http://pology.nedohodnik.net/doc/user/en_US/ch-sieve.html
.. _published: http://termos.trasno.gal/
.. _Real Academia Galega: https://academia.gal

Rule Names
----------

Rule IDs follow this pattern::

    <family>_<term>

These are some examples of rule IDs::

    rag-online
    PT-2010_tab
    clGL-modling_bel
    clGL-all_colar
    expression_error while
    kde-dual_print
    kde_print

The following families exist:

-   ``aaPT``

    Rules for agreements that have been published by `Proxecto Trasno`_ as
    agreements taken before the start of their annual gatherings where
    terminology agreements are usually reached.

-   ``clGL``

    Rules to normalize the language model used in translations beyond the
    agreements reached by `Proxecto Trasno`_.

    These rules only check the Galician text (``msgstr``).

    -   ``clGL-modling``

        Rules that affect the language model (e.g. endings, contractions,
        chosen variants).

    -   ``clGL-all``

        Other normalization rules, usually word choices.

-   ``expression``

    Rules for common expressions or phrases.

    .. note:: In some cases, this family ID includes a suffix that indicates
              the project where the rule is applied.

-   ``gnome``

    Rules specific to GNOME translations.

-   ``kde``

    Rules specific to KDE translations.

-   ``PT-<year>``, ``noPT``

    Rules based on terminology agreements reached by `Proxecto Trasno`_ during
    one of their annual sprints.

    -   ``PT-<year>-gl``

        Rules that affect the language model.

        These rules only check the Galician text (``msgstr``).

-   ``rag``

    Rules based on resources from `Real Academia Galega`_.

Families may include a ``-dual`` suffix that indicates that the rule is a
Galician-to-English counterpart to an English-to-Galician rule.


Environments
------------

Rules support the following environments::

    bittorrent
    cypher
    database
    development
    geography
    graph_theory
    informal


Development
===========

Files
-----

Rules are distributed accross the following files:

-   ``antigas.rules``

    Terminology choices published by `Proxecto Trasno`_ but not approved during
    their annual gatherings, instead coming from their old glossary.

-   ``outras.rules``

    Terminology choices that do not fit any other file.

-   ``rag.rules``

    Terminology choices based on resources from `Real Academia Galega`_.

-   ``trasno.rules``

    Rules that are the result of agreements by `Proxecto Trasno`_.


Credits and License
===================

© 2011-2012 Proxecto Trasno.
© 2019 Adrián Chaves (Gallaecio) <adrian@chaves.io>.
All rights reserved.

Redistribution and use in source (SGML DocBook or plain text) and 'compiled'
forms (SGML, HTML, PDF, PostScript, RTF and so forth) with or without
modification, are permitted provided that the following conditions are met:

-   Redistributions of source code (SGML DocBook or plain text) must retain the
    above copyright notice, this list of conditions and the following
    disclaimer as the first lines of this file unmodified.

-   Redistributions in compiled form (transformed to other DTDs, converted to
    PDF, PostScript, RTF and other formats) must reproduce the above copyright
    notice, this list of conditions and the following disclaimer in the
    documentation and/or other materials provided with the distribution.

THIS DOCUMENTATION IS PROVIDED BY THE PROXECTO TRASNO "AS IS" AND ANY EXPRESS
OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO
EVENT SHALL THE PROXECTO TRASNO BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR
BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER
IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS DOCUMENTATION, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.


.. _Proxecto Trasno: http://trasno.gal/
