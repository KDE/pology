# -*- coding: UTF-8 -*-

"""
Check validity of messages in catalogs of The Battle for Wesnoth.

Sieve parameters:
  - C{check}: select only one or few checks to be applied, instead of all
  - C{showmsg}: show content of the message, with errors highlighted
  - C{lokalize}: open catalogs at problematic messages in Lokalize

Parameter C{check} may be used to to apply only some instead of all checks.
It takes comma-separated list of check keywords, which are provided in
the list of checks that follows.

Currently available checks are:

  - Stray context separators in translation (C{ctxtsep}).
    Wesnoth is still using the old-fashioned way of embedding context
    into C{msgid}, by putting it in front of and separating by C{^} from
    the actual text of C{msgid}.
    An occasional unwary translator sometimes mistakes such context
    for part of the original text, and translates it too.

  - Congruence of interpolations (C{interp}).
    Interpolations (C{"...side $side_number is..."}) must match between
    the original and translation, for the player not to loose information.
    In very rare cases (e.g. some plurals, Markov chain generators)
    the congruence of some interpolations may not be desired, in which case
    they these interpolation can be listed in a special manual comment
    as space-separated list: C{# ignore-interpolations: interp1 interp2 ...}

  - WML validity (C{wml}).
    WML in translation should be valid, for the player not to see visual
    artifacts. Also, WML links must match between original and translation,
    to avoid loss of information.

  - Pango markup validity (C{pango}).
    Just like check for WML markup, only for Pango markup instead.

  - Congruence of leading and trailing space (C{space}).
    For many languages, significant leading and trailing space from the
    original should be preserved. Heuristics is used to determine such places.
    Only explicitly listed languages are checked for this.

  - Docbook validity (C{docbook}).
    Wesnoth manual is written in Docbook, and this check will raise
    alarm if the translation got Docbook markup wrong.
    A bit superfluous and less thorough then what the Docbook processor
    will do when building the language manual, but still may
    be useful for quick checks (e.g. if a translator does not know how
    to build the final manual out of Docbook source).


@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import os
import re

from pology import _, n_
from pology.misc.report import report, format_item_list
from pology.misc.msgreport import report_on_msg_hl, report_msg_content
from pology.misc.msgreport import report_msg_to_lokalize
from pology.misc.stdsvpar import add_param_poeditors
from pology.sieve import SieveError
from pology.file.message import MessageUnsafe


_ctxtsep = "^"


def setup_sieve (p):

    p.set_desc(_("@info sieve discription",
    "Check validity of messages in catalogs of The Battle for Wesnoth."
    ))
    chnames = _known_checks.keys()
    chnames.sort()
    p.add_param("check", unicode, seplist=True,
                metavar=_("@info sieve parameter value placeholder",
                          "KEYWORD,..."),
                desc=_("@info sieve parameter discription",
    "Run only this check instead of all (currently available: %(chklist)s). "
    "Several checks can be specified as a comma-separated list.",
    chklist=format_item_list(chnames)
    ))
    p.add_param("showmsg", bool, defval=False,
                desc=_("@info sieve parameter discription",
    "Also show the full message that had some problems."
    ))
    add_param_poeditors(p)


class Sieve (object):

    def __init__ (self, params):

        self.selected_checks = None
        if params.check is not None:
            unknown_checks = []
            for chname in params.check:
                if chname not in _known_checks:
                    unknown_checks.append(chname)
            if unknown_checks:
                fmtchecks = format_item_list(unknown_checks)
                raise SieveError(
                    _("@info",
                      "Unknown checks selected: %(chklist)s.",
                      chklist=fmtchecks))
            self.selected_checks = set(params.check)

        self.showmsg = params.showmsg
        self.lokalize = params.lokalize

        # Indicators to the caller:
        self.caller_sync = False # no need to sync catalogs to the caller
        self.caller_monitored = False # no need for monitored messages

        self.nproblems = 0


    def process_header (self, hdr, cat):

        def set_checks (names):
            self.current_checks = []
            if self.selected_checks is not None:
                names = set(names).intersection(self.selected_checks)
            for name in names:
                self.current_checks.append(_known_checks[name])

        # Determine applicable checks by characteristic message.
        # Ugly, but no catalog name and nothing in header.
        if cat.select_by_key(None, "en"):
            set_checks(["docbook"])
        elif cat.select_by_key(None, "wesnothd"):
            set_checks(["man"])
        else:
            set_checks(["ctxtsep", "interp", "wml", "pango", "space"])


    def process (self, msg, cat):

        if not msg.translated:
            return

        highlight = []

        # Convert embedded to proper context.
        if _ctxtsep in msg.msgid:
            p = msg.msgid.find(_ctxtsep)
            msg = MessageUnsafe(msg) # should not modify original message
            msg.msgctxt = msg.msgid[:p]
            msg.msgid = msg.msgid[p + len(_ctxtsep):]

        for check in self.current_checks:
            self.nproblems += check(msg, cat, False, highlight)

        if highlight:
            if self.showmsg:
                report_msg_content(msg, cat, highlight=highlight,
                                   delim=("-" * 20))
            else:
                report_on_msg_hl(highlight, msg, cat)
            if self.lokalize:
                report_msg_to_lokalize(msg, cat, highlight)


    def finalize (self):

        if self.nproblems > 0:
            msg = n_("@info:progress BfW stands for \"Battle for Wesnoth\"",
                     "Found %(num)d problem in BfW translations.",
                     "Found %(num)d problems in BfW translations.",
                     num=self.nproblems)
            report("===== " + msg)


# --------------------------------------
# Check for mistranslated contexts.

def _check_ctxtsep (msg, cat, strict, hl):

    nproblems = 0
    for i in range(len(msg.msgstr)):
        p = msg.msgstr[i].find(_ctxtsep)
        if p >= 0:
            hl.append(("msgstr", i,
                       [(p, p + len(_ctxtsep),
                         _("@info", "Stray context separator."))]))
            nproblems += 1

    return nproblems


# --------------------------------------
# Check for congruence of interpolations.

def _check_interp (msg, cat, strict, hl):

    def match_for_index (index, interps_orig, n_can_miss=0):
        nproblems = 0
        interps_trans = _collect_interps(msg.msgstr[index])
        if interps_orig != interps_trans:
            interps_missing = interps_orig.difference(interps_trans)
            # Eliminate from check interpolations explicitly ignored.
            for cmnt in [x.strip() for x in msg.manual_comment]:
                if cmnt.startswith("ignore-interpolations:"):
                    interps = cmnt[cmnt.find(":") + 1:].split()
                    for interp in interps:
                        interp = interp.strip()
                        if not interp.startswith("$"):
                            interp = "$%s" % interp
                        if interp in interps_missing:
                            interps_missing.remove(interp)
            interps_unknown = interps_trans.difference(interps_orig)
            if interps_missing and len(interps_missing) > n_can_miss:
                vfmt = format_item_list(interps_missing)
                hl.append(("msgstr", index,
                           [(None, None,
                             _("@info",
                               "Missing interpolations: %(interplist)s.",
                               interplist=vfmt))]))
                nproblems += 1
            elif interps_unknown:
                vfmt = format_item_list(interps_unknown)
                hl.append(("msgstr", index,
                           [(None, None,
                             _("@info",
                               "Unknown interpolations: %(interplist)s.",
                               interplist=vfmt))]))
                nproblems += 1
        return nproblems

    nproblems = 0
    if msg.msgid_plural is None:
        interps_orig = _collect_interps(msg.msgid)
        nproblems += match_for_index(0, interps_orig)
    else:
        interps_orig = _collect_interps(msg.msgid_plural)
        indices_single = cat.plural_indices_single()
        for i in range(len(msg.msgstr)):
            nproblems += match_for_index(i, interps_orig,
                                         i in indices_single and 1 or 0)

    return nproblems


_interp_rx = re.compile(r"\$\w+(?:\.\w+)*") # intentionally no re.U flag

def _collect_interps (text):

    return set(_interp_rx.findall(text))


# --------------------------------------
# Check for WML validity.

def _check_wml (msg, cat, strict, hl):

    if _detect_markup(msg, cat) != "wml":
        return 0

    # Validate WML in original and collect links.
    # If the original is not valid, do not check translation.
    spans_orig, links_orig = _check_wml_text(msg.msgid)
    if spans_orig:
        return 0

    nproblems = 0
    links_trans = set()
    for i in range(len(msg.msgstr)):
        spans, links = _check_wml_text(msg.msgstr[i])
        if spans:
            hl.append(("msgstr", i, spans))
            nproblems += len(spans)
        elif links != links_orig:
            links_missing = links_orig.difference(links)
            links_unknown = links.difference(links_orig)
            if links_missing:
                vfmt = format_item_list(links_missing)
                hl.append(("msgstr", i,
                           [(None, None,
                             _("@info",
                               "Missing links: %(linklist)s.",
                               linklist=vfmt))]))
                nproblems += 1
            elif links_unknown:
                vfmt = format_item_list(links_unknown)
                hl.append(("msgstr", i,
                           [(None, None,
                             _("@info",
                               "Unknown links: %(linklist)s.",
                               linklist=vfmt))]))
                nproblems += 1

    return nproblems


_any_ws = re.compile(r"\s")

def _is_tag (tag):

    return not _any_ws.search(tag)


_known_tags = {
    "bold": {"text": True},
    "format": {"bold": False, "color": False, "font_size": False,
               "italic": False, "text": True},
    "header": {"text": True},
    "img": {"align": False, "float": False, "src": True},
    "italic": {"text": True},
    "jump": {"amount": False, "to": False},
    "ref": {"dst": True, "force": False, "text": True},
}
_bool_vals = set(["no", "yes"])
_att_val_check = {
    "align" : lambda x: x in ["here", "left", "middle", "right"],
    "amount" : lambda x: x.isdigit(),
    "bold" : lambda x: x in _bool_vals,
    "color" : lambda x: x in ["black", "green", "red", "white", "yellow"],
    "dst" : lambda x: len(x) > 0,
    "float" : lambda x: x in _bool_vals,
    "font_size" : lambda x: x.isdigit(),
    "force" : lambda x: x in _bool_vals,
    "italic" : lambda x: x in _bool_vals,
    "src" : lambda x: len(x) > 0,
    "text" : lambda x: True,
    "to" : lambda x: bool(re.match(r"^[+-]\d+$", x)),
}
_link_atts = set(["dst", "src"])


def _check_wml_text (text):

    spans = []
    links = set()
    p = 0
    while True:
        p = text.find("<", p)
        if p < 0:
            break
        p2 = text.find(">", p)
        if p2 < 0:
            spans.append((p, len(text),
                          _("@info", "End of string within tag.")))
            break
        tag = text[p + 1:p2]
        if not _is_tag(tag):
            spans.append((p, p2, _("@info",  "Invalid tag syntax.")))
            break
        if tag not in _known_tags:
            spans.append((p, p2, _("@info", "Unknown tag.")))
            break
        p3 = text.find("</", p2 + 1)
        if p3 < 0:
            spans.append((p - 1, p2 + 10, _("@info", "Unclosed tag.")))
            break
        p4 = text.find(">", p3)
        if p4 < 0:
            spans.append((p3, len(text),
                          _("@info", "Unterminated closing tag.")))
            break
        tag2 = text[p3 + 2:p4]
        # Any further errors do not terminate checking.
        p = p4 + 1 # start position for next loop
        if tag2 != tag:
            spans.append((p3, p4,
                          _("@info", "Mismatched opening and closing tags.")))
            continue
        spans_att, links_att = _check_wml_att(tag, text[p2 + 1:p3])
        spans.extend([(p2 + 1 + pi1, p2 + 1 + pi2, note)
                      for pi1, pi2, note in spans_att])
        links.update(links_att)

    return spans, links


def _check_wml_att (tag, content):

    spans = []
    links = set()
    have_atts = set()
    lenc = len(content)
    p = 0
    while True:
        while p < lenc and content[p].isspace():
            p += 1
        if p >= lenc:
            break
        # Parse attribute.
        p2 = p
        while p2 < lenc and content[p2].isalpha():
            p2 += 1
        if p2 >= lenc:
            spans.append((p, lenc,
                          _("@info", "End of tag content within attribute.")))
            break
        att = content[p:p2]
        if att not in _known_tags[tag]:
            spans.append((p, p2 + 1,
                          _("@info",
                            "'%(attr)s' is not an attribute of "
                            "tag '%(tag)s'.", attr=att, tag=tag)))
            break
        if content[p2] != "=":
            spans.append((p, p2 + 1,
                         _("@info", "No equal sign after attribute.")))
            break
        if att in have_atts:
            spans.append((p, p2 + 1,
                          _("@info",
                            "Attribute '%(attr)s' repeated.", attr=att)))
            break
        have_atts.add(att)
        # Parse value.
        p3 = p2 + 1
        if content[p3:p3 + 1] == "'":
            terminator = "'"
            p3 += 1
        else:
            terminator = " "
        p4 = p3
        while p4 < lenc and content[p4] != terminator:
            if content[p4] == "\\": # an escape
                p4 += 1
            p4 += 1
        val = content[p3:p4]
        if not _att_val_check[att](val):
            spans.append((p3, p4,
                          _("@info",
                            "Invalid value to attribute '%(attr)s'.",
                            attr=att)))
        if att in _link_atts:
            links.add(val)
        # Prepare next loop.
        p = p4 + 1

    if not spans:
        for att, mandatory in _known_tags[tag].items():
            if mandatory and att not in have_atts:
                spans.append((0, 0,
                              _("@info",
                                "Missing mandatory attribute '%(attr)s'.",
                                attr=att)))

    return spans, links


# --------------------------------------
# Check for Pango markup.

from pology.misc.markup import check_xml_pango_l1

def _check_pango (msg, cat, strict, hl):

    if _detect_markup(msg, cat) != "pango":
        return 0

    # If the original is not valid, do not check translation.
    spans_orig = check_xml_pango_l1(msg.msgid)
    if spans_orig:
        return 0

    nproblems = 0
    for i in range(len(msg.msgstr)):
        spans = check_xml_pango_l1(msg.msgstr[i])
        if spans:
            hl.append(("msgstr", i, spans))
            nproblems += len(spans)

    return nproblems


# --------------------------------------
# Check for congruence of spaces.

_langs_w_outspc = (
    "sr", "sr@latin", "de", "lt", "fr", "ru", "sk", "is",
)

def _check_space (msg, cat, strict, hl):

    # Check only for explicitly listed languages.
    if (cat.language() or cat.name) not in _langs_w_outspc:
        return 0

    # Check if explicitly stated in extracted comment
    # that outer space in original is significant.
    kw_outspcsig = "outer-space-significant"
    outspcsig = reduce(lambda s, x: s or kw_outspcsig in x.lower(),
                        msg.auto_comment, False)

    nproblems = 0
    haslead_o = msg.msgid.startswith(" ")
    hastail_o = msg.msgid.endswith(" ")
    tailnspc_o = msg.msgid.strip()[-1:]
    for i in range(len(msg.msgstr)):
        haslead_t = msg.msgstr[i].startswith(" ")
        hastail_t = msg.msgstr[i].endswith(" ")

        # Consider trailing space in original significant
        # if explicitly stated so, if it is preceded by colon,
        # or there was a leading space.
        if (    hastail_o and not hastail_t
            and (outspcsig or haslead_o or tailnspc_o in ":")
        ):
            hl.append(("msgstr", i, [(-1, 0,
                                      _("@info", "Missing trailing space."))]))
            nproblems += 1

        # Consider leading space always significant.
        if haslead_o and not haslead_t:
            hl.append(("msgstr", i, [(0, 0,
                                      _("@info", "Missing leading space."))]))
            nproblems += 1

        """
        Nah, usually invisible and yet frequent.
        # If original has no trailing space,
        # translation should also have none.
        if not hastail_o and hastail_t:
            hl.append(("msgstr", i, [(-1, 0, "extra trailing space")]))
            nproblems += 1
        """

        # If original has no leading space,
        # translation should also have none.
        if not haslead_o and haslead_t:
            hl.append(("msgstr", i, [(0, 0,
                                      _("@info", "Extra leading space."))]))
            nproblems += 1

    return nproblems


# --------------------------------------
# Check for Docbook markup.

from pology.sieve.check_xml_docbook4 import _check_dbmarkup


# --------------------------------------
# Check for man markup.

def _check_man (msg, cat, strict, hl):

    # TODO.

    return 0


# --------------------------------------
# Map of all existing checks.

_known_checks = {
    "ctxtsep": _check_ctxtsep,
    "interp": _check_interp,
    "wml": _check_wml,
    "pango": _check_pango,
    "space": _check_space,
    "docbook": _check_dbmarkup,
    "man": _check_man,
}

# --------------------------------------
# Utilities.

# Try to heuristically detect which type of markup is used in the message.
# Detection is conservative: better report no markup, than wrong markup.

from pology.misc.markup import collect_xml_spec_l1
from pology import rootdir

_tags_wml = _known_tags
_specpath = os.path.join(rootdir(), "spec", "pango.l1")
_tags_pango = collect_xml_spec_l1(_specpath).keys()

_first_tag_rx = re.compile(r"<\s*(\w+)[^>]*>", re.U)


# Return keyword of markup detected in the text.
def _detect_markup_in_text (text):

    m = _first_tag_rx.search(text)
    if m:
        tag = m.group(1)
        if tag in _tags_wml:
            return "wml"
        elif tag in _tags_pango:
            return "pango"
        else:
            return "unknown"
    else:
        return None


# Return keyword of markup detected in the message.
def _detect_markup (msg, cat):

    # First look into original text.
    # If no markup determined from there, look into translation.
    markup_type = _detect_markup_in_text(msg.msgid)
    if markup_type is None:
        markup_type = _detect_markup_in_text(msg.msgstr[0])

    return markup_type

