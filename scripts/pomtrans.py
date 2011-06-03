#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Perform machine translation of PO files.

Documented in C{doc/user/lingo.docbook#sec-lgmtrans}.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

try:
    import fallback_import_paths
except:
    pass

import sys
import os
import locale

from pology import rootdir, version, _, n_
from pology.catalog import Catalog
from pology.message import MessageUnsafe
from pology.colors import ColorOptionParser
from pology.report import report, error, warning
from pology.fsops import collect_catalogs, collect_system
from pology.fsops import str_to_unicode
from pology.fsops import exit_on_exception
import pology.config as pology_config
from pology.entities import read_entities
from pology.resolve import resolve_entities_simple
from pology.remove import remove_accel_msg


def main ():

    locale.setlocale(locale.LC_ALL, "")

    # Get defaults for command line options from global config.
    cfgsec = pology_config.section("pomtrans")

    showservs = list()
    showservs.sort()

    # Setup options and parse the command line.
    usage = _("@info command usage",
        "%(cmd)s [OPTIONS] TRANSERV PATHS...",
        cmd="%prog")
    desc = _("@info command description",
        "Perform machine translation of PO files.")
    ver = _("@info command version",
        u"%(cmd)s (Pology) %(version)s\n"
        u"Copyright © 2009, 2010 "
        u"Chusslove Illich (Часлав Илић) &lt;%(email)s&gt;",
        cmd="%prog", version=version(), email="caslav.ilic@gmx.net")

    opars = ColorOptionParser(usage=usage, description=desc, version=ver)
    opars.add_option(
        "-a", "--accelerator", dest="accel",
        metavar=_("@info command line value placeholder", "CHAR"),
        help=_("@info command line option description",
               "Accelerator marker character used in messages. "
               "Detected from catalogs if not given."))
    opars.add_option(
        "-c", "--parallel-compendium", dest="parcomp",
        metavar=_("@info command line value placeholder", "FILE"),
        help=_("@info command line option description",
               "Translate from translation to another language, "
               "found in compendium file at the given path."))
    opars.add_option(
        "-l", "--list-transervs",
        action="store_true", dest="list_transervs", default=False,
        help="List available translation services.")
    opars.add_option(
        "-m", "--flag-%s" % _flag_mtrans,
        action="store_true", dest="flag_mtrans", default=False,
        help=_("@info command line option description",
              "Add '%(flag)s' flag to translated messages.",
              flag=_flag_mtrans))
    opars.add_option(
        "-M", "--translation-mode", dest="tmode",
        metavar=_("@info command line value placeholder", "MODE"),
        help=_("@info command line option description",
               "Translation mode for the chosen translation service. "
               "Overrides the default translation mode constructed "
               "based on source and target language. "
               "Mode string format is translation service dependent."))
    opars.add_option(
        "-n", "--no-fuzzy-flag",
        action="store_false", dest="flag_fuzzy", default=True,
        help=_("@info command line option description",
               "Do not add '%(flag)s' flag to translated messages.",
               flag="fuzzy"))
    opars.add_option(
        "-p", "--parallel-catalogs", dest="parcats",
        metavar=_("@info command line value placeholder", "SEARCH:REPLACE"),
        help=_("@info command line option description",
               "Translate from translation to another language "
               "found in parallel catalogs. "
               "For given target catalog path, the path to parallel catalog "
               "is constructed by replacing once SEARCH with REPLACE."))
    opars.add_option(
        "-s", "--source-lang", dest="slang",
        metavar=_("@info command line value placeholder", "LANG"),
        help=_("@info command line option description",
               "Source language code. "
               "Detected from catalogs if not given."))
    opars.add_option(
        "-t", "--target-lang", dest="tlang",
        metavar=_("@info command line value placeholder", "LANG"),
        help=_("@info command line option description",
               "Target language code. "
               "Detected from catalogs if not given."))
    opars.add_option(
        "-T", "--transerv-bin", dest="transerv_bin",
        metavar=_("@info command line value placeholder", "PATH"),
        help=_("@info command line option description",
               "Custom path to translation service executable "
               "(where applicable)."))

    (op, free_args) = opars.parse_args(str_to_unicode(sys.argv[1:]))

    # Could use some speedup.
    try:
        import psyco
        psyco.full()
    except ImportError:
        pass

    if op.list_transervs:
        report("\n".join(sorted(_known_transervs.keys())))
        sys.exit(0)

    if len(free_args) < 1:
        error(_("@info",
                "Translation service not specified."))
    transervkey = free_args.pop(0)
    if transervkey not in _known_transervs:
        error(_("@info",
                "Translation service '%(serv)s' not known.",
                serv=transervkey))

    tsbuilder_wopts = _known_transervs[transervkey]
    tsbuilder = lambda slang, tlang: tsbuilder_wopts(slang, tlang, op)

    paths = free_args
    if not op.parcomp and not op.parcats:
        translate_direct(paths, tsbuilder, op)
    else:
        translate_parallel(paths, tsbuilder, op)


def translate_direct (paths, tsbuilder, options):

    transervs = {}

    catpaths = collect_catalogs(paths)
    for catpath in catpaths:

        # Collect messages and texts to translate.
        cat = Catalog(catpath)
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
            warning(_("@info",
                      "Translation service failure on '%(file)s'.",
                      file=catpath))
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


def translate_parallel (paths, tsbuilder, options):

    pathrepl = options.parcats
    comppath = options.parcomp
    slang = options.slang
    tlang = options.tlang

    ccat = None
    if comppath is not None:
        if not os.path.isfile(comppath):
            error(_("@info",
                    "Compendium '%(file)s' does not exist.",
                    file=comppath))
        ccat = Catalog(comppath, monitored=False)

    if pathrepl is not None:
        lst = pathrepl.split(":")
        if len(lst) != 2:
            error(_("@info",
                    "Invalid search and replace specification '%(spec)s'.",
                    spec=pathrepl))
        pathsrch, pathrepl = lst

    catpaths = collect_catalogs(paths)
    for catpath in catpaths:

        # Open parallel catalog if it exists.
        pcat = None
        if pathrepl is not None:
            pcatpath = catpath.replace(pathsrch, pathrepl, 1)
            if catpath == pcatpath:
                error(_("@info",
                        "Parallel catalog and target catalog are same files "
                        "for '%(file)s'.",
                        file=catpath))
            if os.path.isfile(pcatpath):
                pcat = Catalog(pcatpath, monitored=False)

        # If there is neither the parallel catalog nor the compendium,
        # skip processing current target catalog.
        if not pcat and not ccat:
            continue

        # Collect messages and texts to translate.
        cat = Catalog(catpath)
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
            texts_tr.append(transerv.translate(texts) if texts else [])
            if texts_tr[-1] is None:
                texts_tr = None
                break
        if texts_tr is None:
            warning(_("@info",
                      "Translation service failure on '%(file)s'.",
                      file=catpath))
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
    if options.flag_fuzzy:
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
            error(_("@info",
                    "Cannot determine language of source catalog '%(file)s'.",
                    file=scat.filename))
    if not tlang:
        tlang = tcat.header.get_field_value("Language")
        if not tlang:
            error(_("@info",
                    "Cannot determine language of target catalog '%(file)s'.",
                    file=tcat.filename))

    trdir = (slang, tlang)
    if trdir not in _transervs:
        _transervs[trdir] = tsbuilder(slang, tlang)

    return _transervs[trdir]


def sync_rep (cat, mmsgs):

    if cat.sync():
        report("! %s (%s)" % (cat.filename, len(mmsgs)))


# ----------------------------------------
# Apertium -- a free/open-source machine translation platform
# http://www.apertium.org/

class Translator_apertium (object):

    def __init__ (self, slang, tlang, options):

        cmdpath = "/usr/bin/apertium"
        if options.transerv_bin:
            cmdpath = options.transerv_bin
        if not os.path.isfile(cmdpath):
            error(_("@info Apertium is machine translation software",
                    "Apertium executable not found at '%(path)s'.",
                    path=cmdpath))

        if options.tmode is not None:
            mode = options.tmode
        else:
            mode = "%s-%s" % (slang, tlang)

        self.cmdline = "%s %s -u -f html" % (cmdpath, mode)

        entpath = os.path.join(rootdir(), "spec", "html.entities")
        self.htmlents = read_entities(entpath)


    def translate (self, texts):

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
            warning(_("@info",
                      "Executing Apertium failed:\n%(output)s",
                      output=res[0]))
            # ...really res[0], error is output to stdout. Tsk.
            return None

        texts_tr = res[0].split(sep)
        if len(texts_tr) != len(texts):
            warning(_("@info",
                      "Apertium reported wrong number of translations, "
                      "%(num1)d instead of %(num2)d.",
                      num1=len(texts_tr), num2=len(texts)))
            return None

        texts_tr = [resolve_entities_simple(x, self.htmlents) for x in texts_tr]

        return texts_tr


# ----------------------------------------
# Google Translate
# http://translate.google.com

# Communication code derived from py-gtranslate library
# http://code.google.com/p/py-gtranslate/


class Translator_google (object):

    def __init__ (self, slang, tlang, options):

        if options.tmode is not None:
            self.langpair = options.tmode
        else:
            self.langpair = "%s|%s" % (slang, tlang)


    def translate (self, texts):

        import urllib
        try:
            import simplejson
        except:
            error(_("@info",
                    "Python module '%(mod)s' not available. "
                    "Try installing the '%(pkg)s' package.",
                    mod="simplejson", pkg="python-simplejson"))

        baseurl = "http://ajax.googleapis.com/ajax/services/language/translate"
        baseparams = (("v", "1.0"), ("langpair", self.langpair), ("ie", "utf8"))

        texts_tr = []
        for text in texts:
            params = baseparams + (("q", text.encode("utf8")),)
            parfmt = "&".join(["%s=%s" % (p, urllib.quote_plus(v))
                               for p, v in params])
            execurl = "%s?%s" % (baseurl, parfmt)
            try:
                res = simplejson.load(urllib.FancyURLopener().open(execurl))
                text_tr = unicode(res["responseData"]["translatedText"])
            except:
                text_tr = u""
            texts_tr.append(text_tr)

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
    exit_on_exception(main)
