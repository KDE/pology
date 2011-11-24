# -*- coding: UTF-8 -*-

"""
Common functionality for poediff and poepatch scripts.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3

@warning: Non-public module.
"""

import os
import time

from pology import PologyError, _
from pology.catalog import Catalog
import pology.config as pology_config
from pology.diff import msg_ediff, tdiff
from pology.merge import merge_pofile
from pology.message import MessageUnsafe


def _raise_no_inst (clssname):

    raise PologyError(
        _("@info",
          "Class '%(clss)s' only provides static attributes, "
          "objects of this type cannot be constructed.",
          clss=clssname))


# FIXME: Define message part categories in message module.
# Message part categories.
class MPC:
    curr_fields = [
        "msgctxt", "msgid", "msgid_plural",
    ]
    prev_fields = [x + "_previous" for x in curr_fields]
    currprev_fields = zip(curr_fields, prev_fields)
    prevcurr_fields = zip(prev_fields, curr_fields)

    def __init__ (self):
        _raise_no_inst(self.__class__.__name__)


# Syntax tokens in embedded diff catalogs.
class EDST:
    hmsgctxt_field = u"X-Ediff-Header-Context" # by spec
    hmsgctxt_el = u"~" # by spec
    filerev_sep = u" <<< " # by spec

    def __init__ (self):
        _raise_no_inst(self.__class__.__name__)


def msg_eq_fields (m1, m2, fields):

    if (m1 is None) != (m2 is None):
        return False
    elif m1 is None and m2 is None:
        return True

    for field in fields:
        if not isinstance(field, tuple):
            field = (field, field)
        if m1.get(field[0]) != m2.get(field[1]):
            return False

    return True


def msg_copy_fields (m1, m2, fields):

    if m1 is None:
        m1 = MessageUnsafe()

    for field in fields:
        if not isinstance(field, tuple):
            field = (field, field)
        setattr(m2, field[1], m1.get(field[0]))


def msg_clear_prev_fields (m):

    for field in MPC.prev_fields:
        setattr(m, field, None)


# Remove previous fields if inconsistent with the message in total.
def msg_cleanup (msg):

    # Non-fuzzy messages should have no previous fields.
    # msgid_previous must be present, or there must be no previous fields.
    if not msg.fuzzy or msg.msgid_previous is None:
        for field in MPC.prev_fields:
            if msg.get(field) is not None:
                setattr(msg, field, None)

def diff_cats (cat1, cat2, ecat,
               merge=True, colorize=False, wrem=True, wadd=True, noobs=False):

    dpairs = _pair_msgs(cat1, cat2, merge, wrem, wadd, noobs)

    # Order pairings such that they follow order of messages in
    # the new catalog wherever the new message exists.
    # For unpaired old messages, do heuristic analysis of any
    # renamings of source files, and then insert diffed messages
    # according to source references of old messages.
    dpairs_by2 = [x for x in dpairs if x[1]]
    dpairs_by2.sort(key=lambda x: x[1].refentry)
    dpairs_by1 = [x for x in dpairs if not x[1]]
    fnsyn = None
    if dpairs_by1:
        fnsyn = cat2.detect_renamed_sources(cat1)

    # Make the diffs.
    # Must not add diffed messages directly to global ediff catalog,
    # because then heuristic insertion would throw them all over.
    # Instead add to local ediff catalog, then copy in order to global.
    ndiffed = 0
    lecat = Catalog("", create=True, monitored=False)
    for cdpairs, cfnsyn in ((dpairs_by2, None), (dpairs_by1, fnsyn)):
        for msg1, msg2 in cdpairs:
            ndiffed += _add_msg_diff(msg1, msg2, lecat, colorize, cfnsyn)
    for emsg in lecat:
        ecat.add(emsg, len(ecat))

    return ndiffed


