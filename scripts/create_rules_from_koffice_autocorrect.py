#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Create Pology rules from the KOffice KWord autocorrect xml file.
This script is intended to be run standalone.

Usage::
    python create_rules_from_koffice_autocorrect.py <autocorrect file> <output rule file>

@author: Sébastien Renard <sebastien.renard@digitalfox.org>
@license: GPLv3
"""

import re
import sys
from codecs import open
import locale

def main():
    locale.setlocale(locale.LC_ALL, "")
    
    if len(sys.argv)!=3:
        usage()
    
    #TODO: check file is readable
    kofficeFile=open(sys.argv[1], "r", "utf-8")
    #TODO: check path is writable
    ruleFile=open(sys.argv[2], "w", "utf-8")
    
    # Regexp to find autocorrect items
    regexp=re.compile('<item find="(.*?)" replace="(.*?)" />')
    
    #Header
    ruleFile.write("# Generated rules from KOffice autocorrect file\n")
    ruleFile.write("# by the KOffice project (http://www.koffice.org)\n")
    ruleFile.write("# License: GPLv3\n\n")
    
    #TODO: exceptions should be in a separated file, not hardcoded.
    exceptions=["http:/", "http://", "etc...", "language"]
    for line in kofficeFile:
        match=regexp.match(line.strip())
        if match:
            find=match.group(1)
            replace=match.group(2)
            if find not in exceptions:
                ruleFile.write(u'[&lwb;%s&rwb;]\nhint="%s => %s (d\'après le fichier de correction de KOffice)"\n\n' % (find, find, replace))
    #Footer
    ruleFile.write("\n#End of rule file\n")
    ruleFile.close()

def usage():
    print "\t%s <autocorrect file> <output rule file>" % sys.argv[0]
    sys.exit(1)

if __name__ == '__main__':
    main()
