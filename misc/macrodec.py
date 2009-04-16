# -*- coding: UTF-8 -*-

"""
Declinations of words and phrases by macro expansion.

FIXME: Describe macrodec file format and usage of Declinator.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import sys
import os
import re
import locale

from pology.misc.report import warning
from pology.misc.resolve import first_to_upper, first_to_lower

def _p (x, y): # FIXME: temporary
    return y

# ----------------------------------------
# Constants.

# Significant characters.
_ch_comment = "#"
_ch_head_sep = ":"
_ch_key_sep = "="
_ch_body_sep = ","
_ch_entry_end = ";"
_ch_exp = "|"
_ch_exp_open = "{"
_ch_exp_close = "}"
_ch_exp_mask = "~"
_ch_hidden = "|"
_ch_cut = "!"
_ch_prop = "_"
_ch_caps = "^"
_ch_nocaps = "`"
_ch_mask = "."
_ch_override = "`" # FIXME: Legacy, remove.

# For breaking out of nested loop by exceptions.
class _EndLoop: pass

# ----------------------------------------
# Error handling.

class MacrodecError (Exception):
    """
    Exception for problems in macro declinations.
    """

    def __init__ (self, msg, code, source=None, line=None):
        """
        Constructor.

        All the parameters are made available as instance variables.

        Codes guide: < 1000 user errors, >= 1000 internal errors.

        @param msg: a description of what went wrong
        @type msg: string
        @param code: numerical ID of the problem
        @type code: int
        @param source: name of the source in which the problem occured
        @type source: string or None
        @param line: line in the source in which the problem occured
        @type line: int or None
        """

        self.msg = msg
        self.code = code
        self.source = source
        self.line = line


    def __unicode__ (self):

        if self.source is None:
            s = (_p("@info error format: code, message",
                   "[macrodec-%d]: %s")
                 % (self.code, self.msg))
        elif self.line is None:
            s = (_p("@info error format: code, source name, message",
                    "[macrodec-%d] in %s: %s")
                 % (self.code, self.source, self.msg))
        else:
            s = (_p("@info error format: code, source name, line, message",
                    "[macrodec-%d] at %s:%d: %s")
                 % (self.code, self.source, self.line, self.msg))

        return unicode(s)


    def __str__ (self):

        return self.__unicode__().encode(locale.getpreferredencoding())


# ----------------------------------------
# Normalization.

_wsseq_rx = re.compile(r"(\s)+", re.U)

def simplify (s):
    """
    Simplify whitespace in the string.

    All leading and trailing whitespace are removed,
    all inner whitespace sequences are replaced with one of the whitespaces
    in the sequence (undefined which).

    @param s: string to normalize
    @type s: string

    @returns: normalized string
    @rtype: string
    """

    return _wsseq_rx.sub(r"\1", s.strip())


def shrink (s):
    """
    Remove all whitespace from the string.

    @param s: string to normalize
    @type s: string

    @returns: normalized string
    @rtype: string
    """

    return _wsseq_rx.sub("", s)


def tighten (s):
    """
    Remove all whitespace and lowercase the string.

    @param s: string to normalize
    @type s: string

    @returns: normalized string
    @rtype: string
    """

    return _wsseq_rx.sub("", s.lower())


_non_ascii_ident_rx = re.compile(r"[^a-z0-9_]", re.U|re.I)

def identify (s):
    """
    Construct an uniform-case ASCII-identifier out of the string.

    ASCII-identifier is constructed in the following order:
      - the string is lowercased
      - every character that is neither an ASCII alphanumeric nor
        the underscore is removed
      - if the string starts with a digit, underscore is prepended

    @param s: string to normalize
    @type s: string

    @returns: normalized string
    @rtype: string
    """

    ns = s

    # Lowercase.
    ns = ns.lower()

    # Remove non-identifier chars.
    ns = _non_ascii_ident_rx.sub("", ns) 

    # Prefix with underscore if first char is digit.
    if ns[0:1].isdigit():
        ns = "_" + ns

    return ns


def xentitize (s):
    """
    Replace characters having default XML entities with the entities.

    The replacements are:
      - C{&amp;} for ampersand
      - C{&lt} and C{&gt;} for less-than and greater-then signs
      - C{&apos;} and C{&quot;} for ASCII single and double quotes

    @param s: string to normalize
    @type s: string

    @returns: normalized string
    @rtype: string
    """

    ns = s
    ns = ns.replace("&", "&amp;") # must come first
    ns = ns.replace("<", "&lt;")
    ns = ns.replace(">", "&gt;")
    ns = ns.replace("'", "&apos;")
    ns = ns.replace('"', "&quot;")

    return ns


# ----------------------------------------
# Data structures.

# Entry with phrases and declinations.
class _MdEntry:

    def __init__ (self, source, hidden):
        # File in which this entry is defined.
        self.source = source
        # The entry is for end use (false), or only for expansions (true).
        self.hidden = hidden
        # List of key phrases (MdText).
        self.phrases = []
        # List of declinations (MdDec).
        self.decs = []


# Declination.
class _MdDec:

    def __init__ (self):
        # List of keys (MdKey).
        self.keys = []
        # The list of value segments (can be MdText or MdExp).
        self.vals = []
        # Link from key texts (string) to key objects (MdKey).
        self.key_to_full = {}


# Declination key.
class _MdKey:

    def __init__ (self, text, cut, lineno):
        # Text, selection mask, capitalization, line number.
        self.text = text
        self.cut = cut
        self.lineno = lineno

# Expander.
class _MdExp:

    def __init__ (self, text, mask, caps, lineno):
        # Text, selection mask, capitalization, line number.
        self.text = text
        self.mask = mask
        self.caps = caps
        self.lineno = lineno


# Text segment.
class _MdText:

    def __init__ (self, text, lineno):
        # Text and line number.
        self.text = text
        self.lineno = lineno


# ----------------------------------------
# Interface-independent functions for parsing and declinating entries.

# Caches.
_srcname_anon_counter = 0
_parses_by_source = {}
_rawparse_by_source = {}
_dkeys_by_entry = {}
_dval_iscut_by_entry_dkey = {}


# Parse the string into declination entries.
def _parse_string (ifs, srcname=None, encoding=None):

    if not srcname:
        srcname = _p("@item name of an anonymous input source",
                     "<ANON%d>") % _srcname_anon_counter
        _srcname_anon_counter += 1

    parses = _parses_by_source.get(srcname)
    if parses is not None:
        return parses

    _parse_string_w(ifs, srcname, encoding)

    parses = _assemble_parse_data(srcname)
    _parses_by_source[srcname] = parses

    return parses


def _parse_string_w (ifs, srcname=None, encoding=None):

    if srcname in _rawparse_by_source:
        return

    # States.
    s_end, s_inhead, s_indec, s_inexp, s_inmask = range(5)

    # Parse string.
    ifl = len(ifs)
    entries = []
    incpaths = set()
    includes = []
    pos = 0
    lcount = 1
    entry = None
    state = s_inhead
    try:
        while True:
            if state == s_inhead:
                tok, pos, sep, lcount = \
                    _tosep(ifs, pos,
                           (_ch_body_sep, _ch_head_sep, _ch_entry_end),
                           lcount, _EndLoop)

                # Check if entry is hidden.
                hidden = False
                if tok.strip().startswith(_ch_hidden):
                    # Remove hiding marker.
                    tok = tok.replace(_ch_hidden, "", 1)
                    hidden = True

                # Check if key is allowed override.
                # FIXME: Legacy, no effect, remove.
                override = False
                if tok.strip().startswith(_ch_override):
                    # Remove override marker.
                    tok = tok.replace(_ch_override, "", 1)
                    override = True

                if sep == _ch_entry_end:
                    # File inclusion, recurse and append parsed entries.
                    incname = simplify(tok) # sorry, no idiotic file names
                    # Take path for inclusion relative to the current file,
                    # not the working directory.
                    incpath = os.path.join(os.path.dirname(srcname), incname)
                    if not os.path.isfile(incpath):
                        raise MacrodecError(
                            _p("@info",
                               "included file '%s' does not exist") % incpath,
                            20, srcname, lcount)
                    if incpath not in incpaths and incpath != srcname:
                        includes.append((incpath, hidden))
                        incpaths.add(incpath)
                else:
                    # Record entry phrase.
                    entry = entry or _MdEntry(srcname, hidden)
                    phrase = simplify(tok)
                    entry.phrases.append(_MdText(phrase, lcount))

                    if   sep == _ch_body_sep:
                        # Another entry key, keep on.
                        pass
                    elif sep == _ch_head_sep:
                        # Initialize first declination.
                        entry.decs.append(_MdDec())
                        # Step into declinations.
                        state = s_indec
                    else:
                        raise MacrodecError(
                            _p("@info internal error",
                               "internal: separator %s") % sep, 1020)

            elif state == s_indec:
                tok, pos, sep, lcount = \
                    _tosep(ifs, pos,
                           (_ch_exp, _ch_key_sep, _ch_body_sep, _ch_entry_end),
                           lcount, _EndLoop)

                if   sep == _ch_key_sep:
                    # Record declination key.
                    key = shrink(tok)
                    cut = key.endswith(_ch_cut)
                    if cut:
                        key = key[:-len(_ch_cut)]
                    full_key = _MdKey(key, cut, lcount)
                    entry.decs[-1].keys.append(full_key)
                    entry.decs[-1].key_to_full[key] = full_key
                else:
                    # Record declination text segment.
                    entry.decs[-1].vals.append(_MdText(tok, lcount))
                    if   sep == _ch_body_sep:
                        # Initialize next declination.
                        entry.decs.append(_MdDec())
                    elif sep == _ch_exp:
                        # Step into expander.
                        state = s_inexp
                    elif sep == _ch_entry_end:
                        # Step into end of entry.
                        state = s_end
                    else:
                        raise MacrodecError(
                            _p("@info internal error",
                               "internal: separator %s") % sep, 1030)

            elif state == s_inexp:
                if pos >= ifl:
                    raise _EndLoop

                # Step once or twice, depending on the presence of caps marker.
                caps = None
                for q in range(2):
                    if q == 0:
                        braced = ifs[pos] == _ch_exp_open
                        if braced:
                            pos += 1 # skip open brace
                    if not braced: # unbraced expander
                        exp_ends = [_ch_exp, _ch_exp_mask, _ch_body_sep,
                                    _ch_entry_end, " ", "\t", "\n"]
                    else: # braced expander
                        exp_ends = [_ch_exp_mask, _ch_exp_close]
                    # Add caps and nocaps markers if first pass.
                    if q == 0:
                        exp_ends.extend((_ch_caps, _ch_nocaps))

                    tok, pos, sep, lcount = \
                        _tosep(ifs, pos, exp_ends, lcount, _EndLoop)

                    # If caps marker found, possibly take the second pass.
                    # Otherwise, no second pass.
                    if sep in (_ch_caps, _ch_nocaps):
                        # If token is all whitespace, indicate capitalization
                        # and take second pass.
                        # Otherwise, no second pass and put caps marker back
                        # as part of the token.
                        if not tok.strip():
                            caps = sep == _ch_caps
                        else:
                            tok += sep
                            break
                    else:
                        break

                # Record expander.
                exp = simplify(tok)
                entry.decs[-1].vals.append(_MdExp(exp, "", caps, lcount))

                if   sep == _ch_exp:
                    # Another expander, keep on.
                    pass
                elif sep == _ch_exp_mask:
                    # Step into mask.
                    state = s_inmask
                elif sep == _ch_body_sep:
                    # Initialize next declination.
                    entry.decs.append(_MdDec())
                    # Step into declination body.
                    state = s_indec
                elif sep.isspace():
                    # Back one character, space is part of text.
                    pos -= 1
                    # Step into declination body.
                    state = s_indec
                elif sep == _ch_exp_close:
                    # Step into declination body.
                    state = s_indec
                elif sep == _ch_entry_end:
                    # Step into end of entry.
                    state = s_end
                else:
                    raise MacrodecError(
                        _p("@info internal error",
                           "internal: separator %s") % sep, 1040)

            elif state == s_inmask:
                # Use endings of last expander, sans the mask separator.
                exp_ends.remove(_ch_exp_mask)
                tok, pos, sep, lcount = \
                    _tosep(ifs, pos, exp_ends, lcount, _EndLoop)

                # Add mask to last expander.
                entry.decs[-1].vals[-1].mask = tok

                if   sep == _ch_exp:
                    # Step into expander.
                    state = s_inexp
                elif sep == _ch_body_sep:
                    # Initialize next declination.
                    entry.decs.append(_MdDec())
                    # Step into declination body.
                    state = s_indec
                elif sep.isspace():
                    # Back one character, space is part of text.
                    pos -= 1
                    # Step into declination body.
                    state = s_indec
                elif sep == _ch_exp_close:
                    # Step into declination body.
                    state = s_indec
                elif sep == _ch_entry_end:
                    # Step into end of entry.
                    state = s_end
                else:
                    raise MacrodecError(
                        _p("@info internal error",
                           "internal: separator %s") % sep, 1050)

            elif state == s_end:
                entries.append(entry)
                entry = None
                state = s_inhead

            else:
                raise MacrodecError(
                    _p("@info internal error",
                       "internal: state %d") % state, 1010)

    except _EndLoop:
        if state != s_inhead or entry:
            raise MacrodecError(
                _p("@info", "unexpected end of stream '%s'") % srcname, 10)

    # Link entries by phrases.
    entry_by_phrase = {}
    for entry in entries:
        entry_by_phrase.update([(x.text, entry) for x in entry.phrases])
    _rawparse_by_source[srcname] = (entries, entry_by_phrase, includes)

    # Parse all non-parsed included files.
    for incpath, dummy in includes:
        _parse_file_w(incpath, encoding)


# Parse the file into declination entries.
def _parse_file (filename, encoding=None):

    parses = _parses_by_source.get(filename)
    if parses is not None:
        return parses

    _parse_file_w(filename, encoding)

    parses = _assemble_parse_data(filename)
    _parses_by_source[filename] = parses

    return parses


def _parse_file_w (filename, encoding=None):

    if filename in _rawparse_by_source:
        return

    # Scoop up file contents into a string.
    encoding = encoding or locale.getpreferredencoding()
    if filename != "-":
        ifh = open(filename, "r")
    else:
        ifh = sys.stdin
        filename = _p("@item standard input shown as a file name",
                      "<STDIN>")
    ifs = []
    for line in ifh.readlines():
        line = unicode(line, encoding)
        # Remove comment from the line; mind escapes.
        p = -1
        while True:
            p = line.find(_ch_comment, p + 1)
            if p < 0:
                break
            if p == 0 or line[p - 1] != "\\":
                line = line[:p] + "\n"
                break
        # Add to content string.
        ifs.append(line)
    ifs = "".join(ifs)
    if ifh is not sys.stdin:
        ifh.close()

    return _parse_string_w(ifs, filename, encoding)


# Assemble oredered set of entries by inclusions for given source.
def _assemble_parse_data (srcname, parents=set()):

    parents.add(srcname)
    entries, dummy, includes = _rawparse_by_source[srcname]
    parses = []
    seen_sources = set([srcname])
    for incpath, hidden in includes:
        if incpath in parents:
            continue
        incparses = _assemble_parse_data(incpath, parents)
        for incentries, incsrcname, dummy in incparses:
            if incsrcname not in seen_sources:
                seen_sources.add(incsrcname)
                parses.append((incentries, incsrcname, hidden))
    parses.append((entries, srcname, False))
    parents.remove(srcname)

    return parses


# Go to next separator character in the string, minding escapes.
# Input:
#   s - string
#   pos - start position
#   seps - sequence of separator characters
#   lcount - start line count
#   excobj - object to raise if no separtor found (unless None)
#   escape - escape character
# Output tuple:
# - substring from the start position, up to and excluding the separator,
#   or up to the end of string if no separator found
# - position after the separator, -1 if none found
# - the separator, empty if none found
# - line count increased by the number of encountered newlines,
#   up to and including the separator
def _tosep (s, pos, seps, lcount, excobj=None, escape="\\"):

    slen = len(s)
    npos = pos
    found = False
    sub = ""
    while npos < slen:
        c = s[npos]
        if c == "\n": # before other checks
            lcount += 1
        if c == escape:
            npos += 2
            if npos >= slen:
                break
            sub += s[npos - 1]
            continue
        if c in seps:
            found = True
            break
        sub += c
        npos += 1

    if found:
        return (sub, npos + len(c), c, lcount)
    else:
        if excobj is None:
            return (sub, -1, "", lcount)
        else:
            raise excobj


# Get declination value of an entry for a given declination key.
# Input:
#   entry - instance of MdEntry
#   dkey - declination key
# Output tuple:
# - requested value (or None if declination key was not found)
# - the declination key that was found (might be empty, with a cut, etc.)
def _declinate (entry, dkey):

    dval_iscut = _dval_iscut_by_entry_dkey.get(entry, {}).get(dkey)
    if dval_iscut is not None:
        return dval_iscut

    # TODO: Catch circular referencing.

    # Go through declinations backwards, due to possible overrides.
    dvalue = None
    is_cut = False
    for i_dec in range(len(entry.decs) - 1, -1, -1):
        dec = entry.decs[i_dec]
        dvsegs = []
        dkey_matched = False
        is_cut = False

        # If current declination has some explicit keys,
        # and requested key is not among them,
        # there can be no match.
        if dec.keys:
            full_dkey = dec.key_to_full.get(dkey)
            if not full_dkey:
                continue
            else:
                is_cut = full_dkey.cut
                dkey_matched = True

        # Build final segments out of raw segments.
        for seg in dec.vals:

            if isinstance(seg, _MdText):
                dvseg = (seg.text, False)

            elif isinstance(seg, _MdExp):
                # Fetch the referenced entry.
                ref_entry = _fetch_ref(entry, seg)

                # Construct referenced declination taking mask into account.
                try_ref = True
                if seg.mask:
                    if _ch_mask in seg.mask:
                        # If mask has some placeholders, if must be possible
                        # to fill them exactly with requested declination,
                        # or else the expansion cannot succeed.
                        if seg.mask.count(_ch_mask) == len(dkey):
                            ref_dkey = ""
                            dkey_chars = list(dkey)
                            for c in seg.mask:
                                if c == _ch_mask:
                                    c = dkey_chars.pop(0)
                                ref_dkey += c
                            dkey_matched = True
                        else:
                            try_ref = False
                    else:
                        # Mask without placeholders simply overrides
                        # requested declination.
                        ref_dkey = seg.mask
                else:
                    # No mask, referenced declination same as requested.
                    ref_dkey = dkey
                    dkey_matched = True

                # Get referenced declination from referenced entry.
                if try_ref:
                    dvseg = _declinate(ref_entry, ref_dkey)
                else:
                    dvseg = (None, False)
                # Do not break if dvseg[0] is None, as the key may be cut.

                # Capitalize or decapitalize first letter
                # of referenced value if requested.
                if seg.caps is not None and dvseg[0] is not None:
                    f = seg.caps and first_to_upper or first_to_lower
                    dvseg = (f(dvseg[0]), dvseg[1])

            else:
                raise MacrodecError(
                    _p("@info internal error",
                       "internal: unknown segment type '%s'") % type(seg),
                    1100)

            # Record computed final segment.
            dvsegs.append(dvseg)

        if dkey_matched:
            # Last segment comming from a cut-key discards everything else.
            # Some of the expansions may also not have been resolved.
            undefined = False
            for i_seg in range(len(dvsegs) - 1, -1, -1):
                dvseg = dvsegs[i_seg]
                if dvseg[1]:
                    dvsegs = [dvseg]
                    is_cut = True
                    undefined = False
                    break
                if dvseg[0] is None:
                    undefined = True
            if not undefined:
                dvalue = simplify("".join([x[0] for x in dvsegs]))
                break

    dvals_iscuts = _dval_iscut_by_entry_dkey.get(entry)
    if not dvals_iscuts:
        dvals_iscuts = {}
        _dval_iscut_by_entry_dkey[entry] = dvals_iscuts
    dvals_iscuts[dkey] = (dvalue, is_cut)

    return dvalue, is_cut


# Get all declination keys of an entry yielding complete declinations.
# Input:
#   entry - instance of MdEntry
# Output: list of declination keys (string), in unspecified order.
def _declkeys (entry):

    # TODO: Catch circular referencing.

    dkeys = _dkeys_by_entry.get(entry)
    if dkeys is not None:
        return dkeys

    dkeys = []
    dkeys_set = set()
    for dec in entry.decs:

        inited = False
        if dec.keys:
            inited = True
            loc_dkeys = [x.text for x in dec.keys]

        for seg in dec.vals:
            if isinstance(seg, _MdExp):
                # Fetch the referenced entry and declinations in it.
                ref_entry = _fetch_ref(entry, seg)
                ref_dkeys = _declkeys(ref_entry)

                # Transform keys from the referenced if expansion was masked.
                if seg.mask:
                    if _ch_mask in seg.mask:
                        # Eliminate all obtained keys not matching the mask.
                        # Reduce by mask those that match.
                        mref_dkeys = []
                        for ref_dkey in ref_dkeys:
                            if len(ref_dkey) != len(seg.mask):
                                continue
                            mref_dkey = ""
                            for c, cm in zip(ref_dkey, seg.mask):
                                if cm != _ch_mask:
                                    if cm != c:
                                        mref_dkey = None
                                        break
                                else:
                                    mref_dkey += c
                            if mref_dkey:
                                mref_dkeys.append(mref_dkey)
                        ref_dkeys = mref_dkeys
                    else:
                        # If mask has no placeholders,
                        # then it implies no keys,
                        # but does cancel the whole declination
                        # if no obtained key is equal to mask key.
                        if seg.mask in ref_dkeys:
                            continue
                        else:
                            loc_dkeys = []
                            break

                # If keys were not initialized yet, set those from
                # the reference as initial.
                # Otherwise, eliminate all keys that are not found
                # among those from the reference.
                if not inited:
                    inited = True
                    loc_dkeys = ref_dkeys
                else:
                    loc_dkeys = filter(lambda x: x in ref_dkeys, loc_dkeys)

            if inited and not loc_dkeys:
                # All keys eliminated, end processing this declination.
                break

        for dkey in loc_dkeys:
            if dkey not in dkeys_set:
                dkeys.append(dkey)
                dkeys_set.add(dkey)

    _dkeys_by_entry[entry] = dkeys

    return dkeys


# Get entry referenced by an expansion.
# Input:
#   entry - the entry which contains the expansion (MdEntry)
#   seg - the segment which contains the expansion (MdExp)
# Returns the referenced entry, raises exception if not found.
def _fetch_ref (entry, seg):

    rawparse = _rawparse_by_source.get(entry.source)
    if not rawparse:
        raise MacrodecError(
            _p("@info",
               "entry states unknown source '%s'")
            % entry.source,
            1100)
    dummy, entries_by_source, includes = rawparse

    ref_entry = None
    for i in range(len(includes), -1, -1):
        if i == len(includes):
            isource = entry.source
        else:
            isource = includes[i][0]
        ref_rawparse = _rawparse_by_source.get(isource)
        if not ref_rawparse:
            raise MacrodecError(
                _p("@info internal error",
                   "internal: source '%s' not loaded") % isource,
                1320, entry.source, seg.lineno)
        ref_entry = ref_rawparse[1].get(seg.text)
        if ref_entry:
            break
    if not ref_entry:
        # Referenced entry cannot be found, input error.
        raise MacrodecError(
            _p("@info", "unknown expansion '%s'") % seg.text,
            110, entry.source, seg.lineno)

    return ref_entry


# ----------------------------------------

class Declinator (object):
    """
    FIXME: Write doc.
    """

    def __init__ (self, edsep="-", ekeyfdec=[], ekeyuniq=False,
                  ekeytf=None, ekeyitf=None, dkeytf=None, dkeyitf=None,
                  dvaltf=None, phrasetf=None):
        """
        FIXME: Write doc.
        """

        self._edsep = edsep
        self._ekeyuniq = ekeyuniq
        self._ekeyfdec = ekeyfdec

        self._ekeytf = ekeytf
        self._ekeyitf = ekeyitf
        self._dkeytf = dkeytf
        self._dkeyitf = dkeyitf
        self._dvaltf = dvaltf
        self._phrasetf = phrasetf

        self._ekeys_by_visible_entry = {}
        self._visible_entry_by_ekey = {}
        self._visible_entries = set()
        self._imported_sources = set()

        self._dvaltf1_by_source = {}
        self._phrasetf1_by_source = {}

        self._dkeymaps_by_entry = {}
        self._dvals_by_ekey_odkey = {}
        self._odvals_by_entry_odkey = {}


    def import_file (self, filename, encoding=None,
                     ekeyitf1=None, dvaltf1=None, phrasetf1=None):
        """
        FIXME: Write doc.
        """

        if filename in self._imported_sources:
            return 0

        parse_res = _parse_file(filename, encoding)

        if dvaltf1:
            self._dvaltf1_by_source[filename] = dvaltf1
        if phrasetf1:
            self._phrasetf1_by_source[filename] = phrasetf1

        # Produce keys for phrases of visible entries.
        new_entries = 0
        for entries, incpath, inchidden in parse_res:
            if inchidden or incpath in self._imported_sources:
                continue
            self._imported_sources.add(incpath)
            for entry in entries:
                if entry.hidden or entry in self._visible_entries:
                    continue
                self._visible_entries.add(entry)
                new_entries += 1

                # Basic phrases.
                phrases = [x.text for x in entry.phrases]

                # Requested extra phrases from declinations.
                for dkey in self._ekeyfdec:
                    value, is_cut = _declinate(entry, dkey)
                    if value is not None:
                        phrases.append(value)

                # Compute entry keys from phrases.
                ekeys = set()
                for phrase in phrases:
                    ekey = phrase
                    for ekeyitf in (ekeyitf1, self._ekeyitf):
                        if not ekey:
                            break
                        if ekeyitf:
                            ekey = ekeyitf(ekey)
                    if ekey:
                        ekeys.add(ekey)

                # Check and take appropriate action on conflicts of
                # keys for this entry and those of other entries.
                for ekey in list(ekeys):
                    oentry = self._visible_entry_by_ekey.get(ekey)
                    if oentry is None:
                        continue

                    confposrep = lambda: (
                        _p("@info",
                           "macrodec entries at %s:%d ('%s') and %s:%d ('%s')")
                        % (oentry.source, oentry.phrases[0].lineno,
                           ", ".join([x.text for x in oentry.phrases]),
                           entry.source, entry.phrases[0].lineno,
                           ", ".join([x.text for x in entry.phrases])))

                    if self._ekeyuniq:
                        # Strict conflict resolution.
                        warning(_p("@info",
                                   "%s: both thrown out due to a key conflict")
                                % confposrep())
                        ekeys.clear()
                        self._visible_entry_by_ekey.pop(ekey)
                        self._ekeys_by_visible_entry.pop(oentry)
                        break
                    else:
                        # Relaxed conflict resolution.
                        oekeys = self._ekeys_by_visible_entry[oentry]
                        if len(ekeys) > 1 and len(oekeys) > 1:
                            ekeys.remove(ekey)
                            oekeys.remove(ekey)
                            self._visible_entry_by_ekey.pop(ekey)
                        elif len(oekeys) > 1:
                            oekeys.remove(ekey)
                            self._visible_entry_by_ekey.pop(ekey)
                        elif len(ekeys) > 1:
                            ekeys.remove(ekey)
                        else:
                            warning(_p("@info",
                                       "%s: both thrown out due to "
                                       "irreconcilable key conflict")
                                    % confposrep())
                            ekeys.clear()
                            self._visible_entry_by_ekey.pop(ekey)
                            self._ekeys_by_visible_entry.pop(oentry)
                            break

                if ekeys:
                    ekeys_binding = [(x, entry) for x in ekeys]
                    self._visible_entry_by_ekey.update(ekeys_binding)
                    self._ekeys_by_visible_entry[entry] = ekeys

        return new_entries


    def get2 (self, ekey, dkey, defval=None):
        """
        FIXME: Write doc.
        """

        return self._get2_w(ekey, dkey, defval)


    def _get2_w (self, ekey, dkey, defval=None, igntfs=[]):
        """
        FIXME: Write doc.
        """

        # Try to get entry by entry key.
        # Note: Must not cache by non-transformed key,
        # unless rest argument is cached too.
        ekey_t = ekey
        ekey_rest = None
        if self._ekeytf:
            ekey_t = self._ekeytf(ekey)
            if isinstance(ekey_t, tuple):
                ekey_t, ekey_rest = ekey_t
        entry = self._visible_entry_by_ekey.get(ekey_t)
        if entry is None:
            return defval

        # Collect declination keys for this entry if not collected yet.
        dkeymap = self._dkeymaps_by_entry.get(entry)
        if dkeymap is None:
            dkeymap = self._map_dkeys(entry)
            self._dkeymaps_by_entry[entry] = dkeymap

        # Try to get original declination key by declination key.
        dkey_t = dkey
        for dkeytf in (self._dkeytf,):
            if dkey_t is None:
                break
            opts = None
            if isinstance(dkeytf, tuple):
                dkeytf, opts = dkeytf[0], list(dkeytf[1:])
            if dkeytf is None or dkeytf in igntfs:
                continue
            if opts:
                args = [dkey_t]
                if opts and opts.pop(0):
                    args.append(ekey_rest)
                if opts and opts.pop(0):
                    args.append(entry.source)
                if opts and opts.pop(0):
                    args.append(self.phrases(ekey))
                if opts:
                    igntfs_loc = igntfs + [dkeytf]
                    args.append(self._get2_vm(ekey, opts.pop(0), igntfs_loc))
                dkey_t = dkeytf(*args)
            else:
                dkey_t = dkeytf(dkey_t)
        odkey = dkeymap.get(dkey_t)
        if odkey is None:
            return defval

        # Try to get previously computed declination by entry key
        # and original declination key.
        dvals = self._dvals_by_ekey_odkey.get(ekey)
        if dvals is None:
            dvals = {}
            self._dvals_by_ekey_odkey[ekey] = dvals
        if odkey in dvals: # value could be None
            dval = dvals[odkey]
            return (dval is not None and [dval] or [defval])[0]

        # Try to get previously computed original declination
        # by entry and original declination key.
        odvals = self._odvals_by_entry_odkey.get(entry)
        if odvals is None:
            odvals = {}
            self._odvals_by_entry_odkey[entry] = odvals
        if odkey in dvals: # could be None
            odval, is_cut = odvals[odkey]
        else:
            # Compute original declination value.
            odval, is_cut = _declinate(entry, odkey)
            odvals[odkey] = (odval, is_cut)

        # Transform the declination value.
        dval = odval
        for dvaltf in (self._dvaltf1_by_source.get(entry.source), self._dvaltf):
            if dval is None:
                break
            opts = None
            if isinstance(dvaltf, tuple):
                dvaltf, opts = dvaltf[0], list(dvaltf[1:])
            if dvaltf is None or dvaltf in igntfs:
                continue
            if opts:
                args = [dval]
                if opts and opts.pop(0):
                    args.append(is_cut)
                if opts and opts.pop(0):
                    args.append(ekey_rest)
                if opts and opts.pop(0):
                    args.append(entry.source)
                if opts and opts.pop(0):
                    args.append(self.phrases(ekey))
                if opts:
                    igntfs_loc = igntfs + [dvaltf]
                    args.append(self._get2_vm(ekey, opts.pop(0), igntfs_loc))
                dval = dvaltf(*args)
            else:
                dval = dvaltf(dval)

        # Store final declination by entry key and original declination key.
        dvals[odkey] = dval # even if None

        return (dval is not None and [dval] or [defval])[0]


    def _get2_vm (self, ekey, dkeys, igntfs):

        return dict([(x, self._get2_w(ekey, x, igntfs=igntfs))
                     for x in dkeys])


    def get (self, edkey, defval=None):
        """
        FIXME: Write doc.
        """

        toks = edkey.rsplit(self._edsep, 1)
        if len(toks) != 2:
            return None
        ekey, dkey = toks

        return self.get2(ekey, dkey, defval)


    def ekeys (self):
        """
        FIXME: Write doc.
        """

        return self._visible_entry_by_ekey.keys()


    def phrases (self, ekey):
        """
        FIXME: Write doc.
        """

        ekey_t = ekey
        if self._ekeytf:
            ekey_t = self._ekeytf(ekey)
            if isinstance(ekey_t, tuple):
                ekey_t = ekey_t[0]
        entry = self._visible_entry_by_ekey.get(ekey_t)
        if entry is None:
            return []

        # Transform the phrase.
        phrases = [x.text for x in entry.phrases]
        for phrasetf in filter(lambda x: x is not None,
            (self._phrasetf1_by_source.get(entry.source), self._phrasetf)
        ):
            phrases = filter(lambda x: x is not None, map(phrasetf, phrases))

        return phrases


    def dkeys (self, ekey):
        """
        FIXME: Write doc.
        """

        # Try to get entry by phrase key.
        entry = self._visible_entry_by_ekey.get(ekey)
        if entry is None and self._ekeytf:
            # Try to get entry by transformed key.
            ekey_t = self._ekeytf(ekey)
            entry = self._visible_entry_by_ekey.get(ekey_t)
        if entry is None:
            return []

        # Collect declination keys for this entry if not collected yet.
        dkeymap = self._dkeymaps_by_entry.get(entry)
        if dkeymap is None:
            dkeymap = self._map_dkeys(entry)
            self._dkeymaps_by_entry[entry] = dkeymap

        return dkeymap.keys()


    def _map_dkeys (self, entry):

        dkeys = _declkeys(entry)
        if self._dkeyitf:
            dkeymap = {}
            for dkey in dkeys:
                tdkey = self._dkeyitf(dkey)
                if tdkey is not None:
                    dkeymap[tdkey] = dkey
        else:
            dkeymap = dict(zip(dkeys, dkeys))

        return dkeymap


    def keys (self):
        """
        FIXME: Write doc.
        """

        return list(self.iterkeys())


    def values (self):
        """
        FIXME: Write doc.
        """

        return list(self.itervalues())


    def items (self):
        """
        FIXME: Write doc.
        """

        return list(self.iteritems())


    def __contains__ (self, edkey):
        """
        FIXME: Write doc.
        """

        return self.get(edkey) is not None


    def __getitem__ (self, edkey):
        """
        FIXME: Write doc.
        """

        res = self.get(edkey)
        if res is None:
            raise KeyError, edkey

        return res


    def __iter__ (self):
        """
        FIXME: Write doc.
        """

        return self.iterkeys()


    def iterkeys (self):
        """
        FIXME: Write doc.
        """

        return self._Iterator(self._make_iter(lambda x: x))


    def itervalues (self):
        """
        FIXME: Write doc.
        """

        return self._Iterator(self._make_iter(lambda x: self.get(x)))


    def iteritems (self):
        """
        FIXME: Write doc.
        """

        return self._Iterator(self._make_iter(lambda x: (x, self.get(x))))


    class _Iterator (object):

        def __init__ (self, it):
            self._it = it

        def __iter__ (self):
            return self

        def next (self):
            return self._it() # expected to raise StopIteration on its own


    def _make_iter (self, edkeyf):

        it = iter(self._visible_entry_by_ekey)
        gdat = [None, []] # ekey, dkeys
        def next ():
            while not gdat[1]:
                gdat[0] = it.next() # will raise StopIteration
                gdat[1] = self.dkeys(gdat[0])
            ekey = gdat[0]
            dkey = gdat[1].pop(0)
            return edkeyf(ekey + self._edsep + dkey)

        return next


    def edsep (self):
        """
        Get entry-declination key separator.

        This is the separator that is used by L{get} to split
        the compound key into entry and declination keys for L{get2}.

        @returns: key separator
        @rtype: string
        """

        return self._edsep


class Combinator (object):
    """
    FIXME: Write doc.

    All methods named same as in L{Declinator} have same semantics too.
    """

    def __init__ (self, decs, dvalcf):
        """
        FIXME: Write doc.
        """

        self._decs = decs
        self._dvalcf = dvalcf


    def get2 (self, ekey, dkey, defval=None):
        """
        Combined value by entry and declination key.

        @see: L{Declinator.get2}
        """

        return self._get_any(lambda x: x.get2(ekey, dkey, defval))


    def get (self, edkey, defval=None):
        """
        Combined value by compound key.

        @see: L{Declinator.get}
        """

        return self._get_any(lambda x: x.get(edkey, defval))


    def _get_any (self, getf):

        dvals = []
        for dec in self._decs:
            dval = getf(dec)
            if dval is None:
                return None
            dvals.append(dval)

        return self._combine(dvals)


    def _combine (self, dvals):

        return self._dvalcf(dvals)


    def ekeys (self):
        """
        Entry keys present in all declinators.

        @see: L{Declinator.ekeys}
        """

        return self._intersect(lambda x: x.ekeys())


    def phrases (self, ekey):
        """
        Phrases by entry key present in all declinators.

        @see: L{Declinator.ekeys}
        """

        return self._intersect(lambda x: x.phrases(ekey))


    def dkeys (self, ekey):
        """
        Declination keys by entry key present in all declinators.

        @see: L{Declinator.dkeys}
        """

        return self._intersect(lambda x: x.dkeys(ekey))


    def _intersect (self, selectf):

        if not self._decs:
            return []

        items = reduce(lambda s, x: s.intersection(selectf(x)),
                       self._decs[1:],
                       set(selectf(self._decs[0])))

        return list(items)


    def keys (self):
        """
        Compound keys present in all declinators.
        """

        return list(self.iterkeys())


    def values (self):
        """
        Combined values reachable by same compound key in all declinators.
        """

        return list(self.itervalues())


    def items (self):
        """
        Compound keys and combined values reachable by same compound key
        in all declinators.
        """

        return list(self.iteritems())


    def __contains__ (self, edkey):
        """
        Whether the compound key is contained in every declinator.
        """

        return self.get(edkey) is not None


    def __getitem__ (self, edkey):
        """
        Combinaton of values from all declinators.
        """

        res = self.get(edkey)
        if res is None:
            raise KeyError, edkey

        return res


    def __iter__ (self):
        """
        Iterator through compound keys present in all declinators.
        """

        return self.iterkeys()


    def iterkeys (self):
        """
        Iterator through compound keys present in all declinators.
        """

        return self._Iterator(self._make_iter(lambda x, y: x))


    def itervalues (self):
        """
        Iterator through combined values reachable by same compound key
        in all declinators.
        """

        return self._Iterator(self._make_iter(lambda x, y: y))


    def iteritems (self):
        """
        Iterator through compound keys and combined values reachable
        by same compound key in all declinators.
        """

        return self._Iterator(self._make_iter(lambda x, y: (x, y)))


    class _Iterator (object):

        def __init__ (self, it):
            self._it = it

        def __iter__ (self):
            return self

        def next (self):
            x = self._it() # expected to raise StopIteration on its own
            print x
            return x


    def _make_iter (self, ret):

        if not self._decs:
            def next ():
                raise StopIteration
            return next

        it = self._decs[0].iteritems()
        def next ():
            dvals = []
            while not dvals:
                edkey, dval = it.next()
                dvals.append(dval)
                for dec in self._decs[1:]:
                    dval = dec.get(edkey)
                    if dval is None:
                        dvals = []
                        break
                    dvals.append(dval)
            return ret(edkey, self._combine(dvals))

        return next

