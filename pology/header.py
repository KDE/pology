# -*- coding: UTF-8 -*-

"""
Header entry in PO catalogs.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

from pology import PologyError
from pology.wrap import wrap_field
from pology.monitored import Monitored, Monlist, Monpair
from .message import Message

import datetime
import time
import re

_Header_spec = {
    "title" : {"type" : Monlist,
               "spec" : {"*" : {"type" : str}}},
    "copyright" : {"type" : (str, type(None))},
    "license" : {"type" : (str, type(None))},
    "author" : {"type" : Monlist,
                "spec" : {"*" : {"type" : str}}},
    "comment" : {"type" : Monlist,
                 "spec" : {"*" : {"type" : str}}},
    "field" : {"type" : Monlist,
               "spec" : {"*" : {"type" : Monpair,
                                "spec" : {"first" : {"type" : str},
                                          "second" : {"type" : str}}}}},
    "initialized" : {"type" : bool, "derived" : True},
    # Dummies for summary iteration in catalog:
    "obsolete" : {"type" : bool, "derived" : True},
    "key" : {"type" : bool, "derived" : True},
}

class Header (Monitored):
    """
    Header entry in PO catalogs.

    The PO header is syntactically just another entry in the catalog,
    but with different semantics. Therefore, instead operating on it using
    L{Message}, this class provides a different set of interface attributes
    and methods.

    Like L{Message}, this class implements monitoring; the starred-types
    (e.g. C{list*}) are according to the same convention as for messages,
    and also the strings are assumed unicode unless otherwise noted.

    There is no lightweight alternative to the monitored header, like that of
    L{MessageUnsafe} for messages, because no performance demand is expected
    for the headers only.

    @ivar title: comment lines giving the title
    @type title: list* of strings

    @ivar copyright: comment line with the copyright statement
    @type copyright: string

    @ivar license: comment line with the license statement
    @type license: string

    @ivar author: comment lines stating translators who worked on this catalog
    @type author: list* of strings

    @ivar comment: the free comment lines, being none of the specific ones
    @type comment: list* of strings

    @ivar field: parsed header fields as key-value string pairs
    @type field: list* of pairs*

    @ivar initialized: (read-only) whether the header is fully initialized
    @type initialized: bool

    @see: L{Message}
    """

    def __init__ (self, init=None):
        """
        Initializes the header by the given message or header.

        @param init: the PO entry containing the header, or another header
        @type init: subclass of L{Message_base}, or L{Header}
        """

        if isinstance(init, Header): # copy header fields
            hdr = init
            self._title = Monlist(hdr._title)
            self._copyright = hdr._copyright
            self._license = hdr._license
            self._author = Monlist(hdr._author)
            self._comment = Monlist(hdr._comment)
            self._field = Monlist(list(map(Monpair, hdr._field)))

            # Create the message.
            self._message = hdr.to_msg()

        elif init: # parse header message
            msg = init
            # Comments.
            self._title = Monlist()
            self._copyright = ""
            self._license = ""
            self._author = Monlist()
            self._comment = Monlist()
            intitle = True
            for c in msg.manual_comment:
                if 0: pass
                elif (    not self._copyright
                      and re.search(r"copyright|\(C\)|©", c, re.I|re.U)
                ):
                    self._copyright = c
                    intitle = False
                elif (    not self._license
                      and (    re.search("license", c, re.I)
                           and not re.search("^translation *of.* to", c, re.I))
                ):
                    self._license = c
                    intitle = False
                elif re.search("<.*@.*>", c):
                    self._author.append(c)
                    intitle = False
                elif intitle:
                    self._title.append(c)
                else:
                    self._comment.append(c)

            # Header fields.
            self._field = Monlist()
            for field in msg.msgstr[0].split("\n"):
                m = re.match(r"(.*?): ?(.*)", field)
                if m: self._field.append(Monpair(m.groups()))

            # Copy the message.
            self._message = Message(msg)

        else: # create default fields
            self._title = Monlist(["SOME DESCRIPTIVE TITLE."]);
            self._copyright = "Copyright (C) YEAR THE PACKAGE'S COPYRIGHT HOLDER"
            self._license = "This file is distributed under the same license as the PACKAGE package."
            self._author = Monlist(["FIRST AUTHOR <EMAIL@ADDRESS>, YEAR."])
            self._comment = Monlist([""])

            self._field = Monlist([
                Monpair(("Project-Id-Version", "PACKAGE VERSION")),
                Monpair(("Report-Msgid-Bugs-To", "")),
                Monpair(("POT-Creation-Date", format_datetime())),
                Monpair(("PO-Revision-Date", "YEAR-MO-DA HO:MI+ZONE")),
                Monpair(("Last-Translator", "FULL NAME <EMAIL@ADDRESS>")),
                Monpair(("Language-Team", "LANGUAGE <LL@li.org>")),
                Monpair(("Language", "")),
                Monpair(("MIME-Version", "1.0")),
                Monpair(("Content-Type", "text/plain; charset=CHARSET")),
                Monpair(("Content-Transfer-Encoding", "8bit")),
                Monpair(("Plural-Forms", "nplurals=INTEGER; plural=EXPRESSION;")),
            ])

            # Create the message.
            self._message = Message()
            self._remake_msg(force=True)

        self.assert_spec_init(_Header_spec)

        # Unmodify all monitored members.
        self.modcount = 0


    def __getattr__ (self, att):
        """
        Attribute getter.

        Processes read-only attributes, and sends others to the base class.

        @param att: name of the attribute to get
        @returns: attribute value
        """

        if att == "obsolete":
            return False
        elif att == "key":
            return Message().key # key of an empty-msgid message
        elif att == "initialized":
            # Check if all necessary fields have been initialized.
            gfv = self.get_field_value
            return not (False
               or "PACKAGE VERSION" in gfv("Project-Id-Version", "")
               or "YEAR-MO-DA" in gfv("PO-Revision-Date", "")
               or "FULL NAME" in gfv("Last-Translator", "")
               or "LANGUAGE" in gfv("Language-Team", "")
               or "CHARSET" in gfv("Content-Type", "")
               or "ENCODING" in gfv("Content-Transfer-Encoding", "")
               or "INTEGER" in gfv("Plural-Forms", "")
               or "EXPRESSION" in gfv("Plural-Forms", "")
            )
        else:
            return Monitored.__getattr__(self, att)


    def get (self, att, default=None):
        """
        Get attribute value.

        Allows accessing the header like a dictionary.

        @param att: name of the attribute to get
        @type att: string
        @param default: value to return if the attribute does not exist

        @returns: value of the attribute or the default value
        """

        if hasattr(self, att):
            return getattr(self, att)
        else:
            return default


    def _remake_msg (self, force=False):

        m = self._message

        if (force
            or self.title_modcount or self.title.modcount
            or self.copyright_modcount
            or self.license_modcount
            or self.author_modcount or self.author.modcount
            or self.comment_modcount or self.comment.modcount
        ):
            m.manual_comment = Monlist()
            for t in self.title:
                m.manual_comment.append(t)
            if self.copyright:
                m.manual_comment.append(self.copyright)
            if self.license:
                m.manual_comment.append(self.license)
            for a in self.author:
                m.manual_comment.append(a)
            for c in self.comment:
                m.manual_comment.append(c)

        if force or self.field_modcount or self.field.modcount:
            m.msgstr = Monlist([""])
            for field in self.field:
                m.msgstr[0] += "%s: %s\n" % tuple(field)

        if force or self.modcount:
            m.fuzzy = not self.initialized


    def __eq__ (self, ohdr):
        """
        Reports wheter headers are equal in all apparent parts.

        "Apparent" parts include all those which are visible in the PO file.
        I.e. the check will ignore internal states, like line caches, etc.

        @returns: C{True} if headers are equal in apparent parts
        @rtype: bool
        """

        return self.to_msg() == ohdr.to_msg()


    def __ne__ (self, ohdr):
        """
        Reports wheter headers are not equal in some apparent parts.

        Equivalent to C{not (self == ohdr)}.

        @returns: C{False} if headers are equal in all apparent parts
        @rtype: bool
        """

        return not self.__eq__(ohdr)


    def to_msg (self, force=False):
        """
        Convert the header into ordinary message object.

        The message object returned may be the modification of the one
        passed to the constructor. In that case, and if the message object
        has monitoring features, the force parameter will tell whether to
        modify all message elements, or to try to keep the changes minimal.

        @param force: whether to recreate all message elements
        @type force: bool

        @returns: header as message
        @rtype: the type that initialized the object
        """

        self._remake_msg(force)
        return self._message


    def to_lines (self, wrapf=wrap_field, force=False, colorize=0):
        """
        The line-representation of the header.

        Equivalent to the same-named method of message classes.

        @see: L{Message_base}
        """

        return self.to_msg(force).to_lines(wrapf, force, colorize)


    def to_string (self, wrapf=wrap_field, force=False, colorize=0):
        """
        The string-representation of the header.

        Equivalent to the same-named method of message classes.

        @see: L{Message_base}
        """

        return self.to_msg(force).to_string(wrapf, force, colorize)


    def select_fields (self, name):
        """
        Find header fields with the given name.

        Header fields need not be unique.

        @param name: look for the fields with this name
        @type name: string

        @returns: references to name-value pairs matching the field name
        @rtype: list of pairs*
        """

        fields = []
        for pair in self.field:
            if pair.first == name:
                fields.append(pair)
        return fields


    def get_field_value (self, name, default=None):
        """
        Get the value of the given header field.

        If there are several fields with the same name, it is undefined which
        of them will supply the value; this method should be used only
        for fields which are expected to be unique.
        If there are no fields named as requested, C{default} is returned.

        @param name: field name
        @type name: string
        @param default: value returned if there is no such field
        @type default: as given

        @returns: field value
        @rtype: string or C{default}
        """

        for pair in self.field:
            if pair.first == name:
                return pair.second
        return default


    def replace_field_value (self, name, new_value, nth=0):
        """
        Replace the value of the n-th occurence of the named header field.

        Header fields need not be unique, hence the n-th qualification.

        @param name: name of the header field
        @type name: string

        @param new_value: new value for the field
        @type new_value: string

        @param nth: replace the value of this field among same-named fields
        @type nth: int

        @returns: True if the requested field was found, False otherwise
        @rtype: bool
        """

        nfound = 0
        for i in range(len(self._field)):
            if self.field[i][0] == name:
                nfound += 1
                if nfound - 1 == nth:
                    self.field[i] = Monpair((str(name), new_value))
                    break

        return nfound - 1 == nth


    def set_field (self, name, value, after=None, before=None, reorder=False):
        """
        Set a header field to a value.

        If the field already exists, its value is replaced with the given one.
        If there are several same-named fields, it is undefined which one
        and how many of them are going to have their values replaced;
        this method should be used only for fields expected to be unique.
        If there is no such field yet, it is inserted into the header;
        after the field C{after} or before the field C{before} if given
        and existing, or appended to the end otherwise.
        If the field already exists, but not in the position according to
        C{after} or C{before}, reordering can be requested too.

        @param name: name of the header field
        @type name: unicode

        @param value: new value for the field
        @type value: unicode

        @param after: the field to insert after
        @type after: string

        @param before: the field to insert before
        @type before: string

        @param reorder: whether to move an existing field into better position
        @type reorder: bool

        @returns: position where the field was modified or inserted
        @rtype: int
        """

        ins_pos = -1
        rpl_pos = -1
        for i in range(len(self._field)):
            if self.field[i][0] == name:
                rpl_pos = i
                if not reorder:
                    break
            if (   (after and i > 0 and self.field[i - 1][0] == after)
                or (before and self.field[i][0] == before)
            ):
                ins_pos = i
                # Do not break, must try all fields for value replacement.

        if reorder and ins_pos >= 0 and rpl_pos >= 0 and ins_pos != rpl_pos:
            self._field.pop(rpl_pos)
            if ins_pos > rpl_pos:
                ins_pos -= 1
            rpl_pos = -1

        pair = Monpair((name, value))
        if rpl_pos >= 0:
            self._field[rpl_pos] = pair
            pos = rpl_pos
        elif ins_pos >= 0:
            self._field.insert(ins_pos, pair)
            pos = ins_pos
        else:
            self._field.append(pair)
            pos = len(self._field)

        return pos


    def remove_field (self, name):
        """
        Remove header fields with the given name, if it exists.

        @param name: remove fields with this name
        @type name: string

        @return: number of removed fields
        @rtype: int
        """

        i = 0
        nrem = 0
        while i < len(self.field):
            if self.field[i][0] == name:
                self.field.pop(i)
                nrem += 1
            else:
                i += 1

        return nrem


_dt_fmt = "%Y-%m-%d %H:%M:%S%z"
_dt_fmt_nosec = "%Y-%m-%d %H:%M%z"

def format_datetime (dt=None, wsec=False):
    """
    Format datetime as found in PO header fields.

    If a particular datetime object C{dt} is not given,
    current datetime is used instead.

    If C{wsec} is C{False}, the formatted string will not contain
    the seconds component, which is usual for PO header datetimes.
    If seconds accuracy is desired, C{wsec} can be set to C{True}.

    @param dt: datetime
    @type dt: datetime.datetime
    @param wsec: whether to add seconds component
    @type wsec: bool

    @return: formatted datetime
    @rtype: string
    """

    if dt is not None:
        if wsec:
            dtstr = dt.strftime(_dt_fmt)
        else:
            dtstr = dt.strftime(_dt_fmt_nosec)
        # If timezone is not present, assume UTC.
        if dt.tzinfo is None:
            dtstr += "+0000"
    else:
        if wsec:
            dtstr = time.strftime(_dt_fmt)
        else:
            dtstr = time.strftime(_dt_fmt_nosec)

    return str(dtstr)


_parse_date_rxs = [re.compile(x) for x in (
    r"^ *(\d+)-(\d+)-(\d+) *(\d+):(\d+):(\d+) *([+-]\d+) *$",
    r"^ *(\d+)-(\d+)-(\d+) *(\d+):(\d+)() *([+-]\d+) *$",
    # ...needs empty group to differentiate from the next case.
    r"^ *(\d+)-(\d+)-(\d+) *(\d+):(\d+):(\d+) *$",
    r"^ *(\d+)-(\d+)-(\d+) *(\d+):(\d+) *$",
    r"^ *(\d+)-(\d+)-(\d+) *$",
    r"^ *(\d+)-(\d+) *$",
    r"^ *(\d+) *$",
)]

def parse_datetime (dstr):
    """
    Parse formatted datetime from a PO header field into a datetime object.

    The formatted datetime may also have a seconds component,
    which is typically not present in PO headers.
    It may also lack a contiguous number of components from the back,
    e.g. having no time zone offset, or no time at all.

    @param dstr: formatted datetime
    @type dstr: string

    @return: datetime object
    @rtype: datetime.datetime
    """

    for parse_date_rx in _parse_date_rxs:
        m = parse_date_rx.search(dstr)
        if m:
            break
    if not m:
        raise PologyError(_("@info",
                            "Cannot parse datetime string '%(str)s'.",
                            str=dstr))
    pgroups = list([int(x or 0) for x in m.groups()])
    pgroups.extend([1] * (3 - len(pgroups)))
    pgroups.extend([0] * (7 - len(pgroups)))
    year, month, day, hour, minute, second, off = pgroups
    offhr = off // 100
    offmin = off % 100
    dt = datetime.datetime(year=year, month=month, day=day,
                           hour=hour, minute=minute, second=second,
                           tzinfo=TZInfo(hours=offhr, minutes=offmin))
    return dt


class TZInfo (datetime.tzinfo):
    """
    A simple derived time zone info for use in datetime objects.
    """

    def __init__ (self, hours=None, minutes=None):
        """
        Create a time zone with given offset in hours and minutes.

        The offset given by C{minutes} is added to that given by C{hours},
        e.g. C{hours=2} and C{minutes=30} means two and a half hours offset.
        If C{minutes} is given but C{hours} is not, C{hours} is considered zero.
        If neither C{hours} nor C{minutes} are given,
        the offset is read from system time zone.

        @param hours: the time zone offset in hours
        @type hours: int
        @param minutes: additional offset in minutes
        @type minutes: int
        """

        self._isdst = time.localtime()[-1]
        if hours is None and minutes is None:
            tzoff_sec = -(time.altzone if self._isdst else time.timezone)
            tzoff_hr = tzoff_sec // 3600
            tzoff_min = (tzoff_sec - tzoff_hr * 3600) // 60
        else:
            tzoff_hr = hours or 0
            tzoff_min = minutes or 0

        self._dst = datetime.timedelta(0)
        self._utcoffset = datetime.timedelta(hours=tzoff_hr, minutes=tzoff_min)


    def utcoffset (self, dt):

        return self._utcoffset


    def dst (self, dt):

        return self._dst


    def tzname (self, dt):

        return time.tzname[self._isdst]

