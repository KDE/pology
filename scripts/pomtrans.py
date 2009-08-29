#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Perform machine translation of PO files.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import fallback_import_paths

import sys
import os
from optparse import OptionParser
import locale

from pology import rootdir
from pology.file.catalog import Catalog
from pology.file.message import MessageUnsafe
from pology.misc.report import report, error, warning
from pology.misc.fsops import collect_catalogs, collect_system
from pology.misc.fsops import str_to_unicode
import pology.misc.config as pology_config
from pology.misc.wrap import select_field_wrapper
from pology.misc.entities import read_entities
from pology.misc.resolve import resolve_entities_simple
from pology.hook.remove_subs import remove_accel_msg


def main ():

    locale.setlocale(locale.LC_ALL, "")

    # Get defaults for command line options from global config.
    cfgsec = pology_config.section("pomachtrans")
    def_do_wrap = cfgsec.boolean("wrap", True)
    def_do_fine_wrap = cfgsec.boolean("fine-wrap", True)
    def_use_psyco = cfgsec.boolean("use-psyco", True)

    showservs = list()
    showservs.sort()

    # Setup options and parse the command line.
    usage = u"""
  %prog [OPTIONS] TRANSERV PATHS...
""".rstrip()
    description = u"""
Perform machine translation of PO files.
""".strip()
    version = u"""
%prog (Pology) experimental
Copyright © 2009 Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
""".strip()

    opars = OptionParser(usage=usage, description=description, version=version)
    opars.add_option(
        "-f", "--source-lang", dest="slang",
        metavar="LANG",
        help="Source language code (detected from catalogs if not given).")
    opars.add_option(
        "-t", "--target-lang", dest="tlang",
        metavar="LANG",
        help="Target language code (detected from catalogs if not given).")
    opars.add_option(
        "-a", "--accelerator", dest="accel",
        metavar="CHAR",
        help="Accelerator marker character used in messages "
             "(detected from catalogs if not given).")
    opars.add_option(
        "-p", "--parallel-catalogs", dest="parcats",
        metavar="SEARCH:REPLACE",
        help="Translate from translation to another language "
             "found in parallel catalogs. "
             "For given target catalog path, the path to parallel catalog "
             "is constructed by replacing once SEARCH with REPLACE.")
    opars.add_option(
        "-c", "--parallel-compendium", dest="parcomp",
        metavar="FILE",
        help="Translate from translation to another language, "
             "found in compendium file at the given path.")
    opars.add_option(
        "-m", "--flag-%s" % _flag_mtrans,
        action="store_true", dest="flag_mtrans", default=False,
        help="Also add flag '%s' to translated messages." % _flag_mtrans)
    opars.add_option(
        "-l", "--list-transervs",
        action="store_true", dest="list_transervs", default=False,
        help="List available translation services.")
    opars.add_option(
        "-T", "--transerv-bin", dest="transerv_bin",
        metavar="PATH",
        help="Custom path to translation service executable "
             "(where applicable).")
    opars.add_option(
        "--no-wrap",
        action="store_false", dest="do_wrap", default=def_do_wrap,
        help="No basic wrapping (on column).")
    opars.add_option(
        "--no-fine-wrap",
        action="store_false", dest="do_fine_wrap", default=def_do_fine_wrap,
        help="No fine wrapping (on markup tags, etc).")
    opars.add_option(
        "--no-psyco",
        action="store_false", dest="use_psyco", default=def_use_psyco,
        help="Do not try to use Psyco specializing compiler.")

    (op, free_args) = opars.parse_args(str_to_unicode(sys.argv[1:]))

    # Could use some speedup.
    if op.use_psyco:
        try:
            import psyco
            psyco.full()
        except ImportError:
            pass

    if op.list_transervs:
        report("\n".join(sorted(_known_transervs.keys())))
        sys.exit(0)

    if len(free_args) < 1:
        error("Translation service not specified.")
    transervkey = free_args.pop(0)
    if transervkey not in _known_transervs:
        error("Translation service '%s' not known." % transervkey)

    wrapf = select_field_wrapper(basic=op.do_wrap, fine=op.do_fine_wrap)
    tsbuilder_wopts = _known_transervs[transervkey]
    tsbuilder = lambda slang, tlang: tsbuilder_wopts(slang, tlang, op)

    paths = free_args
    if not op.parcomp and not op.parcats:
        translate_direct(paths, wrapf, tsbuilder, op)
    else:
        translate_parallel(paths, wrapf, tsbuilder, op)


