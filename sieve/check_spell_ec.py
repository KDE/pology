# -*- coding: UTF-8 -*-

"""
Spell-check translation using Enchant.

This sieve uses the Enchant library (U{www.abisource.com/projects/enchant/}),
through PyEnchant module (U{pyenchant.sourceforge.net}) to provide
uniform access to different spell-checkers, such as Aspell, Ispell, etc.

Text is first split into words, possibly eliminating markup and other
verbatim content, which are then fed to the spell-checker one by one.

Sieve parameters:
  - C{provider:<pkeyword>}: keyword of the spell-checker to use
  - C{lang:<code>}: language code of the spelling dictionary
  - C{env:<environment>}: comma-separated list of environments of
        internal word lists
  - C{accel:<chars>}: strip these characters as accelerator markers
  - C{markup:<mkeywords>}: markup types by keywords (comma-separated)
  - C{skip:<regex>}: do not check words which match given regular expression
  - C{filter:<hookspec>,...}: apply F1A or F3A/C hook prior to spell checking
        (see L{langdep.get_hook_lreq} for the format of hook specification)
  - C{suponly}: do not use system dictionary, only internal supplements
  - C{list}: only report unknown words to stdout, one per line
  - C{lokalize}: open catalogs at failed messages in Lokalize

If the spell-checking provider is not given by the C{provider} parameter,
it is first looked for in Pology user configuration,
and then by user and system configuration of Enchant.
List of spell-checking providers known to Enchant, to be used as values
to C{provider} parameter, can be obtained by the C{enchant-lsmod} command.
Value of C{provider} (and the corresponding user configuration field)
can also be a comma-separated list in the order of decreasing priority.

When the dictionary language is not given by the C{lang} parameter,
it is first looked for in the current PO file,
then in Pology user configuration, and finaly by current system locale.

If accelerator marker is not given by C{accel} parameter, the sieve will try
to guess it; it may choose wrongly or decide that there are no accelerators.
See L{catalog.Catalog.accelerator} method for ways of specifying
accelerator marker in catalogs.

If markup types are not given by C{markup} parameter, the sieve will try
to guess them; it may choose wrongly or decide that there is no markup.
See L{catalog.Catalog.set_markup} method for known markup types,
and L{catalog.Catalog.markup} for how they may be specified in catalogs.

Pology internally collects language-specific word lists as supplements
to system spelling dictionaries, within C{lang/<lang>/spell/} directory.
These contain either the words that should enter the default dictionary
but have not been added yet, or, more importantly, the words that are
specific to a given translation environment, i.e. too specific to enter
the general dictionary.
The C{env} parameter is used to specify one or more environments for which
word lists are loaded. Each environment is taken to be a subpath within
C{lang/<lang>/spell/<env>}: all word lists in that subpath and
parent directories will be loaded.
This means that the word lists are hierarchical, so that all-environment lists
(loaded even when C{env} parameter is not given) reside directly in
C{lang/<lang>/spell/}, and the more specific ones in subdirectories below it.
If environment is not given by C{env} parameter, and also not in Pology
user configuration, the sieve will try to read it from each catalog in turn.
See L{environment()<catalog.Catalog.environment>} method of catalog
object for the way environments can be specified in catalog header.

The system dictionary can be avoided alltogether, and only supplemental
word lists used instead, by giving the C{suponly} parameter.

Word list files are in Aspell format, and must have C{.aspell} extension.
This is a simple plain text format listing one correct word per line,
except for the first line, the header, which states the language code,
number of words in the list and encoding of the file::

    personal_ws-1.1 fr 1234 UTF-8
    apricot
    banana
    cherry
    ...

The only significant parameter in the header is in fact the encoding.
Language code and number of words can be arbitrary, as this sieve
will not use them.
To maintain alphabetic ordering of word list files
(and put the correct number of words in the header, even if not important)
you can use the L{organizeDict.py<scripts.organizeDict>} script.

It is possible to selectively disable spell-checking for a message,
or certain words within a message, by adding a special manual comment.
The whole message is skipped by the no-sieve flag C{no-check-spell}::

    # |, no-check-spell

and only some words within the message by listing them in C{well-spelled:}
embedded list::

    # well-spelled: word1, word2, ...

Which of these two methods to use depends on the nature of the message and
specifics of spelling checks for given language/environment.
For example, if most of the message consists of valid words, but there are
only one or two which are special in some way, it is probably better to
list them explicitly, so that all other words are checked.

The following user configuration fields are considered:
  - C{[enchant]/provider}: spell-checker to use
  - C{[enchant]/language}: language of the spelling dictionary
  - C{[enchant]/environment}: comma-separate list of environments
        of dictionary supplements
  - C{[enchant]/supplements-only}: use only internal supplement word lists

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import codecs
import locale
import os
import re
import tempfile

from pology import PologyError, rootdir, _, n_
from pology.check_lingo import flag_no_check_spell, elist_well_spelled
from pology.colors import cjoin
from pology.comments import manc_parse_list, manc_parse_flag_list
import pology.config as cfg
from pology.langdep import get_hook_lreq
from pology.msgreport import report_on_msg
from pology.msgreport import report_msg_to_lokalize
from pology.report import report, warning, format_item_list
from pology.sieve import SieveError, SieveCatalogError
from pology.split import proper_words
from pology.stdsvpar import add_param_spellcheck, add_param_poeditors


def setup_sieve (p):

    p.set_desc(_("@info sieve discription",
    "Spell-check translation using Enchant."
    ))

    p.add_param("provider", unicode, seplist=True,
                metavar=_("@info sieve parameter value placeholder", "NAME"),
                desc=_("@info sieve parameter discription",
    "The spell-checking provider to use. "
    "Several provider can be given as comma-separated list."
    ))

    add_param_spellcheck(p)


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
            self.skip_rx = re.compile(params.skip, re.U|re.I)

        self.pfilters = []
        for hreq in params.filter or []:
            pfilter = get_hook_lreq(hreq)
            if pfilter:
                self.pfilters.append((pfilter, hreq))
            else:
                warning(_("@info",
                          "Cannot load filter '%(filt)s'.",
                          filt=hreq))

        self.suponly = params.suponly

        self.words_only = params.list
        self.lokalize = params.lokalize

        # Langenv-dependent elements built along the way.
        self.checkers = {}
        self.word_lists = {}

        # Tracking of unknown words.
        self.unknown_words = set()

        # Indicators to the caller:
        self.caller_sync = False # no need to sync catalogs
        self.caller_monitored = False # no need for monitored messages


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


    def process (self, msg, cat):

        if not msg.translated:
            return

        failed_w_suggs = []

        for msgstr in msg.msgstr:

            # Skip message if explicitly requested.
            if flag_no_check_spell in manc_parse_flag_list(msg, "|"):
                continue

            # Apply precheck filters.
            for pfilter, hreq in self.pfilters:
                try: # try as type F1A hook
                    msgstr = pfilter(msgstr)
                except TypeError:
                    try: # try as type F3* hook
                        msgstr = pfilter(msgstr, msg, cat)
                    except TypeError:
                        raise SieveError(
                            _("@info",
                              "Cannot execute filter '%(filt)s'.",
                              filt=hreq))

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
                if not self.checker.check(word):
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
                wlist.sort(lambda x, y: locale.strcoll(x.lower(), y.lower()))
                report("\n".join(wlist))


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
        for word in words or []:
            checker.add_to_session(word)

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
    spell_root = os.path.join(rootdir(), "lang", lang, "spell")
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

