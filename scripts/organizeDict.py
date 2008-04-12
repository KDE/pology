#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Organize dictionary file : 
- sort entries
- remove duplicate
- update header
This script is intended to be run standalone.

Usage:
    python <dict file>

@author: Sébastien Renard <sebastien.renard@digitalfox.org>
@license: GPLv3
"""

import re
import sys
from os.path import abspath
from codecs import open

def main():
    if len(sys.argv)!=2:
        usage()
    
    words=[]

    #TODO: check file is writable
    print abspath(sys.argv[1])
    dictFile=open(abspath(sys.argv[1]), "r", "utf-8")
    
    for word in dictFile:
        if word.startswith("personal_ws"):
            continue
        if word in words:
            print "Remove duplicate: %s" % word.rstrip("\n")
        else:
            words.append(word)
    
    words.sort()
    dictFile.close()
    dictFile=open(abspath(sys.argv[1]), "w", "utf-8")
    dictFile.write("personal_ws-1.1 fr %s utf-8\n" % len(words))
    dictFile.writelines(words)
    dictFile.close()
    print "Write %s words" % len(words)
def usage():
    print "\t%s <dict file>" % sys.argv[0]
    sys.exit(1)

if __name__ == '__main__':
    main()
