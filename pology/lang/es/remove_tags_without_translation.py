# -*- coding: utf-8 -*-

"""
Remove contexts that do not have need of translation.

@author: Javier Viñal <fjvinal@gmail.com>
@license: GPLv3
"""

import re

from pology import _, n_

_auto_cmnt_tag_rx = re.compile(r"^\s*Tag:\s*(%s)\s*$" % "|".join("""
    trans_comment literallayout option programlisting othercredit author email holder
    surname personname affiliation address sect1 chapter chapterinfo date command option
    refentrytitle refentryinfo refname synopsis literal varname term glossterm
    filename envar userinput cmdsynopsis
""".split()), re.U|re.I)

def remove_tags_without_translation (msg, cat):
    """
    Remove all paragraph that belong to contexts that do not 
    have need of translation.[type F4A hook].

    @return: number of errors
    """
    if msg.msgctxt in ("EMAIL OF TRANSLATORS", "NAME OF TRANSLATORS", "ROLES OF TRANSLATORS"):
        msg.msgid = ""
        msg.msgid_plural = ""
        msg.msgstr = ""
	return 0
	
    # Avoid specially tagged messages.
    for auto_cmnt in msg.auto_comment:
        if _auto_cmnt_tag_rx.search(auto_cmnt):
	    msg.msgid = ""
	    msg.msgid_plural = ""
	    msg.msgstr = ""
    
    return 0
