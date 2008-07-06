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

import re
import sys
from os.path import abspath
from codecs import open
import locale

from pology.misc.report import error


def main():
    if len(sys.argv)!=2:
        usage()
    
    #TODO: check file is writable
    dictPath=abspath(sys.argv[1])
    print dictPath
    dictEncDefault = "UTF-8"
    dictFile=open(dictPath, "r", dictEncDefault)

    # Parse the header for language and encoding.
    header=dictFile.readline()
    m=re.search(r"^(\S+)\s+(\S+)\s+(\d+)\s+(\S+)\s*", header)
    if not m:
        error("malformed header of the dictionary file")
    dictType, dictLang, numWords, dictEnc=m.groups()

    # Reopen in correct encoding if not the default.
    if dictEnc.lower() != dictEncDefault.lower():
        dictFile.close()
        dictFile=open(dictPath, "r", dictEnc)

    # Read all words and eliminate duplicates.
    words=set()
    for word in dictFile:
        if word.startswith("personal_ws"):
            continue
        if word in words:
            print "Remove duplicate: %s" % word.rstrip("\n")
        else:
            words.add(word)
    words=list(words)
    numWords=len(words)
    dictFile.close()

    # Sort the list according to current locale, ignoring case.
    locale.setlocale(locale.LC_ALL, locale.getdefaultlocale())
    words.sort(lambda x, y: locale.strcoll(x.lower(), y.lower()))

    # Write back the updated dictionary.
    dictFile=open(dictPath, "w", dictEnc)
    dictFile.write("%s %s %d %s\n" % (dictType, dictLang, numWords, dictEnc))
    dictFile.writelines(words)
    dictFile.close()
    print "Write %s words" % len(words)
def usage():
    print "\t%s <dict file>" % sys.argv[0]
    sys.exit(1)

if __name__ == '__main__':
    main()
