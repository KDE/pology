# -*- coding: UTF-8 -*-

"""
Derive forms and properties of syntagmas by macro expansion.

FIXME: Write documentation (incl. synder format).

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import os
import locale
import re
import hashlib
import cPickle as pickle

from pology.misc.report import warning
from pology.misc.normalize import simplify, identify
from pology.misc.resolve import first_to_upper, first_to_lower


# FIXME: Temporary until i18n ready.
def _p (x, y):
    return y


# ----------------------------------------
# Error handling.

class SynderError (Exception):

    def __init__ (self, msg, code, source=None, pos=None):
        """
        Constructor.

        All the parameters are made available as instance variables.

        @param msg: description of what went wrong
        @type msg: string
        @param code: numerical ID of the problem
        @type code: int
        @param source: name of the source in which the problem occured
        @type source: string
        @param pos: line or line and column in the source
            in which the problem occured
        @type pos: int or (int, int)
        """

        self.msg = msg
        self.code = code
        self.source = source
        if isinstance(pos, tuple):
            self.line, self.col = pos
        else:
            self.line = pos
            self.col = None


    def __unicode__ (self):

        if self.source is None:
            s = (_p("context of error message",
                    "[synder-%(code)d]: %(msg)s")
                 % dict(code=self.code, msg=self.msg))
        elif self.line is None:
            s = (_p("context of error message",
                    "[synder-%(code)d] in %(source)s: %(msg)s")
                 % dict(code=self.code, msg=self.msg, source=self.source))
        elif self.col is None:
            s = (_p("context of error message",
                    "[synder-%(code)d] at %(source)s:%(line)d: %(msg)s")
                 % dict(code=self.code, msg=self.msg, source=self.source,
                        line=self.line))
        else:
            s = (_p("context of error message",
                    "[synder-%(code)d] at %(source)s:%(line)d:%(col)d: %(msg)s")
                 % dict(code=self.code, msg=self.msg, source=self.source,
                        line=self.line, col=self.col))

        return unicode(s)


    def __str__ (self):

        return self.__unicode__().encode(locale.getpreferredencoding())


# ----------------------------------------
# Caching.

# Cache for file sources, by absolute path.
_parsed_sources = {}


def empty_source_cache ():
    """
    Clear all cached sources.

    When a synder file is loaded, its parsed form is stored in a cache,
    such that future load instructions on that same path
    (e.g. when the path is included from another file)
    do not waste any extra time and memory.
    This function erases all sources from the cache,
    when loading files anew on future load instructions is desired.
    """

    _parsed_sources.clear()


# ----------------------------------------
# Parsing.

_ch_escape          = "\\"
_ch_comment         = "#"
_ch_props           = ":"
_ch_env             = "@"
_ch_esyn_hd         = "|"
_ch_prop_sep        = ","
_ch_pkey_sep        = "&"
_ch_pval            = "="
_ch_exp             = "|"
_ch_cutprop         = "!"
_ch_termprop        = "."
_ch_exp_mask        = "~"
_ch_exp_mask_pl     = "."
_ch_exp_kext        = "%"
_ch_exp_kext_pl     = "*"
_ch_exp_upc         = "^"
_ch_exp_lwc         = "`"
_ch_tag             = "~"
_ch_tag_sep         = "&"
_ch_grp_opn         = "{"
_ch_grp_cls         = "}"
_ch_inc             = ">"

_strict_ws = " \t\n" #set((" ", "\t", "\n"))
_ch_nl = "\n"


_anonsrc_count = [0]

def _parse_string (instr, srcname=None):

    if srcname is None:
        srcname = _p("automatic name for anonymous input stream",
                     "<stream-%(num)s>") % dict(num=_anonsrc_count[0])
        _anonsrc_count[0] += 1

    indent = None
    ctx = _ctx_void
    dobj = _SDSource(srcname)
    ctx_stack = []

    pos = 0
    bpos = (1, 1)
    while True:
        handler = _ctx_handlers[ctx]
        nctx, ndobj, descend, pos, bpos = handler(dobj, instr, pos, bpos)
        if nctx is not None:
            if descend:
                ctx_stack.append((ctx, dobj))
            ctx, dobj = nctx, ndobj
        elif ctx_stack:
            ctx, dobj = ctx_stack.pop()
        else:
            # Load included sources.
            for i in range(len(dobj.incsources)):
                dobj.incsources[i] = _parse_file(dobj.incsources[i])

            return dobj


def _parse_file (path):

    # Try to return parsed source from cache.
    apath = os.path.abspath(path)
    if apath in _parsed_sources:
        return _parsed_sources[apath]

    # Try to load parsed source from disk.
    source = _read_parsed_file(path)

    if source is None:
        # Parse the file.
        ifs = open(path, "r")
        lines = ifs.readlines()
        ifs.close()

        m = re.search(r"^#\s+~~~\s+(\S+)\s+~~~\s*$", lines[0])
        enc = m and m.group(1) or "UTF-8"
        lines = [x.decode(enc) for x in lines]

        instr = "".join(lines)
        source = _parse_string(instr, path)

        # Write out parsed file.
        _write_parsed_file(source)

    # Cache the source by absolute path.
    _parsed_sources[apath] = source

    return source


_compfile_suff = "c"
_compfile_dver = "0001"
_compfile_hlen = hashlib.md5().digest_size * 2

def _write_parsed_file (source):

    path = source.name
    cpath = source.name + _compfile_suff

    try:
        fhc = open(cpath, "wb")
        fh = open(path, "rb")
    except:
        return False

    # Write out data version and file hash.
    fhc.write(_compfile_dver)
    hasher = hashlib.md5
    fhc.write(hashlib.md5(fh.read()).hexdigest() + "\n")
    pickle.dump(source, fhc, 2) # 0 for ASCII instead of binary
    fhc.close()

    return True


def _read_parsed_file (path):

    cpath = path + _compfile_suff
    try:
        fhc = open(cpath, "rb")
        fh = open(path, "rb")
    except:
        return None

    # Check if data version and file hashes match.
    fdverc = fhc.read(len(_compfile_dver))
    if fdverc != _compfile_dver:
        return None
    fhash = hashlib.md5(fh.read()).hexdigest()
    fhashc = fhc.read(_compfile_hlen + 1)[:-1]
    if fhash != fhashc:
        return None

    source = pickle.load(fhc)

    return source


# ----------------------------------------
# Parsing context handlers.

def _ctx_handler_void (source, instr, pos, bpos):

    obpos = bpos
    testsep = lambda c: (c not in _strict_ws and [""] or [None])[0]
    substr, sep, pos, bpos = _move_to_sep(instr, pos, bpos, testsep, wesc=False)

    if sep is not None:
        indent = instr[pos - bpos[1] + 1:pos]
        if instr[pos] == _ch_inc:
            return _ctx_inc, source, True, pos, bpos
        elif instr[pos] == _ch_env:
            if not source.entries:
                raise SynderError(
                    _p("error message",
                       "No entry yet for which to start an environment."),
                    1002, source.name, bpos)
            if source.indenv is None:
                source.indenv = indent
            if indent != source.indenv:
                raise SynderError(
                    _p("error message",
                       "Inconsistent indenting of environment head."),
                    1003, source.name, bpos)
            entry = source.entries[-1]
            env = _SDEnv(entry, bpos)
            entry.envs.append(env)
            return _ctx_env, env, True, pos, bpos
        else:
            if source.indentry is None:
                source.indentry = indent
            if indent != source.indentry:
                raise SynderError(
                    _p("error message",
                       "Inconsistent indenting of entry head."),
                    1001, source.name, bpos)
            entry = _SDEntry(source, bpos)
            source.entries.append(entry)
            esyn = _SDSyn(entry, bpos)
            entry.syns.append(esyn)
            return _ctx_esyn, esyn, True, pos, bpos
    else:
        return None, None, False, pos, bpos


_seps_esyn = set((_ch_prop_sep, _ch_props, _ch_tag, _ch_nl))

def _ctx_handler_esyn (esyn, instr, pos, bpos):

    opos, obpos = pos, bpos
    testsep = lambda c: c in _seps_esyn and c or None
    substr, sep, pos, bpos, isesc = _move_to_sep(instr, pos, bpos, testsep,
                                                 repesc=True)

    substrls = substr.lstrip(_strict_ws)
    if (    not esyn.segs and substrls.startswith(_ch_esyn_hd)
        and not isesc[len(substr) - len(substrls)]
    ):
        esyn.hidden = True
        substr = substr.lstrip()[len(_ch_esyn_hd):]

    if substr or not esyn.segs:
        esyn.segs.append(_SDText(esyn, obpos, substr))

    if sep == _ch_props:
        entry = esyn.parent
        env = _SDEnv(entry, bpos)
        entry.envs.append(env)
        prop = _SDProp(env, bpos)
        env.props.append(prop)
        return _ctx_pkey, prop, False, pos, bpos
    elif sep == _ch_prop_sep:
        entry = esyn.parent
        esyn = _SDSyn(entry, bpos)
        entry.syns.append(esyn)
        return _ctx_esyn, esyn, False, pos, bpos
    elif sep == _ch_tag:
        tag = _SDTag(esyn, bpos)
        esyn.segs.append(tag)
        return _ctx_tag, tag, True, pos, bpos
    else:
        raise SynderError(
            _p("error message",
               "Unexpected end of entry head started at %(lin)d:%(col)d.")
            % dict(lin=obpos[0], col=obpos[1]),
            1010, esyn.parent.parent.name, bpos)


def _ctx_handler_env (env, instr, pos, bpos):

    obpos = bpos
    testsep = lambda c: c == _ch_props and c or None
    substr, sep, pos, bpos = _move_to_sep(instr, pos, bpos, testsep)

    if sep == _ch_props:
        env.name = substr[len(_ch_env):]
        if not env.name:
            raise SynderError(
                _p("error message",
                   "Empty environment name."),
                1021, env.parent.parent.name, obpos)
        for oenv in env.parent.envs[:-1]:
            if env.name == oenv.name:
                raise SynderError(
                    _p("error message",
                       "Repeated environment name '%(env)s'.")
                    % dict(env=oenv.name),
                    1022, env.parent.parent.name, obpos)
        prop = _SDProp(env, bpos)
        env.props.append(prop)
        return _ctx_pkey, prop, False, pos, bpos
    else:
       raise SynderError(
        _p("error message",
           "Unexpected end of environment head started at %(lin)d:%(col)d.")
        % dict(lin=obpos[0], col=obpos[1]),
        1020, env.parent.parent.name, bpos)


_seps_pkey = set((_ch_pkey_sep, _ch_pval, _ch_prop_sep,
                  _ch_exp, _ch_tag, _ch_nl))

def _ctx_handler_pkey (prop, instr, pos, bpos):

    opos, obpos = pos, bpos
    testsep = lambda c: c in _seps_pkey and c or None
    substr, sep, pos, bpos = _move_to_sep(instr, pos, bpos, testsep)

    if sep in (_ch_pkey_sep, _ch_pval):
        substr = substr.strip()
        cut, terminal = False, False
        while substr.endswith((_ch_cutprop, _ch_termprop)):
            if substr.endswith(_ch_cutprop):
                cut = True
                substr = substr[:-len(_ch_cutprop)]
            elif substr.endswith(_ch_termprop):
                terminal = True
                substr = substr[:-len(_ch_termprop)]
        key = _SDKey(prop, obpos, substr, cut, terminal)
        prop.keys.append(key)

    if sep == _ch_pkey_sep:
        return _ctx_pkey, prop, False, pos, bpos
    if sep == _ch_pval:
        return _ctx_pval, prop, False, pos, bpos
    else:
        # Backtrack and go into value context.
        return _ctx_pval, prop, False, opos, obpos


_seps_pval = set((_ch_prop_sep, _ch_exp, _ch_tag, _ch_nl))

def _ctx_handler_pval (prop, instr, pos, bpos):

    opos, obpos = pos, bpos
    testsep = lambda c: c in _seps_pval and c or None
    substr, sep, pos, bpos = _move_to_sep(instr, pos, bpos, testsep)

    if substr:
        prop.segs.append(_SDText(prop, obpos, substr))

    if sep == _ch_prop_sep:
        env = prop.parent
        prop = _SDProp(env, bpos)
        env.props.append(prop)
        return _ctx_pkey, prop, False, pos, bpos
    elif sep == _ch_exp:
        exp = _SDExp(prop, bpos)
        prop.segs.append(exp)
        return _ctx_exp, exp, True, pos, bpos
    elif sep == _ch_tag:
        tag = _SDTag(prop, bpos)
        prop.segs.append(tag)
        return _ctx_tag, tag, True, pos, bpos
    else:
        return None, None, False, pos, bpos


_seps_exp = set([_ch_prop_sep, _ch_exp] + list(_strict_ws))

def _ctx_handler_exp (exp, instr, pos, bpos):

    if instr[pos:pos + len(_ch_grp_opn)] == _ch_grp_opn:
        enclosed = True
        testsep = lambda c: c in (_ch_grp_cls, _ch_nl) and c or None
    else:
        enclosed = False
        testsep = lambda c: (c in _seps_exp and [""] or [None])[0]

    obpos = bpos
    substr, sep, pos, bpos, isesc = _move_to_sep(instr, pos, bpos, testsep,
                                                 repesc=True)
    if enclosed and sep is None or sep == _ch_nl:
        raise SynderError(
            _p("error message",
               "Unexpected end of expander started at %(lin)d:%(col)d.")
            % dict(lin=obpos[0], col=obpos[1]),
            1050, exp.parent.parent.parent.parent.name, bpos)

    if enclosed:
        substr = substr[len(_ch_grp_opn):]

    p = substr.find(_ch_exp_kext)
    if p >= 0:
        exp.kext = substr[p + len(_ch_exp_kext):]
        substr = substr[:p]

    p = substr.find(_ch_exp_mask)
    if p >= 0:
        exp.mask = substr[p + len(_ch_exp_mask):]
        substr = substr[:p]

    if substr.startswith(_ch_exp_upc) and not isesc[0]:
        exp.caps = True
        substr = substr[len(_ch_exp_upc):]
    elif substr.startswith(_ch_exp_lwc) and not isesc[0]:
        exp.caps = False
        substr = substr[len(_ch_exp_lwc):]

    exp.ref = substr

    return None, None, False, pos, bpos


_seps_tag = set([_ch_prop_sep, _ch_exp, _ch_tag] + list(_strict_ws))

def _ctx_handler_tag (tag, instr, pos, bpos):

    if instr[pos:pos + len(_ch_grp_opn)] == _ch_grp_opn:
        enclosed = True
        testsep = lambda c: c in (_ch_grp_cls, _ch_nl) and c or None
    else:
        enclosed = False
        testsep = lambda c: (c in _seps_exp and [""] or [None])[0]

    obpos = bpos
    substr, sep, pos, bpos = _move_to_sep(instr, pos, bpos, testsep)
    if enclosed and sep is None or sep == _ch_nl:
        raise SynderError(
            _p("error message",
               "Unexpected end of tag started at %(lin)d:%(col)d.")
            % dict(lin=obpos[0], col=obpos[1]),
            1050, exp.parent.parent.parent.parent.name, bpos)

    if enclosed:
        substr = substr[len(_ch_grp_opn):]

    tag.names = substr.split(_ch_tag_sep)

    return None, None, False, pos, bpos


def _ctx_handler_inc (source, instr, pos, bpos):

    # Skip include directive.
    substr, sep, pos, bpos = _move_to_sep(instr, pos, bpos, lambda c: c)

    # Parse include path.
    obpos = bpos
    testsep = lambda c: c == _ch_nl and c or None
    substr, sep, pos, bpos = _move_to_sep(instr, pos, bpos, testsep)

    incpath = substr.strip()
    if not incpath:
        raise SynderError(
            _p("error message",
               "Empty target path in include directive."),
            1100, source.name, obpos)

    # If included path relative, make it relative to current source.
    if not incpath.startswith(os.path.sep):
        path = os.path.join(os.path.dirname(source.name), incpath)
    else:
        path = incpath
    if not os.path.isfile(path):
        raise SynderError(
            _p("error message",
               "No such file '%(path)s'.")
            % dict(path=path),
            1101, source.name, obpos)

    # Add to included sources of this source.
    # Temporarily store paths, to be resolved into full sources later.
    source.incsources.append(path)

    return None, None, False, pos, bpos


# ----------------------------------------
# Parsing context IDs and handlers collected.
# IDs and handlers must be in the same order,
# as IDs are used to index handlers.

(
    _ctx_void,
    _ctx_esyn,
    _ctx_env,
    _ctx_pkey,
    _ctx_pval,
    _ctx_exp,
    _ctx_tag,
    _ctx_inc,
) = range(8)

_ctx_handlers = (
    _ctx_handler_void,
    _ctx_handler_esyn,
    _ctx_handler_env,
    _ctx_handler_pkey,
    _ctx_handler_pval,
    _ctx_handler_exp,
    _ctx_handler_tag,
    _ctx_handler_inc,
)

# ----------------------------------------
# Parsing utilities.

# Find the first separator admitted by the test function,
# skipping over escaped characters, continued lines and comments.
# Return substring to that point (without escapes, comments, line cont.),
# separator, and new position and block position (line, column).
# On request, also return list of escape indicators for each character
# in the substring (True where character was escaped).
# Separator test function takes single argument, the current character,
# and returns None if it is not admitted as separator.
# If end of input is reached without test function admitting a separator,
# separator is reported as None; otherwise, separator is reported as
# the return value from the test function.
def _move_to_sep (instr, pos, bpos, testsep, wesc=True, repesc=False):

    opos = pos
    substr = []
    isesc = []
    sep = None
    while sep is None and pos < len(instr):
        c = instr[pos]
        if c == _ch_comment:
            p = instr.find(_ch_nl, pos)
            if p < 0:
                pos += len(instr) - pos
            else:
                pos = p + len(_ch_nl)
        elif wesc and c == _ch_escape:
            pos += 1
            if pos < len(instr):
                if instr[pos] == _ch_nl: # line continuation
                    pass
                # elif instr[pos] == _ch_ucode: # unicode hex
                else:
                    substr.append(instr[pos])
                    isesc.append(True)
                pos += 1
        else:
            sep = testsep(c)
            if sep is not None:
                pos += len(sep)
            else:
                substr.append(c)
                isesc.append(False)
                pos += 1

    # Update block position (line, column).
    rawsubstr = instr[opos:pos]
    p = rawsubstr.rfind(_ch_nl)
    if p >= 0:
        bpos = (bpos[0] + rawsubstr.count(_ch_nl), len(rawsubstr) - p)
    else:
        bpos = (bpos[0], bpos[1] + len(rawsubstr))

    ret = ("".join(substr), sep, pos, bpos)
    if repesc:
        ret = ret + (isesc,)
    return ret


# ----------------------------------------
# Data structures.

# Synder source.
class _SDSource:

    def __init__ (self, name):

        # Name of the source (filename, etc).
        self.name = name

        # Entries (SDEntry).
        self.entries = []
        # Included sources (must be ordered).
        self.incsources = []
        # Indentation for entry heads and environments
        # (set on first parsed).
        self.indentry = None
        self.indenv = None

        ## Global directives.
        #...


    def __unicode__ (self):
        return (  "============> %s\n" % self.name
                + "\n".join(map(unicode, self.entries)))
    def __str__ (self):
        return self.__unicode__().encode(locale.getpreferredencoding())


# Entry.
class _SDEntry:

    def __init__ (self, parent, pos):

        # Parent source and position in it.
        self.parent = parent
        self.pos = pos

        # Key syntagmas (SDProp).
        self.syns = []
        # Environments (SDEnv).
        self.envs = []

    def __unicode__ (self):
        return (  "  -----> %d:%d\n" % self.pos
                + "  " + "\n  ".join(map(unicode, self.syns)) + "\n"
                + "\n".join(map(unicode, self.envs)))
    def __str__ (self):
        return self.__unicode__().encode(locale.getpreferredencoding())


# Environment.
class _SDEnv:

    def __init__ (self, parent, pos, name=""):

        # Parent entry and position in source.
        self.parent = parent
        self.pos = pos
        # Environment name.
        self.name = name

        # Properties (SDProp).
        self.props = []

    def __unicode__ (self):
        return (  "    @%s:%d:%d\n" % ((self.name,) + self.pos)
                + "\n".join(map(unicode, self.props)))
    def __str__ (self):
        return self.__unicode__().encode(locale.getpreferredencoding())


# Syntagma.
class _SDSyn:

    def __init__ (self, parent, pos, hidden=False):

        # Parent entry and position in source.
        self.parent = parent
        self.pos = pos
        # Visibility of the syntagma.
        self.hidden = hidden

        # Syntagma segments (SDText, SDTag).
        self.segs = []

    def __unicode__ (self):
        return (  "{p:%d:%d|%s}=" % (self.pos + (self.hidden,))
                + u"".join(map(unicode, self.segs)))
    def __str__ (self):
        return self.__unicode__().encode(locale.getpreferredencoding())


# Property.
class _SDProp:

    def __init__ (self, parent, pos):

        # Parent environment and position in source.
        self.parent = parent
        self.pos = pos

        # Keys (SDKey).
        self.keys = []
        # Value segments (SDText, SDExp, SDTag).
        self.segs = []

    def __unicode__ (self):
        return (  "      %d:%d " % self.pos
                + "k=" + u"".join(map(unicode, self.keys)) + " "
                + "v=" + u"".join(map(unicode, self.segs)))
    def __str__ (self):
        return self.__unicode__().encode(locale.getpreferredencoding())


# Property key.
class _SDKey:

    def __init__ (self, parent, pos, name="", cut=False, terminal=False):

        # Parent property and position in source.
        self.parent = parent
        self.pos = pos
        # Key name, cutting and terminal behaviors.
        self.name = name
        self.cut = cut
        self.terminal = terminal

    def __unicode__ (self):
        return "{k:%d:%d:%s|%s&%s}" % (self.pos + (self.name,
                                                   self.cut, self.terminal))
    def __str__ (self):
        return self.__unicode__().encode(locale.getpreferredencoding())


# Expander.
class _SDExp:

    def __init__ (self, parent, pos, ref=None, mask=None, caps=None, kext=None):

        # Parent property and position in source.
        self.parent = parent
        self.pos = pos
        # Reference, selection mask, capitalization, key extender.
        self.ref = ref
        self.mask = mask
        self.caps = caps
        self.kext = kext

    def __unicode__ (self):
        return u"{e:%d:%d:%s|%s|%s|%s}" % (self.pos + (self.ref, self.mask,
                                                       self.caps, self.kext))
    def __str__ (self):
        return self.__unicode__().encode(locale.getpreferredencoding())


# Tag.
class _SDTag:

    def __init__ (self, parent, pos):

        # Parent property and position in source.
        self.parent = parent
        self.pos = pos
        # Names associated to this tag.
        self.names = []

    def __unicode__ (self):
        return u"{g:%d:%d:%s}" % (self.pos + ("+".join(self.names),))
    def __str__ (self):
        return self.__unicode__().encode(locale.getpreferredencoding())


# Text segment.
class _SDText:

    def __init__ (self, parent, pos, text=""):

        # Parent property and position in source.
        self.parent = parent
        self.pos = pos
        # Text.
        self.text = text

    def __unicode__ (self):
        return "{t:%d:%d:%s}" % (self.pos + (self.text,))
    def __str__ (self):
        return self.__unicode__().encode(locale.getpreferredencoding())


# ----------------------------------------
# High level access.

class Synder (object):
    """
    FIXME: Write doc.
    """

    def __init__ (self,
                  env="",
                  pkeysep="-", envsep=":", inenvsep=".",
                  ekeytf=None, ekeyitf=None,
                  pkeytf=None, pkeyitf=None,
                  pvaltf=None,
                  esyntf=None,
                  mvaltf=None):
        """
        FIXME: Write doc.
        """

        self._env = self._normenv(env)

        self._envsep = envsep
        self._inenvsep = inenvsep
        self._pkeysep = pkeysep

        self._ekeytf = ekeytf
        self._ekeyitf = ekeyitf
        self._pkeytf = pkeytf
        self._pkeyitf = pkeyitf
        self._pvaltf = pvaltf
        self._esyntf = esyntf
        self._mvaltf = mvaltf

        self._imported_srcnames = set()
        self._entry_by_srcname_iekey = {}
        self._visible_entry_by_ekey = {}
        self._derivation_by_entry_env1 = {}
        self._raw_derivation_by_entry_env1 = {}


    def _normenv (self, env):

        if isinstance(env, (tuple, list)):
            if not env or not isinstance(env[0], (tuple, list)):
                env = (tuple(env),)
            else:
                env = tuple(map(tuple, env))
        else:
            env = ((env,),)

        return env


    def import_string (self, string):
        """
        FIXME: Write doc.
        """

        source = _parse_string(string)

        return self._process_import(source, visible=True)


    def import_file (self, filename):
        """
        FIXME: Write doc.
        """

        source = _parse_file(filename)

        return self._process_import(source, visible=True)


    def _process_import (self, source, visible):

        if source.name in self._imported_srcnames:
            return 0

        self._imported_srcnames.add(source.name)

        vemap = self._visible_entry_by_ekey
        iemap = {}
        self._entry_by_srcname_iekey[source.name] = iemap

        # Construct wrapping entries and file them by entry keys.
        nadded = 0
        for rawentry in source.entries:

            # Create wrapper entry for the raw entry.
            entry = self._Entry(rawentry, self._ekeyitf)

            # Eliminate key conflicts of this entry to existing entries.
            # Conflicts are checked by internal keys in the current source,
            # and by external keys in all visible sources if source is visible.
            self._eliminate_conflicts(entry, iemap, lambda x: x.iekeys)
            if visible:
                self._eliminate_conflicts(entry, vemap, lambda x: x.ekeys)

            # Register entry in this source by keys.
            if entry.ekeys:
                for iekey in entry.iekeys:
                    iemap[iekey] = entry
                if visible and not all([x.hidden for x in entry.base.syns]):
                    for ekey in entry.ekeys:
                        vemap[ekey] = entry
                nadded += 1

        # Import included sources.
        for incsource in source.incsources:
            self._process_import(incsource, visible=False)

        return nadded


    class _Entry:

        def __init__ (self, entry, ekeyitf):

            self.base = entry

            # Compute internal and external entry keys from head syntagmas.
            self.iekeys = set()
            self.ekeys = set()
            for syn in entry.syns:
                synt = "".join([x.text for x in syn.segs
                                       if isinstance(x, _SDText)])
                iekey = simplify(synt)
                self.iekeys.add(iekey)
                ekeys = ekeyitf(iekey) if ekeyitf else iekey
                if ekeys is not None:
                    if not isinstance(ekeys, (tuple, list)):
                        ekeys = [ekeys]
                    self.ekeys.update(ekeys)


    def _eliminate_conflicts (self, entry, kmap, keyf):

        to_remove_keys = set()
        to_remove_keys_other = {}
        for key in keyf(entry):
            oentry = kmap.get(key)
            if oentry is not None:
                to_remove_keys.add(key)
                if oentry not in to_remove_keys_other:
                    to_remove_keys_other[oentry] = set()
                to_remove_keys_other[oentry].add(key)

        noconfres_oentries = []
        if to_remove_keys == keyf(entry):
            noconfres_oentries.extend(to_remove_keys_other.keys())
        else:
            for oentry, keys in to_remove_keys_other.items():
                if keyf(oentry) == keys:
                    noconfres_oentries.append(oentry)

        if noconfres_oentries:
            # Clear both internal and external keys.
            entry.ekeys.clear()
            entry.iekeys.clear()
            pos1 = "%s:%d" % (entry.base.parent.name, entry.base.syns[0].pos[0])
            pos2s = ["%s:%d" % (x.base.parent.name, x.base.syns[0].pos[0])
                     for x in noconfres_oentries]
            pos2s = "\n".join(pos2s)
            warning(_p("error message",
                       "Entry at %(pos1)s eliminated due to irreconcilable "
                       "key conflict with the following entries:\n"
                       "%(pos2s)s") % locals())
        else:
            for key in to_remove_keys:
                keyf(entry).remove(key)
            for oentry, keys in to_remove_keys_other.items():
                for key in keys:
                    keyf(oentry).remove(key)
                    kmap.pop(key)


    def get2 (self, ekey, pkey, defval=None):
        """
        FIXME: Write doc.
        """

        if self._ekeytf:
            ekey = self._pkeytf(ekey)
            if ekey is None:
                return defval

        entry = self._visible_entry_by_ekey.get(ekey)
        if entry is None:
            return defval

        if self._pkeytf:
            pkey = self._pkeytf(pkey)
            if pkey is None:
                return defval

        pvals = []
        for env1 in self._env:
            pval = self._getprops(entry, env1).get(pkey)
            pvals.append(pval)

        if self._mvaltf:
            pval = self._mvaltf(pvals)
        else:
            for pval in pvals:
                if pval is not None:
                    break

        return pval if pval is not None else defval


    def _getprops (self, entry, env1):

        # Try to fetch derivation from cache.
        props = self._derivation_by_entry_env1.get((entry, env1))
        if props is not None:
            return props

        # Construct raw derivation and extract key-value pairs.
        rprops = self._derive(entry, env1)
        props = dict([(x, y[0]) for x, y in rprops.items()])

        # Internally transform keys if requested.
        if self._pkeyitf:
            nprops = []
            for pkey, pval in props.items():
                pkey = self._pkeyitf(pkey)
                if pkey is not None:
                    nprops.append((pkey, pval))
            props = dict(nprops)

        self._derivation_by_entry_env1[(entry, env1)] = props
        return props


    def _derive (self, entry, env1):

        # Try to fetch raw derivation from cache.
        dprops = self._raw_derivation_by_entry_env1.get((entry, env1))
        if dprops:
            return dprops

        # Derivator core.
        dprops = {}
        env = None
        envs_by_name = dict([(x.name, x) for x in entry.base.envs])
        for env0 in reversed(env1):
            env = envs_by_name.get(env0)
            if env is None:
                continue
            for prop in env.props:
                fsegs = []
                cprops = dict([(simplify(x.name), ([], x)) for x in prop.keys])
                ownpkeys = set(cprops.keys())
                for seg in prop.segs:
                    if isinstance(seg, _SDExp):
                        eprops = self._expand(seg, entry, env1)
                        if isinstance(eprops, dict):
                            if cprops:
                                for cpkey, csegskey in list(cprops.items()):
                                    esegskey = eprops.get(cpkey)
                                    if esegskey is not None:
                                        if not esegskey[1].cut:
                                            csegskey[0].extend(esegskey[0])
                                        else:
                                            csegskey[0][:] = esegskey[0]
                                    else:
                                        cprops.pop(cpkey)
                                        if not cprops:
                                            break
                                if not cprops:
                                    break
                            else:
                                cprops = eprops
                                for (csegs, key) in cprops.values():
                                    if not key.cut:
                                        csegs[:0] = fsegs
                        else:
                            esegs = eprops
                            if cprops:
                                for pkey, (csegs, key) in cprops.items():
                                    if not key.cut or pkey in ownpkeys:
                                        csegs.extend(esegs)
                            else:
                                fsegs.extend(esegs)
                    elif cprops:
                        for pkey, (csegs, key) in cprops.items():
                            if not key.cut or pkey in ownpkeys:
                                csegs.append(seg)
                    else:
                        fsegs.append(seg)
                dprops.update(cprops)

        # Process tags and normalize values.
        ndprops = []
        for pkey, (segs, key) in dprops.items():
            pval = self._segs_to_string(segs, pkey, self._pvaltf)
            if pval is not None:
                ndprops.append((pkey, (pval, key)))
        dprops = dict(ndprops)

        self._raw_derivation_by_entry_env1[(entry, env1)] = dprops
        return dprops


    def _expand (self, exp, entry, env1):
        # TODO: Discover circular expansion paths.

        # Fetch the entry pointed to by the expansion.
        iekey = simplify(exp.ref)
        source = entry.base.parent
        entry = self._entry_by_srcname_iekey[source.name].get(iekey)
        if entry is None:
            for isource in reversed(source.incsources):
                entry = self._entry_by_srcname_iekey[isource.name].get(iekey)
                if entry is not None:
                    break
        if entry is None:
            warning(_p("error message",
                       "Expansion '%(ref)s' does not reference a known entry "
                       "at %(file)s:%(line)s.")
                    % dict(ref=exp.ref, file=source.name, line=exp.pos[0]))
            return {}

        # Derive the referenced entry.
        props = self._derive(entry, env1)

        # Drop terminal properties.
        nprops = []
        for pkey, (pval, key) in props.items():
            if not key.terminal:
                nprops.append((pkey, (pval, key)))
        props = dict(nprops)

        # Apply expansion mask.
        if exp.mask is not None:
            # Eliminate all obtained keys not matching the mask.
            # Reduce by mask those that match.
            nprops = []
            for pkey, pvalskey in props.items():
                if len(pkey) != len(exp.mask):
                    continue
                mpkey = ""
                for c, cm in zip(pkey, exp.mask):
                    if cm != _ch_exp_mask_pl:
                        if cm != c:
                            mpkey = None
                            break
                    else:
                        mpkey += c
                if mpkey is not None:
                    nprops.append((mpkey, pvalskey))
            props = dict(nprops)

        # Apply key extension.
        if exp.kext is not None:
            nprops = []
            for pkey, (pval, key) in props.items():
                npkey = exp.kext.replace(_ch_exp_kext_pl, pkey)
                nprops.append((npkey, (pval, key)))
            props = dict(nprops)

        # Apply capitalization.
        if exp.caps is not None:
            chcaps = first_to_upper if exp.caps else first_to_lower
            nprops = {}
            for pkey, (pval, key) in props.items():
                nprops[pkey] = (chcaps(pval), key)
            props = nprops

        # Put into segs-key form.
        pkeys = props.keys()
        if len(pkeys) != 1 or pkeys[0]:
            nprops = {}
            for pkey, (pval, key) in props.items():
                nprops[pkey] = ([_SDText(None, None, pval)], key)
        else:
            nprops = [_SDText(None, None, nprops.values()[0][0])]
        props = nprops

        return props


    def _segs_to_string (self, segs, pkey, segstf):

        if segstf:
            # Add sentries.
            if not segs:
                segs = [_SDText(None, None, "")]
            if not isinstance(segs[0], _SDTag):
                segs = [_SDTag(None, None)] + segs
            if not isinstance(segs[-1], _SDText):
                segs = segs + [_SDText(None, None, "")]

            # Construct simplified segments: [([tagname...], text)]
            tsegs = []
            i = 0
            while i < len(segs):
                # Tag names for the next piece of text.
                tags = segs[i].names
                # Join contiguous text segments into single plain text.
                i += 1
                i0 = i
                while i < len(segs) and isinstance(segs[i], _SDText):
                    i += 1
                text = "".join([x.text for x in segs[i0:i]])
                # Collect simplified segment.
                tsegs.append((tags, text))

            # Process value (may return None).
            text = segstf(tsegs, pkey)

        else:
            # Collect all text segments, ignoring tags.
            text = "".join([x.text for x in segs if isinstance(x, _SDText)])

        if text is not None:
            text = simplify(text)

        return text


    def get (self, key, defval=None):
        """
        FIXME: Write doc.
        """

        # Split the serialized key into entry and property keys.
        lst = key.split(self._pkeysep, 1)
        if len(lst) < 2:
            return defval
        ekey, pkey = lst

        return self.get2(ekey, pkey, defval)


    def ekeys (self):
        """
        FIXME: Write doc.
        """

        return self._visible_entry_by_ekey.keys()


    def syns (self, ekey):
        """
        FIXME: Write doc.
        """

        if self._ekeytf:
            ekey = self._ekeytf(ekey)
        if ekey is None:
            return []
        entry = self._visible_entry_by_ekey.get(ekey)
        if entry is None:
            return []

        rsyns = []
        for syn in entry.base.syns:
            if not syn.hidden:
                rsyn = self._segs_to_string(syn.segs, None, self._esyntf)
                if rsyn is not None:
                    rsyns.append(rsyn)

        return rsyns


    def pkeys (self, ekey):
        """
        FIXME: Write doc.
        """

        if self._ekeytf:
            ekey = self._ekeytf(ekey)
        if ekey is None:
            return []
        entry = self._visible_entry_by_ekey.get(ekey)
        if entry is None:
            return []

        props = self._getprops(entry)
        for env1 in self._env:
            pkeys = set()
            for env0 in env1:
                props0 = props.get(env0)
                if props0 is not None:
                    pkeys.update(props0.keys())
            if pkeys:
                return pkeys

        return []


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


    def __contains__ (self, key):
        """
        FIXME: Write doc.
        """

        return self.get(key) is not None


    def __getitem__ (self, key):
        """
        FIXME: Write doc.
        """

        res = self.get(key)
        if res is None:
            raise KeyError, key

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


    def _make_iter (self, keyf):

        it = iter(self._visible_entry_by_ekey)
        gdat = [None, []] # ekey, pkeys
        def next ():
            while not gdat[1]:
                gdat[0] = it.next() # will raise StopIteration
                gdat[1] = self.pkeys(gdat[0])
            ekey = gdat[0]
            pkey = gdat[1].pop()
            return keyf(ekey + self._pkeysep + pkey)

        return next

