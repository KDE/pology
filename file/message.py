# -*- coding: UTF-8 -*-

"""
Message entries in PO catalogs.

Classes from this module define the entries proper,
while the header entry is handled by L{pology.file.header}.

@see: L{pology.file.header}

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

from pology.misc.escape import escape
from pology.misc.wrap import wrap_field, wrap_comment, wrap_comment_unwrap
from pology.misc.monitored import Monitored, Monlist, Monset, Monpair

_Message_spec = {
    "manual_comment" : {"type" : Monlist,
                        "spec" : {"*" : {"type" : unicode}}},
    "auto_comment" : {"type" : Monlist,
                      "spec" : {"*" : {"type" : unicode}}},
    "source" : {"type" : Monlist,
                "spec" : {"*" : {"type" : Monpair,
                                 "spec" : {"first" : {"type" : unicode},
                                           "second" : {"type" : int}}}}},
    "flag" : {"type" : Monset,
              "spec" : {"*" : {"type" : unicode}}},

    "obsolete" : {"type" : bool},

    "msgctxt_previous" : {"type" : unicode},
    "msgid_previous" : {"type" : unicode},
    "msgid_plural_previous" : {"type" : unicode},

    "msgctxt" : {"type" : unicode},
    "msgid" : {"type" : unicode},
    "msgid_plural" : {"type" : unicode},
    "msgstr" : {"type" : Monlist,
                "spec" : {"*" : {"type" : unicode}}},

    "key" : {"type" : unicode, "derived" : True},
    "fuzzy" : {"type" : bool},
    "untranslated" : {"type" : bool, "derived" : True},
    "translated" : {"type" : bool, "derived" : True},
    "format" : {"type" : unicode, "derived" : True},

    "refline" : {"type" : int},
    "refentry" : {"type" : int},
}
_Message_single_strings = (
    "msgctxt_previous", "msgid_previous", "msgid_plural_previous",
    "msgctxt", "msgid", "msgid_plural",
)

class Message_base (object):
    """
    Abstract base class for entries in PO catalogs.

    Elements of the message are accessed through instance variables.
    Some of them are read-only, typically those that are derived from the
    normal read-write variables and cannot be set independently.

    The precise type of each variable depends on the subclass through which
    it is accessed, but has a general behavior of one of the standard types.
    E.g. when the behavior is that of a list, the type is stated as C{list*}.
    All strings are assumed unicode, except where noted otherwise.

    Regardless of the exact composition of the message, each will have all
    the instance variables listed. In case the message actually does not have
    an element corresponding to an instance variable, that variable will have
    an appropriate null value.

    Only the read-only instance variables are provided by this base class,
    while the read-write variables are to be provided by its subclasses.
    All are listed here, however, as the interface that all subclasses
    should implement.

    @ivar manual_comment: manual (translator) comments (C{# ...})
    @type manual_comment: list* of strings

    @ivar auto_comment: automatic comments (C{#. ...})
    @type auto_comment: list* of strings

    @ivar source: source references, as filepath:lineno pairs (C{#: ...})
    @type source: list* of pairs*

    @ivar flag: message flags (C{#, ...})
    @type flag: set* of strings

    @ivar obsolete: whether entry is obsolete (C{#~ ...})
    @type obsolete: bool

    @ivar msgctxt_previous: previous context field (C{#| msgctxt "..."})
    @type msgctxt_previous: string

    @ivar msgid_previous: previous message field (C{#| msgid "..."})
    @type msgid_previous: string

    @ivar msgid_plural_previous:
        previous plural field (C{#| msgid_plural "..."})
    @type msgid_plural_previous: string

    @ivar msgctxt: context field (C{msgctxt "..."})
    @type msgctxt: string

    @ivar msgid: message field (C{msgid "..."})
    @type msgid: string

    @ivar msgid_plural: plural field (C{msgid_plural "..."})
    @type msgid_plural: string

    @ivar msgstr: translation fields (C{msgstr "..."}, C{msgstr[n] "..."})
    @type msgstr: list* of strings

    @ivar key: (read-only)
        message key, which defines a unique entry in the catalog

        An undefined composition of C{msgctxt} and C{msgid} fields
        (but not C{msgid_plural} when it exists).
    @type key: string

    @ivar fuzzy:
        whether the message is fuzzy

        The state of fuzziness can be also checked by looking for the C{fuzzy}
        flag in the set of flags, but using this variable is shorter,
        and the message can be properly unfuzzied by assigning False to it
        (e.g. C{*_previous} fields are cleared as well).
    @type fuzzy: bool

    @ivar untranslated: (read-only)
        whether the message is untranslated (False for fuzzy messages)
    @type untranslated: bool

    @ivar translated: (read-only)
        whether the message is translated (False for fuzzy messages)
    @type translated: bool

    @ivar format: (read-only)
        whether the message contains any format flags (e.g. C{c-format})
    @type translated: bool

    @ivar refline:
        referent line number of the message inside the catalog

        Valid only if there were no modifications to the catalog, otherwise
        undefined (made valid again after syncing the catalog).
        Normally this is the line number of C{msgid} keyword,
        but not guaranteed to be so.
    @type refline: int

    @ivar refentry:
        referent entry number of the message inside the catalog

        Valid only if there were no additions/removals of messages from the
        catalog, otherwise undefined (made valid again after syncing the
        catalog).
    @type refentry: int

    @see: L{Message}
    @see: L{MessageUnsafe}
    """

    def __init__ (self, getsetattr):
        """
        Internal constructor for subclasses' usage.

        @param getsetattr:
            the object with C{__getattr__} and C{__setattr__} methods,
            as handler for unhandled instance variables
        """

        self.__dict__["^getsetattr"] = getsetattr


    def __getattr__ (self, att):
        """
        Attribute getter.

        Processes read-only variables, and sends others to the getter
        given by the constructor.

        @param att: name of the attribute to get
        @returns: attribute value
        """

        if 0: pass

        elif att == "translated":
            if self.fuzzy or self.obsolete:
                return False
            if not self.msgstr:
                return False
            # Consider message translated if at least one msgstr is translated:
            # that's how gettext tools do, but then they report an error for
            # missing argument in non-translated msgstrs.
            for val in self.msgstr:
                if val:
                    return True
            return False

        elif att == "untranslated":
            if self.fuzzy or self.obsolete:
                return False
            if not self.msgstr:
                return True
            for val in self.msgstr:
                if not val:
                    return True
            return False

        elif att == "key":
            return self.msgctxt + "|~|" + self.msgid

        elif att == "format":
            format_flag = ""
            for flag in self.flag:
                if flag.find("-format") >= 0:
                    format_flag = flag
                    break
            return format_flag

        else:
            return self.__dict__["^getsetattr"].__getattr__(self, att)


    def __setattr__ (self, att, val):
        """
        Attribute setter.

        May act upon some attributes (e.g. checks), but finally passes
        all of them to the setter given by the constructor.

        @param att: name of the attribute to set
        @param val: value to set the attribute to
        """

        if 0: pass

        elif att == "fuzzy":
            if self.fuzzy != val:
                if val == True:
                    self.flag.add(u"fuzzy")
                else:
                    self.flag.remove(u"fuzzy")

        self.__dict__["^getsetattr"].__setattr__(self, att, val)


    def _renew_lines_bymod (self, mod, wrapf=wrap_field, force=False):

        prefix = {}
        if self.obsolete:
            prefix["curr"] = "#~ "
            prefix["prev"] = "#~| "
        else:
            prefix["curr"] = ""
            prefix["prev"] = "#| "

        if mod["manual_comment"] or not self._lines_manual_comment or force:
            self._lines_manual_comment = []
            for manc in self.manual_comment:
                self._lines_manual_comment.extend(wrap_comment_unwrap("", manc))

        if mod["auto_comment"] or not self._lines_auto_comment or force:
            self._lines_auto_comment = []
            for autoc in self.auto_comment:
                self._lines_auto_comment.extend(wrap_comment_unwrap(".", autoc))

        if mod["source"] or not self._lines_source or force:
            self._lines_source = []
            srcrefs = []
            for src in self.source:
                if src[1] > 0:
                    srcrefs.append(src[0] + ":" + str(src[1]))
                else:
                    srcrefs.append(src[0])
            if srcrefs:
                self._lines_source = wrap_comment(":", " ".join(srcrefs))

        if mod["flag"] or not self._lines_flag or force:
            self._lines_flag = []
            # Rearange so that fuzzy is first, if present.
            flst = []
            for fl in self.flag:
                if fl != u"fuzzy":
                    flst.append(fl)
                else:
                    flst.insert(0, fl)
            if flst:
                self._lines_flag = wrap_comment(",", ", ".join(flst))

        for att in _Message_single_strings:
            att_lins = "_lines_" + att
            if mod[att] or not self.__dict__[att_lins] or force:
                # modcount of this string > 0 or lines not cached or forced
                self.__dict__[att_lins] = []
                msgsth = getattr(self, att)
                if msgsth: # string not empty
                    if att.endswith("_previous"):
                        fname = att[:-len("_previous")]
                        pstat = "prev"
                    else:
                        fname = att
                        pstat = "curr"
                    self.__dict__[att_lins] = wrapf(fname, escape(msgsth),
                                                    prefix[pstat])
                elif att == "msgid": # msgid must go in, even empty
                    self.__dict__[att_lins] = wrapf("msgid", "")

        if mod["msgstr"] or not self._lines_msgstr or force:
            self._lines_msgstr = []
            if not self.msgstr:
                self._lines_msgstr.extend(wrapf("msgstr", "", prefix["curr"]))
            elif not self.msgid_plural:
                self._lines_msgstr.extend(wrapf("msgstr",
                                          escape(self.msgstr[0]),
                                          prefix["curr"]))
            else:
                for i in range(len(self.msgstr)):
                    self._lines_msgstr.extend(wrapf("msgstr[%d]" % (i,),
                                                    escape(self.msgstr[i]),
                                                    prefix["curr"]))

        # Marshal the lines into proper order.
        self._lines_all = []
        lins = self._lines_all

        lins.extend(self._lines_manual_comment)
        lins.extend(self._lines_auto_comment)
        if not self.obsolete: # no source for an obsolete message
            lins.extend(self._lines_source)
        lins.extend(self._lines_flag)

        if u"fuzzy" in self.flag:
        # Old original makes sense only for a message with a fuzzy flag.
        # Note that this check is not the same as checking for self.fuzzy,
        # as self.fuzzy is false for an obsolete message with a fuzzy flag.
            lins.extend(self._lines_msgctxt_previous)
            lins.extend(self._lines_msgid_previous)
            lins.extend(self._lines_msgid_plural_previous)

        lins.extend(self._lines_msgctxt)
        lins.extend(self._lines_msgid)
        lins.extend(self._lines_msgid_plural)
        lins.extend(self._lines_msgstr)

        if self._lines_all[-1] != "\n":
            lins.extend(u"\n")


    def to_lines (self, wrapf=wrap_field, force=False):
        """
        The line-representation of the message.

        Lines are returned with newlines included.

        @param wrapf:
            the function used for wrapping message fields (msgctxt, msgid, ...)
            As arguments the function should accept the field name,
            the field text, and the prefix to all lines,
            and return the list of wrapped lines (with newlines included).
        @type wrapf: string, string, string -> list of strings

        @param force:
            whether to force reformatting of all elements.
            Subclasses may keep a track of lines exactly as read from the
            PO file, and allow reformatting of only the modified elements of
            the message.
        @type force: bool

        @returns: formatted lines
        @rtype: list of strings

        @see: L{pology.misc.wrap}
        """

        if force or self.modcount:
            self._renew_lines(wrapf, force)

        return self._lines_all


    def to_string (self, wrapf=wrap_field, force=False):
        """
        The string-representation of the message.

        Passes the arguments to L{to_lines} and joins the resulting list.

        @see: L{to_lines}
        """

        return "".join(self.to_lines(wrapf, force))


    def _append_to_list (self, other, att):

        self_list = getattr(self, att)
        other_list = getattr(other, att)
        for el in other_list:
            self_list.append(el)


    def _overwrite_list (self, other, att):

        # Overwrites self list by element-assignment/append/pop,
        # so that modification history is tracked.
        self_list = getattr(self, att)
        other_list = getattr(other, att)
        self_len = len(self_list)
        other_len = len(other_list)
        if self_len <= other_len:
            for i in range(self_len):
                self_list[i] = other_list[i]
            for i in range(self_len, other_len):
                self_list.append(other_list[i])
        else:
            for i in range(other_len):
                self_list[i] = other_list[i]
            for i in range(other_len, self_len):
                self_list.pop()


    def merge (self, other):
        """
        Merge in the contents of the other message with the same key.

        Merging is basically riddled with heuristics, depending on the
        state of this and the other message (translated/fuzzy/...)
        When tight control is desired, the merging should be done manually.

        @param other: the message to merge the contents from
        @type other: object containing all the needed instance variables

        @returns:
            True if any changes were made by merging, False otherwise
            (but the reliability of this depends on the subclass).
        @rtype: bool
        """

        # Assert key equality.
        if self.key != other.key:
            raise StandardError, "cannot merge messages with different keys"

        # Don't do anything if any of the two messages are obsolete.
        if self.obsolete or other.obsolete:
            return False

        modcount_before = self.modcount

        # Plural always overrides non-plural, regardless of self/other state.
        if not self.msgid_plural and other.msgid_plural:
            if other.manual_comment:
                self._overwrite_list(other, "manual_comment")
            if other.fuzzy:
                self.msgctxt_previous = other.msgctxt_previous
                self.msgid_previous = other.msgid_previous
                self.msgid_plural_previous = other.msgid_plural_previous
            self.msgid_plural = other.msgid_plural
            self._overwrite_list(other, "msgstr")
            self.fuzzy = other.fuzzy

        else:
            if (   (self.translated and other.translated)
                or (self.fuzzy and other.fuzzy)
                or (self.untranslated and other.untranslated)
            ):
                if not self.manual_comment:
                    self._overwrite_list(other, "manual_comment")
                if other.msgid_plural:
                    self.msgid_plural = other.msgid_plural

            elif self.fuzzy and other.translated:
                self._overwrite_list(other, "manual_comment")
                if not self.msgid_plural or other.msgid_plural:
                    if other.msgid_plural:
                        self.msgid_plural = other.msgid_plural
                    self._overwrite_list(other, "msgstr")
                    if self.msgid_plural == other.msgid_plural:
                        self.fuzzy = False

            elif self.untranslated and (other.translated or other.fuzzy):
                self._overwrite_list(other, "manual_comment")
                if not self.msgid_plural or other.msgid_plural:
                    if other.fuzzy:
                        self.msgctxt_previous = other.msgctxt_previous
                        self.msgid_previous = other.msgid_previous
                        self.msgid_plural_previous = other.msgid_plural_previous
                    if other.msgid_plural:
                        self.msgid_plural = other.msgid_plural
                    self._overwrite_list(other, "msgstr")
                    self.fuzzy = other.fuzzy

        return modcount_before < self.modcount


    def state (self):
        """
        Coded description of the translation state of the message.

        Code string can be one of:
        "T" (translated), "F" (fuzzy), "U" (untranslated), "O" (obsolete).

        @returns: coded translation state
        @rtype: string
        """

        if self.obsolete:
            return "O"
        elif self.fuzzy:
            return "F"
        elif self.translated:
            return "T"
        else:
            return "U"


class Message (Message_base, Monitored): # order important for get/setattr
    """
    The default class for catalog entries.

    The interface is inherited from L{Message_base}, but when used through
    this class it behaves in a special way: the modifications are I{monitored}.
    If you don't need to modify the messages after creation, consider using
    the faster L{MessageUnsafe} class.

    The message interface variables are kept under tight check:
    no new variable can be created by assignment (silent typos not possible),
    and all assignment are checked for value types (cannot assign a number
    where a unicode string is expected).

    Each instance variable has a counterpart modification counter,
    as well as the message as whole. For example:

        >>> msg = Message()
        >>> msg.modcount
        0
        >>> msg.msgid_modcount
        0
        >>> msg.msgid = u"Blah, blah..."
        >>> msg.msgid_modcount
        1
        >>> msg.modcount
        1

    The modifications are tracked by value-comparison, assigning the same
    value does not increase the counters. A typicall use of the counters
    would be to record the top counter, do some operations on the message,
    and check afterwards if the top counter has increased to know if the
    message was modified.

    To implement monitoring, the loosely defined types in the base class
    (those with a star) are actually of one of the internal C{Mon*} types:
    L{Monlist}, L{Monset}, L{Monpair}. They implement some, but not all, of
    the functionality of their standard counterparts. Like this class, they
    inherit from L{Monitored} and have own modification counters:

        >>> msg = Message()
        >>> msg.msgstr = Monlist([u"Foo, bar, "])
        >>> msg.msgstr_modcount
        1
        >>> msg.modcount
        1
        >>> msg.msgstr[0] += "baz..."
        >>> msg.msgstr.modcount
        1
        >>> msg.modcount
        2

    Note the difference between C{msg.msgstr_modcount} and
    C{msg.msgstr.modcount} -- the first increases when the instance variable
    is assigned a different monitored list, while the second when the elements
    of the list object change.

    @see: L{Message_base}
    @see: L{MessageUnsafe}
    @see: L{pology.misc.monitored}
    """

    def __init__ (self, init={}):
        """
        Initializes the message elements by the values in the dictionary.

        The dictionary keys are like the names of instance variables in the
        interface, and not all must be supplied. Those left out will be
        initialized to appropriate null values.

        The monitored sequences should be supplied as their ordinary
        counterparts (e.g. a C{list} in place of L{Monlist}),

        @param init: dictionary of initial values
        @type init: dict
        """

        Message_base.__init__(self, Monitored)

        self._manual_comment = Monlist(init.get("manual_comment", []))
        self._auto_comment = Monlist(init.get("auto_comment", []))
        self._source = Monlist([Monpair(*x) for x in init.get("source", [])])
        self._flag = Monset(init.get("flag", []))

        self._obsolete = init.get("obsolete", False)

        self._msgctxt_previous = init.get("msgctxt_previous", u"")
        self._msgid_previous = init.get("msgid_previous", u"")
        self._msgid_plural_previous = init.get("msgid_plural_previous", u"")

        self._msgctxt = init.get("msgctxt", u"")
        self._msgid = init.get("msgid", u"")
        self._msgid_plural = init.get("msgid_plural", u"")
        self._msgstr = Monlist(init.get("msgstr", []))

        self._fuzzy = (u"fuzzy" in self._flag and not self._obsolete)

        self._refline = init.get("refline", -1)
        self._refentry = init.get("refentry", -1)

        self.assert_spec_init(_Message_spec)

        # Line caches.
        self._lines_all = init.get("lines_all", [])
        self._lines_manual_comment = init.get("lines_manual_comment", [])
        self._lines_auto_comment = init.get("lines_auto_comment", [])
        self._lines_source = init.get("lines_source", [])
        self._lines_flag = init.get("lines_flag", [])
        self._lines_msgctxt_previous = init.get("lines_msgctxt_previous", [])
        self._lines_msgid_previous = init.get("lines_msgid_previous", [])
        self._lines_msgid_plural_previous = \
            init.get("lines_msgid_plural_previous", [])
        self._lines_msgctxt = init.get("lines_msgctxt", [])
        self._lines_msgid = init.get("lines_msgid", [])
        self._lines_msgid_plural = init.get("lines_msgid_plural", [])
        self._lines_msgstr = init.get("lines_msgstr", [])


    def _renew_lines (self, wrapf=wrap_field, force=False):

        mod = {}
        if not self.obsolete_modcount:
            mod["manual_comment"] =    self.manual_comment_modcount \
                                    or self.manual_comment.modcount
            mod["auto_comment"] =    self.auto_comment_modcount \
                                or self.auto_comment.modcount
            mod["source"] = self.source_modcount or self.source.modcount
            mod["flag"] = self.flag_modcount or self.flag.modcount
            for att in _Message_single_strings:
                mod[att] = getattr(self, att + "_modcount") > 0
            mod["msgstr"] = self.msgstr_modcount or self.msgstr.modcount
        else:
            # Must recompute all lines if the message has been modified
            # by changing the obsolete status.
            mod["manual_comment"] = True
            mod["auto_comment"] = True
            mod["source"] = True
            mod["flag"] = True
            for att in _Message_single_strings:
                mod[att] = True
            mod["msgstr"] = True

        return self._renew_lines_bymod(mod, wrapf, force)


class MessageUnsafe (Message_base):
    """
    The lightweight class for catalog entries, for read-only applications.

    Unlike the L{Message}, this class does nothing fancy with the interface
    variables. The interface instance variables are implemented as in
    L{Message_base}, where the starred lists are standard lists, starred sets
    standard sets, etc. There is no assignment and type checking, nor
    modification monitoring. You should use this class when messages are not
    expected to be modified, for the performance benefit. This is typical for
    PO-checking applications.

    The top modification counter still exists, but only as an ordinary
    inactive instance variable, which the client code can manually increase
    to signal that the message has changed. This may be necessary for some
    other client code, which relies on top counter, to function properly.

    @see: L{Message_base}
    """

    def __init__ (self, init={}):
        """
        Initializes the message elements by the values in the dictionary.

        The dictionary keys are like the names of instance variables in the
        interface, and not all must be supplied. Those left out will be
        initialized to appropriate null values.

        @param init: dictionary of initial values
        @type init: dict
        """

        Message_base.__init__(self, object)

        self.manual_comment = init.get("manual_comment", [])
        self.auto_comment = init.get("auto_comment", [])
        self.source = init.get("source", [])
        self.flag = init.get("flag", [])

        self.obsolete = init.get("obsolete", False)

        self.msgctxt_previous = init.get("msgctxt_previous", u"")
        self.msgid_previous = init.get("msgid_previous", u"")
        self.msgid_plural_previous = init.get("msgid_plural_previous", u"")

        self.msgctxt = init.get("msgctxt", u"")
        self.msgid = init.get("msgid", u"")
        self.msgid_plural = init.get("msgid_plural", u"")
        self.msgstr = init.get("msgstr", [u""])

        self.__dict__["fuzzy"] = (u"fuzzy" in self.flag and not self.obsolete)

        self.refline = init.get("refline", -1)
        self.refentry = init.get("refentry", -1)

        # Line caches.
        self._lines_all = init.get("lines_all", [])
        self._lines_manual_comment = init.get("lines_manual_comment", [])
        self._lines_auto_comment = init.get("lines_auto_comment", [])
        self._lines_source = init.get("lines_source", [])
        self._lines_flag = init.get("lines_flag", [])
        self._lines_msgctxt_previous = init.get("lines_msgctxt_previous", [])
        self._lines_msgid_previous = init.get("lines_msgid_previous", [])
        self._lines_msgid_plural_previous = \
            init.get("lines_msgid_plural_previous", [])
        self._lines_msgctxt = init.get("lines_msgctxt", [])
        self._lines_msgid = init.get("lines_msgid", [])
        self._lines_msgid_plural = init.get("lines_msgid_plural", [])
        self._lines_msgstr = init.get("lines_msgstr", [])

        self.modcount = 0


    def _renew_lines (self, wrapf=wrap_field, force=False):

        mod = {}
        cond = self.modcount
        mod["manual_comment"] = cond
        mod["auto_comment"] = cond
        mod["source"] = cond
        mod["flag"] = cond
        for att in _Message_single_strings:
            mod[att] = cond
        mod["msgstr"] = cond

        return self._renew_lines_bymod(mod, wrapf, force)

