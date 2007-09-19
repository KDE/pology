# -*- coding: UTF-8 -*-

from pology.misc.escape import escape, unescape
from pology.misc.wrap import wrap_field
from pology.misc.monitored import Monitored
from message import Message as MessageMonitored
from message import MessageUnsafe as MessageUnsafe
from header import Header

import os, codecs, re, types, signal


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


def _parse_po_file (filename, MessageType=MessageMonitored):
    ifl = codecs.open(filename, "r", "UTF-8")

    ctx_modern, ctx_obsolete, \
    ctx_previous, ctx_current, \
    ctx_none, ctx_msgctxt, ctx_msgid, ctx_msgid_plural, ctx_msgstr = range(9)

    messages1 = list()
    lno = 0

    class Namespace: pass
    loc = Namespace()
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

    for line_raw in ifl.readlines(): # sentry for last entry
        line = line_raw.strip()
        lno += 1

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
                        file, line = srcref.split(":")
                        loc.msg.source.append((file.strip(), int(line)))
                loc.msg.lines_source.append(line_raw)

            elif line.startswith("#,"):
                try_finish()
                string_follows = False
                for flag in line[2:].split(","):
                    flag = flag.strip()
                    if flag:
                        loc.msg.flag.append(flag)
                loc.msg.lines_flag.append(line_raw)

            elif line.startswith("#."):
                try_finish()
                string_follows = False
                loc.msg.auto_comment.append(line[2:].lstrip())
                loc.msg.lines_auto_comment.append(line_raw)

            elif line.startswith("# ") or line == "#":
                try_finish()
                string_follows = False
                loc.msg.manual_comment.append(line[2:].lstrip())
                loc.msg.lines_manual_comment.append(line_raw)

            else:
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
                        loc.msg.lines_msgctxt_previous.append(line_raw)
                    elif loc.field_context == ctx_msgid:
                        loc.msg.msgid_previous += s
                        loc.msg.lines_msgid_previous.append(line_raw)
                    elif loc.field_context == ctx_msgid_plural:
                        loc.msg.msgid_plural_previous += s
                        loc.msg.lines_msgid_plural_previous.append(line_raw)
                else:
                    if loc.field_context == ctx_msgctxt:
                        loc.msg.msgctxt += s
                        loc.msg.lines_msgctxt.append(line_raw)
                    elif loc.field_context == ctx_msgid:
                        loc.msg.msgid += s
                        loc.msg.lines_msgid.append(line_raw)
                    elif loc.field_context == ctx_msgid_plural:
                        loc.msg.msgid_plural += s
                        loc.msg.lines_msgid_plural.append(line_raw)
                    elif loc.field_context == ctx_msgstr:
                        loc.msg.msgstr[msgstr_i] += s
                        loc.msg.lines_msgstr.append(line_raw)
            else:
                raise StandardError,   "expected string continuation at %s:%d" \
                                     % (filename, lno)

        loc.msg.lines_all.append(line_raw)

    try_finish() # the last message

    ifl.close()

    # Repack raw dictionaries as message objects.
    messages2 = []
    for msg1 in messages1:
        messages2.append(MessageType(msg1.__dict__))

    return messages2


def _srcref_repack (srcrefs):
    srcdict = {}
    for file, line in srcrefs:
        if not file in srcdict:
            srcdict[file] = [line]
        else:
            srcdict[file].append(line)
    return srcdict


_Catalog_spec = {
    # Data.
    "header" : {"type" : Header},
    "filename" : {"type" : types.StringTypes},
    "*" : {}, # messages sequence: the type is assigned at construction
}


