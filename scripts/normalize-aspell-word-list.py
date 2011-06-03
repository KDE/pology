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
from pology.report import report, error


def main():

    locale.setlocale(locale.LC_ALL, "")

    # FIXME: Use pology.colors.ColorOptionParser.
    reminv=False
    paths=[]
    for arg in sys.argv[1:]:
        if arg.startswith("-"):
            if arg in ("-r", "--remove-invalid"):
                reminv = True
            else:
                error(_("@info",
                        "Unknown option '%(opt)s' in command line.",
                        opt=arg))
        else:
            paths.append(arg)
    if len(paths)<1:
        usage()

    for path in paths:
        organize(path, reminv)


def organize (dictPath, reminv=False):

    report(dictPath)
    dictEncDefault = "UTF-8"
    dictFile=open(dictPath, "r", dictEncDefault)

    # Parse the header for language and encoding.
    header=dictFile.readline()
    m=re.search(r"^(\S+)\s+(\S+)\s+(\d+)\s+(\S+)\s*", header)
    if not m:
        error(_("@info",
                "Malformed header of the dictionary file '%(file)s'.",
                file=dictPath))
    dictType, dictLang, numWords, dictEnc=m.groups()

    # Reopen in correct encoding if not the default.
    if dictEnc.lower() != dictEncDefault.lower():
        dictFile.close()
        dictFile=open(dictPath, "r", dictEnc)

    # Read all words and eliminate duplicates.
    words=set()
    validCharacters=re.compile(ur"^[\w\d\'・-]+$", re.UNICODE)
    lno = 0
    for word in dictFile:
        lno += 1
        word=word.strip()
        if not word or word.startswith("personal_ws"):
            continue
        if word in words:
            report("  " + _("@item:inlist",
                            "duplicate removed: %(word)s",
                            word=word))
        elif not validCharacters.match(word):
            if not reminv:
                report("  " + _("@item:inlist",
                                "*** invalid word at %(line)s: %(word)s",
                                line=lno, word=word))
                words.add(word)
            else:
                report("  " + _("@item:inlist",
                                "invalid word removed: %(word)s",
                                word=word))
        else:
            words.add(word)
    dictFile.close()
    words=list(words)
    numWords=len(words)

    # Sort the list according to current locale, ignoring case.
    words.sort(lambda x, y: locale.strcoll(x.lower(), y.lower()))

    # Write back the updated dictionary.
    dictFile=open(dictPath, "w", dictEnc)
    dictFile.write("%s %s %d %s\n" % (dictType, dictLang, numWords, dictEnc))
    dictFile.write("\n".join(words))
    dictFile.write("\n")
    dictFile.close()
    report("  " + n_("@item:inlist",
                     "written %(num)d word",
                     "written %(num)d words",
                     num=len(words)))


def usage():
    report(_("@info",
             "Usage: %(cmd)s [-r|--remove-invalid] DICTFILE...",
             cmd=basename(sys.argv[0])))
    sys.exit(1)


if __name__ == '__main__':
    main()
