# -*- coding: UTF-8 -*-

"""
Check for presence of bad patterns in translation.

Sometimes there are simply definable patterns that should never appear
in translation, such as common grammar or orthographical errors.
This sieve allows checking for such patterns, either through substring
matching or regular expressions.
Patterns can be given as parameters, or, more conveniently, read from files.

Sieve parameters:
  - C{pattern:<string>}: pattern to check against
  - C{fromfile:<path>}: file from which to read patterns
  - C{rxmatch}: patterns should be treated as regular expressions
  - C{casesens}: patterns should be treated as case-sensitive

Any number of C{pattern} and C{fromfile} parameters may be given.
By default, patterns are matched as substrings, and C{rxmatch} parameter
can be issued to consider patterns as regular expressions.

@note: This sieve is deprecated; instead use the
L{check-rules<misc.sieve.check_rules}, which provides much more options
for defining, matching, and reporting problems.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

from pology.misc.report import report
from pology.hook.bad_patterns import bad_patterns_msg


def setup_sieve (p):

    p.set_desc(
    "Check for presence of bad patterns in translation."
    )

    p.add_param("pattern", unicode, multival=True,
                metavar="STRING",
                desc=
    "A pattern to check against. "
    "The pattern can be a substring or regular expression, "
    "depending on the '%s' parameter. "
    "This parameter can be repeated to add several patterns."
    )
    p.add_param("fromfile", unicode, multival=True,
                metavar="PATH",
                desc=
    "Read patterns to check against from a file. "
    "The file format is as follows: "
    "each line contains one pattern, "
    "leading and trailing whitespace is removed, "
    "empty lines are ignored; "
    "# denotes start of comment, which extends to end of line."
    "This parameter can be repeated to add several files."
    )
    p.add_param("rxmatch", bool, defval=False,
                desc=
    "Treat patterns as regular expressions; default is substring matching."
    )
    p.add_param("casesens", bool, defval=False,
                desc=
    "Set case-sensitive matching; default is case-insensitive."
    )


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
            report("Total bad patterns detected in translation: %d" % self.nbad)

