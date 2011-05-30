# -*- coding: UTF-8 -*

"""
Process ascription configurations, catalogs, and histories.

@note: For the moment, this module is only for internal use within Pology.
Interfaces may change arbitrarily between any two Pology releases.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import codecs
from ConfigParser import SafeConfigParser
import datetime
import imp
import os
import re
import time

from pology import PologyError, _, n_, t_
from pology.header import format_datetime, parse_datetime
from pology.message import Message, MessageUnsafe
from pology.comments import parse_summit_branches
from pology.diff import msg_ediff
from pology.fsops import join_ncwd
from pology.match import make_msg_fmatcher
from pology.monitored import Monlist
from pology.msgreport import warning_on_msg
from pology.report import warning
from pology.vcs import make_vcs


# -----------------------------------------------------------------------------
# Ascription data representations.

class AscConfig (object):
    """
    Representation of an ascription configuration file.

    The settings are reached through class attributes.
    Some attributes are raw data read from configuration fields,
    while other may be derived based on configuration fields.

    Parameters which have "for header updates" in their description
    are used for creating and updating ascription catalog headers,
    as well as original catalog headers when header update on commit
    is requested. They may contain a number of interpolations, see
    L{Catalog.update_header<pology.catalog.Catalog.update_header>}.

    @ivar path: the path to the ascription configuration file
    @type path: string
    @ivar catroot: the path to root directory of original catalogs
    @type catroot: string
    @ivar ascroot: the path to root directory of ascription catalogs
    @type ascroot: string
    @ivar title: the header title comment  (for header updates;
        only for original catalogs)
    @type title: string or None
    @ivar langteam: the language team name (for header updates)
    @type langteam: string or None
    @ivar teamemail: the language team email address (for header updates)
    @type teamemail: string or None
    @ivar langcode: the language code (for header updates)
    @type langcode: string or None
    @ivar plforms: the PO plural forms specification (for header updates)
    @type plforms: string or None
    @ivar vcs: the version control system for catalogs
    @type vcs: L{VcsBase<pology.vcs.VcsBase>}
    @ivar commitmsg: the automatic commit message
    @type commitmsg: string or None
    @ivar revtags: known review tags (empty string always included)
    @type revtags: set(string*)
    @ivar users: data for ascription users by username
    @type users: {string: L{AscUser}*}
    """

    def __init__ (self, cfgpath):
        """
        Constructor.

        Reads the ascription configuration file to set raw and derived
        ascription settings.

        @param cfgpath: the path to ascription configuration file
        @type cfgpath: string
        """

        config = SafeConfigParser()
        ifl = codecs.open(cfgpath, "r", "UTF-8")
        config.readfp(ifl)
        ifl.close()

        self.path = cfgpath

        gsect = dict(config.items("global"))
        cpathdir = os.path.dirname(cfgpath)
        self.catroot = join_ncwd(cpathdir, gsect.get("catalog-root", ""))
        self.ascroot = join_ncwd(cpathdir, gsect.get("ascript-root", ""))
        if self.catroot == self.ascroot:
            raise PologyError(
                _("@info",
                  "Catalog root and ascription root for '%(file)s' "
                  "resolve to same path '%(dir)s'.",
                  file=cfgpath, dir=self.catroot))

        self.title = gsect.get("title", None)
        self.langteam = gsect.get("language-team", None)
        self.teamemail = gsect.get("team-email", None)
        self.langcode = gsect.get("language", None)
        self.plforms = gsect.get("plural-header", None)

        self.vcs = make_vcs(gsect.get("version-control", "noop"))

        self.commitmsg = gsect.get("commit-message", None)

        cval = gsect.get("review-tags", None)
        if cval is not None:
            self.revtags = set(cval.split())
        else:
            self.revtags = set()
        self.revtags.add("")

        self.users = {}
        userst = "user-"
        for section in config.sections():
            if section.startswith(userst):
                user = section[len(userst):]
                usect = dict(config.items(section))
                if user in self.users:
                    raise PologyError(
                        _("@info",
                          "Repeated user '%(user)s' in '%(file)s'.",
                          user=user, file=cpath))
                if "name" not in usect:
                    raise PologyError(
                        _("@info",
                          "The name is missing for "
                          "user '%(user)s' in '%(file)s'.",
                          user=user, file=cpath))
                udat = AscUser()
                udat.name = usect.get("name")
                udat.oname = usect.get("original-name")
                udat.email = usect.get("email")
                self.users[user] = udat


class AscUser (object):
    """
    Representation of an ascription user.

    @ivar name: user's name readable in English
    @type name: string or None
    @ivar oname: user's name in user's native language
    @type oname: string or None
    @ivar email: user's email address
    @type email: string or None
    """

    def __init__ (self, name=None, oname=None, email=None):
        """
        Constructor.

        See attribute documentation for details on parameters.
        """

        self.name = name
        self.oname = oname
        self.email = email


class AscPoint (object):
    """
    Representation of an ascription point.

    @ivar msg: a stripped version of the original PO message as it appeared
        when the ascription was made, containing only
        L{extraction-invariant parts<message.Message_base.inv>}
    @type msg: L{MessageUnsafe<message.MessageUnsafe>}
    @ivar rmsg: the message in the ascription catalog from which
        C{msg} was parsed
    @type rmsg: L{MessageUnsafe<message.MessageUnsafe>}
    @ivar user: the user to whom the ascription was made
    @type user: string
    @ivar type: the ascription type (one of C{ATYPE_} constants)
    @type type: string
    @ivar tag: the review tag (from the set defined in ascription config)
    @type tag: string
    @ivar date: the date when the ascription was made
    @type date: datetime.datetime
    @ivar slen: the length of the separator in ascription message (C{rmsg})
    @type slen: int
    @ivar fuzz: whether the original message was fuzzy
    @type fuzz: bool
    @ivar obs: whether the original message was obsolete
    @type obs: bool
    @ivar pos: the position of this ascription point within
        the ascription history (increasing from 1, 1 is the latest by date)
    @type pos: int
    """

    _known_attrs = (
        "rmsg", "msg",
        "user", "type", ("tag", ""), "date",
        "slen", "fuzz", "obs",
        "pos"
    )

    def __init__ (self, apoint=None):
        """
        Create an empty ascription point or a shallow copy of another.

        @param apoint: an ascription point
        @type apoint: L{AscPoint}
        """

        for attr in AscPoint._known_attrs:
            if isinstance(attr, tuple):
                attr, dval = attr
            else:
                attr, dval = attr, None
            if apoint is not None:
                self.__dict__[attr] = apoint.__dict__[attr]
            else:
                self.__dict__[attr] = dval


    # Ascription types.
    # NOTE: These string are written into and read from ascription files.
    ATYPE_MOD = "modified"
    ATYPE_REV = "reviewed"


# -----------------------------------------------------------------------------
# Collecting ascription configurations and catalog paths.


def collect_ascription_associations (catpaths):
    """
    Build up ascription associations for catalog paths.

    For each catalog path, the ascription configuration to which it
    belongs is found and parsed, and the corresponding ascription
    catalog path assembled.
    The association is organized as list of two-tuples;
    the first element is the parsed ascription configuration,
    and the second element the list of two-tuples of original
    catalog paths and associated ascription catalog paths
    (whether the ascription catalog already exists or not).
    For example, if the input is::

        ["foo/alpha.po", "foo/bravo.po", "bar/november.po"]

    and the files are covered by ascription configurations at
    C{foo/ascription-config} and C{bar/ascription-config},
    the return value is::

        [(AscConfig("foo/ascription-config"),
         [("foo/alpha.po", "foo-ascript/alpha.po"),
          ("foo/bravo.po", "foo-ascript/bravo.po")]),
         (AscConfig("bar/ascription-config"),
          [("bar/november.po", "bar-ascript/november.po")])]

    (assuming that both ascription configurations set C{*-ascript/}
    directories as corresponding ascription catalog roots).

    @param catpaths: a list of catalog paths
    @type catpaths: [string*]
    @returns: the ascription association list
    @rtype: [(AscConfig, [(string, string)*])*]
    """

    aconfs_by_cfgpath = {}
    catpaths_by_cfgpath = {}
    for catpath in catpaths:
        # Look for the first config file up the directory tree.
        parent = os.path.dirname(os.path.abspath(catpath))
        cfgpath = None
        while True:
            for cfgname in ("ascription-config", "ascribe"):
                test_cfgpath = os.path.join(parent, cfgname)
                if os.path.isfile(test_cfgpath):
                    cfgpath = test_cfgpath
                    break
            if cfgpath:
                break
            pparent = parent
            parent = os.path.dirname(parent)
            if parent == pparent:
                break
        if not cfgpath:
            raise PologyError(
                _("@info",
                  "Cannot find ascription configuration for '%(file)s'.",
                  file=catpath))
        cfgpath = join_ncwd(cfgpath) # for nicer message output
        aconf = aconfs_by_cfgpath.get(cfgpath)
        if not aconf:
            # New config, load.
            aconf = AscConfig(cfgpath)
            aconfs_by_cfgpath[cfgpath] = aconf
            catpaths_by_cfgpath[cfgpath] = []
        catpaths = catpaths_by_cfgpath.get(cfgpath)

        # If this catalog is under ascription,
        # determine path to ascription catalog.
        # Ignore it otherwise.
        relcatpath = _relpath(catpath, aconf.catroot)
        if relcatpath is not None:
            acatpath = join_ncwd(aconf.ascroot, relcatpath)
            catpath = join_ncwd(catpath)
            catpaths.append((catpath, acatpath))

    # Link config objects and catalog paths.
    aconfs_catpaths = []
    for cfgpath in sorted(aconfs_by_cfgpath):
        aconfs_catpaths.append((aconfs_by_cfgpath[cfgpath],
                                catpaths_by_cfgpath[cfgpath]))

    return aconfs_catpaths


def _relpath (path, dirpath):

    absdirpath = os.path.abspath(dirpath)
    lenadpath = len(absdirpath)
    lenadpathws = lenadpath + len(os.path.sep)
    abspath = os.path.abspath(path)
    p = abspath.find(absdirpath)
    if p == 0 and abspath[lenadpath:lenadpathws] == os.path.sep:
        return abspath[lenadpathws:]
    else:
        return None


# -----------------------------------------------------------------------------
# Reading ascriptions.

# FIXME: Factor out into message module.
_id_fields = (
    "msgctxt", "msgid",
)
_nonid_fields = (
    "msgid_plural", "msgstr",
)
_fields_previous = (
    "msgctxt_previous", "msgid_previous", "msgid_plural_previous",
)
_fields_current = (
    "msgctxt", "msgid", "msgid_plural",
)
_fields_comment = (
    "manual_comment", "auto_comment",
)
_multiple_fields = (()
    + ("msgstr",)
    + _fields_comment
)
_nonid_fields_eq_nonfuzzy = (()
    + _nonid_fields
    + ("manual_comment",)
)
_nonid_fields_eq_fuzzy = (()
    + _nonid_fields_eq_nonfuzzy
    + _fields_previous
)
_translator_parts = (
    "manual_comment", "fuzzy", "msgstr",
)

# FIXME: ...but this stays here.
_nonid_fields_tracked = (()
    + _nonid_fields
    + _fields_previous
    + ("manual_comment",)
)


def collect_ascription_history (msg, acat, aconf,
                                nomrg=False, hfilter=None, shallow=False,
                                addrem=None):
    """
    Collect ascription history of a message.

    The ascription history of C{msg} is collected from
    the ascription catalog C{acat},
    falling under the ascription configuration C{aconf}.
    The ascription history is a list of L{AscPoint} objects,
    ordered from the newest to the oldest by date of ascription.

    Some ascription points may be due to merging with template,
    when the ascriptions on a catalog were made just after merging.
    In many cases of examining the history these ascriptions are not useful,
    so they can be removed by setting C{nomrg} to C{True}.

    Sometimes it may be convenient to operate on history in which
    the translations of historical messages have been filtered,
    and this filter can be specified with C{hfilter}.
    If under filter two consecutive historical messages become equal,
    one of them will be eliminated from the history.

    History normally extends in the past through merging with templates
    (think of a paragraph-length message in which only one word was changed),
    so it may contain messages with keys different from the current message
    from some point and onwards. If only the history up to the earliest
    message with equal key is desired, C{shallow} can be set to C{True}.

    Sometimes it may be convenient to operate on I{incremental} history,
    in which every historical message is actually a partial difference
    (added, removed or equal segments) from the previous historical message.
    This can be requested by setting C{addrem} to one of the values
    as described in L{msg_diff<diff.msg_diff>} function.

    @param msg: the message from the original catalog
    @type msg: L{Message_base<message.Message_base>}
    @param acat: the ascription catalog corresponding to the original catalog
    @type acat: L{Catalog<catalog.Catalog>}
    @param aconf: the ascription configuration which covers the catalogs
    @type aconf: L{AscConfig}
    @param nomrg: whether to eliminate from history pure merge ascriptions
    @type nomrg: bool
    @param hfilter: the filter to apply to C{msgstr} fields of
        historical messages
    @type hfilter: (string)->string
    @param shallow: whether to collect history only up to
        last historical message with same key
    @type shallow: bool
    @param addrem: make each historical message an incremental difference
        from the first earlier historical message; see same-name parameter
        of L{msg_diff<diff.msg_diff>} for possible values
    @type addrem: string

    @returns: the ascription history
    @rtype: [AscPoint*]
    """

    ahist = _collect_ascription_history_w(msg, acat, aconf, None, set(),
                                          shallow)

    # If the message is not ascribed,
    # add it in front as modified by unknown user.
    if not ahist or not ascription_equal(msg, ahist[0].msg):
        a = AscPoint()
        a.type = AscPoint.ATYPE_MOD
        a.user = None
        a.msg = msg
        ahist.insert(0, a)

    # Equip ascriptions with position markers,
    # to be able to see gaps possibly introduced by removals.
    pos = 1
    for a in ahist:
        a.pos = pos
        pos += 1

    # Eliminate clean merges from history.
    if nomrg:
        ahist_r = []
        for i in range(len(ahist) - 1):
            a, ao = ahist[i], ahist[i + 1]
            if (   a.type != AscPoint.ATYPE_MOD
                or not merge_modified(ao.msg, a.msg)
            ):
                ahist_r.append(a)
        ahist_r.append(ahist[-1])
        ahist = ahist_r

    # Eliminate contiguous chain of modifications equal under the filter,
    # except for the earliest in the chain.
    # (After elimination of clean merges.)
    if hfilter:
        def flt (msg):
            msg = MessageUnsafe(msg)
            msg.msgstr = map(hfilter, msg.msgstr)
            return msg
        ahist_r = []
        a_prevmod = None
        ahist.reverse()
        for a in ahist:
            if (   a.type != AscPoint.ATYPE_MOD or not a_prevmod
                or flt(a.msg).inv != a_prevmod.msg.inv
            ):
                ahist_r.append(a)
                if a.type == AscPoint.ATYPE_MOD:
                    a_prevmod = AscPoint(a)
                    a_prevmod.msg = flt(a.msg)
        ahist = ahist_r
        ahist.reverse()

    # Reduce history to particular segments of diffs between modifications.
    # (After filtering).
    if addrem:
        a_nextmod = None
        for a in ahist:
            if a.type == AscPoint.ATYPE_MOD:
                if a_nextmod is not None:
                    msg_ediff(a.msg, a_nextmod.msg, emsg=a_nextmod.msg,
                              addrem=addrem)
                a_nextmod = a

    return ahist


def _collect_ascription_history_w (msg, acat, aconf, before, seenmsg,
                                   shallow=False):

    ahist = []

    # Avoid circular paths.
    if msg.key in seenmsg:
        return ahist
    seenmsg.add(msg.key)

    # Collect history from current ascription message.
    if msg in acat:
        amsg = acat[msg]
        for a in collect_ascription_history_segment(amsg, acat, aconf):
            if not before or a.date <= before.date:
                ahist.append(a)

    if shallow:
        return ahist

    # Continue into the past by pivoting around earliest message if fuzzy.
    amsg = ahist[-1].msg if ahist else msg
    if amsg.fuzzy and amsg.msgid_previous:
        pmsg = MessageUnsafe()
        for field in _id_fields:
            setattr(pmsg, field, amsg.get(field + "_previous"))
        # All ascriptions beyond the pivot must be older than the oldest so far.
        after = ahist and ahist[-1] or before
        ct_ahist = _collect_ascription_history_w(pmsg, acat, aconf, after,
                                                 seenmsg)
        ahist.extend(ct_ahist)

    return ahist


def collect_ascription_history_segment (amsg, acat, aconf):
    """
    Collect a segment of an ascription history.

    C{amsg} is an ascription message from the ascription catalog C{acat},
    falling under the ascription configuration C{aconf},
    and it contains a part of the ascription history of some message.
    This function is used to get only that part of the ascription history.
    The ascription history segment is a list of L{AscPoint} objects,
    ordered from the newest to the oldest by date of ascription.

    @param amsg: the ascription message from the ascription catalog
    @type amsg: L{Message_base<message.Message_base>}
    @param acat: the ascription catalog
    @type acat: L{Catalog<catalog.Catalog>}
    @param aconf: the ascription configuration which covers the catalogs
    @type aconf: L{AscConfig}

    @returns: the ascription history segment
    @rtype: [AscPoint*]
    """

    ahist = []
    spos = dict([(field, [0]) for field in _nonid_fields_tracked])
    pvals = dict([(field, [[]]) for field in _nonid_fields_tracked])
    for aflds in _parse_ascription_fields(amsg, acat, aconf):
        a = AscPoint()
        a.user, a.type, a.tag, a.date, a.slen, a.fuzz, a.obs = aflds
        if a.slen: # separator existing, reconstruct the fields
            shead = _field_separator_head(a.slen)
            pmsg = MessageUnsafe()
            for field in _id_fields:
                setattr(pmsg, field, amsg.get(field))
            for field in _nonid_fields_tracked:
                amsg_seq = _get_as_sequence(amsg, field)
                pmsg_seq = []
                for i in range(len(amsg_seq)):
                    aval = amsg_seq[i]
                    pval = _amsg_step_value(aval, shead, u"\n",
                                            spos[field], pvals[field], i)
                    # ...do not break if None, has to roll all spos items
                    if pval is not None:
                        while i >= len(pmsg_seq):
                            pmsg_seq.append(u"")
                        pmsg_seq[i] = pval
                _set_from_sequence(pmsg_seq, pmsg, field)
        else:
            pmsg = MessageUnsafe(ahist[-1].msg) # must exist
        if a.fuzz:
            pmsg.flag.add(u"fuzzy")
        elif u"fuzzy" in pmsg.flag:
            pmsg.flag.remove(u"fuzzy")
        pmsg.obsolete = a.obs
        a.rmsg, a.msg = amsg, pmsg
        ahist.append(a)

    # Sort history by date and put it in reverse.
    # If several ascriptions have same time stamps, preserve their order.
    ahist_ord = zip(ahist, range(len(ahist)))
    ahist_ord.sort(key=lambda x: (x[0].date, x[1]))
    ahist_ord.reverse()
    ahist = [x[0] for x in ahist_ord]

    return ahist


def _parse_ascription_fields (amsg, acat, aconf):
    """
    Get ascriptions from given ascription message as list of tuples
    C{(user, type, tag, date, seplen, isfuzzy, isobsolete)},
    with date being a real C{datetime} object.
    """

    ascripts = []
    for cmnt in amsg.auto_comment:
        p = cmnt.find(":")
        if p < 0:
            warning_on_msg(_("@info",
                             "No type "
                             "in ascription comment '%(cmnt)s'.",
                             cmnt=cmnt), amsg, acat)
            continue
        atype = cmnt[:p].strip()
        atag = ""
        lst = atype.split(_atag_sep, 1)
        if len(lst) == 2:
            atype = lst[0].strip()
            atag = lst[1].strip()
        lst = cmnt[p+1:].split("|")
        if len(lst) < 2 or len(lst) > 3:
            warning_on_msg(_("@info",
                             "Wrong number of descriptors "
                             "in ascription comment '%(cmnt)s'.",
                             cmnt=cmnt), amsg, acat)
            continue

        auser = lst.pop(0).strip()
        if not auser:
            warning_on_msg(_("@info",
                             "Malformed user string "
                             "in ascription comment '%(cmnt)s'.",
                             cmnt=cmnt), amsg, acat)
            continue
        if auser not in aconf.users:
            warning_on_msg(_("@info",
                             "Unknown user "
                             "in ascription comment '%(cmnt)s'.",
                             cmnt=cmnt), amsg, acat)
            continue

        datestr = lst.pop(0).strip()
        try:
            date = parse_datetime(datestr)
        except:
            warning_on_msg(_("@info",
                             "Malformed date string "
                             "in ascription comment '%(cmnt)s'.",
                             cmnt=cmnt), amsg, acat)
            continue

        # States are reset only on modification ascriptions,
        # in order to keep them for the following review ascriptions.
        if atype == AscPoint.ATYPE_MOD:
            isfuzz = False
            isobs = False
        seplen = 0
        if lst:
            tmp = lst.pop(0).strip()
            if _mark_fuzz in tmp:
                isfuzz = True
                tmp = tmp.replace(_mark_fuzz, "", 1)
            if _mark_obs in tmp:
                isobs = True
                tmp = tmp.replace(_mark_obs, "", 1)
            if tmp:
                try:
                    seplen = int(tmp)
                except:
                    warning_on_msg(_("@info",
                                     "Malformed separator length "
                                     "in ascription comment '%(cmnt)s'.",
                                     cmnt=cmnt), amsg, acat)
                    continue

        ascripts.append((auser, atype, atag, date, seplen, isfuzz, isobs))

    return ascripts


def _amsg_step_value (aval, shead, stail, spos, pvals, i):

    if i >= len(spos):
        spos.extend([0] * (i - len(spos) + 1))
    if i >= len(pvals):
        pvals.extend([[] for x in range(i - len(pvals) + 1)])
    p0 = spos[i]
    p1 = aval.find(shead, p0)
    p2 = aval.find(stail, p1 + 1)
    if p2 < 0:
        p2 = len(aval)
    spos[i] = p2 + len(stail)
    mods = aval[p1 + len(shead):p2]
    if _trsep_mod_eq in mods:
        q1 = mods.find(_trsep_mod_eq) + len(_trsep_mod_eq)
        q2 = q1
        while q2 < len(mods) and mods[q2].isdigit():
            q2 += 1
        nrev = int(mods[q1:q2])
        pval = pvals[i][nrev]
    else:
        if _trsep_mod_none in mods:
            pval = None
        else:
            pval = aval[p0:p1]
    pvals[i].append(pval)
    return pval


_trsep_head = u"|"
_trsep_head_ext = u"~"
_trsep_mod_none = u"x"
_trsep_mod_eq = u"e"

def _field_separator_head (length):

    return _trsep_head + _trsep_head_ext * length


def _needed_separator_length (msg):

    goodsep = False
    seplen = 0
    while not goodsep:
        seplen += 1
        sephead = _field_separator_head(seplen)
        goodsep = True
        for field in _nonid_fields_tracked:
            values = msg.get(field)
            if values is None:
                continue
            if isinstance(values, basestring):
                values = [values]
            for value in values:
                if sephead in value:
                    goodsep = False
                    break
            if not goodsep:
                break

    return seplen


def _get_as_sequence (msg, field, asc=True):

    if not asc and not msg.fuzzy and field in _fields_previous:
        # Ignore previous fields on non-ascription messages without fuzzy flag.
        return []

    msg_seq = msg.get(field)
    if msg_seq is None:
        msg_seq = []
    elif field not in _multiple_fields:
        msg_seq = [msg_seq]
    elif field in _fields_comment:
        # Report comments as a single newline-delimited entry.
        if msg_seq:
            msg_seq = [u"\n".join(msg_seq)]

    return msg_seq


def _set_from_sequence (msg_seq, msg, field):

    if field not in _multiple_fields:
        # Single entry; set to given, or to None if no elements.
        msg_val = None
        if msg_seq:
            msg_val = msg_seq[0]
        multiple = False
    elif field in _fields_comment:
        # Comments treated as single newline-delimited entries; split.
        msg_val = []
        if msg_seq:
            msg_val = msg_seq[0].split("\n")
        multiple = True
    else:
        # Straight sequence.
        msg_val = msg_seq
        multiple = True

    if multiple and isinstance(msg, Message):
        msg_val = Monlist(msg_val)

    setattr(msg, field, msg_val)


# -----------------------------------------------------------------------------
# Writing ascriptions.


def ascribe_modification (msg, user, dt, acat, aconf):
    """
    Ascribe message modification.

    @param msg: modified message which is being ascribed
    @type msg: L{Message_base<message.Message_base>}
    @param user: user to whom the ascription is made
    @type user: string
    @param dt: the time stamp when the ascription is made
    @type dt: datetime.datetime
    @param acat: the ascription catalogs
    @type acat: L{Catalog<catalog.Catalog>}
    @param aconf: the ascription configuration
    @type aconf: L{AscConfig}
    """

    _ascribe_any(msg, user, acat, AscPoint.ATYPE_MOD, [], aconf, dt)


def ascribe_review (msg, user, dt, tags, acat, aconf):
    """
    Ascribe message review.

    @param msg: reviewed message which is being ascribed
    @type msg: L{Message_base<message.Message_base>}
    @param user: user to whom the ascription is made
    @type user: string
    @param dt: the time stamp when the ascription is made
    @type dt: datetime.datetime
    @param tags: review tags
    @type tags: [string*]
    @param acat: the ascription catalogs
    @type acat: L{Catalog<catalog.Catalog>}
    @param aconf: the ascription configuration
    @type aconf: L{AscConfig}
    """

    _ascribe_any(msg, user, acat, AscPoint.ATYPE_REV, tags, aconf, dt)


_atag_sep = u"/"
_mark_fuzz = u"f"
_mark_obs = u"o"

def _ascribe_any (msg, user, acat, atype, atags, aconf, dt=None):

    # Create or retrieve ascription message.
    if msg not in acat:
        # Copy ID elements of the original message.
        amsg = Message()
        for field in _id_fields:
            setattr(amsg, field, getattr(msg, field))
        # Append to the end of catalog.
        acat.add_last(amsg)
    else:
        # Retrieve existing ascription message.
        amsg = acat[msg]

    # Reconstruct historical messages, from first to last.
    rahist = collect_ascription_history_segment(amsg, acat, aconf)
    rahist.reverse()

    # Do any of non-ID elements differ to last historical message?
    if rahist:
        hasdiff_state = rahist[-1].msg.state() != msg.state()
        hasdiff_nonid = _has_nonid_diff(rahist[-1].msg, msg)
    else:
        hasdiff_nonid = True
        hasdiff_state = True
    hasdiff = hasdiff_nonid or hasdiff_state

    # Add ascription comment.
    modstr = user + " | " + format_datetime(dt, wsec=True)
    modstr_wsep = modstr
    if hasdiff:
        wsep = ""
        if hasdiff_nonid:
            seplen = _needed_separator_length(msg)
            wsep += str(seplen)
        if msg.obsolete:
            wsep += _mark_obs
        if msg.fuzzy:
            wsep += _mark_fuzz
        if wsep:
            modstr_wsep += " | " + wsep
    first = True
    for atag in atags or [""]:
        field = atype
        if atag != "":
            field += _atag_sep + atag
        if first:
            _asc_append_field(amsg, field, modstr_wsep)
            first = False
        else:
            _asc_append_field(amsg, field, modstr)

    # Add non-ID fields.
    if hasdiff_nonid:
        _add_nonid(amsg, msg, seplen, rahist)

    # Update state.
    if msg.fuzzy:
        amsg.flag.add(u"fuzzy")
    else:
        amsg.flag.remove(u"fuzzy")
    if msg.obsolete:
        amsg.obsolete = True
    else:
        amsg.obsolete = False


def _has_nonid_diff (pmsg, msg):

    for field in _nonid_fields_tracked:
        msg_value = msg.get(field)
        if not msg.fuzzy and field in _fields_previous:
            # Ignore previous values in messages with no fuzzy flag.
            msg_value = None
        pmsg_value = pmsg.get(field)
        if msg_value != pmsg_value:
            return True

    return False


def _add_nonid (amsg, msg, slen, rahist):

    shead = _field_separator_head(slen)
    nones = [_field_separator_head(x.slen) + _trsep_mod_none
             for x in rahist if x.slen]
    padnone = u"\n".join(nones)

    for field in _nonid_fields_tracked:

        msg_seq = _get_as_sequence(msg, field, asc=False)
        amsg_seq = _get_as_sequence(amsg, field)

        # Expand items to length in new message.
        for i in range(len(amsg_seq), len(msg_seq)):
            amsg_seq.append(padnone)

        # Add to items.
        for i in range(len(amsg_seq)):
            if i < len(msg_seq):
                nmod = 0
                i_eq = None
                for a in rahist:
                    if not a.slen: # no modification in this ascription
                        continue
                    if i_eq is None:
                        msg_seq_p = _get_as_sequence(a.msg, field)
                        if i < len(msg_seq_p) and msg_seq[i] == msg_seq_p[i]:
                            i_eq = nmod
                            # ...no break, need number of modifications.
                    nmod += 1
                if i_eq is None:
                    add = msg_seq[i] + shead
                else:
                    add = shead + _trsep_mod_eq + str(i_eq)
            else:
                add = shead + _trsep_mod_none
            if amsg_seq[i]:
                amsg_seq[i] += u"\n"
            amsg_seq[i] += add

        _set_from_sequence(amsg_seq, amsg, field)


fld_sep = ":"

def _asc_append_field (msg, field, value):

    stext = u"".join([field, fld_sep, " ", str(value)])
    msg.auto_comment.append(stext)


# -----------------------------------------------------------------------------
# Utilities for comparing and selecting ascriptions.


def ascription_equal (msg1, msg2):
    """
    Whether two messages are equal from the ascription viewpoint.

    @param msg1: first message
    @type msg1: L{Message_base<message.Message_base>}
    @param msg2: second message
    @type msg2: L{Message_base<message.Message_base>}

    @returns: C{True} if messages are equal, C{False} otherwise
    @rtype: bool
    """

    if msg1.state() != msg2.state():
        return False
    if msg1.fuzzy:
        check_fields = _nonid_fields_eq_fuzzy
    else:
        check_fields = _nonid_fields_eq_nonfuzzy
    for field in check_fields:
        if msg1.get(field) != msg2.get(field):
            return False
    return True


def merge_modified (msg1, msg2):
    """
    Whether second message may have been derived from first
    by merging with templates.

    @param msg1: first message
    @type msg1: L{Message_base<message.Message_base>}
    @param msg2: second message
    @type msg2: L{Message_base<message.Message_base>}

    @returns: C{True} if C{msg2} is derived by merging from C{msg1},
        C{False} otherwise
    @rtype: bool
    """

    # Anything can happen on merge when going from obsolete to current.
    if msg1.obsolete and not msg2.obsolete:
        return True

    # Manual comments do not change on merge.
    if msg1.manual_comment != msg2.manual_comment:
        return False

    # Current and previous original fields may have changed on merge,
    # depending on whether both messages are fuzzy, or only one, and which.
    if msg1.fuzzy == msg2.fuzzy:
        fields = msg1.fuzzy and _fields_previous or _fields_current
        for field in fields:
            if msg1.get(field) != msg2.get(field):
                return False
    else:
        fields = (msg1.fuzzy and zip(_fields_previous, _fields_current)
                              or zip(_fields_current, _fields_previous))
        for field1, field2 in fields:
            if msg1.get(field1) != msg2.get(field2):
                return False

    # Translation does not change on merge, except
    # on multiplication/reduction when plurality differs.
    if (msg1.msgid_plural is None) != (msg2.msgid_plural is None):
        if not msg1.fuzzy and not msg2.fuzzy:
            # Plurality cannot change between two non-fuzzy messages.
            return False
        if msg1.msgid_plural is not None:
            # Reduction to non-plural.
            if msg1.msgstr[0] != msg2.msgstr[0]:
                return False
        else:
            # Multiplication to plural.
            for msgstr in msg2.msgstr:
                if msgstr != msg1.msgstr[0]:
                    return False
    else:
        if msg1.msgstr != msg2.msgstr:
            return False

    return True


def first_non_fuzzy (ahist, start=0):
    """
    Find first non fuzzy message in the ascription history.

    @param ahist: the ascription history
    @type ahist: [AscPoint*]
    @param start: position in history to start searching from
    @type start: int

    @returns: index of first non-fuzzy message, or None if there is none such
    @rtype: int
    """

    for i in range(start, len(ahist)):
        hmsg = ahist[i].msg
        if hmsg and not hmsg.fuzzy:
            return i

    return None


def has_tracked_parts (msg):
    """
    Check whether the message has any parts which are tracked for ascription.

    For example, a pristine untranslated message is considered to have
    no tracked parts.

    @returns: C{True} if there are any tracked parts, C{False} otherwise
    @rtype: bool
    """

    for part in _nonid_fields_tracked:
        pval = msg.get(part)
        if part not in _multiple_fields:
            if pval is not None and part != "msgid_plural":
                return True
        else:
            if part == "msgstr":
                for pval1 in pval:
                    if pval1:
                        return True
            elif pval:
                return True

    return False


# -----------------------------------------------------------------------------
# Argument parsing for selectors.

def parse_users (userspec, aconf):
    """
    Parse ascription user specification.

    The user specification is a comma-separated list of user names.
    If the list starts with tilde (~), all users defined in
    the ascription configuration but for those listed
    will be selected (inverted selection).

    If an undefined user (according to ascription configuration) is mentioned,
    an exception is raised.

    @param userspec: the user specification
    @type userspec: string
    @param aconf: the ascription configuration
    @type aconf: L{AscConfig}

    @returns: selected user names
    @rtype: set(string*)
    """

    return _parse_fixed_set(userspec, aconf, aconf.users,
                            t_("@info",
                               "User '%(name)s' not defined in '%(file)s'."))


def parse_review_tags (tagspec, aconf):
    """
    Parse review tag specification.

    The tag specification is a comma-separated list of tags.
    If the list starts with tilde (~), all review tags defined in
    the ascription configuration but for those listed
    will be selected (inverted selection).

    If an undefined tag (according to ascription configuration) is mentioned,
    an exception is raised.

    @param tagspec: the review tag specification
    @type tagspec: string
    @param aconf: the ascription configuration
    @type aconf: L{AscConfig}

    @returns: selected review tags
    @rtype: set(string*)
    """

    tags = _parse_fixed_set(tagspec, aconf, aconf.revtags,
                            t_("@info",
                               "Review tag '%(name)s' "
                               "not defined in '%(file)s'."))
    if not tags:
        tags = set([""])

    return tags


def _parse_fixed_set (elstr, aconf, knownels, errfmt):

    if not elstr:
        return set()

    elstr = elstr.replace(" ", "")
    inverted = False
    if elstr.startswith("~"):
        inverted = True
        elstr = elstr[1:]

    els = set(elstr.split(","))
    for el in els:
        if el not in knownels:
            raise PologyError(
                errfmt.with_args(name=el, file=aconf.path).to_string())
    if inverted:
        els = set(knownels).difference(els)

    return els

# -----------------------------------------------------------------------------
# Caching for selectors.

_cache = {}

def cached_matcher (expr):
    """
    Fetch a cached message matcher for the given expression,
    for use in ascription selectors.

    When this function is called for the first time on a new expression,
    the matcher function is created and cached.
    On subsequent invocations with the same expression,
    the matcher is fetched from the cache rather than created anew.

    @param expr: the matching expression; see
        L{make_msg_matcher<match.make_msg_matcher>} for details
    @type expr: string

    @returns: the matcher function
    @rtype: (L{Message_base<message.Message_base>},
        L{Catalog<catalog.Catalog>})->bool
    """

    key = ("matcher", expr)
    if key not in _cache:
        _cache[key] = make_msg_fmatcher(expr, abort=True)

    return _cache[key]


def cached_users (userspec, aconf, utype=None):
    """
    Fetch a cached set of users for the given user specification,
    for use in ascription selectors.

    When this function is called for the first time on a new combination
    of user specification C{userspec}, ascription configuration C{aconf},
    and "user type" C{utype}, the specification is parsed and users collected.
    On subsequent invocations with the same combination,
    the user set is fetched from the cache rather than created anew.
    C{utype} is actually just an arbitrary string,
    for when you need to cache users by different categories.

    @param userspec: the user specification; see L{parse_users} for details
    @type userspec: string
    @param aconf: the ascription configuration
    @type aconf: L{AscConfig}
    @param utype: user type
    @type utype: string

    @returns: the set of users
    @rtype: set(string*)
    """

    key = ("users", userspec, aconf, utype)
    if key not in _cache:
        _cache[key] = parse_users(userspec, aconf)

    return _cache[key]


def cached_review_tags (tagspec, aconf):
    """
    Fetch a cached set of review tags for the given tag specification,
    for use in ascription selectors.

    When this function is called for the first time on a new combination
    of tag specification C{tagspec} and ascription configuration C{aconf},
    the specification is parsed and tags collected.
    On subsequent invocations with the same combination,
    the tag set is fetched from the cache rather than created anew.

    @param tagspec: the tag specification; see L{parse_review_tags} for details
    @type tagspec: string
    @param aconf: the ascription configuration
    @type aconf: L{AscConfig}

    @returns: the set of tags
    @rtype: set(string*)
    """

    key = ("tags", tagspec, aconf)
    if key not in _cache:
        _cache[key] = parse_review_tags(tagspec, aconf)

    return _cache[key]


# -----------------------------------------------------------------------------
# Making selectors.

# Build compound selector out of list of specifications.
# Selector specification is a string in format NAME:ARG1:ARG2:...
# (instead of colon, separator can be any non-alphanumeric excluding
# underscore and hyphen)
def make_ascription_selector (selspecs, hist=False):
    """
    Build compound ascription selector out of string specifications
    of basic selectors.

    Selector specification string has the format NAME:ARG1:ARG2:...
    Instead of colon, separator can be any non-alphanumeric character
    used consistently, except for underscore and hyphen.
    The compound selector is obtained by constructing each
    basic selector according to the specification in turn,
    and linking them with AND-boolean semantics.

    Parameter C{hist} determines whether the compound selector should
    be a shallow selector (C{True}) or a history selector (C{False}).
    If a history selector is required but cannot be made from
    the given composition of basic selectors, an exception is raised.

    @param selspecs: specifications of basic selectors
    @type selspecs: [string*]
    @param hist: C{True} if the compound selector should be history selector,
        C{False} if it should be shallow selector
    @type hist: bool

    @returns: the compound selector
    @rtype: (L{Message_base<message.Message_base>}, L{Catalog<catalog.Catalog>},
        [AscPoint*], L{AscConfig})->bool (shallow),
        (...)->int/None (history)
    """

    # Component selectors.
    selectors = []
    for selspec in selspecs:
        argsep = ":"
        for c in selspec:
            if not (c.isalpha() or c.isdigit() or c in ("_", "-")):
                argsep = c
                break
        lst = selspec.split(argsep)
        sname, sargs = lst[0], lst[1:]
        negated = False
        if sname.startswith("n"):
            sname = sname[1:]
            negated = True
        sfactory, can_hist = _selector_factories.get(sname, (None, False))
        if not sfactory:
            raise PologyError(
                _("@info",
                  "Unknown selector '%(sel)s'.",
                  sel=sname))
        if hist:
            if not can_hist:
                raise PologyError(
                    _("@info",
                      "Selector '%(sel)s' cannot be used "
                      "as history selector.",
                      sel=sname))
            if negated:
                raise PologyError(
                    _("@info",
                      "Negated selectors (here '%(sel)s') cannot be used "
                      "as history selectors.",
                      sel=sname))
        try:
            selector = sfactory(sargs)
        except PologyError, e:
            raise PologyError(
                _("@info",
                  "Selector '%(sel)s' not created due to "
                  "the following error:\n"
                  "%(msg)s",
                  sel=selspec, msg=unicode(e)))
        if negated:
            selector = _negate_selector(selector)
        selectors.append((selector, selspec))

    # Compound selector.
    if hist:
        res0 = None
    else:
        res0 = False
    def cselector (msg, cat, ahist, aconf):
        res = res0
        for selector, selspec in selectors:
            try:
                res = selector(msg, cat, ahist, aconf)
            except PologyError, e:
                raise PologyError(
                    _("@info",
                      "Selector '%(sel)s' failed on message "
                      "%(file)s:%(line)d:(#%(entry)d) "
                      "with the following error:\n"
                      "%(msg)s",
                      sel=selspec, file=cat.filename, line=msg.refline,
                      entry=msg.refentry, msg=unicode(e)))
            if not res:
                return res
        return res

    return cselector


def _negate_selector (selector):

    def negative_selector (*args):
        return not selector(*args)

    return negative_selector


_external_mods = {}

def import_ascription_extensions (modpath):
    """
    Import extensions to ascription functionality from a Python module.

    Additional selector factories can be introduced by defining
    the C{asc_selector_factories} dictionary,
    in which the key is the selector name,
    and the value a tuple of the selector factory function
    and the indicator of whether the selector can be used as
    a history selector or not.
    For example::

        asc_selector_factories = {
            # key: (function, can_be_used_as_history_selector),
            "specsel1": (selector_specsel1, True),
            "specsel2": (selector_specsel2, False),
            ...
        }

    @param modpath: path to Python file
    @type modpath: string
    """

    # Load external module.
    try:
        modfile = open(modpath)
    except IOError:
        raise PologyError(
            _("@info",
              "Cannot load external module '%(file)s'.",
              file=modpath))
    # Load file into new module.
    modname = "mod" + str(len(_external_mods))
    xmod = imp.new_module(modname)
    exec modfile in xmod.__dict__
    modfile.close()
    _external_mods[modname] = xmod # to avoid garbage collection

    # Collect everything collectable from the module.

    xms = []

    xms.append("asc_selector_factories")
    selector_factories = getattr(xmod, xms[-1], None)
    if selector_factories is not None:
        _selector_factories.update(selector_factories)

    # Warn of unknown externals.
    known_xms = set(xms)
    for xm in filter(lambda x: x.startswith("asc_"), dir(xmod)):
        if xm not in known_xms:
            warning(_("@info",
                      "Unknown external resource '%(res)s' "
                      "in module '%(file)s'.",
                      res=xm, file=modpath))


# Registry of basic selector factories.
_selector_factories = {
    # key: (function, can_be_used_as_history_selector),
}

# -----------------------------------------------------------------------------
# Internal selector factories.
# Use make_ascription_selector() to create selectors.

# NOTE:
# Plain selectors should return True or False.
# History selectors should return 1-based index into ascription history
# when the appropriate historical message is found, and 0 otherwise.
# In this way, when it is only necessary to test if a message is selected,
# returns from both types of selectors can be tested for simple falsity/truth,
# and non-zero integer return always indicates history selection.

def _selector_any (args):

    if len(args) != 0:
        raise PologyError(_("@info", "Wrong number of arguments."))

    def selector (msg, cat, ahist, aconf):

        return True

    return selector

_selector_factories["any"] = (_selector_any, False)


def _selector_active (args):

    if len(args) != 0:
        raise PologyError(_("@info", "Wrong number of arguments."))

    def selector (msg, cat, ahist, aconf):

        return msg.translated and not msg.obsolete

    return selector

_selector_factories["active"] = (_selector_active, False)


def _selector_current (args):

    if len(args) != 0:
        raise PologyError(_("@info", "Wrong number of arguments."))

    def selector (msg, cat, ahist, aconf):

        return not msg.obsolete

    return selector

_selector_factories["current"] = (_selector_current, False)


def _selector_branch (args):

    if len(args) != 1:
        raise PologyError(_("@info", "Wrong number of arguments."))
    branch = args[0]
    if not branch:
        raise PologyError(_("@info", "Branch ID must not be empty."))
    branches = set(branch.split(","))

    def selector (msg, cat, ahist, aconf):

        return bool(branches.intersection(parse_summit_branches(msg)))

    return selector

_selector_factories["branch"] = (_selector_branch, False)


def _selector_unasc (args):

    if len(args) != 0:
        raise PologyError(_("@info", "Wrong number of arguments."))

    def selector (msg, cat, ahist, aconf):

        # Do not consider pristine messages as unascribed.
        return ahist[0].user is None and has_tracked_parts(msg)

    return selector

_selector_factories["unasc"] = (_selector_unasc, False)


def _selector_fexpr (args):

    if len(args) != 1:
        raise PologyError(_("@info", "Wrong number of arguments."))
    expr = args[0]
    if not expr:
        raise PologyError(_("@info", "Match expression must not be empty."))

    def selector (msg, cat, ahist, aconf):

        matcher = cached_matcher(expr)
        return bool(matcher(msg, cat))

    return selector

_selector_factories["fexpr"] = (_selector_fexpr, False)


def _selector_e (args):

    if len(args) != 1:
        raise PologyError(_("@info", "Wrong number of arguments."))
    entry = args[0]
    if not entry or not entry.isdigit():
        raise PologyError(
            _("@info",
              "Message entry number must be a positive integer."))
    refentry = int(entry)

    def selector (msg, cat, ahist, aconf):

        return msg.refentry == refentry

    return selector

_selector_factories["e"] = (_selector_e, False)


def _selector_l (args):

    if len(args) != 1:
        raise PologyError(_("@info", "Wrong number of arguments."))
    line = args[0]
    if not line or not line.isdigit():
        raise PologyError(
            _("@info",
              "Message line number must be a positive integer."))
    refline = int(line)

    def selector (msg, cat, ahist, aconf):

        return abs(msg.refline - refline) <= 1

    return selector

_selector_factories["l"] = (_selector_l, False)


# Select messages between and including first and last reference by entry.
# If first entry is not given, all messages to the last entry are selected.
# If last entry is not given, all messages from the first entry are selected.
def _selector_espan (args):

    if not 1 <= len(args) <= 2:
        raise PologyError(_("@info", "Wrong number of arguments."))
    first = args[0]
    last = args[1] if len(args) > 1 else ""
    if not first and not last:
        raise PologyError(
            _("@info",
              "At least one of the first and last message entry numbers "
              "must be given."))
    if first and not first.isdigit():
        raise PologyError(
            _("@info",
              "First message entry number must be a positive integer."))
    if last and not last.isdigit():
        raise PologyError(
            _("@info",
              "Last message entry number must be a positive integer."))
    first_entry = (first and [int(first)] or [None])[0]
    last_entry = (last and [int(last)] or [None])[0]

    def selector (msg, cat, ahist, aconf):

        if first_entry is not None and msg.refentry < first_entry:
            return False
        if last_entry is not None and msg.refentry > last_entry:
            return False
        return True

    return selector

_selector_factories["espan"] = (_selector_espan, False)


# Select messages between and including first and last reference by line.
# If first line is not given, all messages to the last line are selected.
# If last line is not given, all messages from the first line are selected.
def _selector_lspan (args):

    if not 1 <= len(args) <= 2:
        raise PologyError(_("@info", "Wrong number of arguments."))
    first = args[0]
    last = args[1] if len(args) > 1 else ""
    if not first and not last:
        raise PologyError(
            _("@info",
              "At least one of the first and last message line numbers "
              "must be given."))
    if first and not first.isdigit():
        raise PologyError(
            _("@info",
              "First message line number must be a positive integer."))
    if last and not last.isdigit():
        raise PologyError(
            _("@info",
              "Last message line number must be a positive integer."))
    first_line = (first and [int(first)] or [None])[0]
    last_line = (last and [int(last)] or [None])[0]

    def selector (msg, cat, ahist, aconf):

        if first_line is not None and msg.refline < first_line:
            return False
        if last_line is not None and msg.refline > last_line:
            return False
        return True

    return selector

_selector_factories["lspan"] = (_selector_lspan, False)


def _selector_hexpr (args):

    if not 1 <= len(args) <= 3:
        raise PologyError(_("@info", "Wrong number of arguments."))
    expr = args[0]
    user_spec = args[1] if len(args) > 1 else ""
    addrem = args[2] if len(args) > 2 else ""
    if not expr:
        raise PologyError(
            _("@info",
              "Match expression cannot be empty."))

    def selector (msg, cat, ahist, aconf):

        if ahist[0].user is None:
            return 0

        matcher = cached_matcher(expr)
        users = cached_users(user_spec, aconf)

        if not addrem:
            i = 0
        else:
            i = first_non_fuzzy(ahist, 0)
            if i is None:
                return 0

        while i < len(ahist):
            a = ahist[i]
            if users and a.user not in users:
                i += 1
                continue

            if not addrem:
                amsg = a.msg
                i_next = i + 1
            else:
                i_next = first_non_fuzzy(ahist, i + 1)
                if i_next is not None:
                    amsg2 = ahist[i_next].msg
                else:
                    amsg2 = MessageUnsafe(a.msg)
                    for field in _nonid_fields_tracked:
                        amsg2_value = amsg2.get(field)
                        if amsg2_value is None:
                            pass
                        elif isinstance(amsg2_value, basestring):
                            setattr(amsg2, field, None)
                        else:
                            amsg2_value = [u""] * len(amsg2_value)
                    i_next = len(ahist)
                amsg = MessageUnsafe(a.msg)
                msg_ediff(amsg2, amsg, emsg=amsg, addrem=addrem)

            if matcher(amsg, cat):
                return i + 1

            i = i_next

        return 0

    return selector

_selector_factories["hexpr"] = (_selector_hexpr, True)


# Select last ascription (any, or by users).
def _selector_asc (args):

    if not 0 <= len(args) <= 1:
        raise PologyError(_("@info", "Wrong number of arguments."))
    user_spec = args[0] if len(args) > 0 else ""

    def selector (msg, cat, ahist, aconf):

        if ahist[0].user is None:
            return 0

        users = cached_users(user_spec, aconf)

        hi_sel = 0
        for i in range(len(ahist)):
            a = ahist[i]
            if not users or a.user in users:
                hi_sel = i + 1
                break

        return hi_sel

    return selector

_selector_factories["asc"] = (_selector_asc, True)


# Select last modification (any or by users).
def _selector_mod (args):

    if not 0 <= len(args) <= 1:
        raise PologyError(_("@info", "Wrong number of arguments."))
    user_spec = args[0] if len(args) > 0 else ""

    def selector (msg, cat, ahist, aconf):

        if ahist[0].user is None:
            return 0

        users = cached_users(user_spec, aconf)

        hi_sel = 0
        for i in range(len(ahist)):
            a = ahist[i]
            if not a.user:
                continue
            if a.type == AscPoint.ATYPE_MOD and (not users or a.user in users):
                hi_sel = i + 1
                break

        return hi_sel

    return selector

_selector_factories["mod"] = (_selector_mod, True)


# Select first modification (any or by m-users, and not by r-users)
# after last review (any or by r-users, and not by m-users).
def _selector_modar (args):

    return _w_selector_modax(False, True, args, 3)

_selector_factories["modar"] = (_selector_modar, True)


# Select first modification (any or by m-users, and not by mm-users)
# after last modification (any or by mm-users, and not by m-users).
def _selector_modam (args):

    return _w_selector_modax(True, False, args, 2)

_selector_factories["modam"] = (_selector_modam, True)


# Select first modification (any or by m-users, and not by rm-users)
# after last review or modification (any or by m-users, and not by rm-users).
def _selector_modarm (args):

    return _w_selector_modax(True, True, args, 3)

_selector_factories["modarm"] = (_selector_modarm, True)


# Select first modification of translation
# (any or by m-users, and not by r-users)
# after last review (any or by r-users, and not by m-users).
def _selector_tmodar (args):

    return _w_selector_modax(False, True, args, 3, True)

_selector_factories["tmodar"] = (_selector_tmodar, True)


# Worker for builders of *moda* selectors.
def _w_selector_modax (amod, arev, args, maxnarg, tronly=False):

    if not 0 <= len(args) <= maxnarg:
        raise PologyError(_("@info", "Wrong number of arguments."))
    muser_spec = args[0] if len(args) > 0 else ""
    rmuser_spec = args[1] if len(args) > 1 else ""
    atag_spec = args[2] if len(args) > 2 else ""

    def selector (msg, cat, ahist, aconf):

        if ahist[0].user is None:
            return 0

        musers = cached_users(muser_spec, aconf, utype="m")
        rmusers = cached_users(rmuser_spec, aconf, utype="rm")
        atags = cached_review_tags(atag_spec, aconf)

        hi_sel = 0
        for i in range(len(ahist)):
            a = ahist[i]

            # Check if this message cancels further modifications.
            if (    (   (amod and a.type == AscPoint.ATYPE_MOD)
                     or (arev and a.type == AscPoint.ATYPE_REV and a.tag in atags))
                and (not rmusers or a.user in rmusers)
                and (not musers or a.user not in musers)
            ):
                break

            # Check if this message is admissible modification.
            if (    a.type == AscPoint.ATYPE_MOD
                and (not musers or a.user in musers)
                and (not rmusers or a.user not in rmusers)
            ):
                # Cannot be a candidate if in translation-only mode and
                # there is no difference in translation to earlier message.
                ae = ahist[i + 1] if i + 1 < len(ahist) else None
                if not (tronly and ae and ae.msg.msgstr == a.msg.msgstr):
                    hi_sel = i + 1

        return hi_sel

    return selector


# Select last review (any or by users).
def _selector_rev (args):

    if not 0 <= len(args) <= 2:
        raise PologyError(_("@info", "Wrong number of arguments."))
    user_spec = args[0] if len(args) > 0 else ""
    atag_spec = args[1] if len(args) > 1 else ""

    def selector (msg, cat, ahist, aconf):

        if ahist[0].user is None:
            return 0

        users = cached_users(user_spec, aconf)
        atags = cached_review_tags(atag_spec, aconf)

        hi_sel = 0
        for i in range(len(ahist)):
            a = ahist[i]
            if (    a.type == AscPoint.ATYPE_REV and a.tag in atags
                and (not users or a.user in users)
            ):
                hi_sel = i + 1
                break

        return hi_sel

    return selector

_selector_factories["rev"] = (_selector_rev, True)


# Select first review (any or by r-users, and not by m-users)
# before last modification (any or by m-users, and not by r-users).
def _selector_revbm (args):

    if not 0 <= len(args) <= 3:
        raise PologyError(_("@info", "Wrong number of arguments."))
    ruser_spec = args[0] if len(args) > 0 else ""
    muser_spec = args[1] if len(args) > 1 else ""
    atag_spec = args[2] if len(args) > 2 else ""

    def selector (msg, cat, ahist, aconf):

        if ahist[0].user is None:
            return 0

        rusers = cached_users(ruser_spec, aconf, utype="r")
        musers = cached_users(muser_spec, aconf, utype="m")
        atags = cached_review_tags(atag_spec, aconf)

        hi_sel = 0
        can_select = False
        for i in range(len(ahist)):
            a = ahist[i]
            if (     a.type == AscPoint.ATYPE_MOD
                and (not musers or a.user in musers)
                and (not rusers or a.user not in rusers)
            ):
                # Modification found, enable selection of review.
                can_select = True
            if (    a.type == AscPoint.ATYPE_REV and a.tag in atags
                and (not rusers or a.user in rusers)
                and (not musers or a.user not in musers)
            ):
                # Review found, select it if enabled, and stop anyway.
                if can_select:
                    hi_sel = i + 1
                break

        return hi_sel

    return selector

_selector_factories["revbm"] = (_selector_revbm, True)


# Select first modification (any or by users) at or after given time.
def _selector_modafter (args):

    if not 0 <= len(args) <= 2:
        raise PologyError(_("@info", "Wrong number of arguments."))
    time_spec = args[0] if len(args) > 0 else ""
    user_spec = args[1] if len(args) > 1 else ""
    if not time_spec:
        raise PologyError(
            _("@info",
              "Time specification cannot be empty."))

    date = parse_datetime(time_spec)

    def selector (msg, cat, ahist, aconf):

        if ahist[0].user is None:
            return 0

        users = cached_users(user_spec, aconf)

        hi_sel = 0
        for i in range(len(ahist) - 1, -1, -1):
            a = ahist[i]
            if (    a.type == AscPoint.ATYPE_MOD
                and (not users or a.user in users)
                and a.date >= date
            ):
                hi_sel = i + 1
                break

        return hi_sel

    return selector

_selector_factories["modafter"] = (_selector_modafter, True)

