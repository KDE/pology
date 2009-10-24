# -*- coding: UTF-8 -*-

"""
Derive forms and properties of syntagmas by macro expansion.

A syntagma, a set of one or several words with a certain meaning,
in a human language may have many grammar forms and properties.
When the forms are sufficiently regular small perturbations of
the original syntagma (e.g. different word endings by grammar case),
it is possible to construct them by macro derivation,
rather than having to write out each form in full.

This module provides facilities for such macro derivations on syntagmas.
It consists of two elements: the text format for defining macro derivations,
and the derivator class which reads and processes these definitions.
The derivator class is documented in the usual places, and the rest of
this text deals with syntax and semantics of derivation definitions.

As an example application, we consider a dictionary of proper names,
where for each name in source language we want to define the basic name
and some of its forms and properties in target language.


Basic Derivations
=================

For the name in source language "Venus" and in target language "Venera",
we could write the following simplest derivation, which defines only
the basic form in target language::

    Venus: =Venera

C{Venus} is the key syntagma or derivation key,
which is separated by the colon character from its properties.
Properties are written as C{KEY=VALUE} pairs, and separated by commas;
in C{=Venera}, the key is empty string and the value is C{Venera}.

We would now like to define some grammar cases in target language.
"Venera" is the nominative (basic) case, so instead of empty string
we use C{nom} as its key; other cases that we want to define are
genitive (C{gen}) "Venere", dative (C{dat}) "Veneri",
and accusative (C{acc}) "Veneru". Then we can write::

    Venus: nom=Venera, gen=Venere, dat=Veneri, acc=Veneru

By this point, everything is written out manually, there are no
"macro derivations" to speak of. But observe the difference between
different cases of "Venera" -- only the final letter is changing.
Therefore, we first write the following I{base} derivation for
this system of case endings alone, called "declension-1"::

    |declension-1: nom=a, gen=e, dat=i, acc=u

A base derivation is normally also I{hidden}, by prepending
the pipe character to its syntagma. We make it hidden because it should
be used only in other derivations, and does not represent a proper entry
in our dictionary example; in the processing stage, derivations with
hidden syntagmas will not be offered on queries into dictionary.
We can now use this derivation to shorten the derivation for "Venus"::

    Venus: Vener|declension-1

Here C{Vener} is the root, and C{|declension-1} is the expansion,
referencing the previously defined base derivation.
The final forms are derived by inserting the property values found in
the expansion (C{a} from C{nom=a}, C{e} from C{gen=e}, etc.)
at the position where the expansion occurs, for each of the keys
found in the expansion, thus obtaining the expected properties
(C{nom=Venera}, C{gen=Venere}, etc.) for current derivation.

Note that C{declension-1} may be a too verbose name for the base derivation.
If the declension type can be identified by the stem of the nominative case
(here {a}), to have much more natural looking derivations we could write::

    |a: nom=a, gen=e, dat=i, acc=u
    Venus: Vener|a

Now the derivation looks just like the nominative case alone,
only having the root and nominative stem separated by the pipe.

The big gain of this transformation is, of course, when there are many
syntagmas having the same declension type.
Other such source-target pairs could be "Earth" and "Zemlja",
"Europe" and "Evropa", "Rhea" and "Reja", so we can write::

    |a: nom=a, gen=e, dat=i, acc=u
    Venus: Vener|a
    Earth: Zemlj|a
    Europe: Evrop|a
    Rhea: Rej|a

This is a good point to note that derivations are separated by newlines.
If necessary, single derivation can be split into several lines
by putting a backslash at the end of each line but the last.

Expansion is implicitly terminated by a whitespace or a comma, or by
another expansion. If these characters are part of the expansion itself
(i.e. of the syntagma of the derivation it refers to), or the text continues
right after the expansion without a whitespace, braces can be used
to explicitly delimit the expansion::

    Alpha Centauri: Alf|{a}-Kentaur

Any character which is special in the current context may be escaped
with a backslash. Only the second colon here is a separator::

    Destination\\: Void: Odredišt|{e}: ništavilo

A single derivation may state more than one key syntagma, comma-separated.
For example, if the syntagma in source language has several spellings::

    Iapetus, Japetus: Japet|

A syntagma can also be an empty string. This is useful for base derivations
when nominative-stem naming is used and a nominative stem happens to be null
-- such as in the previous example.
The derivation to which this empty expansion refers to would be::

    |: nom=, gen=a, dat=u, acc=

Same-valued properties do not have to be repeated, but instead
several keys can be linked to one value, ampersand-separated.
The previous base derivation could thus be defined as::

    |: nom&acc=, gen=a, dat=u

Derivation definitions may contain the # to end of line comments::

    # A comment.
    Venus: Vener|a # another comment


Multiple Expansions
===================

A single derivation may contain more than one expansion.
There are two distinct types of multiple expansion, outer and inner.

Outer multiple expansion is used when it is advantageous to split
derivations by grammar classes. The examples so far were only deriving
grammar cases of nouns, but we may also want to define possesive adjective
per noun. For "Venera", the possesive adjective in nominative is "Venerin".
Using the same nominative-stem naming of base derivations, we could write::

    |a: …  # as above
    |in: …  # posessive adjective
    Venus: Vener|a, Vener|in

Expansions are resolved from left to right, with the expected effect
of derived properties accumulating along the way.
The only question is what happens if two expansions produce properties
with same keys but different values -- then the value produced by
the last (rightmost) expansion takes precedence.

Inner multiple expansion is used on multi-word syntagmas, when
more than one word needs expansion. For example, the target pair
of "Orion Nebula" is "Orionova maglina", where the first word
is a possesive adjective, and the second a noun.
The derivation for this is::

    |a: …  # as above
    |ova>: …  # posessive adjective as noun, > is not special
    Orion Nebula: Orion|ova> maglin|a

Inner expansions are resolved from left to right, such that all expansions
right of the expansion currently resolved are treated as plain text.
If all expansions define same properties by key, then the derivation
will have all those properties, with values derived as expected.
However, if there is a mismatch between properties, then the derivation
will get the intersection of them, i.e. only those common to all expansions.

Both outer and inner expansion may be used in a single derivation.


Expansion Masks
===============

An expansion can be made not to result in all properties of referred to
derivation, but only a subset of them, and with modification to keys.

Consider again the example of "Orion Nebula" and "Orionova maglina".
Here the possesive adjective "Orionova" has to be matched in both case
and gender to the noun "maglina" (feminine).
Earlier we defined a special adjective-as-noun derivation C{|ova},
which was also specialized to the feminine gender of "maglina",
but now we want to make use of full posessive adjective derivation instead.
Let the property keys of this derivation be of the form C{nommas}
(nominative masculine), C{genmas} (genitive masculine), …, C{nomfem}
(nominative feminine), C{genfem} (genitive feminine), ….
If we use the stem of nominative masculine form, "Orionov", to name
the possesive adjective base derivation, then we get::

    |ov: nommas=…, genmas=…, …, nomfem=…, genfem=…, …
    Orion Nebula: Orion|ov~...fem maglin|a

C{|ov~...fem} here is a masked expansion. It states to expand only
those properties which have keys starting with any three characters
and ending in C{fem}, as well as to drop C{fem} (being a constant)
from the resulting keys. This precisely selects only the feminine
forms of the possesive adjective and transforms their keys into
noun keys needed to match with those of C{|a} expansion.

We could also use this same masked expansion to produce the earlier
specialized adjective-as-noun base derivation::

    |ov: nommas=…, genmas=…, …, nomfem=…, genfem=…, …
    |ova>: |ov~...fem
    Orion Nebula: Orion|ova> maglin|a

A special case of masked expansion is when there are no variable
characters in the mask (no dots). In the pair "Constellation of Cassiopeia"
and "Sazvežđe Kasiopeje", the "of Cassiopeia" is constructed by genitive
case, "Kasiopeje", avoiding the need for preposition. If "Cassiopeia"
has its own derivation, then we can use it like this::

    Cassiopeia: Kasiopej|a
    Constellation of Cassiopeia: Sazvežđ|e |Cassiopeia~gen

The {|e} is the usual nominative-stem expansion.
The C{|Cassiopeia~gen} expansion produces only the genitive form
of "Cassiopeia", but with an empty property key.
If this expansion would be treated as normal inner expansion,
it would cancel all forms produced by C{|e} expansion,
since none of them has an empty key.
Instead, when an expansion produces a single form with empty key,
its value is treated as raw text and inserted into all forms produced
to that point. Just as if we had written::

    Constellation of Cassiopeia: Sazvežđ|e Kasiopeje

Sometimes the default modification of propety keys, removal
of all fixed characters in the mask, is not exactly what we want.
This should be a rare case, but if it happens, the mask can also
be given a I{key extender}. For example, if we would want to select
only feminine forms of {|ov} expansion, but preserve the C{fem} ending
of the resulting keys, we could write::

    Foobar: Fubar|ov~...fem%*fem

The key extender in this expansion is C{%*fem}.
For each resulting property, the final key is constructed by substituting
every asterisk, C{*}, with the key resulting from C{~...fem} mask.
Thus, here the C{fem} ending is added to every key, as desired.

Expanded values can have their capitalization changed.
By prepending circumflex (C{^}) or backtick (C{`}) to the expansion
reference, the first letter in resulting values is uppercased or lowercased,
respectively. We could derive the pair "Distant Sun" and "Udaljeno sunce"
by using "Sun" and "Sunce" (note the case difference in "Sunce"/"sunce")
like this::

    Sun: Sunc|e  # this defines uppercase first letter
    Distant Sun: Dalek|o> |`Sun  # this needs lowercase first letter


Special Properties
==================

Property keys may be given several endings, to make these properties
behave differently from what was described so far.
These ending are not treated as part of the property key itself,
so they should not be given when querying derivations by syntagma
and property key.

I{Cutting} properties are used to avoid the normal insertion on expansion.
For example, if we want also to define the gender of nouns
through base expansions, we could come up with::

    |a: nom=a, gen=e, dat=i, acc=u, gender=fem
    Venus: Vener|a

However, this will cause the C{gender} property in expansion to become
C{Venerafem}. For the C{gender} property to be taken verbatim,
without adding the segments from the calling derivation around it,
we add make it a cutting property by appending exclamation ({!}) to its key::

    |a: nom=a, gen=e, dat=i, acc=u, gender!=fem

Now when dictionary is queried for C{Venus} syntagma and C{gender} property,
we will get the expected C{fem} value.

Cutting properties also behave differently in multiple inner expansions.
Instead of being canceled when not all inner expansions define it,
simply the rightmost value is taken -- just like in outer expansions.

I{Terminal} properties are those hidden with respect to expansion,
i.e. they are not taken into the calling derivation.
A property is made terminal by appending a dot (C{.}) to its key.
For example, if some derivations have the short description property C{desc},
we typically do not want it to propagate into calling derivations
which happen not to override it by outer expansion::

    Mars: Mars|, desc.=planet
    Red Mars: Crven|i> Mars|  # a novel

I{Canceling} properties will cause a previously defined property with
the same key to be removed from the collection of properties.
Canceling property is indicated by ending its key with a circumflex (C{^}).
The value of canceling property has no meaning, and can be anything.
Canceling is useful in expansions and alternative derivations (see below),
where some properties introduced by expansion or alternative fallback
should be removed from the final collection of properties.


Text Tags
=========

Key syntagmas and property values can be equipped with simple tags,
which start with tag name in the form C{~TAG} and extend to next tag
or end of text.
For example, when deriving people names, we may want to tag their
first and last names, using tags C{~fn} and C{~sn} respectively::

    ~fn Isaac ~sn Newton: ~fn Isak| ~sn Njutn|

In default processing, these tags are simply ignored, syntagmas
and property values are reported as if there were no tags.
However, derivator objects (which process derivation definitions) can
take as optional parameters transformation functions for key syntagmas
and property values, to which  tagged text segments will be passed,
so that they can act on particular tags when producing the final text.

Tag is implicitly terminated by whitespace or comma (or colon in case of
key syntagmas), but when none of these characters can be put after a tag,
tag name can be explicitly delimited by braces (C{~{TAG}}).


Alternative Derivations
=======================

Sometimes there may be several alternative derivations to the given syntagma.
The default (in suitable sense) derivation is written as usual, and
other derivations are written under named I{environments}.

For example, if deriving a transcribed person's name, there may be several
versions of the transcription. For "Isaac Newton", the usual, traditional
transcription may be "Isak Njutn", while the modern transcription
(i.e. applied to a living person of that name) would be "Ajzak Njuton".
Then we could have an environment C{modern} and write::

    Isaac Newton: Isak| Njutn|
        @modern: Ajzak| Njuton|

Environment name is preceded with C{@} and ended with colon,
after which the usual derivation follows.
There can be any number of non-default environments.

The immediate question that arises is how are expansions treated in
non-default environments. In the previous example, what does C{|} expansion
resolve to in C{modern} environment? This depends on processing.
By default, processing will require that derivations referenced
by expansions also have matching environments. If C{|} were defined as::

    |: nom=, gen=a, dat=u, acc=

then expansion of "Isaac Newton" in C{modern} environment would fail.
Instead, it would be necessary to define the base derivations as::

    |: nom=, gen=a, dat=u, acc=
        @modern: nom=, gen=a, dat=u, acc=

However, this may not be a very useful requirement. As can be seen in this
example already, in many cases base derivations are likely to be same for
all environments, so they would be needlessly duplicated.
It is therefore possible to define environment fallback chain in processing,
such that when a derivation in certain environment is requested,
environments in the fallback chain are tried in order.
In this example, if the chain would be given as C{("modern", "")}
(name of default environment is empty string), then we could write::

    |: nom=, gen=a, dat=u, acc=
    Isaac Newton: Isak| Njutn|
        @modern: Ajzak| Njuton|
    Charles Messier: Šarl| Mesje|

When derivation of "Isaac Newton" in C{modern} environment is requested,
the default expansion for C{|} will be used, and the derivation will succeed.
Derivation of "Charles Messier" in C{modern} environment will succeed too,
because the environment fallback chain is applied throughout;
if "Charles Messier" had different C{modern} transcription,
we would have explicitly provided it.


Treatment of Whitespace
=======================

ASCII whitespace in derivations, namely the space, tab and newline,
are not preserved as-is, but by default I{simplified} in all final forms.
The simplification consists of removing all leading and trailing whitespace,
and replacing all inner sequences of whitespace with a single space.
These two derivations are equivalent::

    Venus: nom=Venera
    Venus  :  nom =  Venera

but these two are not::

    Venus: Vener|a
    Venus: Vener  |a

because the two spaces between the root C{Vener} and expansion {|a} become
inner spaces in resulting forms, so they get converted into a single space.

Non-ASCII whitespace, on the other hand, is preserved as-is.
This means that significant whitespace, like non-breaking space,
zero width space, word joiners, etc. can be used normally.

For property values and key syntagmas it is possible to have different
treatment of whitespace, through an optional parameter to the derivator object.
This parameter is a transformation function to which text segments
with raw whitespace are passed, so it can do with them as desired.

Due to simplifaction of whitespace, indentation of key syntagmas and
environment names is not significant, but it is enforced to be consistent.
This will fail parsing::

    Isaac Newton: Isak| Njutn|
        @modern: Ajzak| Njuton|
     George Washington: Džordž| Vašington|  # inconsitent indent
      @modern: Džordž| Vošington|  # inconsitent indent

This is done both in order to enforce a single indentation style when
several people are working on the same source, as well as to discourage
indentation schemes unfriendly to version control systems, such as::

    Isaac Newton: Isak| Njutn|
         @modern: Ajzak| Njuton|
    George Washington: Džordž| Vašington|
              @modern: Džordž| Vošington|  # inconsitent indent

(Unfriendliness to VCS comes from the need to reindent lines which are
otherwise unchanged, merely in order to keep them aligned to lines
which were actually changed.)


Uniqueness, Ordering and Inclusions
===================================

Within given source of derivations, each derivation must have at least one
unique key syntagma, because it is used as derivation key on lookups.
These two derivations are in conflict::

    Mars: Mars|  # the planet
    Mars: mars|  # the chocholate bar

There are several possibilities to resolve conflicts in derivation keys.
The simplest possibility is to have keyword-like key syntagmas,
if key syntagmas themselves do not need to be human readable::

    marsplanet: Mars|
    marsbar: mars|

If key syntagmas do have to be human readable, then one option is
to extend them in human readable way as well::

    Mars (planet): Mars|
    Mars (chocolate bar): mars|

This too is not acceptable if key syntagmas are intended to be of
equal weight to derived syntagmas, like in a dictionary application.
In that case, the solution is to add a hidden keyword-like syntagma
to both derivations::

    Mars, |marsplanet: Mars|
    Mars, |marsbar: mars|

Processing will now silently eliminate "Mars" as key to either derivation,
because it is conflicted, and leave only C{marsplanet} as key for the first
and C{marsbar} as key for the second derivation.
It is these keys that are also used in expansions, to point
to appropriate derivation.
However, when querying the derivator object for key syntagmas
by derivation key C{marsplanet}, only "Mars" will be returned,
because C{marsplanet} is hidden; likewise for C{marsbar}.

Ordering of derivations is not important. The following order is valid,
althoug the expansion C{|Venus~gen} is seen before the derivation of "Venus"::

    Merchants of Venus: Trgovc|i> s |Venus~gen
    Venus: Vener|a

This enables derivations to be ordered naturally, e.g. alphabetically,
instead of being forced to perturb the order due to technical demans.

It is possible to include one file with derivations into another.
A typical case would be to split the base derivations into a separate file,
and include it into the visible derivations. If basic derivations are
defined in C{base.sd}::

    |: nom=, gen=a, dat=u, acc=, gender!=mas
    |a: nom=a, gen=e, dat=i, acc=u, gender!=fem
    …

then the file C{solarsys.sd}, placed in the same directory, can include
C{base.sd} and use its derivations in expansions like this::

    >base.sd
    Mercury: Merkur|
    Venus: Vener|a
    Earth: Zemlj|a
    …

C{>} is the inclusion directive, followed by the absolute or relative path
to file to be included. If the path is relative, it always relative to
the including file, and not e.g. to some externaly specified set of
inclusion paths.

If the including and included file contain a derivation with same key
syntagmas, that is not a conflict. On expansion, first the derivations
in the current file are checked, and if the referenced derivation
is not there, then the included files are checked in reverse
to the inclusion order. In this way, it is possible to override
some of base derivations in only one or few including files.

Inclusions are "shallow": only the derivations in the included file
itself are visible (available for use in expansions) in the including file.
In other words, if file A includes file B, and file B includes file C,
then derivations from C are not automatically visible in A; to use them,
A must explicitly include C.

Shallow inclusion and ordering-independent resolution of expansions
together make it possible to have mutual inclusions: A can include B,
while B can include A. This is an important capability when building
derivations of taxonomies. While derivation of X naturally belongs to A
and of Y to B, X may nevertheless be used in expansion in another
derivation in B, and Y in another derivation in A.

When a derivator object is created, files with derivations are imported
into it one by one, to make them available for queries.
Derivations from imported files (but not from files included by them,
according to shallow inclusion principle) all share a single namespace.
This means that key syntagmas (derivation keys) across imported files
can conflict, and must be resolved by one of outlined methods.

Design guideline behind the inclusion mechanism was that in each collection
of derivations, each I{visible} derivation, one which is available
to queries by the user of the collection, must be accessible by at least
one unique key, which does not depend on the underlying file hierarchy.


Error Handling
==============

There are three levels of errors which may happen in derivations.

The first level are syntax errors, such as derivation missing a colon which
separates key syntagma from the rest, unclosed braced expansion, etc.
These errors are reported as soon as a derivation source is imported into
the derivator object.

The second level of errors are expansion errors, such as an expansion
pointing to undefined derivation, or an expansion mask discarding everything.
These errors are reported by the derivator object lazily,
when the problematic derivation is actually looked up for the first time.

On the third level are semantic errors, such as if we want every derivation
to have a certain property, or C{gender} property to have only values C{mas},
C{fem} and C{neu}, and a derivation violates these requirements.
At the moment, there is no special way to catch these errors.

In future, a mechanism (in form of file-level directives, perhaps)
may be introduced to immediately report reference errors on request,
and to constrain property keys and property values to avoid semantic errors.
Until then, the way to validate a collection of derivations would be
to write a piece of Python code which will import all files into
a derivator object, iterate through derivations (this alone will catch
expansion errors) and check for semantic errors.


Miscellaneous Bits
==================

C{syntax/} directory in Pology distribution contains syntax highlighting definitions for syntagma derivations for some text editors.


@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import os
import locale
import re
import hashlib
import copy
import cPickle as pickle

from pology.misc.report import warning
from pology.misc.normalize import simplify
from pology.misc.resolve import first_to_upper, first_to_lower


# FIXME: Temporary until i18n ready.
def _p (x, y):
    return y


# ----------------------------------------
# Error handling.

class SynderError (Exception):

    def __init__ (self, msg, code, source=None, pos=None):
        """
        Constructor.

        All the parameters are made available as instance variables.

        @param msg: description of what went wrong
        @type msg: string
        @param code: numerical ID of the problem
        @type code: int
        @param source: name of the source in which the problem occured
        @type source: string
        @param pos: line or line and column in the source
            in which the problem occured
        @type pos: int or (int, int)
        """

        self.msg = msg
        self.code = code
        self.source = source
        if isinstance(pos, tuple):
            self.line, self.col = pos
        else:
            self.line = pos
            self.col = None


    def __unicode__ (self):

        if self.source is None:
            s = (_p("context of error message",
                    "[synder-%(code)d]: %(msg)s")
                 % dict(code=self.code, msg=self.msg))
        elif self.line is None:
            s = (_p("context of error message",
                    "[synder-%(code)d] in %(source)s: %(msg)s")
                 % dict(code=self.code, msg=self.msg, source=self.source))
        elif self.col is None:
            s = (_p("context of error message",
                    "[synder-%(code)d] at %(source)s:%(line)d: %(msg)s")
                 % dict(code=self.code, msg=self.msg, source=self.source,
                        line=self.line))
        else:
            s = (_p("context of error message",
                    "[synder-%(code)d] at %(source)s:%(line)d:%(col)d: %(msg)s")
                 % dict(code=self.code, msg=self.msg, source=self.source,
                        line=self.line, col=self.col))

        return unicode(s)


    def __str__ (self):

        return self.__unicode__().encode(locale.getpreferredencoding())


# ----------------------------------------
# Caching.

# Cache for file sources, by absolute path.
_parsed_sources = {}


def empty_source_cache ():
    """
    Clear all cached sources.

    When file with derivations is loaded, its parsed form is cached,
    such that future load instructions on that same path
    (e.g. when the path is included from another file)
    do not waste any extra time and memory.
    This function erases all sources from the cache,
    when loading files anew on future load instructions is desired.
    """

    _parsed_sources.clear()


# ----------------------------------------
# Parsing.

_ch_escape          = "\\"
_ch_comment         = "#"
_ch_props           = ":"
_ch_env             = "@"
_ch_ksyn_hd         = "|"
_ch_prop_sep        = ","
_ch_pkey_sep        = "&"
_ch_pval            = "="
_ch_exp             = "|"
_ch_cutprop         = "!"
_ch_termprop        = "."
_ch_remprop         = "^"
_ch_exp_mask        = "~"
_ch_exp_mask_pl     = "."
_ch_exp_kext        = "%"
_ch_exp_kext_pl     = "*"
_ch_exp_upc         = "^"
_ch_exp_lwc         = "`"
_ch_tag             = "~"
_ch_tag_sep         = "&"
_ch_grp_opn         = "{"
_ch_grp_cls         = "}"
_ch_inc             = ">"

_strict_ws = " \t\n" #set((" ", "\t", "\n"))
_ch_nl = "\n"


def _parse_string_w (instr, srcname):

    ctx = _ctx_void
    dobj = _SDSource(srcname)
    ctx_stack = []

    pos = 0
    bpos = (1, 1)
    while True:
        handler = _ctx_handlers[ctx]
        nctx, ndobj, descend, pos, bpos = handler(dobj, instr, pos, bpos)
        if nctx is not None:
            if descend:
                ctx_stack.append((ctx, dobj))
            ctx, dobj = nctx, ndobj
        elif ctx_stack:
            ctx, dobj = ctx_stack.pop()
        else:
            return dobj


_anonsrc_count = [0]

def _parse_string (instr, srcname=None):

    # Try to return parsed source from cache.
    if srcname in _parsed_sources:
        return _parsed_sources[srcname]

    if srcname is None:
        srcname = _p("automatic name for anonymous input stream",
                     "<stream-%(num)s>") % dict(num=_anonsrc_count[0])
        _anonsrc_count[0] += 1

    source = _parse_string_w(instr, srcname)

    # Cache the source by name (before procesing includes).
    _parsed_sources[srcname] = source

    # Load included sources.
    source.incsources = _include_sources(source, source.incsources)

    return source


def _parse_file (path):

    # Try to return parsed source from cache.
    apath = os.path.abspath(path)
    if apath in _parsed_sources:
        return _parsed_sources[apath]

    # Try to load parsed source from disk.
    source = _read_parsed_file(apath)
    if source:
        # Set attributes discarded on compiling.
        source.name = path

    if source is None:
        # Parse the file.
        ifs = open(path, "r")
        lines = ifs.readlines()
        ifs.close()

        m = re.search(r"^#\s+~~~\s+(\S+)\s+~~~\s*$", lines[0]) if lines else None
        enc = m and m.group(1) or "UTF-8"
        lines = [x.decode(enc) for x in lines]

        instr = "".join(lines)
        source = _parse_string_w(instr, path)

        # Write out parsed file.
        # Temporarily discard attributes relative to importing.
        iname = source.name
        source.name = None
        _write_parsed_file(source, apath)
        source.name = iname

    # Cache the source by absolute path (before procesing includes).
    _parsed_sources[apath] = source

    # Load included sources.
    source.incsources = _include_sources(source, source.incsources)

    return source


def _include_sources (source, incpaths):

    incsources = []
    incroot = os.path.dirname(os.path.abspath(source.name))
    for incpath in incpaths:
        # If included path relative, make it relative to current source.
        if not incpath.startswith(os.path.sep):
            path = os.path.join(incroot, incpath)
        else:
            path = incpath
        if not os.path.isfile(path):
            # FIXME: Position of include directive in the file lost,
            # propagate it to this place to report error properly.
            raise SynderError(
                _p("error message",
                   "Included file '%(incpath)s' not found at '%(path)s'.")
                   % locals(),
                1101, source.name)
        incsource = _parse_file(path)
        incsources.append(incsource)

    return incsources


_compfile_suff = "c"
_compfile_dver = "0003"
_compfile_hlen = hashlib.md5().digest_size * 2

def _write_parsed_file (source, path):

    cpath = path + _compfile_suff
    try:
        fhc = open(cpath, "wb")
        fh = open(path, "rb")
    except:
        return False

    # Write out data version and file hash.
    fhc.write(_compfile_dver)
    hasher = hashlib.md5
    fhc.write(hashlib.md5(fh.read()).hexdigest() + "\n")
    pickle.dump(source, fhc, 2) # 0 for ASCII instead of binary
    fhc.close()

    return True


def _read_parsed_file (path):

    cpath = path + _compfile_suff
    try:
        fhc = open(cpath, "rb")
        fh = open(path, "rb")
    except:
        return None

    # Check if data version and file hashes match.
    fdverc = fhc.read(len(_compfile_dver))
    if fdverc != _compfile_dver:
        return None
    fhash = hashlib.md5(fh.read()).hexdigest()
    fhashc = fhc.read(_compfile_hlen + 1)[:-1]
    if fhash != fhashc:
        return None

    # Load the compiled source.
    source = pickle.load(fhc)

    return source


# ----------------------------------------
# Parsing context handlers.

def _ctx_handler_void (source, instr, pos, bpos):

    obpos = bpos
    testsep = lambda c: (c not in _strict_ws and [""] or [None])[0]
    substr, sep, pos, bpos = _move_to_sep(instr, pos, bpos, testsep, wesc=False)

    if sep is not None:
        indent = instr[pos - bpos[1] + 1:pos]
        if instr[pos] == _ch_inc:
            return _ctx_inc, source, True, pos, bpos
        elif instr[pos] == _ch_env:
            if not source.derivs:
                raise SynderError(
                    _p("error message",
                       "No derivation yet for which to start an environment."),
                    1002, source.name, bpos)
            if source.indenv is None:
                source.indenv = indent
            if indent != source.indenv:
                raise SynderError(
                    _p("error message",
                       "Inconsistent indenting of environment head."),
                    1003, source.name, bpos)
            deriv = source.derivs[-1]
            env = _SDEnv(deriv, bpos)
            deriv.envs.append(env)
            return _ctx_env, env, True, pos, bpos
        else:
            if source.indderiv is None:
                source.indderiv = indent
            if indent != source.indderiv:
                raise SynderError(
                    _p("error message",
                       "Inconsistent indenting of derivation head."),
                    1001, source.name, bpos)
            deriv = _SDDeriv(source, bpos)
            source.derivs.append(deriv)
            ksyn = _SDSyn(deriv, bpos)
            deriv.syns.append(ksyn)
            return _ctx_ksyn, ksyn, True, pos, bpos
    else:
        return None, None, False, pos, bpos


_seps_ksyn = set((_ch_prop_sep, _ch_props, _ch_tag, _ch_nl))

def _ctx_handler_ksyn (ksyn, instr, pos, bpos):

    opos, obpos = pos, bpos
    testsep = lambda c: c in _seps_ksyn and c or None
    substr, sep, pos, bpos, isesc = _move_to_sep(instr, pos, bpos, testsep,
                                                 repesc=True)

    substrls = substr.lstrip(_strict_ws)
    if (    not ksyn.segs and substrls.startswith(_ch_ksyn_hd)
        and not isesc[len(substr) - len(substrls)]
    ):
        ksyn.hidden = True
        substr = substr.lstrip()[len(_ch_ksyn_hd):]

    if substr or not ksyn.segs:
        ksyn.segs.append(_SDText(ksyn, obpos, substr))

    if sep == _ch_props:
        deriv = ksyn.parent
        env = _SDEnv(deriv, bpos)
        deriv.envs.append(env)
        prop = _SDProp(env, bpos)
        env.props.append(prop)
        return _ctx_pkey, prop, False, pos, bpos
    elif sep == _ch_prop_sep:
        deriv = ksyn.parent
        ksyn = _SDSyn(deriv, bpos)
        deriv.syns.append(ksyn)
        return _ctx_ksyn, ksyn, False, pos, bpos
    elif sep == _ch_tag:
        tag = _SDTag(ksyn, bpos)
        ksyn.segs.append(tag)
        return _ctx_tag, tag, True, pos, bpos
    else:
        raise SynderError(
            _p("error message",
               "Unexpected end of derivation head started at %(lin)d:%(col)d.")
            % dict(lin=obpos[0], col=obpos[1]),
            1010, ksyn.parent.parent.name, bpos)


def _ctx_handler_env (env, instr, pos, bpos):

    obpos = bpos
    testsep = lambda c: c == _ch_props and c or None
    substr, sep, pos, bpos = _move_to_sep(instr, pos, bpos, testsep)

    if sep == _ch_props:
        env.name = substr[len(_ch_env):]
        if not env.name:
            raise SynderError(
                _p("error message",
                   "Empty environment name."),
                1021, env.parent.parent.name, obpos)
        for oenv in env.parent.envs[:-1]:
            if env.name == oenv.name:
                raise SynderError(
                    _p("error message",
                       "Repeated environment name '%(env)s'.")
                    % dict(env=oenv.name),
                    1022, env.parent.parent.name, obpos)
        prop = _SDProp(env, bpos)
        env.props.append(prop)
        return _ctx_pkey, prop, False, pos, bpos
    else:
       raise SynderError(
        _p("error message",
           "Unexpected end of environment head started at %(lin)d:%(col)d.")
        % dict(lin=obpos[0], col=obpos[1]),
        1020, env.parent.parent.name, bpos)


_seps_pkey = set((_ch_pval, _ch_prop_sep, _ch_exp, _ch_tag, _ch_nl))

def _ctx_handler_pkey (prop, instr, pos, bpos):

    opos, obpos = pos, bpos
    testsep = lambda c: c in _seps_pkey and c or None
    substr, sep, pos, bpos = _move_to_sep(instr, pos, bpos, testsep)

    if sep == _ch_pval:
        substr = substr.strip()
        for rawkey in substr.split(_ch_pkey_sep):
            cut, terminal, canceling = [False] * 3
            while rawkey.endswith((_ch_cutprop, _ch_termprop, _ch_remprop)):
                if rawkey.endswith(_ch_cutprop):
                    cut = True
                    rawkey = rawkey[:-len(_ch_cutprop)]
                elif rawkey.endswith(_ch_termprop):
                    terminal = True
                    rawkey = rawkey[:-len(_ch_termprop)]
                elif rawkey.endswith(_ch_remprop):
                    canceling = True
                    rawkey = rawkey[:-len(_ch_remprop)]
            key = _SDKey(prop, obpos, rawkey, cut, terminal, canceling)
            prop.keys.append(key)
        return _ctx_pval, prop, False, pos, bpos
    else:
        # Backtrack and go into value context.
        return _ctx_pval, prop, False, opos, obpos


_seps_pval = set((_ch_prop_sep, _ch_exp, _ch_tag, _ch_nl))

def _ctx_handler_pval (prop, instr, pos, bpos):

    opos, obpos = pos, bpos
    testsep = lambda c: c in _seps_pval and c or None
    substr, sep, pos, bpos = _move_to_sep(instr, pos, bpos, testsep)

    if substr:
        prop.segs.append(_SDText(prop, obpos, substr))

    if sep == _ch_prop_sep:
        env = prop.parent
        prop = _SDProp(env, bpos)
        env.props.append(prop)
        return _ctx_pkey, prop, False, pos, bpos
    elif sep == _ch_exp:
        exp = _SDExp(prop, bpos)
        prop.segs.append(exp)
        return _ctx_exp, exp, True, pos, bpos
    elif sep == _ch_tag:
        tag = _SDTag(prop, bpos)
        prop.segs.append(tag)
        return _ctx_tag, tag, True, pos, bpos
    else:
        return None, None, False, pos, bpos


_seps_exp = set([_ch_prop_sep, _ch_exp] + list(_strict_ws))

def _ctx_handler_exp (exp, instr, pos, bpos):

    if instr[pos:pos + len(_ch_grp_opn)] == _ch_grp_opn:
        enclosed = True
        testsep = lambda c: c in (_ch_grp_cls, _ch_nl) and c or None
    else:
        enclosed = False
        testsep = lambda c: (c in _seps_exp and [""] or [None])[0]

    obpos = bpos
    substr, sep, pos, bpos, isesc = _move_to_sep(instr, pos, bpos, testsep,
                                                 repesc=True)
    if enclosed and sep is None or sep == _ch_nl:
        raise SynderError(
            _p("error message",
               "Unexpected end of expander started at %(lin)d:%(col)d.")
            % dict(lin=obpos[0], col=obpos[1]),
            1050, exp.parent.parent.parent.parent.name, bpos)

    if enclosed:
        substr = substr[len(_ch_grp_opn):]

    p = substr.find(_ch_exp_kext)
    if p >= 0:
        exp.kext = substr[p + len(_ch_exp_kext):]
        substr = substr[:p]

    p = substr.find(_ch_exp_mask)
    if p >= 0:
        exp.mask = substr[p + len(_ch_exp_mask):]
        substr = substr[:p]

    if substr.startswith(_ch_exp_upc) and not isesc[0]:
        exp.caps = True
        substr = substr[len(_ch_exp_upc):]
    elif substr.startswith(_ch_exp_lwc) and not isesc[0]:
        exp.caps = False
        substr = substr[len(_ch_exp_lwc):]

    exp.ref = substr

    return None, None, False, pos, bpos


_seps_tag = set([_ch_prop_sep, _ch_exp, _ch_tag] + list(_strict_ws))

def _ctx_handler_tag (tag, instr, pos, bpos):

    if instr[pos:pos + len(_ch_grp_opn)] == _ch_grp_opn:
        enclosed = True
        testsep = lambda c: c in (_ch_grp_cls, _ch_nl) and c or None
    else:
        enclosed = False
        testsep = lambda c: (c in _seps_exp and [""] or [None])[0]

    obpos = bpos
    substr, sep, pos, bpos = _move_to_sep(instr, pos, bpos, testsep)
    if enclosed and sep is None or sep == _ch_nl:
        raise SynderError(
            _p("error message",
               "Unexpected end of tag started at %(lin)d:%(col)d.")
            % dict(lin=obpos[0], col=obpos[1]),
            1050, exp.parent.parent.parent.parent.name, bpos)

    if enclosed:
        substr = substr[len(_ch_grp_opn):]

    tag.names = substr.split(_ch_tag_sep)

    return None, None, False, pos, bpos


def _ctx_handler_inc (source, instr, pos, bpos):

    # Skip include directive.
    substr, sep, pos, bpos = _move_to_sep(instr, pos, bpos, lambda c: c)

    # Parse include path.
    obpos = bpos
    testsep = lambda c: c == _ch_nl and c or None
    substr, sep, pos, bpos = _move_to_sep(instr, pos, bpos, testsep)

    incpath = substr.strip()
    if not incpath:
        raise SynderError(
            _p("error message",
               "Empty target path in include directive."),
            1100, source.name, obpos)

    # Add to included sources of this source.
    # Temporarily store paths, to be resolved into full sources later.
    source.incsources.append(incpath)

    return None, None, False, pos, bpos


# ----------------------------------------
# Parsing context IDs and handlers collected.
# IDs and handlers must be in the same order,
# as IDs are used to index handlers.

(
    _ctx_void,
    _ctx_ksyn,
    _ctx_env,
    _ctx_pkey,
    _ctx_pval,
    _ctx_exp,
    _ctx_tag,
    _ctx_inc,
) = range(8)

_ctx_handlers = (
    _ctx_handler_void,
    _ctx_handler_ksyn,
    _ctx_handler_env,
    _ctx_handler_pkey,
    _ctx_handler_pval,
    _ctx_handler_exp,
    _ctx_handler_tag,
    _ctx_handler_inc,
)

# ----------------------------------------
# Parsing utilities.

# Find the first separator admitted by the test function,
# skipping over escaped characters, continued lines and comments.
# Return substring to that point (without escapes, comments, line cont.),
# separator, and new position and block position (line, column).
# On request, also return list of escape indicators for each character
# in the substring (True where character was escaped).
# Separator test function takes single argument, the current character,
# and returns None if it is not admitted as separator.
# If end of input is reached without test function admitting a separator,
# separator is reported as None; otherwise, separator is reported as
# the return value from the test function.
def _move_to_sep (instr, pos, bpos, testsep, wesc=True, repesc=False):

    opos = pos
    substr = []
    isesc = []
    sep = None
    while sep is None and pos < len(instr):
        c = instr[pos]
        if c == _ch_comment:
            p = instr.find(_ch_nl, pos)
            if p < 0:
                pos += len(instr) - pos
            else:
                pos = p
        elif wesc and c == _ch_escape:
            pos += 1
            if pos < len(instr):
                if instr[pos] == _ch_nl: # line continuation
                    pass
                # elif instr[pos] == _ch_ucode: # unicode hex
                else:
                    substr.append(instr[pos])
                    isesc.append(True)
                pos += 1
        else:
            sep = testsep(c)
            if sep is not None:
                pos += len(sep)
            else:
                substr.append(c)
                isesc.append(False)
                pos += 1

    # Update block position (line, column).
    rawsubstr = instr[opos:pos]
    p = rawsubstr.rfind(_ch_nl)
    if p >= 0:
        bpos = (bpos[0] + rawsubstr.count(_ch_nl), len(rawsubstr) - p)
    else:
        bpos = (bpos[0], bpos[1] + len(rawsubstr))

    ret = ("".join(substr), sep, pos, bpos)
    if repesc:
        ret = ret + (isesc,)
    return ret


# ----------------------------------------
# Data structures.

# Synder source.
class _SDSource:

    def __init__ (self, name):

        # Name of the source (filename, etc).
        self.name = name

        # Derivations (SDDeriv).
        self.derivs = []
        # Included sources (must be ordered).
        self.incsources = []
        # Indentation for derivation and environments heads
        # (set on first parsed).
        self.indderiv = None
        self.indenv = None

        ## Global directives.
        #...


    def __unicode__ (self):
        return (  "============> %s\n" % self.name
                + "\n".join(map(unicode, self.derivs)))
    def __str__ (self):
        return self.__unicode__().encode(locale.getpreferredencoding())


# Derivation.
class _SDDeriv:

    def __init__ (self, parent, pos):

        # Parent source and position in it.
        self.parent = parent
        self.pos = pos

        # Key syntagmas (SDProp).
        self.syns = []
        # Environments (SDEnv).
        self.envs = []

    def __unicode__ (self):
        return (  "  -----> %d:%d\n" % self.pos
                + "  " + "\n  ".join(map(unicode, self.syns)) + "\n"
                + "\n".join(map(unicode, self.envs)))
    def __str__ (self):
        return self.__unicode__().encode(locale.getpreferredencoding())


# Environment.
class _SDEnv:

    def __init__ (self, parent, pos, name=""):

        # Parent derivation and position in source.
        self.parent = parent
        self.pos = pos
        # Environment name.
        self.name = name

        # Properties (SDProp).
        self.props = []

    def __unicode__ (self):
        return (  "    @%s:%d:%d\n" % ((self.name,) + self.pos)
                + "\n".join(map(unicode, self.props)))
    def __str__ (self):
        return self.__unicode__().encode(locale.getpreferredencoding())


# Syntagma.
class _SDSyn:

    def __init__ (self, parent, pos, hidden=False):

        # Parent derivation and position in source.
        self.parent = parent
        self.pos = pos
        # Visibility of the syntagma.
        self.hidden = hidden

        # Syntagma segments (SDText, SDTag).
        self.segs = []

    def __unicode__ (self):
        return (  "{p:%d:%d|%s}=" % (self.pos + (self.hidden,))
                + u"".join(map(unicode, self.segs)))
    def __str__ (self):
        return self.__unicode__().encode(locale.getpreferredencoding())


# Property.
class _SDProp:

    def __init__ (self, parent, pos):

        # Parent environment and position in source.
        self.parent = parent
        self.pos = pos

        # Keys (SDKey).
        self.keys = []
        # Value segments (SDText, SDExp, SDTag).
        self.segs = []

    def __unicode__ (self):
        return (  "      %d:%d " % self.pos
                + "k=" + u"".join(map(unicode, self.keys)) + " "
                + "v=" + u"".join(map(unicode, self.segs)))
    def __str__ (self):
        return self.__unicode__().encode(locale.getpreferredencoding())


# Property key.
class _SDKey:

    def __init__ (self, parent, pos, name="",
                  cut=False, terminal=False, canceling=False):

        # Parent property and position in source.
        self.parent = parent
        self.pos = pos
        # Key behaviors.
        self.name = name
        self.cut = cut
        self.terminal = terminal
        self.canceling = canceling

    def __unicode__ (self):
        return "{k:%d:%d:%s|%s&%s}" % (self.pos + (self.name,
                                                   self.cut, self.terminal,
                                                   self.canceling))
    def __str__ (self):
        return self.__unicode__().encode(locale.getpreferredencoding())


# Expander.
class _SDExp:

    def __init__ (self, parent, pos, ref=None, mask=None, caps=None, kext=None):

        # Parent property and position in source.
        self.parent = parent
        self.pos = pos
        # Reference, selection mask, capitalization, key extender.
        self.ref = ref
        self.mask = mask
        self.caps = caps
        self.kext = kext

    def __unicode__ (self):
        return u"{e:%d:%d:%s|%s|%s|%s}" % (self.pos + (self.ref, self.mask,
                                                       self.caps, self.kext))
    def __str__ (self):
        return self.__unicode__().encode(locale.getpreferredencoding())


# Tag.
class _SDTag:

    def __init__ (self, parent, pos):

        # Parent property and position in source.
        self.parent = parent
        self.pos = pos
        # Names associated to this tag.
        self.names = []

    def __unicode__ (self):
        return u"{g:%d:%d:%s}" % (self.pos + ("+".join(self.names),))
    def __str__ (self):
        return self.__unicode__().encode(locale.getpreferredencoding())


# Text segment.
class _SDText:

    def __init__ (self, parent, pos, text=""):

        # Parent property and position in source.
        self.parent = parent
        self.pos = pos
        # Text.
        self.text = text

    def __unicode__ (self):
        return "{t:%d:%d:%s}" % (self.pos + (self.text,))
    def __str__ (self):
        return self.__unicode__().encode(locale.getpreferredencoding())


# ----------------------------------------
# High level access.

class Synder (object):
    """
    Derivator objects import sources of derivations
    and get queried for properties of syntagmas.

    Lookup can be done by derivation key and property key,
    but also by single compound key (serialization of the previous two),
    to have interface and behavior similar to built-in dictionaries.

    Basic usage is rather simple. If there are derivation files
    C{planets.sd} and {moons.sd}, they can be used like this::

        >>> sd = Synder()
        >>> sd.import_file("planets.sd")
        >>> sd.import_file("moons.sd")
        >>>
        >>> # Lookup of properties by derivation and property key.
        >>> sd.get2("Venus", "nom")
        Venera
        >>> sd.get2("Callisto", "nom")
        Kalisto
        >>> sd.get2("Foobar", "nom")
        None
        >>> # Lookup of properties by compound key.
        >>> sd["Venus-nom"]
        Venera
        >>>
        >>> # Iteration through properties by derivation keys.
        >>> for dkey in sd.dkeys(): print sd.get2(dkey, "nom")
        ...
        Venera
        Kalisto
        Merkur
        Jupiter
        …
        >>> # Iteration through properties by compound keys.
        >>> for ckey in sd: print sd[ckey]
        ...
        Venera
        Veneri
        Venerom
        …
        Merkuru
        Merkur
        Merkura
        …
        >>> # Querying for key syntagmas.
        >>> sd.syns("Venus")
        ['Venus']
        >>> sd.syns("Iapetus")
        ['Iapetus', 'Japetus']
        >>> sd.syns("Japetus")
        ['Iapetus', 'Japetus']
        >>>
        >>> # Querying for property keys.
        >>> sd.pkeys("Venus")
        ['gen', 'acc', 'nom', 'dat', 'gender']

    Syntax errors in derivations sources will raise L{SynderError}
    exceptions on import.
    Unresolvable conflicts in derivation keys will be reported
    as warning on import, and conflicted derivations will not be imported.
    Errors in expansions are not reported on import, but when
    the problematic derivation is queried; warnings are output,
    and C{None} (or default value) is returned for all properties.
    """

    def __init__ (self,
                  env="",
                  ckeysep="-",
                  strictkey=False,
                  dkeytf=None, dkeyitf=None,
                  pkeytf=None, pkeyitf=None,
                  pvaltf=None,
                  ksyntf=None,
                  envtf=None):
        """
        Constructor of syntagma derivators.

        The default resolution of derivation key conflicts,
        as described in module documentation, can be changed
        to strict resolution through C{strictkey} parameter.
        If C{strictkey} is C{True}, all key syntagmas must be unique.

        Parameter C{env} is used to specify the environment from which
        the derivations are taken. In case no non-default environments
        have been used in derivations, C{env} is simply empty string.
        Otherwise, it can be:
          - a string specifying a non-default environment
          - a tuple specifying an environment fallback chain
          - a tuple of tuples, specifying more than one environment chain
        (Lists can also be used instead of tuples.)

        If several environment fallback chains are given, when a property
        is requrested they are tried in the order of specification,
        and the first yielded property is returned.
        It is also possible to combine properties from different
        environment chains in a custom way, by supplying a property
        value transformation function (C{pvaltf} parameter).

        Compound keys, for single-key lookups, are built by joining
        the derivation and property keys with a separator.
        This separator can be chosen through C{ckeysep} parameter.
        The separator string can be contained inside a derivation key,
        but it must not be found inside any property key
        (the compound key is split from the back).

        A myriad of I{transformation functions} can be applied by
        derivator object to imported derivations, through C{*tf} parameters.
        They are as follows (stating only default inputs, see below
        for more possibilities):
          - C{dkeytf}: applied to derivation key supplied on lookups
                (e.g. in L{get} or L{get2} methods). Takes the derivation
                key as parameter, returns either the derivation key
                or a tuple of the derivation key and another object.
          - C{dkeyitf}: applied to all derivation keys on import.
                Same default input-output as C{dkey}.
          - C{pkeytf}: like C{dkeytf}, only working analogously on
                property key instead of derivation key.
          - C{pkeyitf}: like C{dkeyitf}, only working analogously on
                property key instead of derivation key.
          - C{pvaltf}: applied to tagged segments of property values.
                The input to this function is a list of lists
                by each environment fallback chain;
                list for one environemnt chain consists of 2-tuples,
                each tuple having a list of tags as the first element,
                and a text segment as the second element.
                For example, if there is only one environment chain
                (e.g. C{evn=""} or C{env=("someenv", "")},
                and the property value is derived to be C{foo ~tag bar}
                in this environment, then the argument to the function
                will be C{[[([''], "foo "), (['tag'], " bar")]]}.
                If an environemnt chain yielded no property value,
                its element will be C{None} instead of list of 2-tuples.
                The return value is the final property value string.
                Note that simplification will not be applied to this
                value afterwards, so if desired,
                L{simplify()<pology.misc.normalize.simplify>}
                should be manually called inside the function.
          - C{ksyntf}: quite similar to C{pvaltf}, only applied to
                tagged segments of key syntagmas.
                The difference is that there are no multiple environments
                for key syntagmas, so the input value is just one list
                of tagged text segments (what would be the first element
                of input list to C{pvaltf}).
          - C{envtf}: applied to environment fallback chain on lookups.
                Takes original environment chain as argument,
                returns new environment chain
                (in one of the forms acceptable as C{env} parameter).

        Transformation functions can take more input arguments than
        the default described above, on demand.
        If transformation function  is supplied directly,
        e.g. C{pvaltf=somefunc}, it is sent default inputs.
        Extra inputs are requested by supplying instead a tuple, where
        the first element is the transformation function, and the following
        elements are predefined keywords of available extra inputs,
        e.g. C{pvalf=(somefunc, "dkey", "pkrest")}.
        Available extra inputs by transformation function are:
          - C{dkeytf}: C{"self"} the derivation object.
          - C{pkeytf}: C{"self"}, C{"dkey"} the derivation key
                (original or that returned by C{dkeytf}),
                C{"dkrest"} the second object returned by C{dkeytf}.
          - C{pvaltf}: C{"self"}, C{"dkey"}, C{"pkey"} the property
                key (original or that returned by C{pkeytf}),
                C{"env"} the tuple of environment chains, C{"dkrest"},
                C{"pkrest"} the second object returned by C{pkeytf}.
          - C{ksyntf}: C{"self"}, C{"dkey"}, C{"dkrest"}.
          - C{envtf}: C{"self"}, C{"dkey"}, C{"dkrest"}.

        @param env: environment for derivations
        @type env: string, (string*), ((string*)*)
        @param ckeysep: derivation-property key separator in compound keys
        @type ckeysep: string
        @param strictkey: whether all key syntagmas must be unique to
            avoid conflicts
        @param dkeytf: transformation function for lookup derivation keys
        @param dkeyitf: transformation function for imported derivation keys
        @param pkeytf: transformation function for lookup property keys
        @param pkeyitf: transformation function for imported property keys
        @param pvaltf: transformation fucntion for property values
        @param ksyntf: transformation fucntion for key syntagamas
        """

        self._env = self._normenv(env)

        self._ckeysep = ckeysep

        self._dkeytf = self._resolve_tf(dkeytf, ["self"])
        self._dkeyitf = self._resolve_tf(dkeyitf, [])
        self._pkeytf = self._resolve_tf(pkeytf, ["dkey", "dkrest", "self"])
        self._pkeyitf = self._resolve_tf(pkeyitf, [])
        self._pvaltf = self._resolve_tf(pvaltf, ["pkey", "dkey", "env",
                                                 "dkrest", "pkrest", "self"])
        self._ksyntf = self._resolve_tf(ksyntf, ["dkey", "dkrest", "self"])
        self._envtf = self._resolve_tf(envtf, ["dkey", "dkrest", "self"])

        self._strictkey = strictkey

        self._imported_srcnames = set()
        self._visible_srcnames = set()
        self._derivs_by_srcname = {}
        self._deriv_by_srcname_idkey = {}
        self._visible_deriv_by_dkey = {}
        self._props_by_deriv_env1 = {}
        self._raw_props_by_deriv_env1 = {}
        self._single_dkeys = set()


    def _normenv (self, env):

        if isinstance(env, (tuple, list)):
            if not env or isinstance(env[0], basestring):
                env = (env,)
        else:
            env = ((env,),)

        return env


    def _resolve_tf (self, tfspec, kneargs):

        eaords = [0]
        if isinstance(tfspec, (tuple, list)):
            tf0, eargs = tfspec[0], list(tfspec[1:])
            unkeargs = set(eargs).difference(kneargs)
            if unkeargs:
                arglist = " ".join(sorted(unkeargs))
                raise StandardError(
                    _p("error message",
                       "Unknown extra arguments for transformation function "
                       "requested in derivator constructor: %(arglist)s")
                    % locals())
            eaords.extend([kneargs.index(x) + 1 for x in eargs])
        else:
            tf0 = tfspec

        if tf0 is None:
            return None

        def tf (*args):
            args0 = [args[x] for x in eaords]
            return tf0(*args0)

        return tf


    def import_string (self, string, ignhid=False):
        """
        Import string with derivations.

        @param string: the string to parse
        @type string: string
        @param ignhid: also make hidden derivations visible if C{True}
        @type ignhid: bool

        @returns: number of newly imported visible derivations
        @rtype: int
        """

        source = _parse_string(string)
        return self._process_import_visible(source, ignhid)


    def import_file (self, filename, ignhid=False):
        """
        Import file with derivations.

        @param filename: the path to file to parse
        @type filename: string
        @param ignhid: also make hidden derivations visible if C{True}
        @type ignhid: bool

        @returns: number of newly imported visible derivations
        @rtype: int
        """

        source = _parse_file(filename)
        return self._process_import_visible(source, ignhid)


    def _process_import_visible (self, source, ignhid):

        nnew = self._process_import(source)
        nvis = self._make_visible(source, ignhid)
        return (nvis, nnew)


    def _process_import (self, source):

        if source.name in self._imported_srcnames:
            return 0

        self._imported_srcnames.add(source.name)

        iderivs = []
        self._derivs_by_srcname[source.name] = iderivs
        idmap = {}
        self._deriv_by_srcname_idkey[source.name] = idmap

        # Construct wrapping derivations and file them by derivation keys.
        nadded = 0
        for rawderiv in source.derivs:

            # Create wrapper derivation for the raw derivation.
            deriv = self._Deriv(rawderiv, self._dkeyitf)

            # Eliminate internal key conflicts of this derivation.
            self._eliminate_conflicts(deriv, idmap, None, lambda x: x.idkeys)

            # Register internal derivation in this source.
            if deriv.idkeys:
                iderivs.append(deriv)
                for idkey in deriv.idkeys:
                    idmap[idkey] = deriv
                nadded += 1

        # Import included sources.
        for incsource in source.incsources:
            nadded += self._process_import(incsource)

        return nadded


    def _make_visible (self, source, ignhid):

        if source.name in self._visible_srcnames:
            return 0

        self._visible_srcnames.add(source.name)

        nvis = 0

        for deriv in self._derivs_by_srcname[source.name]:
            if not ignhid and all([x.hidden for x in deriv.base.syns]):
                continue

            # Eliminate external key conflicts of this derivation.
            self._eliminate_conflicts(deriv, self._visible_deriv_by_dkey,
                                      self._single_dkeys, lambda x: x.dkeys)

            # Register visible derivation in this source.
            if deriv.dkeys:
                self._single_dkeys.add(tuple(deriv.dkeys)[0])
                for dkey in deriv.dkeys:
                    self._visible_deriv_by_dkey[dkey] = deriv
                nvis += 1

        return nvis


    class _Deriv:

        def __init__ (self, deriv, dkeyitf):

            self.base = deriv

            # Compute internal and external derivation keys from key syntagmas.
            self.idkeys = set()
            self.dkeys = set()
            for syn in deriv.syns:
                synt = "".join([x.text for x in syn.segs
                                       if isinstance(x, _SDText)])
                idkey = simplify(synt)
                self.idkeys.add(idkey)
                dkeys = dkeyitf(idkey) if dkeyitf else idkey
                if dkeys is not None:
                    if not isinstance(dkeys, (tuple, list)):
                        dkeys = [dkeys]
                    self.dkeys.update(dkeys)


    def _eliminate_conflicts (self, deriv, kmap, kskeys, keyf):

        to_remove_keys = set()
        to_remove_keys_other = {}
        for key in keyf(deriv):
            oderiv = kmap.get(key)
            if oderiv is not None:
                to_remove_keys.add(key)
                if oderiv not in to_remove_keys_other:
                    to_remove_keys_other[oderiv] = set()
                to_remove_keys_other[oderiv].add(key)

        noconfres_oderivs = []
        if self._strictkey or to_remove_keys == keyf(deriv):
            noconfres_oderivs.extend(to_remove_keys_other.keys())
        else:
            for oderiv, keys in to_remove_keys_other.items():
                if keyf(oderiv) == keys:
                    noconfres_oderivs.append(oderiv)

        if noconfres_oderivs:
            # Clear both internal and external keys.
            deriv.dkeys.clear()
            deriv.idkeys.clear()
            eposf = lambda x: (x.base.parent.name, x.base.syns[0].pos[0])
            noconfres_oderivs.sort(key=eposf)
            pos1 = "%s:%d" % eposf(deriv)
            pos2s = ["%s:%d" % eposf(x) for x in noconfres_oderivs]
            pos2s = "\n".join(pos2s)
            warning(_p("error message",
                       "Derivation at %(pos1)s eliminated due to "
                       "key conflict with the following derivations:\n"
                       "%(pos2s)s") % locals())
        else:
            for key in to_remove_keys:
                keyf(deriv).remove(key)
            for oderiv, keys in to_remove_keys_other.items():
                for key in keys:
                    keyf(oderiv).remove(key)
                    kmap.pop(key)
                    if kskeys is not None and key in kskeys:
                        kskeys.remove(key)
                        kskeys.add(tuple(keyf(oderiv))[0])


    def _resolve_dkey (self, dkey):

        dkrest = ()
        if self._dkeytf:
            dkey = self._dkeytf(dkey, self)
            if isinstance(dkey, tuple):
                dkey, dkrest = dkey[0], dkey[1:]

        deriv = None
        if dkey is not None:
            deriv = self._visible_deriv_by_dkey.get(dkey)
            if deriv is None:
                dkey = None

        return dkey, dkrest, deriv


    def _resolve_pkey (self, pkey, dkey, dkrest):

        pkrest = ()
        if self._pkeytf:
            pkey = self._pkeytf(pkey, dkey, dkrest, self)
            if isinstance(pkey, tuple):
                pkey, pkrest = pkey[0], pkey[1:]

        return pkey, pkrest


    def _resolve_env (self, env, dkey, dkrest):

        if self._envtf:
            env = self._envtf(env, dkey, dkrest, self)
            if env is not None:
                env = self._normenv(env)

        return env


    def get2 (self, dkey, pkey, defval=None):
        """
        Get property value by derivation key and property key.

        @param dkey: derivation key
        @type dkey: string
        @param pkey: property key
        @type pkey: string
        @param defval: the value to return if the property does not exist
        @type defval: string

        @returns: the property value
        @rtype: string
        """

        dkey, dkrest, deriv = self._resolve_dkey(dkey)
        if dkey is None:
            return defval

        pkey, pkrest = self._resolve_pkey(pkey, dkey, dkrest)
        if pkey is None:
            return defval

        env = self._resolve_env(self._env, dkey, dkrest)
        if env is None:
            return defval

        mtsegs = []
        for env1 in env:
            tsegs = self._getprops(deriv, env1).get(pkey)
            mtsegs.append(tsegs)

        if self._pvaltf:
            pval = self._pvaltf(mtsegs, pkey, dkey, env,
                                dkrest, pkrest, self)
        else:
            pval = None
            for tsegs in mtsegs:
                if tsegs is not None:
                    pval = simplify("".join([x[0] for x in tsegs]))
                    break

        return pval if pval is not None else defval


    def _getprops (self, deriv, env1):

        # Try to fetch derivation from cache.
        props = self._props_by_deriv_env1.get((deriv, env1))
        if props is not None:
            return props

        # Construct raw derivation and extract key-value pairs.
        rprops = self._derive(deriv, env1)
        props = dict([(x, self._simple_segs(y[0])) for x, y in rprops.items()
                                                   if not y[1].canceling])

        # Internally transform keys if requested.
        if self._pkeyitf:
            nprops = []
            for pkey, segs in props.items():
                pkey = self._pkeyitf(pkey)
                if pkey is not None:
                    nprops.append((pkey, segs))
            props = dict(nprops)

        self._props_by_deriv_env1[(deriv, env1)] = props
        return props


    def _derive (self, deriv, env1):

        # Try to fetch raw derivation from cache.
        dprops = self._raw_props_by_deriv_env1.get((deriv, env1))
        if dprops is not None:
            return dprops

        # Derivator core.
        dprops = {}
        env = None
        envs_by_name = dict([(x.name, x) for x in deriv.base.envs])
        for env0 in reversed(env1):
            env = envs_by_name.get(env0)
            if env is None:
                continue
            for prop in env.props:
                fsegs = []
                cprops = dict([(simplify(x.name), ([], x)) for x in prop.keys])
                ownpkeys = set(cprops.keys())
                for seg in prop.segs:
                    if isinstance(seg, _SDExp):
                        eprops = self._expand(seg, deriv, env1)
                        if len(eprops) != 1 or eprops.keys()[0]:
                            if cprops:
                                for cpkey, csegskey in list(cprops.items()):
                                    if not csegskey[1].cut:
                                        esegskey = eprops.get(cpkey)
                                        if esegskey is not None:
                                            if not esegskey[1].cut:
                                                csegskey[0].extend(esegskey[0])
                                        else:
                                            cprops.pop(cpkey)
                                            if not cprops:
                                                break
                                for epkey, esegskey in eprops.items():
                                    if esegskey[1].cut:
                                        cprops[epkey] = esegskey
                                if not cprops:
                                    break
                            else:
                                for pkey, (esegs, key) in eprops.items():
                                    csegs = esegs[:]
                                    if not key.cut:
                                        csegs[:0] = fsegs
                                    cprops[pkey] = (csegs, key)
                        else:
                            esegs = eprops.values()[0][0]
                            if cprops:
                                for pkey, (csegs, key) in cprops.items():
                                    if not key.cut or pkey in ownpkeys:
                                        csegs.extend(esegs)
                            else:
                                fsegs.extend(esegs)
                    elif cprops:
                        for pkey, (csegs, key) in cprops.items():
                            if not key.cut or pkey in ownpkeys:
                                csegs.append(seg)
                    else:
                        fsegs.append(seg)
                for pkey, (segs, key) in list(cprops.items()):
                    if key.canceling and pkey in dprops:
                        osegskey = dprops.get(pkey)
                        if osegskey is not None and not osegskey[1].canceling:
                            dprops.pop(pkey)
                            cprops.pop(pkey)
                dprops.update(cprops)

        # Eliminate leading and trailing empty text segments.
        map(self._trim_segs, [x[0] for x in dprops.values()])

        self._raw_props_by_deriv_env1[(deriv, env1)] = dprops
        return dprops


    def _expand (self, exp, pderiv, env1):
        # TODO: Discover circular expansion paths.

        # Fetch the derivation pointed to by the expansion.
        idkey = simplify(exp.ref)
        source = pderiv.base.parent
        deriv = self._deriv_by_srcname_idkey[source.name].get(idkey)
        if deriv is None:
            for isource in reversed(source.incsources):
                deriv = self._deriv_by_srcname_idkey[isource.name].get(idkey)
                if deriv is not None:
                    break
        if deriv is None:
            raise SynderError(
                _p("error message",
                   "Expansion '%(ref)s' does not reference a known derivation.")
                % dict(ref=exp.ref, file=source.name, line=exp.pos[0]),
                5010, source.name, exp.pos)

        # Derive the referenced derivation.
        props = self._derive(deriv, env1)

        # Drop terminal properties.
        nprops = []
        for pkey, (segs, key) in props.items():
            if not key.terminal:
                nprops.append((pkey, (segs, key)))
        props = dict(nprops)

        # Apply expansion mask.
        if exp.mask is not None:
            # Eliminate all obtained keys not matching the mask.
            # Reduce by mask those that match.
            nprops = []
            for pkey, segskey in props.items():
                if len(pkey) != len(exp.mask):
                    continue
                mpkey = ""
                for c, cm in zip(pkey, exp.mask):
                    if cm != _ch_exp_mask_pl:
                        if cm != c:
                            mpkey = None
                            break
                    else:
                        mpkey += c
                if mpkey is not None:
                    nprops.append((mpkey, segskey))
            props = dict(nprops)

        # Apply key extension.
        if exp.kext is not None:
            nprops = []
            for pkey, (segs, key) in props.items():
                npkey = exp.kext.replace(_ch_exp_kext_pl, pkey)
                nprops.append((npkey, (segs, key)))
            props = dict(nprops)

        # Apply capitalization.
        if exp.caps is not None:
            chcaps = first_to_upper if exp.caps else first_to_lower
            nprops = []
            for pkey, (segs, key) in props.items():
                chcapsed = False
                nsegs = []
                for seg in segs:
                    if (    not chcapsed
                        and isinstance(seg, _SDText) and seg.text.strip()
                    ):
                        nseg = copy.copy(seg)
                        nseg.text = chcaps(seg.text)
                        chcapsed = True
                        nsegs.append(nseg)
                    else:
                        nsegs.append(seg)
                nprops.append((pkey, (nsegs, key)))
            props = dict(nprops)

        if not props:
            raise SynderError(
                _p("error message",
                   "Expansion '%(ref)s' expands into nothing.")
                % dict(ref=exp.ref, file=source.name, line=exp.pos[0]),
                5020, source.name, exp.pos)

        return props


    def _trim_segs (self, segs):

        for i0, di, stripf in (
            (0, 1, unicode.lstrip),
            (len(segs) - 1, -1, unicode.rstrip),
        ):
            i = i0
            while i >= 0 and i < len(segs):
                if isinstance(segs[i], _SDText):
                    segs[i].text = stripf(segs[i].text)
                    if segs[i].text:
                        break
                i += di


    def _simple_segs (self, segs):

        # Add sentries.
        if not segs:
            segs = [_SDText(None, None, "")]
        if not isinstance(segs[0], _SDTag):
            segs = [_SDTag(None, None)] + segs
        if not isinstance(segs[-1], _SDText):
            segs = segs + [_SDText(None, None, "")]

        # Construct simplified segments: [(text, [tagname...])...]
        tsegs = []
        i = 0
        while i < len(segs):
            # Tag names for the next piece of text.
            tags = segs[i].names
            # Join contiguous text segments into single plain text.
            i += 1
            i0 = i
            while i < len(segs) and isinstance(segs[i], _SDText):
                i += 1
            text = "".join([x.text for x in segs[i0:i]])
            # Collect simplified segment.
            tsegs.append((text, tags))

        return tsegs


    def get (self, ckey, defval=None):
        """
        Get property value by compound key.

        @param ckey: compound key
        @type ckey: string
        @param defval: the value to return if the property does not exist
        @type defval: string

        @returns: the property value
        @rtype: string
        """

        # Split the compound key into derivation and property keys.
        lst = ckey.rsplit(self._ckeysep, 1)
        if len(lst) < 2:
            return defval
        dkey, pkey = lst

        return self.get2(dkey, pkey, defval)


    def dkeys (self, single=False):
        """
        Get list of all derivation keys.

        For derivations accessible through more than one derivation
        key, by default all of them are included in the result.
        If instead only a single random of those keys is wanted
        (i.e. strictly one key per derivation), C{single} can
        be set to C{True}.

        @param single: whether to return a single key for each derivation
        @type single: param

        @returns: list of derivation keys
        @rtype: [string*]
        """

        if not single:
            return self._visible_deriv_by_dkey.keys()
        else:
            return self._single_dkeys


    def syns (self, dkey):
        """
        Get list of key syntagmas by derivation key.

        Key syntagmas are always returned in the order in which
        they appear in the derivation.
        If no derivation is found for the given key,
        an empty list is returned.

        @param dkey: derivation key
        @type dkey: string

        @returns: key syntagmas
        @rtype: [string*]
        """

        dkey, dkrest, deriv = self._resolve_dkey(dkey)
        if dkey is None:
            return []

        rsyns = []
        for syn in deriv.base.syns:
            if not syn.hidden:
                tsegs = self._simple_segs(syn.segs)
                if self._ksyntf:
                    rsyn = self._ksyntf(tsegs, dkey, dkrest, self)
                else:
                    rsyn = simplify("".join([x[0] for x in tsegs]))
                if rsyn is not None:
                    rsyns.append(rsyn)

        return rsyns


    def altdkeys (self, dkey):
        """
        Get list of all derivation keys pointing to same entry as given key.

        @param dkey: derivation key
        @type dkey: string

        @returns: alternative derivation keys
        @rtype: [string*]
        """

        dkey, dkrest, deriv = self._resolve_dkey(dkey)
        if dkey is None:
            return []

        return deriv.dkeys


    def pkeys (self, dkey):
        """
        Get set of property keys available for given derivation key.

        If no derivation is found for the given key,
        an empty set is returned.

        @param dkey: derivation key
        @type dkey: string

        @returns: property keys
        @rtype: set(string*)
        """

        dkey, dkrest, deriv = self._resolve_dkey(dkey)
        if dkey is None:
            return set()

        env = self._resolve_env(self._env, dkey, dkrest)
        if env is None:
            return set()

        pkeys = set()
        for env1 in env:
            props = self._getprops(deriv, env1)
            pkeys.update(props.keys())

        return pkeys


    def props (self, dkey):
        """
        Get dictionary of property values by property keys for
        given derivation key.

        If no derivation is found for the given key,
        an empty dictionary is returned.

        @param dkey: derivation key
        @type dkey: string

        @returns: property dictionary
        @rtype: {(string, string)*}
        """

        # TODO: Implement more efficiently.
        props = dict([(x, self.get2(dkey, x)) for x in self.pkeys(dkey)])

        return props


    def envs (self, dkey):
        """
        Get list of all explicitly defined environments in given derivation.

        "Explicitly" means environments mentioned in the derivation itself,
        and not those inherited through expansions.

        @param dkey: derivation key
        @type dkey: string

        @returns: explicit environment names
        @rtype: [string*]
        """

        dkey, dkrest, deriv = self._resolve_dkey(dkey)
        if dkey is None:
            return []

        return [x.name for x in deriv.base.envs]


    def source_name (self, dkey):
        """
        Get the name of the source in which the derivation is found.

        If no derivation is found for the given key, C{None} is returned.

        @param dkey: derivation key
        @type dkey: string

        @returns: name of the source
        @rtype: string
        """

        dkey, dkrest, deriv = self._resolve_dkey(dkey)
        if dkey is None:
            return None

        srcname = deriv.base.parent.name.split(os.path.sep)[-1]
        srcname = srcname[:srcname.rfind(".")]

        return srcname


    def source_pos (self, dkey):
        """
        Get the position in the source where the derivation is found.

        Position is a 3-tuple of file path, line and column numbers.
        If no derivation is found for the given key, C{None} is returned.

        @param dkey: derivation key
        @type dkey: string

        @returns: source position
        @rtype: (string, int, int)
        """

        dkey, dkrest, deriv = self._resolve_dkey(dkey)
        if dkey is None:
            return None

        path = deriv.base.parent.name
        lno, cno = deriv.base.pos

        return path, lno, cno


    def keys (self):
        """
        Get the list of all compound keys.

        @returns: compound keys
        @rtype: [string*]
        """

        return list(self.iterkeys())


    def values (self):
        """
        Get the list of all property values.

        @returns: property values
        @rtype: [string*]
        """

        return list(self.itervalues())


    def items (self):
        """
        Get the list of all pairs of compound keys and property values.

        @returns: compound keys and property values
        @rtype: [(string, string)*]
        """

        return list(self.iteritems())


    def __contains__ (self, ckey):
        """
        Check if the compound key is present in the derivator.

        @returns: C{True} if present, C{False} otherwie
        @rtype: bool
        """

        return self.get(ckey) is not None


    def __getitem__ (self, ckey):
        """
        Get property value by compound key, in dictionary notation.

        Like L{get}, but raises C{KeyError} if key is not found.

        @returns: property value
        @rtype: string
        """

        res = self.get(ckey)
        if res is None:
            raise KeyError, ckey

        return res


    def __iter__ (self):
        """
        Iterate through all compound keys, in random order.

        @returns: iterator through compound keys
        @rtype: iterator(string)
        """

        return self.iterkeys()


    def iterkeys (self):
        """
        Iterate through all compound keys, in random order.

        @returns: iterator through compound keys
        @rtype: iterator(string)
        """

        return self._Iterator(self._make_iter(lambda x: x))


    def itervalues (self):
        """
        Iterate through all property values, in random order.

        @returns: iterator through property values
        @rtype: iteratorstring)
        """

        return self._Iterator(self._make_iter(lambda x: self.get(x)))


    def iteritems (self):
        """
        Iterate through all pairs of compound key and property value,
        in random order.

        @returns: iterator through compound key property value pairs
        @rtype: iterator((string, string))
        """

        return self._Iterator(self._make_iter(lambda x: (x, self.get(x))))


    class _Iterator (object):

        def __init__ (self, it):
            self._it = it

        def __iter__ (self):
            return self

        def next (self):
            return self._it() # expected to raise StopIteration on its own


    def _make_iter (self, keyf):

        it = iter(self._visible_deriv_by_dkey)
        gdat = [None, []] # dkey, pkeys
        def next ():
            while not gdat[1]:
                gdat[0] = it.next() # will raise StopIteration
                gdat[1] = self.pkeys(gdat[0])
            dkey = gdat[0]
            pkey = gdat[1].pop()
            return keyf(dkey + self._ckeysep + pkey)

        return next


    def empty_pcache (self):

        self._props_by_deriv_env1 = {}
        self._raw_props_by_deriv_env1 = {}

