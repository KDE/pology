# -*- coding: UTF-8 -*-

"""
Check for presence of bad patterns in translation.

Documented in C{doc/user/sieving.docbook}.

@note: Deprecated.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

from pology import _, n_
from pology.bpatterns import bad_patterns_msg
from pology.report import report


def setup_sieve (p):

    p.set_desc(_("@info sieve discription",
    "Check for presence of bad patterns in translation."
    ))

    p.add_param("pattern", unicode, multival=True,
                metavar=_("@info sieve parameter value placeholder", "STRING"),
                desc=_("@info sieve parameter discription",
    "A pattern to check against. "
    "The pattern can be a substring or regular expression, "
    "depending on the '%s' parameter. "
    "This parameter can be repeated to add several patterns."
    ))
    p.add_param("fromfile", unicode, multival=True,
                metavar=_("@info sieve parameter value placeholder", "PATH"),
                desc=_("@info sieve parameter discription",
    "Read patterns to check against from a file. "
    "The file format is as follows: "
    "each line contains one pattern, "
    "leading and trailing whitespace is removed, "
    "empty lines are ignored; "
    "# denotes start of comment, which extends to end of line."
    "This parameter can be repeated to add several files."
    ))
    p.add_param("rxmatch", bool, defval=False,
                desc=_("@info sieve parameter discription",
    "Treat patterns as regular expressions; default is substring matching."
    ))
    p.add_param("casesens", bool, defval=False,
                desc=_("@info sieve parameter discription",
    "Set case-sensitive matching; default is case-insensitive."
    ))


class Sieve (object):

    def __init__ (self, params):

        # Indicators to the caller:
        self.caller_sync = False # no need to sync catalogs to the caller
        self.caller_monitored = False # no need for monitored messages

        # Create checker hook.
        self.check = bad_patterns_msg(rxmatch=params.rxmatch,
                                      casesens=params.casesens,
                                      patterns=params.pattern,
                                      fromfiles=params.fromfile)

        self.nbad = 0


    def process (self, msg, cat):

        # Check only translated messages.
        if not msg.translated:
            return

        self.nbad += self.check(msg, cat)


    def finalize (self):

        if self.nbad > 0:
            msg = n_("@info:progress",
                     "Detected %(num)d bad pattern in translation.",
                     "Detected %(num)d bad patterns in translation.",
                     num=self.nbad)
            report("===== " + msg)

