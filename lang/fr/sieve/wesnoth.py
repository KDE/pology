# -*- coding: UTF-8 -*-

"""
Auto correct translation according to the rules etablished by the French
BFW traduction team.
It includes unbreakable spaces, hyphen (…), apostrophe, extra spaces (option).

inspired from other sieves
@author: alberic89 <alberic89@gmx.com>
@license: GPLv3"""

import re

from typing import List
from pology import _, n_
from pology.report import report
from pology.sieve import add_param_filter


def setup_sieve(p):
    p.set_desc(
        _(
            "@info sieve description",
            "Correct message according to BFW french standard",
        )
    )

    p.add_param(
        "quiet",
        bool,
        defval=False,
        desc=_(
            "@info sieve parameter description",
            "Do not show summary (for script usage)",
        ),
    )

    p.add_param(
        "level",
        str,
        defval="",
        desc=_(
            "@info sieve parameter description",
            "Set level of correction (1, 2 and 3). You can use multiple levels, for example level:12",
        ),
    )

    p.add_param(
        "extra_spaces",
        list,
        defval=[],
        desc=_(
            "@info sieve parameter description",
            "Replace all extra spaces by punctuation space on the message of the numero given. You can specify multiple messages with comma-separated list.",
        ),
    )

    p.add_param(
        "ellipsis3points",
        bool,
        defval=False,
        desc=_(
            "@info sieve parameter description",
            "Replace all Unicode ellipsis (…) by three dots (...)",
        ),
    )

    p.add_param(
        "ellipsisUnicode",
        bool,
        defval=False,
        desc=_(
            "@info sieve parameter description",
            "Replace all three dots (...) by Unicode ellipsis (…)",
        ),
    )


class SpecialFilter:
    """A special filter"""

    def __init__(self, name, value, condition, action):
        """value is a boolean to know if this filter must be used.
        action should be a function with the msg object.
        condition a function which takes msg in argument and returns boolean (if the filter is conditional)"""
        self.name = name
        self.value = value
        self.condition = condition
        self.action = action

    def process(self, msg):
        if self.condition(msg):
            for i in range(len(msg.msgstr)):
                msg.msgstr[i] = self.action(msg.msgstr[i])
        return msg

    def __eq__(self, y):
        return y == self.value

    def __repr__(self):
        return f"{self.name} : {self.value} : {self.action}"


def _replace_group(match, group, replacement):
    if groupn := match.group(group):
        return match.group().replace(groupn, replacement)
    else:
        return match.group()


class Sieve(object):
    """Correct translation according to BFW French standard"""

    # apostrophe typographique "’" : \u2019
    # espace insécable " " : \u00A0
    # espace insécable fine " " : \u202F

    def __init__(self, params):
        self.nmatch = 0
        self.p = params
        self.level = params.level
        nums = [0]
        for _ in params.extra_spaces:
            if _.isdigit():
                nums.append(nums.pop() * 10 + int(_))
            else:
                nums.append(0)

        self.spaces = nums
        self.space_start = re.compile(r"^ +")
        self.space_end = re.compile(r" +$")
        regex_replacements_1 = (
            (re.compile(r"(?<=\d)(\s+)(?=%(?=$| |\.|,))"), "\u00A0"),  # %
            (re.compile(r"\b(\s+)(?=:|»)"), "\u00A0"),  # : »
            (re.compile(r"(?<=«)(\s+)\b"), "\u00A0"),  # «
            (re.compile(r"\b(\s+)(?=;|!|\?)"), "\u202F"),  # ; ! ?
            (re.compile(r"\b(  )\b"), " "),  # double space
        )
        regex_replacements_2 = (
            (
                re.compile(r"(?<==')([^\\']*(\b\\'\b))*([^\\']*)(?=')"),
                lambda m: _replace_group(m, 2, "\u2019"),
            ),
            (re.compile(r"\b(')(?=$|\b|\s[:;!?]|[.,])"), "\u2019"),  # '
        )

        regex_replacements_3 = (
            (re.compile(r"\b( )(?=\.|,)"), ""),  # remove space before point and virgule
        )

        self.regex_replacements = {
            "1": regex_replacements_1,
            "2": regex_replacements_2,
            "3": regex_replacements_3,
        }

        replacements_1 = ()
        replacements_2 = ()
        replacements_3 = ()

        self.replacements = {
            "1": replacements_1,
            "2": replacements_2,
            "3": replacements_3,
        }

        self.filters = (
            SpecialFilter(
                "extra_spaces",
                params.extra_spaces,
                lambda msg: msg.refentry in self.spaces,
                self.replace_extra_spaces,
            ),
            SpecialFilter(
                "ellipsis3points",
                params.ellipsis3points,
                lambda _: True,
                lambda text: text.replace("\u2026", "..."),
            ),
            SpecialFilter(
                "ellipsisUnicode",
                params.ellipsisUnicode,
                lambda _: True,
                lambda text: text.replace("...", "\u2026"),
            ),
        )  # in future, add other specials filters
        self.used_filters = [_ for _ in self.filters if _.value]

    def process(self, msg, cat):
        oldcount = msg.modcount

        for nb in self.level:
            for i in range(len(msg.msgstr)):
                msg.msgstr[i] = self.correctTypo(
                    msg.msgstr[i],
                    self.replacements[nb],
                    self.regex_replacements[nb],
                )

        for _ in self.used_filters:
            if _.value:
                msg = _.process(msg)

        if oldcount < msg.modcount:
            self.nmatch += 1

    def finalize(self):
        if self.nmatch > 0 and not self.p.quiet:
            report(
                n_(
                    "@info",
                    "There was %(num)d corrected message.",
                    "There were %(num)d corrected messages.",
                    num=self.nmatch,
                )
            )

    def correctTypo(self, text, replacements, regex_replacements):
        """Set correct typo"""

        for _ in replacements:
            text = text.replace(_[0], _[1])
        for _ in regex_replacements:
            text = _[0].sub(_[1], text)

        return text

    def replace_extra_spaces(self, text):
        """Replace space at start and end by punctuation space"""
        # punctuation space " " : \u2008
        match_start = re.search(self.space_start, text)
        match_end = re.search(self.space_end, text)

        if match_start:
            text = re.sub(self.space_start, "\u2008" * len(match_start[0]), text)

        if match_end:
            text = re.sub(self.space_end, "\u2008" * len(match_end[0]), text)

        return text
