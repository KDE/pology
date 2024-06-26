# -*- coding: UTF-8 -*-

"""
Message entries in PO catalogs.

Classes from this module define the entries proper,
while the header entry is handled by L{pology.header}.

@see: L{pology.header}

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

from pology.colors import ColorString, cjoin
from pology.escape import escape_c
from pology.wrap import wrap_field, wrap_comment, wrap_comment_unwrap
from pology.monitored import Monitored, Monlist, Monset, Monpair


_Message_spec = {
    "manual_comment" : {"type" : Monlist,
                        "spec" : {"*" : {"type" : str}}},
    "auto_comment" : {"type" : Monlist,
                      "spec" : {"*" : {"type" : str}}},
    "source" : {"type" : Monlist,
                "spec" : {"*" : {"type" : Monpair,
                                 "spec" : {"first" : {"type" : str},
                                           "second" : {"type" : int}}}}},
    "flag" : {"type" : Monset,
              "spec" : {"*" : {"type" : str}}},

    "obsolete" : {"type" : bool},

    "msgctxt_previous" : {"type" : (str, type(None))},
    "msgid_previous" : {"type" : (str, type(None))},
    "msgid_plural_previous" : {"type" : (str, type(None))},

    "msgctxt" : {"type" : (str, type(None))},
    "msgid" : {"type" : str},
    "msgid_plural" : {"type" : (str, type(None))},
    "msgstr" : {"type" : Monlist,
                "spec" : {"*" : {"type" : str}}},

    "key" : {"type" : str, "derived" : True},
    "fmt" : {"type" : str, "derived" : True},
    "inv" : {"type" : str, "derived" : True},
    "trn" : {"type" : str, "derived" : True},
    "fuzzy" : {"type" : bool},
    "untranslated" : {"type" : bool, "derived" : True},
    "translated" : {"type" : bool, "derived" : True},
    "active" : {"type" : bool, "derived" : True},
    "format" : {"type" : str, "derived" : True},

    "refline" : {"type" : int},
    "refentry" : {"type" : int},
}

# Exclusive groupings.
_Message_single_fields = (
    "msgctxt_previous", "msgid_previous", "msgid_plural_previous",
    "msgctxt", "msgid", "msgid_plural",
)
_Message_list_fields = (
    "manual_comment", "auto_comment",
    "msgstr",
)
_Message_list2_fields = (
    "source",
)
_Message_set_fields = (
    "flag",
)
_Message_state_fields = (
    "fuzzy", "obsolete",
)

# Convenience groupings.
_Message_all_fields = (()
    + _Message_single_fields
    + _Message_list_fields
    + _Message_list2_fields
    + _Message_set_fields
    + _Message_state_fields
)
_Message_sequence_fields = (()
    + _Message_list_fields
    + _Message_list2_fields
    + _Message_set_fields
)
_Message_key_fields = (
    "msgctxt", "msgid",
)
_Message_mandatory_fields = (
    "msgid", "msgstr",
)
_Message_currprev_fields = (
    ("msgctxt", "msgctxt_previous"),
    ("msgid", "msgid_previous"),
    ("msgid_plural", "msgid_plural_previous"),
)
_Message_fmt_fields = (
    "msgctxt",
    "msgid",
    "msgid_plural",
    "msgstr",
    "obsolete",
    "fuzzy",
)
_Message_inv_fields = (
    "obsolete",
    "fuzzy",
    "manual_comment",
    "msgctxt_previous",
    "msgid_previous",
    "msgid_plural_previous",
    "msgctxt",
    "msgid",
    "msgid_plural",
    "msgstr",
)


def _escape (text):

    text = escape_c(text)
    if isinstance(text, ColorString):
        text = text.replace("&quot;", "\\&quot;")
    return text


class Message_base (object):
    """
    Abstract base class for entries in PO catalogs.

    Elements of the message are accessed through instance attributes.
    Some of them are read-only, typically those that are derived from the
    normal read-write attributes and cannot be set independently.

    The precise type of each attribute depends on the subclass through which
    it is accessed, but has a general behavior of one of the standard types.
    E.g. when the behavior is that of a list, the type is stated as C{list*}.
    All strings are assumed unicode, except where noted otherwise.

    Regardless of the exact composition of the message, each message object
    will have all the instance attributes listed. In case the message actually
    does not have an element corresponding to an instance attribute,
    that attribute will have an appropriate null value.

    Only the read-only attributes are provided by this base class,
    while the read-write attributes are to be provided by its subclasses.
    All are listed here, however, as the interface that all subclasses
    should implement.

    @ivar manual_comment: manual (translator) comments (C{# ...})
    @type manual_comment: list* of strings

    @ivar auto_comment: automatic (extracted) comments (C{#. ...})
    @type auto_comment: list* of strings

    @ivar source: source references, as filepath:lineno pairs (C{#: ...})
    @type source: list* of pairs*

    @ivar flag: message flags (C{#, ...})
    @type flag: set* of strings

    @ivar obsolete: whether entry is obsolete (C{#~ ...})
    @type obsolete: bool

    @ivar msgctxt_previous: previous context field (C{#| msgctxt "..."})
    @type msgctxt_previous: string or None

    @ivar msgid_previous: previous message field (C{#| msgid "..."})
    @type msgid_previous: string or None

    @ivar msgid_plural_previous:
        previous plural field (C{#| msgid_plural "..."})
    @type msgid_plural_previous: string or None

    @ivar msgctxt: context field (C{msgctxt "..."})
    @type msgctxt: string or None

    @ivar msgid: message field (C{msgid "..."})
    @type msgid: string

    @ivar msgid_plural: plural field (C{msgid_plural "..."})
    @type msgid_plural: string or None

    @ivar msgstr: translation fields (C{msgstr "..."}, C{msgstr[n] "..."})
    @type msgstr: list* of strings

    @ivar key: (read-only) key composition

        Message key is formed by the parts of the message which define
        unique entry in a catalog.

        The value is an undefined serialization of C{msgctxt} and C{msgid}.
    @type key: string

    @ivar fmt: (read-only) format composition

        Format composition consists of all message parts which determine
        contents of compiled message in the MO file, including whether
        it is compiled at all.

        The value is an undefined serialization of: C{msgctxt}, C{msgid},
        C{msgid_plural}, C{msgstr}, C{fuzzy}, C{obsolete}.
    @type fmt: string

    @ivar inv: (read-only) extraction-invariant composition

        Extraction-invariant parts of the message are those that are not
        dependent on the placement and comments to the message in the code.
        In effect, these are the parts which are not eliminated when
        the message is obsoleted after merging.

        The value is an undefined serialization of: C{msgctxt}, C{msgid},
        C{msgid_plural}, C{msgstr}, C{fuzzy}, C{obsolete}, C{manual_comment},
        C{msgctxt_previous}, C{msgid_previous}, C{msgid_plural_previous}.
    @type inv: string

    @ivar trn: (read-only) translator-controlled composition

        Translator-controlled parts of the message are those that are
        normally modified by a translator when working on a PO file.

        The value is an undefined serialization of: C{msgstr}, C{fuzzy},
        C{manual_comment}.
    @type trn: string

    @ivar fuzzy:
        whether the message is fuzzy

        The state of fuzziness can be also checked and set by looking for
        and adding/removing the C{fuzzy} flag from the set of flags,
        but this is needed frequently enough to deserve a standalone attribute.
        Note: To "thoroughly" unfuzzy the message, see method L{unfuzzy}.
    @type fuzzy: bool

    @ivar untranslated: (read-only)
        whether the message is untranslated (False for fuzzy messages)
    @type untranslated: bool

    @ivar translated: (read-only)
        whether the message is translated (False for fuzzy messages)
    @type translated: bool

    @ivar active: (read-only)
        whether the translation of the message is used at destination
        (C{False} for untranslated, fuzzy and obsolete messages)
    @type active: bool

    @ivar format: (read-only)
        the format flag of the message (e.g. C{c-format}) or empty string
    @type format: string

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

    @ivar key_previous: (read-only) previous key composition

        Like L{key}, except this is for previous fields.
        If there are no previous fields, this is C{None}.

        The value is an undefined serialization of C{msgctxt_previous}
        and C{msgid_previous}.
    @type key: string or C{None}

    @see: L{Message}
    @see: L{MessageUnsafe}
    """

    def __init__ (self, getsetattr):
        """
        Internal constructor for subclasses' usage.

        @param getsetattr:
            the object with C{__getattr__} and C{__setattr__} methods,
            as handler for unhandled instance attributes
        """

        self.__dict__["^getsetattr"] = getsetattr
        self._colorize_prev = 0


    def __getattr__ (self, att):
        """
        Attribute getter.

        Processes read-only attributes, and sends others to the getter
        given by the constructor.

        @param att: name of the attribute to get
        @returns: attribute value
        """

        if 0: pass

        elif att == "translated":
            if self.fuzzy:
                return False
            # Consider message translated if at least one msgstr is translated:
            # that's how gettext tools do, but then they report an error for
            # missing argument in non-translated msgstrs.
            for val in self.msgstr:
                if val:
                    return True
            return False

        elif att == "untranslated":
            if self.fuzzy:
                return False
            for val in self.msgstr:
                if val:
                    return False
            return True

        elif att == "active":
            return self.translated and not self.obsolete

        elif att == "key":
            return self._compose(["msgctxt", "msgid"])

        elif att == "fmt":
            return self._compose(["msgctxt", "msgid",
                                  "msgid_plural", "msgstr",
                                  "fuzzy", "obsolete"])

        elif att == "inv":
            return self._compose(["msgctxt", "msgid",
                                  "msgid_plural", "msgstr",
                                  "fuzzy", "obsolete",
                                  "manual_comment", "msgctxt_previous",
                                  "msgid_previous", "msgid_plural_previous"])

        elif att == "trn":
            return self._compose(["msgstr", "fuzzy", "manual_comment"])

        elif att == "format":
            format_flag = ""
            for flag in self.flag:
                if flag.find("-format") >= 0:
                    format_flag = flag
                    break
            return format_flag

        elif att == "fuzzy":
            return "fuzzy" in self.flag

        elif att == "key_previous":
            if self.msgid_previous is not None:
                return self._compose(["msgctxt_previous", "msgid_previous"])
            else:
                return None

        else:
            return self.__dict__["^getsetattr"].__getattr__(self, att)


    def _compose (self, fields):

        fmtvals = []
        for field in fields:
            val = self.get(field)
            if field in _Message_state_fields:
                fval = val and "1" or "0"
            elif field in _Message_list_fields:
                fval = "\x02".join(["%s" % x for x in val])
            elif field in _Message_list2_fields:
                fval = "\x02".join(["%s:%s" % tuple(x) for x in val])
            elif field in _Message_set_fields:
                vlst = ["%s" % x for x in val]
                vlst.sort()
                fval = "\x02".join(vlst)
            else:
                fval = val is None and "\x00" or "%s" % val
            fmtvals.append(fval)
        return "\x04".join(fmtvals)


    def get (self, att, default=None):
        """
        Get attribute value.

        Allows accessing the message like a dictionary.

        @param att: name of the attribute to get
        @type att: string
        @param default: value to return if attribute does not exist

        @returns: value of the attribute or the default value
        """

        if hasattr(self, att):
            return getattr(self, att)
        else:
            return default


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
            if val == True:
                self.flag.add("fuzzy")
            elif "fuzzy" in self.flag:
                self.flag.remove("fuzzy")

        else:
            self.__dict__["^getsetattr"].__setattr__(self, att, val)


    def __eq__ (self, omsg):
        """
        Reports whether messages are equal in all apparent parts.

        "Apparent" parts include all those which are visible in the PO file.
        I.e. the check will ignore internal states, like line caches, etc.

        @returns: C{True} if messages are equal in apparent parts
        @rtype: bool
        """

        # Make messages the same type.
        # NOTE: All this instead of just omsg = type(self)(omsg)
        # for the sake of performance.
        if not isinstance(omsg, Message_base):
            omsg = MessageUnsafe(omsg)
        msg = self
        if isinstance(self, Message) and isinstance(omsg, MessageUnsafe):
            msg = MessageUnsafe(msg)
        elif isinstance(self, MessageUnsafe) and isinstance(omsg, Message):
            omsg = MessageUnsafe(omsg)

        for field in _Message_all_fields:
            if msg.get(field) != omsg.get(field):
                return False

        return True


    def __ne__ (self, omsg):
        """
        Reports whether messages are not equal in some apparent parts.

        Equivalent to C{not (self == omsg)}.

        @returns: C{False} if messages are equal in all apparent parts
        @rtype: bool
        """

        return not self.__eq__(omsg)

    def __hash__ (self):
        return id(self)//16

    def _renew_lines_bymod (self, mod, wrapf=wrap_field, force=False,
                            colorize=0):

        prefix = {}
        if self.obsolete:
            prefix["curr"] = "#~ "
            prefix["prev"] = "#~| "
        else:
            prefix["curr"] = ""
            prefix["prev"] = "#| "

        if force or mod["manual_comment"] or not self._lines_manual_comment:
            self._lines_manual_comment = []
            for manc in self.manual_comment:
                ls = wrap_comment_unwrap("", manc)
                if colorize >= 2:
                    ls = [ColorString("<grey>%s</grey>") % x for x in ls]
                self._lines_manual_comment.extend(ls)

        if force or mod["auto_comment"] or not self._lines_auto_comment:
            self._lines_auto_comment = []
            for autoc in self.auto_comment:
                ls = wrap_comment_unwrap(".", autoc)
                if colorize >= 2:
                    ls = [ColorString("<blue>%s</blue>") % x for x in ls]
                self._lines_auto_comment.extend(ls)

        if force or mod["source"] or not self._lines_source:
            self._lines_source = []
            srcrefs = []
            for src in self.source:
                if src[1] > 0:
                    srcrefs.append(src[0] + ":" + str(src[1]))
                else:
                    srcrefs.append(src[0])
            if srcrefs:
                ls = wrap_comment(":", cjoin(srcrefs, " "))
                if colorize >= 2:
                    ls = [ColorString("<blue>%s</blue>") % x for x in ls]
                self._lines_source = ls

        if force or mod["flag"] or not self._lines_flag:
            self._lines_flag = []
            # Rearange so that fuzzy is first, if present.
            flst = []
            for fl in self.flag:
                if fl == "fuzzy":
                    if colorize >= 1:
                        fl = ColorString("<underline>%s</underline>") % fl
                    flst.insert(0, fl)
                else:
                    flst.append(fl)
            if flst:
                ls = wrap_comment(",", cjoin(flst, ", "))
                if colorize >= 2:
                    ls = [ColorString("<blue>%s</blue>") % x for x in ls]
                self._lines_flag = ls

        for att in _Message_single_fields:
            att_lins = "_lines_" + att
            if force or mod[att] or not self.__dict__[att_lins]:
                # modcount of this string > 0 or lines not cached or forced
                self.__dict__[att_lins] = []
                msgsth = getattr(self, att)
                if msgsth is not None or att in _Message_mandatory_fields:
                    if msgsth is None:
                        msgsth = ""
                    if att.endswith("_previous"):
                        fname = att[:-len("_previous")]
                        pstat = "prev"
                    else:
                        fname = att
                        pstat = "curr"
                        if colorize >= 1:
                            fname = ColorString("<bold>%s</bold>") % fname
                    self.__dict__[att_lins] = wrapf(fname, _escape(msgsth),
                                                    prefix[pstat])

        # msgstr must be renewed if the plurality of the message changed.
        new_plurality = (    getattr(self, "_lines_msgstr", [])
                         and (   (    self.msgid_plural is None
                                  and "msgstr[" in self._lines_msgstr[0])
                              or (    self.msgid_plural is not None
                                  and "msgstr[" not in self._lines_msgstr[0])))

        if force or mod["msgstr"] or not self._lines_msgstr or new_plurality:
            self._lines_msgstr = []
            msgstr = self.msgstr or [""]
            if self.msgid_plural is None:
                fname = "msgstr"
                if colorize >= 1:
                    fname = ColorString("<bold>%s</bold>") % fname
                self._lines_msgstr.extend(wrapf(fname,
                                          _escape(msgstr[0]),
                                          prefix["curr"]))
            else:
                for i in range(len(msgstr)):
                    fname = "msgstr[%d]" % i
                    if colorize >= 1:
                        fname = ColorString("<bold>%s</bold>") % fname
                    self._lines_msgstr.extend(wrapf(fname,
                                                    _escape(msgstr[i]),
                                                    prefix["curr"]))

        # Marshal the lines into proper order.
        self._lines_all = []
        lins = self._lines_all

        lins.extend(self._lines_manual_comment)
        lins.extend(self._lines_auto_comment)
        if not self.obsolete: # no source for an obsolete message
            lins.extend(self._lines_source)
        lins.extend(self._lines_flag)

        # Actually, it might make sense regardless...
        ## Old originals makes sense only for a message with a fuzzy flag.
        #if self.fuzzy:
        lins.extend(self._lines_msgctxt_previous)
        lins.extend(self._lines_msgid_previous)
        lins.extend(self._lines_msgid_plural_previous)

        lins.extend(self._lines_msgctxt)
        lins.extend(self._lines_msgid)
        lins.extend(self._lines_msgid_plural)
        lins.extend(self._lines_msgstr)

        if self._lines_all[-1] != "\n":
            lins.extend("\n")


    def to_lines (self, wrapf=wrap_field, force=False, colorize=0):
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

        @param colorize: whether and how much to colorize the message.
            Typically useful when the message is output to terminal,
            HTML file, etc. as accompanying information to a user.
            If the value is 0, no colorization is applied;
            1 gives conservative colorization, 2 and more full colorization.
        @type colorize: int

        @returns: formatted lines
        @rtype: list of strings

        @see: L{pology.wrap}
        """

        # Renew lines if one of: forced, no lines formed yet, no modcounter,
        # different colorization.
        if colorize != self._colorize_prev:
            force = True
        if force or getattr(self, "modcount", True) or not self._lines_all:
            self._renew_lines(wrapf, force, colorize)
            self._colorize_prev = colorize

        return self._lines_all


    def to_string (self, wrapf=wrap_field, force=False, colorize=0):
        """
        The string-representation of the message.

        Passes the arguments to L{to_lines} and joins the resulting list.

        @see: L{to_lines}
        """

        return cjoin(self.to_lines(wrapf, force, colorize))


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


    def unfuzzy (self):
        """
        Thoroughly unfuzzy the message.

        Strictly speaking, a message is fuzzy if it has the C{fuzzy} flag set.
        Thus a message can be unfuzzied by removing this flag, either
        manually from the C{flag} set, or through attribute C{fuzzy}.
        But if there were previous fields (e.g. C{msgid_previous})
        added to the message when it was made fuzzy on merge, they will
        remain in the message after it has been unfuzzied in this way.
        This is normally not wanted, and in such cases this method may
        be used to I{thouroughly} unfuzzy the message: remove C{fuzzy} flag,
        set C{fuzzy} attribute to C{False}, and all C{*_previous}
        attributes to C{None}.

        If the message is not strictly fuzzy upon this call,
        it is undefined whether any present previous fields will be
        left untouched, or removed nontheless.

        @returns: True if the message was unfuzzied, false otherwise
        """

        if not self.fuzzy:
            return False

        self.fuzzy = False # also removes fuzzy flag
        self.msgctxt_previous = None
        self.msgid_previous = None
        self.msgid_plural_previous = None

        return True


    def clear (self, keepmanc=False, msgstrlen=None):
        """
        Revert message to pristine untranslated state.

        Reverting to untranslated state removes manual comments (by default),
        C{fuzzy} flag, and previous fields, and clears C{msgstr} fields.

        @param keepmanc: do not remove manual comments
        @type keepmanc: bool
        @param msgstrlen: the number of empty msgstr fields;
            if C{None}, the existing number of fields is preserved
        @type msgstrlen: int
        """

        if not keepmanc:
            self.manual_comment = type(self.manual_comment)()
        self.fuzzy = False # also removes fuzzy flag
        self.msgctxt_previous = None
        self.msgid_previous = None
        self.msgid_plural_previous = None
        if msgstrlen is None:
            msgstrlen = len(self.msgstr)
        self.msgstr = type(self.msgstr)([""] * msgstrlen)


    def state (self):
        """
        Coded description of the translation state of the message.

        Code string can be one of:
        "T" (translated), "F" (fuzzy), "U" (untranslated),
        "OT" (obsolete translated), "OF" (obsolete fuzzy),
        "OU" (obsolete untranslated).

        @returns: coded translation state
        @rtype: string
        """

        if not self.obsolete:
            if self.fuzzy:
                return "F"
            elif self.translated:
                return "T"
            else:
                return "U"
        else:
            if self.fuzzy:
                return "OF"
            elif self.translated:
                return "OT"
            else:
                return "OU"


    def set (self, omsg):
        """
        Copy all parts from the other message.

        All mutable parts are deeply copied.

        @param omsg: the message from which to copy the parts
        @type omsg: instance of L{Message_base}

        @returns: self
        """

        return self._set_parts(omsg, _Message_all_fields)


    def set_key (self, omsg):
        """
        Copy all key parts from the other message.

        See L{key} attribute for the description and list of key parts.

        All mutable parts are deeply copied.

        @param omsg: the message from which to copy the parts
        @type omsg: instance of L{Message_base}

        @returns: self
        """

        return self._set_parts(omsg, _Message_key_fields)


    def set_fmt (self, omsg):
        """
        Copy all format parts from the other message.

        See L{fmt} attribute for the description and list of format parts.

        All mutable parts are deeply copied.

        @param omsg: the message from which to copy the parts
        @type omsg: instance of L{Message_base}

        @returns: self
        """

        return self._set_parts(omsg, _Message_fmt_fields)


    def set_inv (self, omsg):
        """
        Copy extraction-invariant parts from the other message.

        See L{inv} attribute for the description and list of
        extraction-invariant parts.

        All mutable parts are deeply copied.

        @param omsg: the message from which to copy the parts
        @type omsg: instance of L{Message_base}

        @returns: self
        """

        return self._set_parts(omsg, _Message_inv_fields)


    def _set_parts (self, omsg, parts):
        """
        Worker for set* methods.
        """

        for part in parts:
            oval = omsg.get(part)
            val = self.get(part)
            if oval is not None:
                if part in _Message_list2_fields:
                    oval = type(val)([type(x)(x) for x in oval])
                elif part in _Message_sequence_fields:
                    oval = type(val)(oval)
                elif val is not None:
                    oval = type(val)(oval)
            setattr(self, part, oval)

        return self


class Message (Message_base, Monitored): # order important for get/setattr
    """
    The default class for catalog entries.

    The interface is inherited from L{Message_base}, but when used through
    this class it behaves in a special way: the modifications are I{monitored},
    such that no new attributes can be created by assignment
    and all assignments are checked for value types.
    If you don't need to modify the messages after creation, consider using
    the faster L{MessageUnsafe} class.

    The loosely defined types in the base class (those with a star)
    are resolved into one of C{Mon*} types: L{Monlist}, L{Monset}, L{Monpair}.
    They implement some, but not all, of the functionality of their standard
    counterparts.

    @see: L{Message_base}
    @see: L{MessageUnsafe}
    @see: L{pology.monitored}
    """

    def __init__ (self, init={}):
        """
        Initializes the message elements by the values in the dictionary.

        The dictionary keys are like the names of attributes in the
        interface, and not all must be supplied. Those left out will be
        initialized to appropriate null values.

        The monitored sequences should be supplied as their ordinary
        counterparts (e.g. a C{list} in place of L{Monlist}),

        @param init: dictionary of initial values
        @type init: dict
        """

        # NOTE: Make sure all sequences are shallow copied.

        Message_base.__init__(self, Monitored)

        self._manual_comment = Monlist(init.get("manual_comment", [])[:])
        self._auto_comment = Monlist(init.get("auto_comment", [])[:])
        self._source = Monlist(list(map(Monpair, init.get("source", [])[:])))
        self._flag = Monset(init.get("flag", []))

        self._obsolete = init.get("obsolete", False)

        self._msgctxt_previous = init.get("msgctxt_previous", None)
        self._msgid_previous = init.get("msgid_previous", None)
        self._msgid_plural_previous = init.get("msgid_plural_previous", None)

        self._msgctxt = init.get("msgctxt", None)
        self._msgid = init.get("msgid", "")
        self._msgid_plural = init.get("msgid_plural", None)
        self._msgstr = Monlist(init.get("msgstr", [])[:])

        self._fuzzy = ("fuzzy" in self._flag and not self._obsolete)

        self._refline = init.get("refline", -1)
        self._refentry = init.get("refentry", -1)

        self.assert_spec_init(_Message_spec)

        # Line caches.
        self._lines_all = init.get("_lines_all", [])[:]
        self._lines_manual_comment = init.get("_lines_manual_comment", [])[:]
        self._lines_auto_comment = init.get("_lines_auto_comment", [])[:]
        self._lines_source = init.get("_lines_source", [])[:]
        self._lines_flag = init.get("_lines_flag", [])[:]
        self._lines_msgctxt_previous = init.get("_lines_msgctxt_previous", [])[:]
        self._lines_msgid_previous = init.get("_lines_msgid_previous", [])[:]
        self._lines_msgid_plural_previous = init.get("_lines_msgid_plural_previous", [])[:]
        self._lines_msgctxt = init.get("_lines_msgctxt", [])[:]
        self._lines_msgid = init.get("_lines_msgid", [])[:]
        self._lines_msgid_plural = init.get("_lines_msgid_plural", [])[:]
        self._lines_msgstr = init.get("_lines_msgstr", [])[:]

    def _renew_lines (self, wrapf=wrap_field, force=False, colorize=0):

        if not self.obsolete_modcount:
            mod = {}
            mod["manual_comment"] = (   self.manual_comment_modcount
                                     or self.manual_comment.modcount)
            mod["auto_comment"] = (   self.auto_comment_modcount
                                   or self.auto_comment.modcount)
            mod["source"] = self.source_modcount or self.source.modcount
            mod["flag"] = self.flag_modcount or self.flag.modcount
            for att in _Message_single_fields:
                mod[att] = getattr(self, att + "_modcount") > 0
            mod["msgstr"] = self.msgstr_modcount or self.msgstr.modcount
        else:
            # Must recompute all lines if the message has been modified
            # by changing the obsolete status.
            mod = None
            force = True

        return self._renew_lines_bymod(mod, wrapf, force, colorize)


class MessageUnsafe (Message_base):
    """
    The lightweight class for catalog entries, for read-only applications.

    Unlike the L{Message}, this class does nothing special with attributes.
    The interface attributes are implemented as in L{Message_base},
    where the starred lists are standard lists, starred sets
    standard sets, etc. There is no assignment and type checking, nor
    modification monitoring. You should use this class when messages are not
    expected to be modified, for the performance benefit.

    The top modification counter still exists, but only as an ordinary
    inactive attribute, which the client code can manually increase
    to signal that the message has changed. This may be necessary for some
    client code, which relies on top counter to function properly.

    @see: L{Message_base}
    """

    def __init__ (self, init={}):
        """
        Initializes the message elements by the values in the dictionary.

        The dictionary keys are like the names of attributes in the
        interface, and not all must be supplied. Those left out will be
        initialized to appropriate null values.

        @param init: dictionary of initial values
        @type init: dict
        """

        # NOTE: Make sure all sequences are shallow copied.

        Message_base.__init__(self, object)

        self.manual_comment = list(init.get("manual_comment", []))
        self.auto_comment = list(init.get("auto_comment", []))
        self.source = [tuple(x) for x in init.get("source", [])]
        self.flag = set(init.get("flag", []))

        self.obsolete = init.get("obsolete", False)

        self.msgctxt_previous = init.get("msgctxt_previous", None)
        self.msgid_previous = init.get("msgid_previous", None)
        self.msgid_plural_previous = init.get("msgid_plural_previous", None)

        self.msgctxt = init.get("msgctxt", None)
        self.msgid = init.get("msgid", "")
        self.msgid_plural = init.get("msgid_plural", None)
        self.msgstr = list(init.get("msgstr", [""]))

        self.refline = init.get("refline", -1)
        self.refentry = init.get("refentry", -1)

        # No need to look for line caches, as lines must always be reformatted.


    def _renew_lines (self, wrapf=wrap_field, force=False, colorize=0):

        # No monitoring, content must always be reformatted.
        return self._renew_lines_bymod(None, wrapf, True, colorize)

