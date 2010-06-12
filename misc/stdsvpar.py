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
    "For a module pology.hook.FOO which defines FOO() function, "
    "the hook specification is simply FOO. "
    "If the hook function is named BAR() instead of FOO(), then "
    "the hook specification is FOO/BAR. "
    "Language specific hooks (pology.l10n.LANG.hook.FOO) are aditionally "
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
                desc=_("@info sieve parameter discription "
                       "only 'entname' and 'entvalue' in the last line "
                       "should be translated",
    "File defining the entities used in messages "
    "(parameter can be repeated to add more files). Entity file "
    "defines entities one per line, in the format:"
    "\n\n"
    "<!ENTITY entname 'entvalue'>"
    ))

