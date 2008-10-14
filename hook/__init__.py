# -*- coding: UTF-8 -*-
# hook.__init__

"""
Hooks pluggable into various Pology contexts.

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
The return value of side-effect hooks is an integer, the number of errors encountered internally by the hook. Clients may use this number to decide
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

Hooks on PO messages in a catalog:

  - C{F4A} = C{(msg, cat)->numerr}: filters a message, modifying it
  - C{V4A} = C{(msg, cat)->parts}: validates a message
  - C{S4A} = C{(msg, cat)->numerr}: side-effects on a message (no modification)

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
==============

Since hooks have fixed input signatures by type, the way to customize
a given hook behavior is to produce its function by another function.
The hook-producing function is called a "hook factory". It works by
preparing anything needed for the hook, and then defining the hook proper
and returning it, thereby creating a lexical closure around it::

    def hook_factory (parfoo, parbar):

        # perhaps use parfoo, parbar to setup hook definition

        def hook (...):

            # perhaps use parfoo, parbar in the hook definition too

        return hook

In fact, most of the C{hook.<submod>} modules define hook factories rather
than hooks directly.

Notes
=====

Hooks should be defined in submodules C{hook.<submod>} and language-dependent
C{l10n.<lang>.hook.<submod>}, so that they can be automatically obtained by
L{misc.langdep.get_hook}. In particular, Pology utilities allowing users to
insert hooks into processing will expect hooks to be in these locations,
such that L{misc.langdep.get_hook_lreq} function can fetch the hook from
a string specification.
If a hook module implements a single hook, and the hook function is named
C{process()}, users can select it by giving only the hook module name,
without the function name.

Annotated parts for PO messages returned by hooks are a reduced version,
but a valid instance of highlight specifications used by reporting functions,
e.g. L{report_msg_content()<misc.msgreport.report_msg_content>}.
Annotated parts do not have the optional fourth element of a tuple in
highlight specification, which is used to provide the filtered text against
which spans were constructed, instead of the original text.

In connection with the previous, if a validation hook internally filters
the text and constructs list of problematic spans against such text,
just before returning it can use L{adapt_spans()<misc.diff.adapt_spans>}
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
@license: GPLv3
"""

