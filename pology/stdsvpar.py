# -*- coding: UTF-8 -*-

"""
Standard sieve parameters.

This module defines parameters frequently used by different sieves,
for adding to their parameter lists.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

from pology import _, n_


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
    Add sieve parameters which open messages in known editors.
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

