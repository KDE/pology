#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Obtains a list of proper words (that that begins with a capital letter or
# contains an intermediate capital letter)
# that are not included yet in the local dictionary.
# It is a tool that helps to complete the local dictionary.
# The code is adapted from the Servian team pology scripts by Chusslove Illich.

import fallback_import_paths

import sys
import os
import re
import locale
import enchant

from pology import version, _, n_
from pology.catalog import Catalog
from pology.colors import ColorOptionParser
from pology.fsops import str_to_unicode, collect_catalogs
from pology.fsops import collect_paths_cmdline
from pology.split import proper_words
# from pology.msgreport import warning_on_msg, report_msg_content
# from pology.report import report, warning, error, format_item_list
from pology.stdcmdopt import add_cmdopt_filesfrom


def _main ():

	locale.setlocale(locale.LC_ALL, "")

	usage= _("@info command usage",
		"%(cmd)s [OPTIONS] VCS [POPATHS...]",
		cmd="%prog")
	desc = _("@info command description",
		"Obtains a list of proper words from the message text ")
	ver = _("@info command version",
		u"%(cmd)s (Pology) %(version)s\n"
		u"Copyright ©  2011 "
		u"Javier Viñal &lt;%(email)s&gt;",
		cmd="%prog", version=version(), email="fjvinal@gmail.com")

	opars = ColorOptionParser(usage=usage, description=desc, version=ver)
	add_cmdopt_filesfrom(opars)

	(options, free_args) = opars.parse_args(str_to_unicode(sys.argv[1:]))

	# Collect PO files in given paths.
	popaths = collect_paths_cmdline(rawpaths=free_args,
									filesfrom=options.files_from,
									elsecwd=True,
									respathf=collect_catalogs,
									abort=True)

	dict_en = enchant.Dict("en")
	dict_local = enchant.Dict("es")

	for path in popaths:
		extract_proper_words(path, dict_en, dict_local)

	dict_en.close()
	for word in sorted(dict_local.session_dict()):
		print word
	dict_local.session_dict(clear=True)
	dict_local.close()

_ent_proper_word = re.compile("^\w*?[A-Z]\w*$")

def extract_proper_words (path, dict_en, dict_local):

	cat = Catalog(path)

	for msg in cat:
		words = proper_words(msg.msgstr[0], True, cat.accelerator(), msg.format)
		for word in words:
			if _ent_proper_word.match(word):
				if not dict_en.check(str(word)) and not dict_local.check(str(word)):
					#report("%s" %(word))
					dict_local.session_dict(str(word))


if __name__ == '__main__':
	_main()

