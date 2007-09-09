# -*- coding: UTF-8 -*-

from pology.misc.escape import escape, unescape
from pology.misc.wrap import wrap_field
from message import Message as MessageMonitored
from message import MessageUnsafe as MessageUnsafe
from header import Header

import os
import codecs
import re


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


class Catalog (object):
    """Catalog of messages."""

    def __init__ (self, filename,
                  create=False, wrapf=wrap_field, monitored=True):
        """Build message catalog by reading from a PO file or creating anew.

        FIXME: Describe options.
        """

        self._wrapf = wrapf

        # Select type of message object to use.
        if monitored:
            self._MessageType = MessageMonitored
        else:
            self._MessageType = MessageUnsafe

        # For all read messages, store an ordered bundle:
        # - the message itself
        # - whether the message has been comitted to file
        # - whether the message has been marked for removal on sync
        if os.path.exists(filename):
            m = _parse_po_file(filename, self._MessageType)
            self.header = Header(m[0])
            self.header_commited = True
            self._messages = [[x, True, False] for x in m[1:]]
        elif create:
            self.header = Header()
            self.header_commited = False
            self._messages = []
        else:
            raise StandardError, "file '%s' does not exist" % (filename,)

        self.filename = filename

        # Fill in the message key-position links and removal status.
        self._msgpos = {}
        for i in range(len(self._messages)):
            self._msgpos[self._messages[i][0].key] = i

        # Find position after all non-obsolete messages.
        op = len(self._messages)
        while op > 0 and self._messages[op - 1][0].obsolete:
            op -= 1
        self._obspos = op

        # Global removal state: set to true when any message is removed,
        # reset upon sync.
        self._some_removed = False


    def __len__ (self):

        return len(self._messages)


    def __getitem__ (self, i):

        return self._messages[i][0]


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
        if not msg.msgid:
            raise StandardError, \
                  "trying to insert message with empty msgid into the catalog"
        if not isinstance(msg, self._MessageType):
            raise TypeError, \
                  "trying to insert wrong message object type into the catalog"

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
                ckey = self._messages[i][0].key
                self._msgpos[ckey] = i + 1

            # Update position after all non-obsolete messages.
            if not msg.obsolete:
                self._obspos += 1

            # Store the message.
            self._messages.insert(ip, [msg, False, False])
            # ...indicating by False that it is not present in the file yet,
            # (the other False is removal on sync indicator).
            self._msgpos[msg.key] = ip # store new key-position link

            return ip

        else:
            # The message exists, merge.
            ip = self._msgpos[msg.key]
            self._messages[ip][0].merge(msg)
            return ip


    def remove (self, ident):
        """Remove a message from the catalog.

        ident can be either a message to be removed (matched by key),
        or an index into the catalog. Removal by key is costly! (O(n))
        """

        # Determine position and key by given ident.
        if isinstance(ident, int):
            ip = ident
            key = self._messages[ip][0].key
        else:
            key = ident.key
            ip = self._msgpos[key]

        # Update key-position links for the removed index.
        nmsgs = len(self._messages)
        for i in range(ip + 1, nmsgs):
            ckey = self._messages[i][0].key
            self._msgpos[ckey] = i - 1

        # Update position after all non-obsolete messages.
        if not self._messages[ip][0].obsolete:
            self._obspos -= 1

        # Remove from messages and key-position links,
        # and indicate a removal has occured (for sync).
        self._messages.pop(ip)
        self._msgpos.pop(key)
        self._some_removed = True


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
        self._messages[ip][2] = True


    def sync (self, force=False):
        """Writes catalog file to disk if any message has been modified.

        Unmodified messages are not reformatted, unless force is True.
        Returns True if file was modified, False otherwise.
        """

        # Temporarily insert header, for homogeneous iteration.
        self._messages.insert(0, [self.header, self.header_commited, False])
        nmsgs = len(self._messages)

        # Starting position for reinserting obsolete messages.
        obstop = self._obspos

        # NOTE: Key-position links may be invalidated from this point onwards,
        # by reorderings/removals. To make sure it is not used before the
        # rebuild at the end, delete now.
        del self._msgpos

        flines = []
        anymod = False
        i = 0
        while i < nmsgs:
            msg, infile, remsync = self._messages[i]
            key = msg.key
            if remsync:
            # Removal on sync requested, just note modification and skip.
                anymod = True
                i += 1
            elif msg.obsolete and i < obstop:
            # Obsolete message out of order, reinsert and repeat the index.
                bundle = self._messages.pop(i)
                self._messages.insert(self._obspos - 1, bundle)
                # Move top position of obsolete messages.
                obstop -= 1
            else:
            # Normal message, append formatted lines to rest.
                flines.extend(msg.to_lines(self._wrapf, force))
                if force or msg.modcount or not infile:
                    anymod = True
                    msg.modcount = 0 # must not be reset before to_lines()
                    self._messages[i][1] = True
                    # ...True indicates the message has been comitted to file.
                i += 1

        # Write to disk if needed.
        dowrite = anymod or self._some_removed
        if dowrite:
            # Remove one trailing newline, from the last message.
            if flines[-1] == "\n": flines.pop(-1)
            ofl = codecs.open(self.filename, "w", "UTF-8")
            ofl.writelines(flines)
            ofl.close()

        # Remove temporarily inserted header.
        self._messages.pop(0)

        # Execute pending removals on the catalog as well.
        newlst = []
        for bundle in self._messages:
            if not bundle[2]: # not remove on sync
                newlst.append(bundle)
        self._messages = newlst

        # Rebuild key-position links due to any reordered/removed messages.
        self._msgpos = {}
        for i in range(len(self._messages)):
            self._msgpos[self._messages[i][0].key] = i

        # Update position after all non-obsolete messages.
        self._obspos = obstop

        # Reset removal state.
        self._some_removed = False
        self._msgrem = {}

        return dowrite


    def insertion_inquiry (self, msg):
        """Compute the tentative insertion position of a message into the
        catalog and its "belonging weight" (returned as a tuple, respectively).

        The belonging weight is computed by analyzing the source references.
        O(n) runtime complexity.
        """

        return self._pick_insertion_point(msg, self._obspos)


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
            fs2 = _srcref_repack(self._messages[i][0].source)
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
                                        wl = w; ipl = i - 1
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
                                    wl = w; ipl = i - 1
                if ipl >= 0:
                    ip_candidates.append((ipl, wl))

        # Pick the best insertion position candidate.
        ip_candidates.sort(cmp=lambda x, y: cmp(y[1], x[1]))
        #print ip_candidates
        return ip_candidates[0]