def cats_update_effort (cat1, cat2, merge=True):

    dpairs = _pair_msgs(cat1, cat2, merge, wrem=False, wadd=True, noobs=False)

    nntw_total = 0

    for msg1, msg2 in dpairs:

        if not msg2.active:
            continue
        if msg1 is None:
            msg1 = MessageUnsafe()

        # The update effort of the given old-new message pair is equal
        # to "nominal number of newly translated words" (NNTW),
        # which is defined as follows:
        # - nominal length of a word in msgid is set to 6 characters (WL).
        # - number of characters in new msgid is divided by WL
        #   to give nominal number of words in new msgid (NWO)
        # - number of equal characters in old and new msgid is divided by WL
        #   to give nominal number of equal words in msgid (NEWO)
        # - number of characters in new msgstr is divided by number of
        #   characters in new msgid to give translation expansion factor (EF)
        # - number of equal characters in old and new msgstr is divided
        #   by WL*EF to give nominal number of equal words in msgstr (NEWT)
        # - character-based similarity ratio of old and new msgid
        #   (from 0.0 for no similarity to 1.0 for equality) is computed (SRO)
        # - character-based similarity ratio of old and new msgstr
        #   is computed (SRT)
        # - similarity ratio threshold is set to 0.5 (SRB)
        # - reduction due to similiarity factor is computed as
        #   RSF = (min(SRO, SRT) - SRB) / (1 - SRB)
        # - nominal number of newly translated words is computed as
        #   NNTW = min(NWO - max(NEWO, NEWT) * RSF, NWO)
        #
        # Only those pairs where the new message is active are counted in.
        #
        # On plural messages, for the moment only msgid and msgstr[0]
        # are considered, and the above procedured applied to them.
        # This underestimates the effort of updating a new plural message
        # when old message was ordinary.

        wl = 6.0
        nwo = len(msg2.msgid) / wl
        diffo, dro = tdiff(msg1.msgid, msg2.msgid, diffr=True)
        newo = len([c for t, c in diffo if t == " "]) / wl
        ef = float(len(msg2.msgstr[0])) / len(msg2.msgid)
        difft, drt = tdiff(msg1.msgstr[0], msg2.msgstr[0], diffr=True)
        newt = len([c for t, c in difft if t == " "]) / (wl * ef)
        sro = 1.0 - dro
        srt = 1.0 - drt
        srb = 0.5
        rsf = (min(sro, srt) - srb) / (1.0 - srb)
        nntw = max(min(nwo - max(newo, newt) * rsf, nwo), 0.0)
        nntw_total += nntw

    return nntw_total


def _calc_text_update_effort (text1, text2):

    dr1 = 0.5
    ediff, dr = word_ediff(text1, text2, markup=True, diffr=True)



def _pair_msgs (cat1, cat2,
                merge=True, wrem=True, wadd=True, noobs=False):

    # Remove obsolete messages if they are not to be diffed.
    if noobs:
        for cat in (cat1, cat2):
            _rmobs_no_sync(cat)

    # Clean up inconsistencies in messages.
    for cat in (cat1, cat2):
        for msg in cat:
            msg_cleanup(msg)

    # Delay inverting of catalogs until necessary.
    def icat_w (cat, icat_pack):
        if icat_pack[0] is None:
            #print "===> inverting: %s" % cat.filename
            icat = Catalog("", create=True, monitored=False)
            for msg in cat:
                imsg = _msg_invert_cp(msg)
                if imsg not in icat:
                    icat.add_last(imsg)
            icat_pack[0] = icat
        return icat_pack[0]

    icat1_pack = [None]
    icat1 = lambda: icat_w(cat1, icat1_pack)

    icat2_pack = [None]
    icat2 = lambda: icat_w(cat2, icat2_pack)

    # Delay merging of catalogs until necessary.
    def mcat_w (cat1, cat2, mcat_pack):
        if mcat_pack[0] is None:
            #print "===> merging: %s -> %s" % (cat1.filename, cat2.filename)
            # Merge is done if requested and both catalogs exist.
            if merge and not cat1.created() and not cat2.created():
                mcat_pack[0] = merge_pofile(cat1.filename, cat2.filename,
                                            getcat=True, monitored=False,
                                            quiet=True, abort=True)
                if noobs:
                    _rmobs_no_sync(mcat_pack[0])
            else:
                mcat_pack[0] = {} # only tested for membership
        return mcat_pack[0]

    mcat12_pack = [None]
    mcat12 = lambda: mcat_w(cat1, cat2, mcat12_pack)

    mcat21_pack = [None]
    mcat21 = lambda: mcat_w(cat2, cat1, mcat21_pack)

    # Pair messages:
    # - first try to find an old message for each new
    # - then try to find a new message for each unpaired old
    # - finally add remaining unpaired messages to be diffed with None
    msgs1_paired = set()
    msgs2_paired = set()
    dpairs = []

    for msg2 in cat2:
        msg1 = _get_msg_pair(msg2, cat1, icat1, mcat12)
        if msg1 and msg1 not in msgs1_paired:
            # Record pairing.
            msgs1_paired.add(msg1)
            msgs2_paired.add(msg2)
            dpairs.append((msg1, msg2))

    for msg1 in cat1:
        if msg1 in msgs1_paired:
            continue
        msg2 = _get_msg_pair(msg1, cat2, icat2, mcat21)
        if msg2 and msg2 not in msgs2_paired:
            # Record pairing.
            msgs1_paired.add(msg1)
            msgs2_paired.add(msg2)
            dpairs.append((msg1, msg2))

    for msg2 in (wadd and cat2 or []):
        if msg2 not in msgs2_paired:
            dpairs.append((None, msg2))

    for msg1 in (wrem and cat1 or []):
        if msg1 not in msgs1_paired:
            dpairs.append((msg1, None))

    return dpairs


