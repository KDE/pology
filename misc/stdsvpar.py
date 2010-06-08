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

