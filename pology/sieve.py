# -*- coding: UTF-8 -*-

"""
Helpers for catalog sieves.

Pology's C{posieve} script processes catalogs with "sieves": objects to which
catalog entries are fed one by one, possibly with finalization phase at the end.
This module contains some common helpers which are used by many sieves.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""


from pology import PologyError, _
from pology.comments import manc_parse_flag_list


class SieveError (PologyError):
    """
    Base exception class for sieve errors with special meaning.
    """



class SieveMessageError (SieveError):
    """
    Exception for single messages.

    If sieve's C{process} method throws it, client is allowed to send
    other messages from the same catalog to the sieve.
    """



class SieveCatalogError (SieveError):
    """
    Exception for single catalogs.

    If sieve's C{process} or C{process_header} method throw it, client is not
    allowed to send other messages from the same catalog to the sieve,
    but can send messages from other catalogs.
    """



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


def add_param_lang (p, appx=None):
    """
    Add C{lang} parameter to sieve parameters.

    @param appx: one or more trailing paragraphs for the parameter description
    @type appx: string
    """

    desc = _("@info sieve parameter discription",
    "The language of translation. "
    "If the user configuration or a catalog header specifies the language, "
    "this parameter takes precedence."
    )
    if appx:
        desc = "%s\n\n%s" % (desc, appx)
    p.add_param("lang", str,
                metavar=_("@info sieve parameter value placeholder", "CODE"),
                desc=desc)


def add_param_env (p, appx=None):
    """
    Add C{env} parameter to sieve parameters.

    @param appx: one or more trailing paragraphs for the parameter description
    @type appx: string
    """

    desc = _("@info sieve parameter discription",
    "The environment (language variation) of translation. "
    "If the user configuration or a catalog header specifies the environment, "
    "this parameter takes precedence. "
    "Several environments can be given as comma-separated list."
    )
    if appx:
        desc = "%s\n\n%s" % (desc, appx)
    p.add_param("env", str, seplist=True,
                metavar=_("@info sieve parameter value placeholder", "CODE"),
                desc=desc)


def add_param_accel (p, appx=None):
    """
    Add parameter C{accel} to sieve parameters.

    @param appx: one or more trailing paragraphs for the parameter description
    @type appx: string
    """

    desc = _("@info sieve parameter discription",
    "Character which is used as UI accelerator marker in text fields."
    )
    if appx:
        desc = "%s\n\n%s" % (desc, appx)
    p.add_param("accel", str, multival=True,
                metavar=_("@info sieve parameter value placeholder", "CHAR"),
                desc=desc)


def add_param_markup (p, appx=None):
    """
    Add parameter C{markup} to sieve parameters.

    @param appx: one or more trailing paragraphs for the parameter description
    @type appx: string
    """

    desc = _("@info sieve parameter discription",
    "Markup that can be expected in text fields, as special keyword. "
    "Several markups can be given as comma-separated list."
    )
    if appx:
        desc = "%s\n\n%s" % (desc, appx)
    p.add_param("markup", str, seplist=True,
                metavar=_("@info sieve parameter value placeholder", "KEYWORD"),
                desc=desc)


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

    p.add_param("filter", str, multival=True,
                metavar=_("@info sieve parameter value placeholder",
                          "HOOKSPEC"),
                desc=desc)


def add_param_poeditors (p):
    """
    Add parameters for opening messages in editors to sieve parameters.
    """

    p.add_param("lokalize", bool, defval=False,
                desc=_("@info sieve parameter discription",
    "Open catalogs on reported messages in Lokalize. "
    "Lokalize must be already running with the project "
    "that contains the sieved catalogs opened."
    ))


def add_param_entdef (p):
    """
    Add C{entdef} parameter to sieve parameters.
    """

    p.add_param("entdef", str, multival=True,
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

    add_param_lang(p, appx=_("@info sieve parameter discription",
        "The language determines which system dictionary, "
        "as well as internal word lists, to use for spell-checking. "
        "If the language is left undefined for a given catalog, "
        "it will be skipped and a warning may be output."
        ))
    add_param_env(p, appx=_("@info sieve parameter discription",
        "The environment determines which additional "
        "internal word lists to use for spell-checking. "
        "If the environment is left undefined for a given catalog, "
        "only environment-agnostic internal word lists will be used."
        ))
    add_param_accel(p)
    add_param_markup(p)
    p.add_param("skip", str,
                metavar=_("@info sieve parameter value placeholder", "REGEX"),
                desc=_("@info sieve parameter discription",
    "Regular expression to eliminate from spell-checking words that match it."
    ))
    p.add_param("case", bool, defval=False,
                desc=_("@info sieve parameter discription",
    "Make matching patterns given as parameter values case-sensitive."
    ))
    add_param_filter(p,
        intro=_("@info sieve parameter discription",
        "The F1A or F3A/C hook through which to filter the translation "
        "before passing it to spell-checking."
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

