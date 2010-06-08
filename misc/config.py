# -*- coding: UTF-8 -*-

"""
Access user configuration for Pology.

The user can modify default aspects of Pology's behavior through
the Pology's global configuration file C{~/.pologyrc}.
This file is divided into sections and fields in the INI-style format,
for example::

    # let's have some apples for the moment
    [fruit]
    sort = apples
    amount = 10

When refering to global configuration within Pology documentation
(e.g. in documentation for scripts), fields are written shorthand
as C{[section]/name} (e.g. C{[fruit]/sort} and C{[fruit]/amount}).

The configuration file must be UTF-8 encoded.

For accessing the configuration within Pology code, this module as whole
is treated as single object. The API reflects division into sections,
with each section containing configuration fields::

    >>> import pology.misc.config as config
    >>> fruit = config.section("fruit")
    >>> fruit.string("sort")
    'apples'
    >>> fruit.integer("amount")
    10
    >>>

At every place where the configuration is sourced, the API documentation
should state which sections and fields (with their types) are accessed,
how they are used, and what is the behavior when they are not set.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import codecs
import os
from ConfigParser import SafeConfigParser

from pology import _, n_
from pology.misc.report import error


_config = SafeConfigParser()

def _parse_config ():

    # Try to correctly resolve the config file location across systems.
    cfgbase = "pologyrc"
    if os.name=="nt":
        cfgpath = os.path.join(os.environ.get("APPDATA", ""), cfgbase)
    else:
        cfgbase = "." + cfgbase
        cfgpath = os.path.join(os.environ.get("HOME", ""), cfgbase)

    # Parse the config if available.
    if os.path.isfile(cfgpath):
        ifl = codecs.open(cfgpath, "r", "UTF-8")
        _config.readfp(ifl)
        ifl.close()

# Parse configuration on first import.
_parse_config()


def has_section (name):
    """
    Check if the section of the configuration exists already.

    @param name: name of the section
    @type name: string

    @returns: C{True} if the section exists, C{False} otherwise
    @rtype: bool
    """

    return _config.has_section(name)


class section:
    """
    Section of the configuration.

    All getter methods take the field name and the default value,
    which is returned when the field is not set.
    If the configuration field is set but cannot be converted into
    a value of requested type, execution aborts with an error message.

    @ivar name: name of the section
    @type name: string
    """

    def __init__ (self, name):
        """
        Retrieve a section of the configuration.

        Constructed section object is valid even when the configuration does
        not contain the requested section (in that case, all field queries
        on the section are going to return default values).

        @param name: name of the section
        @type name: string
        """

        self.name = name


    def fields (self):
        """
        Get all configuration field names in this section.

        @rtype: set(string)
        """

        if not _config.has_section(self.name):
            return set()

        return set(_config.options(self.name))


    def _value (self, typ, name, default=None, typename=None):

        if not _config.has_option(self.name, name):
            return default

        value = _config.get(self.name, name)
        if typ is not bool:
            try:
                cvalue = typ(value)
            except:
                cvalue = None
        else:
            cvalue = strbool(value)

        if cvalue is None:
            if typename:
                error(_("@info",
                        "User configuration: value '%(val)s' "
                        "of field '%(field)s' in section '%(sec)s' "
                        "cannot be converted into '%(type)s' type.")
                      % dict(val=value, field=name, sec=self.name,
                             type=typename))
            else:
                error(_("@info",
                        "User configuration: value '%(val)s' "
                        "of field '%(field)s' in section '%(sec)s' "
                        "cannot be converted into requested type.")
                      % dict(val=value, field=name, sec=self.name))

        return cvalue


    def string (self, name, default=None):
        """
        Get a configuration field as a string.

        @rtype: unicode or as C{default}
        """

        return self._value(unicode, name, default, "string")


    def integer (self, name, default=None):
        """
        Get a configuration field as an integer number.

        @rtype: int or as C{default}
        """

        return self._value(int, name, default, "integer")


    def real (self, name, default=None):
        """
        Get a configuration field as a real number.

        @rtype: float or as C{default}
        """

        return self._value(float, name, default, "real")


    def boolean (self, name, default=None):
        """
        Get a configuration field as a boolean.

        @rtype: bool or as C{default}
        """

        return self._value(bool, name, default, "boolean")


    def strslist (self, name, default=None, sep=","):
        """
        Get a configuration field as a list of separated strings.

        Separator character or string is used to split the field value
        into substrings::

            afield = foo, bar, baz

        Leading and trailing whitespace in list elements is stripped.

        If list elements should be able to contain any characters
        or whitespace is significant, use delimited list instead (L{strdlist}).

        @param sep: the separator
        @type sep: string

        @rtype: unicode or as C{default}
        """

        value = self._value(unicode, name, None, "string")
        if value is None:
            return default
        lst = value.split(sep)
        lst = [x.strip() for x in lst]

        return lst


    def strdlist (self, name, default=None):
        """
        Get a configuration field as a list of delimited strings.

        Delimiter is taken to be the non-alphanumeric character with
        which the field value starts. In this example::

            afield = /foo/bar/baz/

        the delimiter is C{/}.

        If the field value does not start with a non-alphanumeric,
        or it does not end with the delimiter, error is signalled.

        @rtype: unicode or as C{default}
        """

        value = self._value(unicode, name, None, "string")
        if value is None:
            return default
        value = value.strip()

        if len(value) < 2:
            error(_("@info",
                    "User configuration: value '%(val)s' of field '%(field)s' "
                    "in section '%(sec)s' is too short for a delimited list.")
                  % dict(val=value, field=name, sec=self.name))
        if value[0].isalnum():
            error(_("@info",
                    "User configuration: value '%(val)s' of field '%(field)s' "
                    "in section '%(sec)s' does not start with "
                    "a non-alphanumeric delimiter character.")
                  % dict(val=value, field=name, sec=self.name))

        delim = value[0]

        if value[-1] != delim:
            error(_("@info",
                    "User configuration: value '%(val)s' of field '%(field)s' "
                    "in section '%(sec)s' does not end with "
                    "the delimiter character with which it starts.")
                  % dict(val=value, field=name, sec=self.name))

        lst = value[1:-1].split(delim)

        return lst


def strbool (value):
    """
    Parse the string specification of a boolean value.

    Values considered C{false} are: C{"0"}, C{"no"}, C{"false"}, C{"off"};
    and C{True}: C{1}, C{"yes"}, C{"true"}, C{"on"}.
    String is stripped of leading and trailing whitespace and lowercased
    before matching.

    If the string matches none of the expected logical specifiers,
    C{None} is returned.

    @param value: string to parse
    @type value: string

    @return: parsed boolean
    @rtype: bool
    """

    value = value.strip().lower()
    if value in ("0", "no", "false", "off"):
        return False
    elif value in ("1", "yes", "true", "on"):
        return True
    else:
        return None

