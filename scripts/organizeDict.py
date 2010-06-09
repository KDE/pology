#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Organize dictionary file:
  - sort entries
  - remove duplicate
  - update header

This script is intended to be run standalone.

Usage::
    python <dict file>

@author: Sébastien Renard <sebastien.renard@digitalfox.org>
@license: GPLv3
"""

import locale
from codecs import open
from os.path import abspath, basename
import re
import sys

import fallback_import_paths
from pology import _, n_
from pology.misc.report import report, error


def main():

    locale.setlocale(locale.LC_ALL, "")

    if len(sys.argv)<2:
        usage()

    for path in sys.argv[1:]:
        organize(path)


def organize (dictPath):

    report(dictPath)
    dictEncDefault = "UTF-8"
    dictFile=open(dictPath, "r", dictEncDefault)

    # Parse the header for language and encoding.
    header=dictFile.readline()
    m=re.search(r"^(\S+)\s+(\S+)\s+(\d+)\s+(\S+)\s*", header)
    if not m:
        error(_("@info",
                "Malformed header of the dictionary file '%(file)s'.")
              % dict(file=dictPath))
    dictType, dictLang, numWords, dictEnc=m.groups()

    # Reopen in correct encoding if not the default.
    if dictEnc.lower() != dictEncDefault.lower():
        dictFile.close()
        dictFile=open(dictPath, "r", dictEnc)

    # Read all words and eliminate duplicates.
    words=set()
    for word in dictFile:
        if not word.strip():
            continue
        if word.startswith("personal_ws"):
            continue
        if word in words:
            report("  " + (_("@item:inlist",
                            "removed duplicate: %(word)s")
                           % dict(word=word.rstrip("\n"))))
        else:
            words.add(word)
    words=list(words)
    numWords=len(words)
    dictFile.close()

    # Sort the list according to current locale, ignoring case.
    words.sort(lambda x, y: locale.strcoll(x.lower(), y.lower()))

    # Write back the updated dictionary.
    dictFile=open(dictPath, "w", dictEnc)
    dictFile.write("%s %s %d %s\n" % (dictType, dictLang, numWords, dictEnc))
    dictFile.writelines(words)
    dictFile.close()
    report("  " + (n_("@item:inlist",
                      "written %(num)d word",
                      "written %(num)d words",
                      len(words))
                   % dict(num=len(words))))


def usage():
    report(_("@info",
             "Usage: %(cmd)s DICTFILE...")
           % dict(cmd=basename(sys.argv[0])))
    sys.exit(1)


if __name__ == '__main__':
    main()
