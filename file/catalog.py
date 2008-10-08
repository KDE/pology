# -*- coding: UTF-8 -*-

"""
Collection of PO entries.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

from pology.misc.escape import escape, unescape
from pology.misc.wrap import wrap_field
from pology.misc.monitored import Monitored
from message import Message as MessageMonitored
from message import MessageUnsafe as MessageUnsafe
from header import Header

import os, codecs, re, types, signal, difflib, copy


def _parse_quoted (s):

    sp = s[s.index("\"") + 1:s.rindex("\"")]
    sp = unescape(sp);
    return sp


class _MessageDict:

    def __init__ (self):

        self.manual_comment = []
        self.auto_comment = []
        self.source = []
        self.flag = []
        self.obsolete = False
        self.msgctxt_previous = u""
        self.msgid_previous = u""
        self.msgid_plural_previous = u""
        self.msgctxt = u""
        self.msgid = u""
        self.msgid_plural = u""
        self.msgstr = []
        self.refline = -1
        self.refentry = -1

        self.lines_all = []
        self.lines_manual_comment = []
        self.lines_auto_comment = []
        self.lines_source = []
        self.lines_flag = []
        self.lines_msgctxt_previous = []
        self.lines_msgid_previous = []
        self.lines_msgid_plural_previous = []
        self.lines_msgctxt = []
        self.lines_msgid = []
        self.lines_msgid_plural = []
        self.lines_msgstr = []


def _mine_po_encoding (filename):

    ifl = open(filename, "r")
    enc = "UTF-8"
    enc_rx = re.compile(r"Content-Type:.*charset=(.+?)\\n", re.I)
    for line in ifl.xreadlines():
        if line.strip().startswith("#:"):
            break
        m = enc_rx.search(line)
        if m:
            enc = m.group(1).strip()
            if not enc or enc == "CHARSET": # fall back to UTF-8
                enc = "UTF-8"
            break
    ifl.close()
    return enc


def _parse_po_file (filename, MessageType=MessageMonitored, headonly=False):

    fenc = _mine_po_encoding(filename)
    ifl = codecs.open(filename, "r", fenc)
    lines = re.split(r"\r\n|\r|\n", ifl.read())
    # ...no file.readlines(), it treats some other characters as line breaks.
    nlines = len(lines)
    ifl.close()

    ctx_modern, ctx_obsolete, \
    ctx_previous, ctx_current, \
    ctx_none, ctx_msgctxt, ctx_msgid, ctx_msgid_plural, ctx_msgstr = range(9)

    messages1 = list()
    lno = 0
    eno = 0

    class Namespace: pass
    loc = Namespace()
    loc.lno = 0
    loc.tail = None
    loc.msg = _MessageDict()
    loc.life_context = ctx_modern
    loc.field_context = ctx_none
    loc.age_context = ctx_current

    # The message has been completed by the previous line if the context just
    # switched away from ctx_msgstr;
    # call whenever context switch happens, *before* assigning new context.
    def try_finish ():
        if loc.field_context == ctx_msgstr:
            messages1.append(loc.msg)
            #print filename, lno - 1
            loc.msg = _MessageDict()
            loc.field_context = ctx_none
            # In header-only mode, the first message read is the header.
            # Compose the tail of this and rest of the lines, and
            # set lno to nlines for exit.
            if headonly:
                loc.tail = "".join(lines[loc.lno-1:])
                loc.lno = nlines

    while loc.lno < nlines: # sentry for last entry
        line_raw = lines[lno]
        loc.lno += 1
        lno = loc.lno # shortcut
        line = line_raw.strip()
        if not line:
            continue

        string_follows = True
        loc.age_context = ctx_current

        if line.startswith("#"):

            if 0: pass

            elif line.startswith("#~|"):
                line = line[3:].lstrip()
                loc.life_context = ctx_obsolete
                loc.age_context = ctx_previous

            elif line.startswith("#~"):
                line = line[2:].lstrip()
                loc.life_context = ctx_obsolete

            elif line.startswith("#|"):
                line = line[2:].lstrip()
                loc.life_context = ctx_modern
                loc.age_context = ctx_previous

            elif line.startswith("#:"):
                try_finish()
                string_follows = False
                for srcref in line[2:].split(" "):
                    srcref = srcref.strip()
                    if srcref:
                        lst = srcref.split(":", 1)
                        if len(lst) == 2:
                            file = lst[0]
                            try:
                                line = int(lst[1])
                            except:
                                file = srcref
                                line = -1
                            loc.msg.source.append((file, line))
                        else:
                            loc.msg.source.append((srcref, -1))

            elif line.startswith("#,"):
                try_finish()
                string_follows = False
                for flag in line[2:].split(","):
                    flag = flag.strip()
                    if flag:
                        loc.msg.flag.append(flag)

            elif line.startswith("#."):
                try_finish()
                string_follows = False
                loc.msg.auto_comment.append(line[2:].lstrip())

            elif line.startswith("#"):
                try_finish()
                string_follows = False
                loc.msg.manual_comment.append(line[2:].lstrip())

            else:
                # Cannot reach, all unknown comments treated as manual above.
                raise StandardError,   "unknown comment type at %s:%d" \
                                     % (filename, lno)

        if line and string_follows: # for starting fields
            if 0: pass

            elif line.startswith("msgctxt"):
                # TODO: Assert context.
                try_finish()
                loc.field_context = ctx_msgctxt
                line = line[7:].lstrip()

            elif line.startswith("msgid_plural"):
                # TODO: Assert context.
                # No need for try_finish(), msgid_plural cannot start message.
                loc.field_context = ctx_msgid_plural
                line = line[12:].lstrip()

            elif line.startswith("msgid"):
                # TODO: Assert context.
                try_finish()
                if loc.life_context == ctx_obsolete:
                    loc.msg.obsolete = True
                loc.field_context = ctx_msgid
                if loc.age_context == ctx_current:
                    loc.msg.refline = lno
                    loc.msg.refentry = eno
                    eno += 1
                line = line[5:].lstrip()

            elif line.startswith("msgstr"):
                # TODO: Assert context.
                loc.field_context = ctx_msgstr
                line = line[6:].lstrip()
                msgstr_i = 0
                if line.startswith("["):
                    line = line[1:].lstrip()
                    llen = len(line)
                    p = 0
                    while p < llen and line[p].isdigit():
                        p += 1
                    if p == 0:
                        raise StandardError,   "malformed msgstr id at %s:%d" \
                                             % (filename, lno)
                    msgstr_i = int(line[:p])
                    line = line[p:].lstrip()
                    if line.startswith("]"):
                        line = line[1:].lstrip()
                    else:
                        raise StandardError,   "malformed msgstr id at %s:%d" \
                                             % (filename, lno)
                # Add missing msgstr entries.
                for i in range(len(loc.msg.msgstr), msgstr_i + 1):
                    loc.msg.msgstr.append(u"")

            elif not line.startswith("\""):
                raise StandardError,   "unknown field name at %s:%d" \
                                     % (filename, lno)

        if line and string_follows: # for continuing fields
            if line.startswith("\""):
                s = _parse_quoted(line)
                if loc.age_context == ctx_previous:
                    if loc.field_context == ctx_msgctxt:
                        loc.msg.msgctxt_previous += s
                    elif loc.field_context == ctx_msgid:
                        loc.msg.msgid_previous += s
                    elif loc.field_context == ctx_msgid_plural:
                        loc.msg.msgid_plural_previous += s
                else:
                    if loc.field_context == ctx_msgctxt:
                        loc.msg.msgctxt += s
                    elif loc.field_context == ctx_msgid:
                        loc.msg.msgid += s
                    elif loc.field_context == ctx_msgid_plural:
                        loc.msg.msgid_plural += s
                    elif loc.field_context == ctx_msgstr:
                        loc.msg.msgstr[msgstr_i] += s
            else:
                raise StandardError,   "expected string continuation at %s:%d" \
                                     % (filename, lno)

        # Update line caches.
        loc.msg.lines_all.append(line_raw)
        if 0: pass
        elif line_raw.startswith("#:"):
            loc.msg.lines_source.append(line_raw)
        elif line_raw.startswith("#,"):
            loc.msg.lines_flag.append(line_raw)
        elif line_raw.startswith("#."):
            loc.msg.lines_auto_comment.append(line_raw)
        elif line_raw.startswith("#") and line_raw[1:2] not in ("~", "|"):
            loc.msg.lines_manual_comment.append(line_raw)
        elif loc.age_context == ctx_previous:
            if loc.field_context == ctx_msgctxt:
                loc.msg.lines_msgctxt_previous.append(line_raw)
            elif loc.field_context == ctx_msgid:
                loc.msg.lines_msgid_previous.append(line_raw)
            elif loc.field_context == ctx_msgid_plural:
                loc.msg.lines_msgid_plural_previous.append(line_raw)
            else:
                raise StandardError,   "internal problem (11) at %s:%d" \
                                     % (filename, lno)
        elif loc.age_context == ctx_current:
            if loc.field_context == ctx_msgctxt:
                loc.msg.lines_msgctxt.append(line_raw)
            elif loc.field_context == ctx_msgid:
                loc.msg.lines_msgid.append(line_raw)
            elif loc.field_context == ctx_msgid_plural:
                loc.msg.lines_msgid_plural.append(line_raw)
            elif loc.field_context == ctx_msgstr:
                loc.msg.lines_msgstr.append(line_raw)
            else:
                raise StandardError,   "internal problem (12) at %s:%d" \
                                     % (filename, lno)
        else:
            raise StandardError,   "internal problem (10) at %s:%d" \
                                 % (filename, lno)

    try_finish() # the last message

    # Repack raw dictionaries as message objects.
    messages2 = []
    for msg1 in messages1:
        messages2.append(MessageType(msg1.__dict__))

    return (messages2, fenc, loc.tail)


def _srcref_repack (srcrefs):
    srcdict = {}
    for file, line in srcrefs:
        if not file in srcdict:
            srcdict[file] = [line]
        else:
            srcdict[file].append(line)
    srcdict[file].sort()
    return srcdict


_Catalog_spec = {
    # Data.
    "header" : {"type" : Header},
    "filename" : {"type" : types.StringTypes},
    "name" : {"type" : types.StringTypes, "derived" : True},
    "*" : {}, # messages sequence: the type is assigned at construction
}


class Catalog (Monitored):
    """
    Class for access and operations on PO catalogs.

    Catalog behaves as an ordered sequence of messages. The typical way of
    iterating over the messages from a PO file would be::

        cat = Catalog("relative/path/foo.po")
        for msg in cat:
            ...
            (do something with msg)
            ...
        cat.sync()

    where L{sync()<sync>} method is used to write any modifications back to
    the PO file on disk.

    The header entry of the catalog is not part of the message sequence,
    but is provided by the L{header} instance variable, an object of
    type different from an ordinary message entry.

    The catalog is a I{monitored} class. The instance variables are limited
    to a prescribed set and type-checked on assignment, have shadowing
    I{modification counters}, and any modifications are reflected on the top
    modification counter for the catalog as whole. For example:

        >>> cat = Catalog("relative/path/foo.po")
        >>> cat.filename  # file name of the catalog
        'relative/path/foo.po'
        >>> cat[0].msgid  # first message in the catalog
        u'Welcome to Foobar'
        >>> cat.modcount  # the top modcounter
        0
        >>> cat.filename_modcount  # shadowing counter to instance variable
        0
        >>> cat.filename = "relative/path/bar.po"  # change the file name
        >>> cat.modcount, cat.filename_modcount  # both counters increase
        (1, 1)
        >>> cat.remove(0)  # remove the first message from the catalog
        >>> cat.modcount  # the top counter increases again
        2

    Catalog message entries themeselves may also be monitored (default),
    but need not, depending on the mode of creation. If the entries are
    monitored, then any change to an entry also increases catalog's top
    modcounter.

    @ivar header: the header entry
    @type header: L{Header}

    @ivar filename: the file name which the catalog was created with
    @type filename: string

    @ivar name: (read-only)
        the name of the catalog

        Determined as base of the filename, without extension.
    @type name: string

    @see: L{Monitored}
    @see: L{Message}, L{MessageUnsafe}
    @see: L{Header}
    """

    def __init__ (self, filename,
                  create=False, wrapf=wrap_field, monitored=True,
                  headonly=False):
        """
        Build a message catalog by reading from a PO file or creating anew.

        The message entries in the catalog may be monitored themselves or not.
        That is, when monitoring is requested, entries are represented by
        the L{Message} class, otherwise with L{MessageUnsafe}.

        Monitored messages are usually appropriate when the application is
        expected to modify them. Non-monitored messages should provide better
        performance, so use them whenever the catalog is opened for read-only
        purposes (such as checks).

        Catalog can also be opened in header-only mode, for better
        performance when only the header data is needed. This mode provides
        L{header} instance variable as usual, but the rest of entries are
        unavailable. If any of the operations dealing with message entries
        are invoked, an error is signaled.

        @param filename: name of the PO catalog on disk, or new catalog
        @type filename: string

        @param create:
            whether a blank catalog can be created when the PO file does
            not already exist, or signal an error
        @type create: bool

        @param wrapf:
            the function used for wrapping message fields in output.
            See C{to_lines()} method of L{Message_base} for details.
        @type wrapf: string, string, string -> list of strings

        @param monitored: whether the message entries are monitored
        @type monitored: bool

        @param headonly: whether to open in header-only mode
        @type headonly: bool

        @see: L{pology.misc.wrap}
        """
        self._wrapf = wrapf

        # Select type of message object to use.
        if monitored:
            message_type = MessageMonitored
        else:
            message_type = MessageUnsafe

        # Read messages or create empty catalog:
        if os.path.exists(filename):
            m, e, t = _parse_po_file(filename, message_type, headonly)
            self._encoding = e
            self._created_from_scratch = False
            if not m[0].msgctxt and not m[0].msgid:
                # Proper PO, containing the header.
                self._header = Header(m[0])
                self._header._committed = True # status for sync
                self.__dict__["*"] = m[1:]
            else:
                # Improper PO, missing the header.
                self._header = Header()
                self._header._committed = False # status for sync
                self.__dict__["*"] = m
            self._tail = t
        elif create:
            self._encoding = "UTF-8"
            self._created_from_scratch = True
            self._header = Header()
            self._header._committed = False # status for sync
            self.__dict__["*"] = []
            self._tail = None
        else:
            raise StandardError, "file '%s' does not exist" % (filename,)

        self._filename = filename

        self._messages = self.__dict__["*"] # nicer name for the sequence

        # Fill in the message key-position links.
        # Set committed and remove-on-sync status.
        self._msgpos = {}
        for i in range(len(self._messages)):
            self._msgpos[self._messages[i].key] = i
            self._messages[i]._committed = True
            self._messages[i]._remove_on_sync = False

        # Find position after all non-obsolete messages.
        op = len(self._messages)
        while op > 0 and self._messages[op - 1].obsolete:
            op -= 1
        self._obspos = op

        # Initialize monitoring.
        final_spec = copy.deepcopy(_Catalog_spec)
        final_spec["*"]["type"] = message_type
        self.assert_spec_init(final_spec)

        # Cached plural definition from the header.
        self._plustr = ""

        # Cached language of the translation.
        # None means the language has not been determined.
        self._lang = None

        # Cached accelerator markers.
        # None means the accelerator markers have not been determined,
        # empty means there are none.
        self._accels = None

        # Cached markup types.
        # None means the markup types have not been determined,
        # empty means there are none.
        self._mtypes = None


    def _assert_headonly (self):

        if self._tail:
            raise StandardError, \
                  "trying to access messages in header-only mode"


    def __getattr__ (self, att):
        """
        Attribute getter.

        Processes read-only variables, and sends others to the base class.

        @param att: name of the attribute to get
        @returns: attribute value
        """
        if 0: pass

        elif att == "name":
            basename = os.path.basename(self._filename)
            p = basename.rfind(".")
            if p >= 0:
                return basename[:p]
            else:
                return basename

        else:
            return Monitored.__getattr__(self, att)


    def __len__ (self):
        """
        The number of messages in the catalog.

        The number includes obsolete entries, and excludes header entry.

        @returns: the number of messages
        @rtype: int
        """

        self._assert_headonly()
        return len(self._messages)


    def __getitem__ (self, ident):
        """
        Get message by position or another message.

        If the position is out of range, or the lookup message does not have
        a counterpart in this catalog with the same key, an error is signaled.

        Runtime complexity O(1), regardless of the C{ident} type.

        @param ident: position index or another message
        @type ident: int or subclass of L{Message_base}

        @returns: reference to the message in catalog
        @rtype: subclass of L{Message_base}
        """

        self._assert_headonly()
        self.assert_spec_getitem()
        if not isinstance(ident, int):
            ident = self._msgpos[ident.key]
        return self._messages[ident]


    def __contains__ (self, msg):
        """
        Whether the message with the same key exists in the catalog.

        Runtime complexity O(1).

        @param msg: message to look for
        @type msg: subclass of L{Message_base}

        @returns: C{True} if the message exists
        @rtype: bool
        """

        self._assert_headonly()
        return msg.key in self._msgpos


    def find (self, msg):
        """
        Position of the message in the catalog.

        Runtime complexity O(1).

        @param msg: message to look for
        @type msg: subclass of L{Message_base}

        @returns: position index if the message exists, -1 otherwise
        @rtype: int
        """

        self._assert_headonly()
        if msg.key in self._msgpos:
            return self._msgpos[msg.key]
        else:
            return -1


    def add (self, msg, pos=None):
        """
        Add a message to the catalog.

        If the message with the same key already exists, it will be merged
        (see C{merge()} method of L{Message_base}).

        If the message does not exist in the catalog, when the position is
        C{None}, the insertion will be attempted such as that the messages be
        near according to the source references; if the position is not
        C{None}, the message is inserted at the given position, unless it is
        obsolete.

        Negative positions can be given, and count backward from the first
        non-obsolete message (i.e. -1 means insertion after all non-obsolete
        messages).

        Runtime complexity O(n), even if the position is explicitly stated;
        O(1) only when the position is given as -1.

        @param msg: message to insert or merge
        @type msg: subclass of L{Message_base}

        @param pos: position index to insert at
        @type pos: int or C{None}

        @returns: the position where merged or inserted
        @rtype: int
        """

        self._assert_headonly()
        self.assert_spec_setitem(msg)

        if not msg.msgid:
            raise StandardError, \
                  "trying to insert message with empty msgid into the catalog"

        if not msg.key in self._msgpos:
            # The message is new, insert.
            nmsgs = len(self._messages)
            if msg.obsolete:
                # Insert obsolete message to the very end.
                ip = len(self._messages)

            else:
                if pos is None:
                    # Find best insertion position.
                    ip, none = self._pick_insertion_point(msg, self._obspos)
                else:
                    if pos >= 0:
                        # Take given position as exact insertion point.
                        ip = pos
                    else:
                        # Count backwards from the first obsolete message.
                        ip = self._obspos + pos + 1

            # Update key-position links for the index to be added.
            for i in range(ip, nmsgs):
                ckey = self._messages[i].key
                self._msgpos[ckey] = i + 1

            # Update position after all non-obsolete messages.
            if not msg.obsolete:
                self._obspos += 1

            # Store the message.
            self._messages.insert(ip, msg)
            self._messages[ip]._remove_on_sync = False # no pending removal
            self._messages[ip]._committed = False # write it on sync
            self._msgpos[msg.key] = ip # store new key-position link
            self.__dict__["#"]["*"] += 1 # indicate sequence change

            return ip

        else:
            # The message exists, merge.
            ip = self._msgpos[msg.key]
            self._messages[ip].merge(msg)
            return ip


    def remove (self, ident):
        """
        Remove a message from the catalog, by position or another message.

        If the position is out of range, or the lookup message does not have
        a counterpart in this catalog with the same key, an error is signaled.

        Runtime complexity O(n), regardless of C{ident} type.
        Use L{remove_on_sync()<remove_on_sync>} method for O(1) complexity,
        when the logic allows the removal to be delayed to syncing time.

        @param ident: position index or another message
        @type ident: int or subclass of L{Message_base}

        @returns: C{None}
        """

        self._assert_headonly()

        # Determine position and key by given ident.
        if isinstance(ident, int):
            ip = ident
            key = self._messages[ip].key
        else:
            key = ident.key
            ip = self._msgpos[key]

        # Update key-position links for the removed index.
        nmsgs = len(self._messages)
        for i in range(ip + 1, nmsgs):
            ckey = self._messages[i].key
            self._msgpos[ckey] = i - 1

        # Update position after all non-obsolete messages.
        if not self._messages[ip].obsolete:
            self._obspos -= 1

        # Remove from messages and key-position links.
        self._messages.pop(ip)
        self._msgpos.pop(key)
        self.__dict__["#"]["*"] += 1 # indicate sequence change


    def remove_on_sync (self, ident):
        """
        Remove a message from the catalog, by position or another message,
        on the next sync.

        If the position is out of range, or the lookup message does not have
        a counterpart in this catalog with the same key, an error is signaled.

        Suited for for-in iterations over a catalog with a sync afterwards,
        so that the indices are not confused by removal, and good performance.

        Runtime complexity O(1).

        @param ident: position index or another message
        @type ident: int or subclass of L{Message_base}

        @returns: C{None}
        """

        self._assert_headonly()

        # Determine position and key by given ident.
        if isinstance(ident, int):
            ip = ident
        else:
            ip = self._msgpos[ident.key]

        # Indicate removal on sync for this message.
        self._messages[ip]._remove_on_sync = True
        self.__dict__["#"]["*"] += 1 # indicate sequence change (pending)


    def sync (self, force=False):
        """
        Write catalog file to disk if any message has been modified.

        All activities scheduled for sync-time are performed, such as
        delayed message removal.

        Unmodified messages are not reformatted, unless forced.

        @param force: whether to reformat unmodified messages
        @type force: bool

        @returns: C{True} if the file was modified, C{False} otherwise
        @rtype: bool
        """

        # Cannot sync catalogs which have been given no path
        # (usually temporary catalogs).
        if not self._filename.strip():
            raise StandardError, "trying to sync nameless catalog"

        # If no modifications throughout and sync not forced, return.
        if not self.modcount and not force:
            return False

        # No need to indicate sequence changes here, as after sync the
        # catalog is set to unmodified throughout.

        # Temporarily insert header, for homogeneous iteration.
        self._messages.insert(0, self._header)
        self._messages[0]._remove_on_sync = False # never remove header
        nmsgs = len(self._messages)

        # Starting position for reinserting obsolete messages.
        obstop = self._obspos

        # NOTE: Key-position links may be invalidated from this point onwards,
        # by reorderings/removals. To make sure it is not used before the
        # rebuild at the end, delete now.
        del self._msgpos

        flines = []
        i = 0
        while i < nmsgs:
            msg = self._messages[i]
            if msg._remove_on_sync:
                # Removal on sync requested, just skip.
                i += 1
            elif msg.obsolete and i < obstop:
                # Obsolete message out of order, reinsert and repeat the index.
                msg = self._messages.pop(i)
                self._messages.insert(self._obspos - 1, msg)
                # Move top position of obsolete messages.
                obstop -= 1
            else:
                # Normal message, append formatted lines to rest.
                flines.extend(msg.to_lines(self._wrapf,
                                           force or not msg._committed))
                # Message should finish with an empty line,
                # unless it is the last one.
                if i < nmsgs - 1 and flines[-1] != "\n":
                    flines.append("\n")
                i += 1

        # Remove one trailing newline from the last message,
        # unless there is a tail.
        if not self._tail and flines[-1] == "\n":
            flines.pop(-1)
        # Create the parent directory if it does not exist.
        dirname = os.path.dirname(self._filename)
        if dirname and not os.path.isdir(dirname):
            os.makedirs(dirname)
        # Write to file atomically wrt. SIGINT.
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        ofl = codecs.open(self._filename, "w", self._encoding)
        ofl.writelines(flines)
        if self._tail: # write tail if any
            ofl.write(self._tail)
        ofl.close()
        signal.signal(signal.SIGINT, signal.SIG_DFL)

        # Indicate the catalog is no longer created from scratch, if it was.
        self._created_from_scratch = False

        # Remove temporarily inserted header, indicate it has been committed.
        self._messages.pop(0)
        self._header._committed = True

        # Execute pending removals on the sequence as well.
        # Indicate for each message that it has been committed.
        newlst = []
        for msg in self._messages:
            if not msg._remove_on_sync:
                msg._committed = True
                newlst.append(msg)
        self.__dict__["*"] = newlst
        self._messages = self.__dict__["*"]

        # Rebuild key-position links due to any reordered/removed messages.
        self._msgpos = {}
        for i in range(len(self._messages)):
            self._msgpos[self._messages[i].key] = i

        # Update position after all non-obsolete messages.
        self._obspos = obstop

        # Reset modification state throughout.
        self.modcount = 0

        return True


    def insertion_inquiry (self, msg, srefsyn={}):
        """
        Compute the tentative insertion of the message into the catalog.

        The tentative insertion is a tuple of position of a message when it
        would be inserted into the catalog, and the I{weight} indicating
        the quality of positioning. The weight is computed by analyzing
        the source references.

        Runtime complexity O(n).

        @param msg: message to compute the tentative insertion for
        @type msg: subclass of L{Message_base}
        @param srefsyn: synonymous names to some of the source files
        @type srefsyn: dictionary: file name, list of synonymous names

        @returns: the insertion position and its weight
        @rtype: int, float
        """

        self._assert_headonly()
        return self._pick_insertion_point(msg, self._obspos, srefsyn)


    def created (self):
        """
        Whether the catalog has been newly created (no existing PO file).

        A catalog is no longer considered newly created after the first sync.

        @returns: C{True} if newly created, C{False} otherwise
        @rtype: bool
        """

        return self._created_from_scratch


    def _pick_insertion_point (self, msg, last, srefsyn={}):

        # Return the best insertion position with associated weight.
        # Assume the existing messages in the catalog are properly ordered.

        # Insert at the last position if the candidate message has
        # no source references.
        if not msg.source:
            return last, 0.0

        ins_pos = -1
        # Try to find insertion position by comparing the source references
        # of the candidate the source references of the existing messages.
        # The order of matching must be very specific for logical insertion.
        # If the matching source files are found, insert according to
        # the line number.
        for src, lno in msg.source:
            src_pos = 0
            src_match = False
            curr_prim_esrc = ""
            for i in range(last):
                emsg = self._messages[i]
                if not emsg.source:
                    continue
                same_prim_esrc = False
                for esrc, elno in emsg.source:
                    if curr_prim_esrc in [esrc] + srefsyn.get(esrc, []):
                        same_prim_esrc = True
                        break
                if not same_prim_esrc:
                    curr_prim_esrc, elno = emsg.source[0]

                if src in [curr_prim_esrc] + srefsyn.get(curr_prim_esrc, []):
                    # The source file names match.
                    # Insert at this position if the candidate's line
                    # number preceeds that of the current message.
                    src_match = True
                    if lno < elno:
                        ins_pos = i
                        break
                elif src_match:
                    # The sources no longer match, but were matched
                    # before. This means the candidate line number is
                    # after all existing, so insert at this position.
                    ins_pos = i
                    break

                if ins_pos >= 0:
                    break

            if ins_pos >= 0:
                break

        if ins_pos >= 0:
            return ins_pos, 1.0
        else:
            return last, 0.0


    def nplurals (self):
        """
        Number of msgstr fields expected for plural messages.

        Determined by the Plural-Forms header field; if this field
        is absent from the header, defaults to 1.

        @returns: number of plurals
        @rtype: int
        """

        # Get nplurals string from the header.
        plforms = self._header.get_field_value("Plural-Forms")
        if not plforms: # no plural definition
            return 1
        nplustr = plforms.split(";")[0]

        # Get the number of forms from the string.
        m = re.search(r"\d+", nplustr)
        if not m: # malformed nplurals
            return 1

        return int(m.group(0))


    def plural_index (self, number):
        """
        Msgstr field index in plural messages for given number.

        Determined by the Plural-Forms header field; if this field
        is absent from the header, defaults to 0.

        @param number: the number to determine the plural form for
        @type number: int

        @returns: index of msgstr field
        @rtype: int
        """

        # Get plural definition from the header.
        plforms = self._header.get_field_value("Plural-Forms")
        if not plforms: # no plural definition, assume 0
            return 0
        plustr = plforms.split(";")[1]

        # Rebuild evaluation string only if changed to last invocation.
        if plustr != self._plustr:
            # Record raw plural definition for check on next call.
            self._plustr = plustr

            # Prepare Python-evaluable string out of the raw definition.
            plustr = plustr[plustr.find("=") + 1:] # remove plural= part
            p = -1
            evalstr = ""
            while 1:
                p = plustr.find("?")
                if p < 0:
                    evalstr += " " + plustr
                    break
                cond = plustr[:p]
                plustr = plustr[p + 1:]
                cond = cond.replace("&&", " and ")
                cond = cond.replace("||", " or ")
                evalstr += "(" + cond + ") and "
                p = plustr.find(":")
                body = plustr[:p]
                plustr = plustr[p + 1:]
                evalstr += "\"" + body + "\" or "
            if not evalstr.strip():
                evalstr = "0"

            # Record the current evaluable definition.
            self._plustr_eval = evalstr

        # Evaluate the definition.
        n = number # set eval context (plural definition uses n as variable)
        form = int(eval(self._plustr_eval))

        return form


    def plural_indices_single (self):
        """
        Indices of the msgstr fields which are used for single number only.

        @returns: msgstr indices used for single numbers
        @rtype: list of ints
        """

        # Get plural definition from the header.
        plforms = self._header.get_field_value("Plural-Forms")
        if not plforms: # no plural definition, assume 0
            return 0
        plustr = plforms.split(";")[1]

        lst = re.findall(r"\bn\s*==\s*\d+\s*\)?\s*\?\s*(\d+)", plustr)
        if not lst and re.search(r"\bn\s*!=\s*\d+\s*([^?]|$)", plustr):
            lst = ["0"]

        return [int(x) for x in lst]


    def select_by_key (self, msgctxt, msgid):
        """
        Select message from the catalog by the fields that define its key.

        If matched, the message is returned as a single-element list, or
        an empty list when there is no match. This is so that the result
        of this method is in line with other C{select_*} methods.

        Runtime complexity as that of L{find}.

        @param msgctxt: the text of C{msgctxt} field (can be empty)
        @type msgctxt: string

        @param msgid: the text of C{msgid} field
        @type msgid: string

        @returns: selected messages
        @rtype: list of subclass of L{Message_base}
        """

        m = MessageUnsafe({"msgctxt" : msgctxt, "msgid" : msgid})
        p = self.find(m)
        if p >= 0:
            return [self._messages[p]]
        else:
            return []


    def select_by_msgid (self, msgid):
        """
        Select messages from the catalog by matching C{msgid} field.

        Several messages may have the same C{msgid} field, due to different
        C{msgctxt} fields. Empty list is returned when there is no match.

        Runtime complexity O(n).

        @param msgid: the text of C{msgid} field
        @type msgid: string

        @returns: selected messages
        @rtype: list of subclass of L{Message_base}
        """

        selected_msgs = []
        for msg in self._messages:
            if msg.msgid == msgid:
                selected_msgs.append(msg)

        return selected_msgs


    def select_by_msgid_fuzzy (self, msgid, cutoff=0.6):
        """
        Select messages from the catalog by near-matching C{msgid} field.

        The C{cutoff} parameter determines the minimal admissible similarity
        (1.0 fo exact match).

        The messages are returned ordered by decreasing similarity.

        Runtime complexity O(n) * O(length(msgid)*avg(length(msgids)))
        (probably).

        @param msgid: the text of C{msgid} field
        @type msgid: string

        @param cutoff: minimal similarity
        @type cutoff: float

        @returns: selected messages
        @rtype: list of subclass of L{Message_base}
        """

        # Build dictionary of message keys by msgid;
        # there can be several keys per msgid, pack in a list.
        msgkeys = {}
        for msg in self._messages:
            if msg.msgid not in msgkeys:
                msgkeys[msg.msgid] = []
            msgkeys[msg.msgid].append(msg.key)

        # Get near-match msgids.
        near_msgids = difflib.get_close_matches(msgid, msgkeys, cutoff=cutoff)

        # Collect messages per selected msgids.
        selected_msgs = []
        for near_msgid in near_msgids:
            for msgkey in msgkeys[near_msgid]:
                selected_msgs.append(self._messages[self._msgpos[msgkey]])

        return selected_msgs


    def accelerator (self, bymsgs=False):
        """
        Report characters used as accelerator markers in GUI messages.

        Accelerator characters are determined by looking for some
        header fields, and if not found, by heuristically examining
        messages if C{bymsgs} is C{True}.

        The header fields are tried in this order: C{Accelerator-Marker},
        C{X-Accelerator-Marker}.
        In each field, several accelerator markers can be stated as
        comma-separated list, or there may be several fields;
        the union of all parsed markers is reported.

        If empty set is returned, it was determined that there are
        no accelerator markers in the catalog;
        if C{None}, that there is no determination about markers.

        It is not defined when the header or messages will be examined,
        or if they will be reexamined when they change (most probably not).
        If you want to set accelerator markers after the catalog has been
        opened, use L{set_accelerator}.

        If C{bymsgs} is C{True}, runtime complexity may be O(n).

        @param bymsgs: examine messages if necessary
        @type bymsgs: bool

        @returns: accelerator markers
        @rtype: set of strings or C{None}

        @note: Heuristic examination of messages not implemented yet.
        """

        # Check if accelerators have been already determined.
        if self._accels is not None:
            return self._accels

        accels = None

        # Analyze header.

        # - check the fields observed in the wild to state accelerators.
        for fname in (
            "Accelerator-Marker",
            "X-Accelerator-Marker",
        ):
            fields = self._header.select_fields(fname)
            for fname, fval in fields:
                if accels is None:
                    accels = set()
                accels.update([x.strip() for x in fval.split(",")])
        if accels:
            accels.discard("")

        # Skip analyzing messages if not necessary or not requested.
        if accels is not None or not bymsgs:
            self._accels = accels
            return accels

        # Analyze messages.
        # TODO.
        pass

        self._accels = accels
        return accels


    def set_accelerator (self, accels):
        """
        Set accelerator markers that can be expected in messages.

        Accelerator markers set by this method will later be readable by
        the L{accelerator} method. This will not modify the catalog header
        in any way; if that is desired, it must be done manually by
        manipulating the header fields.

        If C{accels} is given as C{None}, it means the accelerator markers
        are undetermined; if empty, that there are no markers in messages.

        @param accels: accelerator markers
        @type accels: sequence of strings or C{None}
        """

        if accels is not None:
            self._accels = set(accels)
        else:
            self._accels = None


    def markup (self, bymsgs=False):
        """
        Report what types of markup can be expected in messages.

        Markup types are determined by looking for some header fields,
        and if not found, by heuristically examining messages
        if C{bymsgs} is C{True}. Markup types are represented as
        short symbolic names, e.g. "html", "docbook", "mediawiki", etc.

        The header fields are tried in this order: C{Text-Markup},
        C{X-Text-Markup}.
        In each field, several markup types can be stated as
        comma-separated list, or there may be several fields;
        the union of all parsed types is reported.

        If empty set is returned, it was determined that there is
        no markup in the catalog;
        if C{None}, that there is no determination about markup.

        It is not defined when the header or messages will be examined,
        or if they will be reexamined when they change (most probably not).
        If you want to set markup types after the catalog has been
        opened, use L{set_markup} method.

        If C{bymsgs} is C{True}, runtime complexity may be O(n).

        @param bymsgs: examine messages if necessary
        @type bymsgs: bool

        @returns: markup names
        @rtype: set of strings or C{None}

        @note: Heuristic examination of messages not implemented yet.
        """

        # Check if markup types have been already determined.
        if self._mtypes is not None:
            return self._mtypes

        mtypes = None

        # Analyze header.

        # - check the fields observed in the wild to state markup types.
        for fname in (
            "Text-Markup",
            "X-Text-Markup",
        ):
            fields = self._header.select_fields(fname)
            for fname, fval in fields:
                if mtypes is None:
                    mtypes = set()
                mtypes.update([x.strip() for x in fval.split(",")])
        if mtypes:
            mtypes.discard("")

        # Skip analyzing messages if not necessary or not requested.
        if mtypes is not None or not bymsgs:
            self._mtypes = mtypes
            return mtypes

        # Analyze messages.
        # TODO.
        pass

        self._mtypes = mtypes
        return mtypes


    def set_markup (self, mtypes):
        """
        Set markup types that can be expected in messages.

        Markup types set by this method will later be readable by
        the L{markup} method. This will not modify the catalog header
        in any way; if that is desired, it must be done manually by
        manipulating the header fields.

        If C{mtypes} is given as C{None}, it means the markup types
        are undetermined; if empty, that there is no markup in messages.

        @param mtypes: markup types
        @type mtypes: sequence of strings or C{None}
        """

        if mtypes is not None:
            self._mtypes = set(mtypes)
        else:
            self._mtypes = None


    def language (self):
        """
        Report language of the translation.

        Language is determined by looking for the C{Language} header field.
        If this field is present, it should contain the language code
        in line with GNU C library locales, e.g. C{pt} for Portuguese,
        or C{pt_BR} for Brazilian Portuguese.
        If the field is not present, language is considered undetermined,
        and C{None} is returned.

        It is not defined when the header will be examined,
        or if it will be reexamined when it changes (most probably not).
        If you want to set language after the catalog has been
        opened, use L{set_language} method.

        @returns: language code
        @rtype: string or C{None}
        """

        # Check if language has already been determined.
        if self._lang is not None:
            return self._lang

        lang = None

        fval = self._header.get_field_value("Language")
        if fval:
            lang = fval.strip()

        self._lang = lang
        return lang


    def set_language (self, lang):
        """
        Set language of the translation.

        Language set by this method will later be readable by
        the L{language} method. This will not modify the catalog header
        in any way; if that is desired, it must be done manually by
        manipulating the header fields.

        If C{lang} is given as C{None}, it means the language is undetermined.
        If it is given as empty string, it means the language is deliberately
        considered unknown.

        @param lang: language code
        @type lang: string or C{None}
        """

        if lang is not None:
            self._lang = unicode(lang)
        else:
            self._lang = None