def _rmobs_no_sync (cat):

    for msg in cat:
        if msg.obsolete:
            cat.remove_on_sync(msg)
    cat.sync_map()


# Determine the pair of the message in the catalog, if any.
def _get_msg_pair (msg, ocat, icat, mcat):

    # If no direct match, try pivoting around any previous fields.
    # Iterate through test catalogs in this order,
    # to delay construction of those which are not necessary.
    for tcat in (ocat, icat, mcat):
        if callable(tcat):
            tcat = tcat()
        omsg = tcat.get(msg)
        if not omsg and msg.fuzzy:
            omsg = tcat.get(_msg_invert_cp(msg))
        if tcat is not ocat: # tcat is one of pivot catalogs
            omsg = ocat.get(_msg_invert_cp(omsg))
        if omsg:
            break

    return omsg


# Out of a message with previous fields,
# construct a lightweight message with previous and current fields exchanged.
# If there are no previous fields, return None.
# To be used only for lookups
def _msg_invert_cp (msg):

    if msg is None:
        return None

    lmsg = MessageUnsafe()
    if msg.key_previous is not None:
        # Need to invert only key fields, but whadda hell.
        for fcurr, fprev in MPC.currprev_fields:
            setattr(lmsg, fcurr, msg.get(fprev))
            setattr(lmsg, fprev, msg.get(fcurr))
    else:
        return lmsg.set_key(msg)

    return lmsg


def _add_msg_diff (msg1, msg2, ecat, colorize, fnsyn=None):

    # Skip diffing if old and new messages are "same".
    if msg1 and msg2 and msg1.inv == msg2.inv:
        return 0

    # Create messages for special pairings.
    msg1_s, msg2_s = _create_special_diff_pair(msg1, msg2)

    # Create the diff.
    tmsg = msg2 or msg1
    emsg = msg2_s or msg1_s
    if emsg is tmsg:
        emsg = MessageUnsafe(tmsg)
    emsg = msg_ediff(msg1_s, msg2_s, emsg=emsg, ecat=ecat, colorize=colorize)

    # Add to the diff catalog.
    if fnsyn is None:
        ecat.add(emsg, len(ecat))
    else:
        ecat.add(emsg, srefsyn=fnsyn)

    return 1