def translate_direct (paths, wrapf, tsbuilder, options):

    transervs = {}

    catpaths = collect_catalogs(paths)
    for catpath in catpaths:

        # Collect messages and texts to translate.
        cat = Catalog(catpath, wrapf=wrapf)
        if options.accel is not None: # force explicitly given accelerator
            cat.set_accelerator(options.accel)
        texts = []
        msgs = []
        for msg in cat:
            if to_translate(msg, options):
                msgf = MessageUnsafe(msg)
                remove_accel_msg(msgf, cat)
                texts.append(msgf.msgid)
                if msg.msgid_plural is not None:
                    texts.append(msgf.msgid_plural)
                msgs.append(msg)

        # Translate collected texts.
        transerv = get_transerv("en", options.tlang, cat, cat, tsbuilder)
        texts_tr = transerv.translate(texts)
        if texts_tr is None:
            warning("Skipping '%s' due to translation service failure."
                    % catpath)
            continue

        # Put translated texts into messages.
        singlepls = cat.plural_indices_single()
        for msg in msgs:
            msgid_tr = texts_tr.pop(0)
            if msg.msgid_plural is not None:
                msgid_plural_tr = texts_tr.pop(0)
                for i in range(len(msg.msgstr)):
                    if i in singlepls:
                        msg.msgstr[i] = msgid_tr
                    else:
                        msg.msgstr[i] = msgid_plural_tr
            else:
                msg.msgstr[0] = msgid_tr
            decorate(msg, options)

        sync_rep(cat, msgs)


def translate_parallel (paths, wrapf, tsbuilder, options):

    pathrepl = options.parcats
    comppath = options.parcomp
    slang = options.slang
    tlang = options.tlang

    ccat = None
    if comppath is not None:
        if not os.path.isfile(comppath):
            error("Compendium file '%s' does not exist." % comppath)
        ccat = Catalog(comppath, monitored=False)

    if pathrepl is not None:
        lst = pathrepl.split(":")
        if len(lst) != 2:
            error("Invalid search and replace specification '%s'." % pathrepl)
        pathsrch, pathrepl = lst

    catpaths = collect_catalogs(paths)
    for catpath in catpaths:

        # Open parallel catalog if it exists.
        pcat = None
        if pathrepl is not None:
            pcatpath = catpath.replace(pathsrch, pathrepl, 1)
            if catpath == pcatpath:
                error("Same parallel and target catalog paths for '%s'."
                      % catpath)
            if os.path.isfile(pcatpath):
                pcat = Catalog(pcatpath, monitored=False)

        # If there is neither the parallel catalog nor the compendium,
        # skip processing current target catalog.
        if not pcat and not ccat:
            continue

        # Collect messages and texts to translate.
        cat = Catalog(catpath, wrapf=wrapf)
        pmsgs, psmsgs, ptexts = [], [], []
        cmsgs, csmsgs, ctexts = [], [], []
        for msg in cat:
            if to_translate(msg, options):
                # Priority: parallel catalog, then compendium.
                for scat, msgs, smsgs, texts in (
                    (pcat, pmsgs, psmsgs, ptexts),
                    (ccat, cmsgs, csmsgs, ctexts),
                ):
                    if scat and msg in scat:
                        smsg = scat[msg]
                        if smsg.translated:
                            msgs.append(msg)
                            smsgs.append(smsg)
                            texts.extend(smsg.msgstr)
                            break

        # Translate collected texts.
        texts_tr = []
        for texts, scat in ((ptexts, pcat), (ctexts, ccat)):
            transerv = get_transerv(slang, tlang, scat, cat, tsbuilder)
            texts_tr.append(transerv.translate(texts))
            if texts_tr[-1] is None:
                texts_tr = None
                break
        if texts_tr is None:
            warning("Skipping '%s' due to translation service failure."
                    % catpath)
            continue
        ptexts_tr, ctexts_tr = texts_tr

        # Put translated texts into messages.
        # For plural messages, assume 1-1 match to parallel language.
        for msgs, smsgs, texts in (
            (pmsgs, psmsgs, ptexts_tr),
            (cmsgs, csmsgs, ctexts_tr),
        ):
            for msg, smsg in zip(msgs, smsgs):
                ctexts = []
                for i in range(len(smsg.msgstr)):
                    ctexts.append(texts.pop(0))
                for i in range(len(msg.msgstr)):
                    msg.msgstr[i] = i < len(ctexts) and ctexts[i] or ctexts[-1]
                    decorate(msg, options)

        sync_rep(cat, pmsgs + cmsgs)


