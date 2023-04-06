# -*- coding: utf-8 -*-

"""
Spell-check translation using Enchant (U{http://www.abisource.com/projects/enchant/}).

Documented in C{doc/user/sieving.docbook}.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import codecs
from functools import cmp_to_key
from locale import strcoll
import os
from pathlib import Path
import re
import tempfile
from time import strftime

from pology import PologyError, datadir, _, n_
from pology.spell import flag_no_check_spell, elist_well_spelled
from pology.colors import cjoin
from pology.comments import manc_parse_list, manc_parse_flag_list
import pology.config as cfg
from pology.getfunc import get_hook_ireq
from pology.msgreport import report_on_msg
from pology.msgreport import report_msg_to_lokalize
from pology.msgreport import spell_xml_error
from pology.report import report, warning, format_item_list
from pology.sieve import SieveError, SieveCatalogError
from pology.split import proper_words
from pology.sieve import add_param_spellcheck, add_param_poeditors


def setup_sieve (p):

    p.set_desc(_("@info sieve description",
    "Spell-check translation using Enchant."
    ))

    p.add_param("provider", str, seplist=True,
                metavar=_("@info sieve parameter value placeholder", "NAME"),
                desc=_("@info sieve parameter description",
    "The spell-checking provider to use. "
    "Several provider can be given as comma-separated list."
    ))

    add_param_spellcheck(p)

    p.add_param("xml", str,
                metavar=_("@info sieve parameter value placeholder", "FILE"),
                desc=_("@info sieve parameter description",
    "Build XML report file at given path."
    ))


def normalize_msgid_word(word):
    return re.sub(r"['’]s$", "", word).lower()


class Sieve (object):

    def __init__ (self, params):

        cfgs = cfg.section("enchant")

        self.providers = (   ",".join(params.provider or "")
                          or cfgs.string("provider")
                          or None)

        self.lang = (   params.lang
                     or cfgs.string("language")
                     or None)

        self.envs = params.env
        if self.envs is None and cfgs.string("environment") is not None:
            self.envs = cfgs.string("environment").split(",")
        if self.envs is None:
            self.envs = []
        self.envs = [x.strip() for x in self.envs]

        self.accel = params.accel

        self.markup = params.markup

        self.skip_rx = None
        if params.skip is not None:
            flags = re.U
            if not params.case:
                flags |= re.I
            self.skip_rx = re.compile(params.skip, flags)

        self.pfilters = [[get_hook_ireq(x, abort=True), x]
                         for x in (params.filter or [])]

        self.suponly = params.suponly

        self.words_only = params.list
        self.lokalize = params.lokalize

        # File we are processing
        self.filename = ""
        # File used for the XML output, if requested
        self.xmlFile = None

        # Langenv-dependent elements built along the way.
        self.checkers = {}
        self.word_lists = {}

        # Tracking of unknown words.
        self.unknown_words = set()

        # Indicators to the caller:
        self.caller_sync = False # no need to sync catalogs
        self.caller_monitored = False # no need for monitored messages

        if params.xml:
            try:
                # TODO: create nice api to manage xml file in rules.py
                self.xmlFile = Path(params.xml).open("w")
                self.xmlFile.write('<?xml version="1.0" encoding="UTF-8"?>\n')
                self.xmlFile.write('<pos date="%s">\n' % strftime('%c'))
            except Exception as exc:
                warning(_("@info",
                          "Cannot open file '%(file)s': %(ex)s. XML output "
                          "disabled.", file=params.xml, ex=exc))


    def process_header (self, hdr, cat):

        # Check if the catalog itself states the language, and if yes,
        # create the language-dependent stuff if not already created
        # for this langenv.
        clang = self.lang or cat.language()
        if not clang:
            raise SieveCatalogError(
                _("@info",
                  "Cannot determine language for catalog '%(file)s'.",
                  file=cat.filename))
        cenvs = self.envs or cat.environment() or []
        ckey = (clang, tuple(cenvs))
        if ckey not in self.checkers:
            # Get Pology's internal word list for this langenv.
            if clang not in self.word_lists: # may be in but None
                self.word_lists[ckey] = _compose_word_list(clang, cenvs)
            # Create spell-checker object.
            clang_mod = (self.suponly and [None] or [clang])[0]
            checker = _create_checker(self.providers, clang_mod,
                                      self.word_lists[ckey])
            if not checker:
                raise SieveError(
                    _("@info",
                      "No spelling dictionary for language '%(lang)s' and "
                      "provider '%(prov)s'.",
                      lang=clang, prov=self.providers))
            self.checkers[ckey] = checker

        # Get language-dependent stuff.
        self.checker = self.checkers[ckey]

        # Force explicitly given accelerators and markup.
        if self.accel is not None:
            cat.set_accelerator(self.accel)
        if self.markup is not None:
            cat.set_markup(self.markup)

        # Close previous/open new XML section.
        if self.xmlFile:
            filename = Path(cat.filename).name
            # Close previous PO.
            if self.filename != "":
                self.xmlFile.write("</po>\n")
            self.filename = filename
            # Open new PO.
            poTag='<po name="%s">\n' % filename
            self.xmlFile.write(poTag) # Write to result


    def process (self, msg, cat):

        if not msg.translated:
            return

        if (
            msg.msgctxt
            and re.search(r"^(EMAIL|NAME) OF TRANSLATORS$", msg.msgctxt)
        ):
            return

        failed_w_suggs = []
        msgstr_cnt = 0

        msgid_words = [
            normalize_msgid_word(word)
            for word in proper_words(
                msg.msgid,
                True,
                cat.accelerator(),
                msg.format,
            )
        ]

        for msgstr in msg.msgstr:

            # Skip message if explicitly requested.
            if flag_no_check_spell in manc_parse_flag_list(msg, "|"):
                continue

            # Apply precheck filters.
            for pfilter, pfname in self.pfilters:
                try: # try as type F1A hook
                    msgstr = pfilter(msgstr)
                except TypeError:
                    try: # try as type F3* hook
                        msgstr = pfilter(msgstr, msg, cat)
                    except TypeError:
                        raise SieveError(
                            _("@info",
                              "Cannot execute filter '%(filt)s'.",
                              filt=pfname))

            # Split text into words.
            # TODO: See to use markup types somehow.
            words = proper_words(msgstr, True, cat.accelerator(), msg.format)

            # Eliminate from checking words matching the skip regex.
            if self.skip_rx:
                words = [x for x in words if not self.skip_rx.search(x)]

            # Eliminate from checking words explicitly listed as good.
            locally_ignored = manc_parse_list(msg, elist_well_spelled, ",")
            words = [x for x in words if x not in locally_ignored]

            for word in words:
                if word.lower() in msgid_words:
                    continue

                if self.checker.check(word):
                    continue

                failed = True
                self.unknown_words.add(word)

                if not self.words_only or self.lokalize:
                    suggs = self.checker.suggest(word)
                    incmp = False
                    if len(suggs) > 5: # do not put out too many words
                        suggs = suggs[:5]
                        incmp = True
                    failed_w_suggs.append((word, suggs))

                if not self.words_only:
                    if self.xmlFile:
                        xmlError = spell_xml_error(msg, cat, word, suggs,
                                                    msgstr_cnt)
                        self.xmlFile.writelines(xmlError)

                    if suggs:
                        fsuggs = format_item_list(suggs, incmp=incmp)
                        report_on_msg(_("@info",
                                        "Unknown word '%(word)s' "
                                        "(suggestions: %(wordlist)s).",
                                        word=word, wordlist=fsuggs),
                                        msg, cat)
                    else:
                        report_on_msg(_("@info",
                                        "Unknown word '%(word)s'.",
                                        word=word),
                                        msg, cat)

            msgstr_cnt += 1 # Increase msgstr id count

        if self.lokalize and failed_w_suggs:
            repls = [_("@label", "Spelling errors:")]
            for word, suggs in failed_w_suggs:
                if suggs:
                    fmtsuggs=format_item_list(suggs, incmp=incmp)
                    repls.append(_("@item",
                                   "%(word)s (suggestions: %(wordlist)s)",
                                   word=word, wordlist=fmtsuggs))
                else:
                    repls.append("%s" % (word))
            report_msg_to_lokalize(msg, cat, cjoin(repls, "\n"))


    def finalize (self):

        if self.unknown_words:
            if not self.words_only:
                nwords = len(self.unknown_words)
                msg = n_("@info:progress",
                         "Encountered %(num)d unknown word.",
                         "Encountered %(num)d unknown words.",
                         num=nwords)
                report("===== " + msg)
            else:
                wlist = list(self.unknown_words)
                wlist.sort(key=cmp_to_key(strcoll))
                report("\n".join(wlist))

        if self.xmlFile:
            self.xmlFile.write("</po>\n")
            self.xmlFile.write("</pos>\n")
            self.xmlFile.close()


# Get checker object from Enchant.
def _create_checker (providers, langtag, words):

    try:
        import enchant
    except ImportError:
        pkgs = ["python-enchant"]
        raise PologyError(_("@info",
                            "Python wrapper for Enchant not found, "
                            "please install it (possible package names: "
                            "%(pkglist)s).",
                            pkglist=format_item_list(pkgs)))

    if langtag is not None:
        try:
            broker = enchant.Broker()
            if providers is not None:
                broker.set_ordering(langtag, providers)
            checker = broker.request_dict(langtag)
            checker.check(".")
        except:
            checker = None
    else:
        tmpf = tempfile.NamedTemporaryFile()
        tmpf.close()
        checker = enchant.request_pwl_dict(tmpf.name)
        os.unlink(tmpf.name)

    if checker:
        pname = checker.provider.name.split()[0].lower()
        need_upcasing = (pname in ("personal", "myspell"))
        for word in words or []:
            checker.add_to_session(word)
            if need_upcasing:
                checker.add_to_session(word[0].upper() + word[1:])
                checker.add_to_session(word.upper())
    return checker


# Collect words from all internal word lists
# available for given language+environment.
def _compose_word_list (lang, envs):

    # Collect all applicable word list files.
    wlist_files = set()
    for env in (envs or [""]):
        wlist_files.update(_get_word_list_files(lang, env))
    wlist_files = list(wlist_files)
    wlist_files.sort()

    # Read words.
    words = []
    for wlist_file in wlist_files:
        words.extend(_read_wlist_aspell(wlist_file))
    return words


def _get_word_list_files (lang, env):

    # Collect word list paths.
    wlist_files = set()
    spell_root = os.path.join(datadir(), "lang", lang, "spell")
    spell_subdir = os.path.join(".", (env or ""))
    while spell_subdir:
        spell_dir = os.path.join(spell_root, spell_subdir)
        if os.path.isdir(spell_dir):
            for item in os.listdir(spell_dir):
                if item.endswith(".aspell"):
                    wlist_files.add(os.path.join(spell_dir, item))
        spell_subdir = os.path.dirname(spell_subdir)
    return wlist_files


# Read words from an Aspell word list.
def _read_wlist_aspell (fname):

    # Parse the header for encoding.

    defenc = "UTF-8"
    fl = codecs.open(fname, "r", defenc)
    header = fl.readline()
    m = re.search(r"^(\S+)\s+(\S+)\s+(\d+)\s+(\S+)\s*", header)
    if not m:
        warning(_("@info",
                  "Malformed header in dictionary file '%(file)s'.",
                  file=fname))
        return []
    enc = m.group(4)
    # Reopen in correct encoding if not the default.
    if enc.lower() != defenc.lower():
        fl.close()
        fl = codecs.open(fname, "r", enc)

    # Read words.
    words = []
    for line in fl:
        word = line.strip()
        if word:
            words.append(word)
    return words