def _create_special_diff_pair (msg1, msg2):

    msg1_s, msg2_s = msg1, msg2

    if not msg1 or not msg2:
        # No special cases if either message non-existant.
        pass

    # Cases f-nf-*.
    elif msg1.fuzzy and msg1.key_previous is not None and not msg2.fuzzy:
        # Case f-nf-ecc.
        if msg_eq_fields(msg1, msg2, MPC.curr_fields):
            msg1_s = MessageUnsafe(msg1)
            msg_copy_fields(msg1, msg1_s, MPC.prevcurr_fields)
            msg_clear_prev_fields(msg1_s)
        # Case f-nf-necc.
        else:
            msg1_s = MessageUnsafe(msg1)
            msg2_s = MessageUnsafe(msg2)
            msg_copy_fields(msg1, msg1_s, MPC.prevcurr_fields)
            msg_copy_fields(msg1, msg2_s, MPC.currprev_fields)

    # Cases nf-f-*.
    elif not msg1.fuzzy and msg2.fuzzy and msg2.key_previous is not None:
        # Case nf-f-ecp.
        if msg_eq_fields(msg1, msg2, MPC.currprev_fields):
            msg2_s = MessageUnsafe(msg2)
            msg_clear_prev_fields(msg2_s)
        # Case nf-f-necp.
        else:
            msg1_s = MessageUnsafe(msg1)
            msg2_s = MessageUnsafe(msg2)
            msg_copy_fields(msg2, msg1_s, MPC.prev_fields)
            msg_copy_fields(msg2, msg2_s, MPC.currprev_fields)

    return msg1_s, msg2_s


def diff_hdrs (hdr1, hdr2, vpath1, vpath2, hmsgctxt, ecat, colorize):

    hmsg1, hmsg2 = [x and MessageUnsafe(x.to_msg()) or None
                    for x in (hdr1, hdr2)]

    ehmsg = hmsg2 and MessageUnsafe(hmsg2) or None
    ehmsg, dr = msg_ediff(hmsg1, hmsg2, emsg=ehmsg, ecat=ecat,
                          colorize=colorize, diffr=True)
    if dr == 0.0:
        # Revert to empty message if no difference between headers.
        ehmsg = MessageUnsafe()

    # Add visual paths as old/new segments into msgid.
    vpaths = [vpath1, vpath2]
    # Always use slashes as path separator, for portability of ediffs.
    vpaths = [x.replace(os.path.sep, "/") for x in vpaths]
    ehmsg.msgid = u"- %s\n+ %s" % tuple(vpaths)
    # Add trailing newline if msgstr has it, again to appease msgfmt.
    if ehmsg.msgstr[0].endswith("\n"):
        ehmsg.msgid += "\n"

    # Add context identifying the diffed message as header.
    ehmsg.msgctxt = hmsgctxt

    # Add conspicuous separator at the top of the header.
    ehmsg.manual_comment.insert(0, u"=" * 76)

    return ehmsg, dr > 0.0


def init_ediff_header (ehdr, hmsgctxt=EDST.hmsgctxt_el, extitle=None):

    cfgsec = pology_config.section("user")
    user = cfgsec.string("name", "J. Random Translator")
    email = cfgsec.string("email", None)

    listtype = type(ehdr.title)

    if extitle is not None:
        title = u"+- ediff (%s) -+" % extitle
    else:
        title = u"+- ediff -+"
    ehdr.title = listtype([title])

    year = time.strftime("%Y")
    if email:
        author = u"%s <%s>, %s." % (user, email, year)
    else:
        author = u"%s, %s." % (user, year)
    #ehdr.author = listtype([author])
    ehdr.author = listtype([])

    ehdr.copyright = u""
    ehdr.license = u""
    ehdr.comment = listtype()

    rfv = ehdr.replace_field_value # shortcut

    rfv("Project-Id-Version", u"ediff")
    ehdr.remove_field("Report-Msgid-Bugs-To")
    ehdr.remove_field("POT-Creation-Date")
    rfv("PO-Revision-Date", unicode(time.strftime("%Y-%m-%d %H:%M%z")))
    enc = "UTF-8" # strictly, input catalogs may have different encodings
    rfv("Content-Type", u"text/plain; charset=%s" % enc)
    rfv("Content-Transfer-Encoding", u"8bit")
    if email:
        translator = u"%s <%s>" % (user, email)
    else:
        translator = u"%s" % user
    rfv("Last-Translator", translator)
    rfv("Language-Team", u"Differs")
    # FIXME: Something smarter? (Not trivial.)
    ehdr.remove_field("Plural-Forms")

    # Context of header messages in the catalog.
    ehdr.set_field(EDST.hmsgctxt_field, hmsgctxt)


def get_msgctxt_for_headers (cat):

    hmsgctxt = u""
    good = False
    while not good:
        hmsgctxt += EDST.hmsgctxt_el
        good = True
        for msg in cat:
            if hmsgctxt == msg.msgctxt:
                good = False
                break

    return hmsgctxt