class Catalog (Monitored):
    """Catalog of messages."""

    def __init__ (self, filename,
                  create=False, wrapf=wrap_field, monitored=True):
        """Build message catalog by reading from a PO file or creating anew.

        FIXME: Describe options.
        """

        self._wrapf = wrapf

        # Select type of message object to use.
        if monitored:
            message_type = MessageMonitored
        else:
            message_type = MessageUnsafe

        # Read messages or create empty catalog:
        if os.path.exists(filename):
            m = _parse_po_file(filename, message_type)
            self._created_from_scratch = False
            self._header = Header(m[0])
            self._header._committed = True # status for sync
            self.__dict__["*"] = m[1:]
        elif create:
            self._created_from_scratch = True
            self._header = Header()
            self._header._committed = False # status for sync
            self.__dict__["*"] = []
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
        _Catalog_spec["*"]["type"] = message_type
        self.assert_spec_init(_Catalog_spec)


    def __len__ (self):

        return len(self._messages)


    def __getitem__ (self, ident):

        self.assert_spec_getitem()
        if not isinstance(ident, int):
            ident = self._msgpos[ident.key]
        return self._messages[ident]


    def __contains__ (self, msg):

        return msg.key in self._msgpos


    def add (self, msg, pos=None):
        """Add a message to the catalog.

        If the message with the same key already exists, it will be merged.
        When the pos is None, the insertion will be attempted such as that
        the messages be near according to the source references.
        If pos is not None, the message is inserted at position given by pos,
        unless it is obsolete.
        Negative pos counts backward from first non-obsolete message (i.e.
        pos=-1 means insert after all non-obsolete messages).

        Returns the position where merged or inserted.
        O(n) runtime complexity, unless pos=-1 when O(1).
        """

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
        """Remove a message from the catalog.

        ident can be either a message to be removed (matched by key),
        or an index into the catalog. Removal by key is costly! (O(n))
        """

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
        """Remove a message from the catalog on the next sync.

        ident can be either a message to be removed (matched by key),
        or an index into the catalog.
        Well suited for a for-iteration over a catalog with a sync afterwards,
        so that the indices are not confused by removal.
        """

        # Determine position and key by given ident.
        if isinstance(ident, int):
            ip = ident
        else:
            ip = self._msgpos[ident.key]

        # Indicate removal on sync for this message.
        self._messages[ip]._remove_on_sync = True
        self.__dict__["#"]["*"] += 1 # indicate sequence change (pending)


    def sync (self, force=False):
        """Writes catalog file to disk if any message has been modified.

        Unmodified messages are not reformatted, unless force is True.
        Return True if file was modified, False otherwise.
        """

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
                i += 1

        # Remove one trailing newline, from the last message.
        if flines[-1] == "\n": flines.pop(-1)
        # Create the parent directory if it does not exist.
        dirname = os.path.dirname(self._filename)
        if dirname and not os.path.isdir(dirname):
            os.makedirs(dirname)
        # Write to file atomically wrt. SIGINT.
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        ofl = codecs.open(self._filename, "w", "UTF-8")
        ofl.writelines(flines)
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


    def insertion_inquiry (self, msg):
        """Compute the tentative insertion position of a message into the
        catalog and its "belonging weight" (returned as a tuple, respectively).

        The belonging weight is computed by analyzing the source references.
        O(n) runtime complexity.
        """

        return self._pick_insertion_point(msg, self._obspos)


    def created (self):
        """Whether the catalog has been newly created (no existing file)."""

        return self._created_from_scratch


    def _pick_insertion_point (self, msg, last):

        # List of candidate positions with quality weights.
        # 0.0 <= weight < 1.0 -- default insertion at the end (last)
        # 1.0 <= weight < 2.0 -- either prev or next message in the same source
        # 2.0 <= weight < 3.0 -- both prev and next message in the same source
        ip_candidates = [(last, 0.0)]

        # Try to find better position for insertion.
        fs = _srcref_repack(msg.source) # need source refs in a dictionary
        fs2 = {}
        for i in range(0, last):
            # See if the current and the previous messages share a source.
            mid_source = u""
            fs1 = fs2
            fs2 = _srcref_repack(self._messages[i].source)
            if i > 0:
                for f1 in fs1:
                    if f1 in fs2:
                        mid_source = f1; break

            # See if the new message fits between the current and the
            # previous if they share a source.
            # Pick best local by distance penalty.
            if mid_source:
                ipl = -1; wl = 0.0
                for f in fs:
                    if f in fs1 and f in fs2:
                        lcombos = [(x, x1, x2) for x in fs[f] \
                                               for x1 in fs1[f] \
                                               for x2 in fs2[f]]
                        for lno, lno1, lno2 in lcombos:
                            if lno1 != lno2 and lno1 <= lno and lno <= lno2:
                                w = 2 + 1.0 / (lno2 - lno1 + 2)
                                if w > wl:
                                    wl = w; ipl = i
                if ipl >= 0:
                    ip_candidates.append((ipl, wl))
            else:
                # See if the new message fits after the previous.
                if i > 0:
                    ipl = -1; wl = 0.0
                    for f in fs:
                        if f in fs1:
                            lcombos = [(x, x1) for x in fs[f] \
                                               for x1 in fs1[f]]
                            for lno, lno1 in lcombos:
                                if lno1 <= lno:
                                    w = 1 + 1.0 / (lno - lno1 + 2)
                                    if w > wl:
                                        wl = w; ipl = i
                    if ipl >= 0:
                        ip_candidates.append((ipl, wl))
                # See if the new message fits before the current.
                ipl = -1; wl = 0.0
                for f in fs:
                    if f in fs2:
                        lcombos = [(x, x2) for x in fs[f] \
                                           for x2 in fs2[f]]
                        for lno, lno2 in lcombos:
                            if lno <= lno2:
                                w = 1 + 1.0 / (lno2 - lno + 2)
                                if w > wl:
                                    wl = w; ipl = i
                if ipl >= 0:
                    ip_candidates.append((ipl, wl))

        # Pick the best insertion position candidate.
        ip_candidates.sort(cmp=lambda x, y: cmp(y[1], x[1]))
        #print ip_candidates
        return ip_candidates[0]