def to_translate (msg, options):

    return msg.untranslated


_flag_mtrans = u"mtrans"

def decorate (msg, options):

    msg.unfuzzy() # clear any previous fuzzy stuff
    msg.fuzzy = True
    if options.flag_mtrans:
        msg.flag.add(_flag_mtrans)


# Cache of translation services by (source, target) language pair.
_transervs = {}

# Return translation service for (slang, tlang) pair.
# If the service was not created yet, create it and cache it.
# If slang or tlang are None, use target language of corresponding catalog.
def get_transerv (slang, tlang, scat, tcat, tsbuilder):

    if not slang:
        slang = scat.header.get_field_value("Language")
        if not slang:
            error("Cannot determine language of source catalog '%s'."
                  % scat.filename)
    if not tlang:
        tlang = tcat.header.get_field_value("Language")
        if not tlang:
            error("Cannot determine language of target catalog '%s'."
                  % tcat.filename)

    trdir = (slang, tlang)
    if trdir not in _transervs:
        _transervs[trdir] = tsbuilder(slang, tlang)

    return _transervs[trdir]


def sync_rep (cat, mmsgs):

    if cat.sync():
        report("%s (%s)" % (cat.filename, len(mmsgs)))


# ----------------------------------------
# Apertium -- a free/open-source machine translation platform
# http://www.apertium.org/

class Translator_apertium (object):

    def __init__ (self, slang, tlang, options):

        cmdpath = "/usr/bin/apertium"
        if options.transerv_bin:
            cmdpath = options.transerv_bin
        if not os.path.isfile(cmdpath):
            error("Apertium executable not found at '%s'." % cmdpath)

        mode = "%s-%s" % (slang, tlang)

        self.cmdline = "%s %s -u -f html" % (cmdpath, mode)

        entpath = os.path.join(rootdir(), "spec", "html.entities")
        self.htmlents = read_entities(entpath)


    def translate (self, texts):

        if len(texts) == 0:
            return []

        # Serialize texts to send to Apertium in one go.
        # Separate texts with an inplace tag followed by dot,
        # to have each text interpreted as standalone sentence.
        # FIXME: Any way to really translate each text in turn,
        # without it being horribly slow?
        sep0 = "<br class='..."
        sep1 = ""
        sep2 = "'/>."
        sep = None
        while not sep: # determine shortest acceptable separator
            sep = sep0 + sep1 + sep2
            for text in texts:
                if sep in text:
                    sep = None
                    break
        stext = sep.join(texts)

        res = collect_system(self.cmdline, instr=stext)
        if res[2] != 0:
            warning("Executing Apertium failed:\n%s" % res[0])
            # ...really res[0], error is output to stdout. Tsk.
            return None

        texts_tr = res[0].split(sep)
        if len(texts_tr) != len(texts):
            warning("Apertium reported wrong number of translations (%d/%d)."
                    % (len(texts_tr), len(texts)))
            return None

        texts_tr = [resolve_entities_simple(x, self.htmlents) for x in texts_tr]

        return texts_tr


# ----------------------------------------

# Collect defined translation services by name.
_known_transervs = {}
def _init ():
    tspref = "Translator_"
    for locvar, locval in globals().items():
        if locvar.startswith(tspref):
            _known_transervs[locvar[len(tspref):]] = locval
_init()


if __name__ == '__main__':
    main()
