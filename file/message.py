# -*- coding: UTF-8 -*-

from pology.misc.escape import escape
from pology.misc.wrap import wrap_field, wrap_comment, wrap_comment_unwrap
from pology.misc.monitored import Monitored, Monlist, Monset, Monpair

_Message_spec = {
    "manual_comment" : {"type" : Monlist,
                        "spec" : {"*" : {"type" : unicode}}},
    "auto_comment" : {"type" : Monlist,
                      "spec" : {"*" : {"type" : unicode}}},
    "source" : {"type" : Monset,
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
}
_Message_single_strings = (
    "msgctxt_previous", "msgid_previous", "msgid_plural_previous",
    "msgctxt", "msgid", "msgid_plural",
)

class Message_base (object):

    def __init__ (self, getsetattr):
        self.__dict__["^getsetattr"] = getsetattr

    def __getattr__ (self, att):
        if 0: pass

        elif att == "translated":
            if self.fuzzy or self.obsolete:
                return False
            if not self.msgstr:
                return False
            for val in self.msgstr:
                if not val:
                    return False
            return True

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
                srcrefs.append(src[0] + ":" + str(src[1]))
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

        if force or self.modcount:
            self._renew_lines(wrapf, force)

        return self._lines_all

    def to_string (self, wrapf=wrap_field, force=False):
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
        """Merge in the contents of the other message with the same key.

        Return True if any changes were made by merging, False otherwise
        (though this is reliable only for a monitored message).

        Merging is basically riddled with heuristics, depending on the
        state of self and the other message (translated/fuzzy/...) If
        tight control is desired, the merging should be done manually.
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
            if (self.translated and other.translated) \
            or (self.fuzzy and other.fuzzy):
                if not self.manual_comment:
                    self._overwrite_list(other, "manual_comment")

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


class Message (Message_base, Monitored): # order important for get/setattr
    """Single message in the catalog."""

    def __init__ (self, init={}):
        """Create new message.

        Dictionary init contains same-name keys as message fields to
        initialize to; for any missing key, an appropriate default is used.
        """

        Message_base.__init__(self, Monitored)

        self._manual_comment = Monlist(init.get("manual_comment", []))
        self._auto_comment = Monlist(init.get("auto_comment", []))
        self._source = Monset([Monpair(*x) for x in init.get("source", [])])
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
    """Single message in the catalog, non-monitored version."""

    def __init__ (self, init={}):
        """Create new message, filling in any fields given by the dictionary.

        Dictionary init contains same-name entries to initialize to;
        for any missing key, an appropriate empty default is used.
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

