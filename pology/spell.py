# -*- coding: UTF-8 -*-

"""
Check spelling in text using different spell checkers.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
author: Javier Vinal (Javier Viñal) <fjvinal@gmail.com>
@license: GPLv3
"""

import os
import codecs
import re
import tempfile

from pology import PologyError, datadir, _, n_
from pology.comments import manc_parse_flag_list, manc_parse_list
import pology.config
from pology.msgreport import report_on_msg
from pology.report import warning, format_item_list


# Pipe flag to manually prevent spellcheck for a particular message.
flag_no_check_spell = "no-check-spell"

# Embedded list of words manually declared valid for a particular message.
elist_well_spelled = "well-spelled:"


def check_spell (lang=None, encoding="UTF-8", variety=None, extopts={},
                 envs=None, suponly=False, maxsugg=5):
    """
    Check spelling using Aspell [hook factory].

    Aspell language is selected by the C{lang} parameter, which should be
    a language code of one of the installed spelling dictionaries.
    Text encoding used by the dictionary is provided by the C{encoding}
    parameter. If the dictionary comes in several varieties, a non-default
    one is selected using the C{variety} parameter.
    Any additional options from the set of Aspell configuration fields can
    be passed in as (name, value) dictionary by the C{extopts} parameter.

    Pology may contain internal supplemental dictionaries for selected
    language in C{lang/<lang>/spell/} directory, and these are automatically
    picked up. Any subdirectories in C{lang/<lang>/spell/} are considered
    as to contain supplemental dictionaries in special "environments"
    (e.g. jargon, certain projects, etc.), and are not included by default.
    Such environments can be included by the C{envs} parameter, which
    is a list of relative paths added to C{lang/<lang>/spell/} directory.
    All supplemental dictionaries from such paths are included, as well as
    from all their parent directories up to C{lang/<lang>/spell/}
    (this makes supplemental dictionaries hierarchical, e.g.
    environment C{foo/bar} is a child of C{foo}, and thus when C{foo/bar}
    is requested, both its and supplements of C{foo} are used).

    If C{lang} is C{None}, then automatic detection of the language based
    on the catalog of the message is attempted
    (see catalog L{language()<catalog.Catalog.language>} method).
    Similar is attempted for environments if C{env} is C{None}
    (see catalog L{environment()<catalog.Catalog.environment>} method).

    Aspell's system dictionary can be completely excluded from the check
    by the C{suponly} parameter, when the check will use only internal
    supplemental dictionaries.

    Misspelled words are reported to stdout, with suggestions if available.
    Maximum number of suggestions to display is selected by the C{maxsugg}
    parameter; if negative, all suggestions are shown.

    Spell checking is performed by internally splitting text into words, and
    querying Aspell word by word. Spliting is performed in a simple fashion;
    it is assumed that text has been appropriately filtered down to plain text,
    e.g. that any XML-like markup and other literals have been removed
    (see L{pology.remove} for filtering possibilities).

    Spell checking can be skipped entirely on a message by issuing
    the C{no-check-spell} L{sieve flag<sieve.parse_sieve_flags>}.
    Alternatively, only certain words may be declared well spelled
    by adding a manual comment starting with C{well-spelled:}
    and followed by comma-separated list of words. Example::

        # |, no-check-spell
        msgid "Aaaargh, gahhh, khh..."
        msgstr ""

        # well-spelled: Aaaargh, kh
        msgid "Aaaargh, kh, kh... I have been defeated...!"
        msgstr ""

    @param lang: language of spelling dictionary
    @type lang: string
    @param encoding: encoding used by the dictionary
    @type encoding: string
    @param variety: variety of dictionary
    @type variety: string
    @param extopts: additional options to send to Aspell
    @type extopts: dict
    @param envs: environments for supplemental dictionaries
    @type envs: list of strings
    @param suponly: whether to use only supplemental dictionaries
    @type suponly: bool
    @param maxsugg: maximum number of suggestions to show for misspelled word
    @type maxsugg: int

    @return: type S3A hook
    @rtype: C{(text, msg, cat) -> numerr}
    """

    provider = "aspell-raw"
    return _check_spell_w(provider, lang, encoding, variety, extopts,
                          envs, suponly, maxsugg, False)


def check_spell_sp (lang=None, encoding="UTF-8", variety=None, extopts={},
                    envs=None, suponly=False, maxsugg=5):
    """
    Like L{check_spell}, except that erroneous spans are returned
    instead of reporting problems to stdout [hook factory].

    @return: type V3A hook
    @rtype: C{(text, msg, cat) -> spans}
    """

    provider = "aspell-raw"
    return _check_spell_w(provider, lang, encoding, variety, extopts,
                          envs, suponly, maxsugg, True)


def _check_spell_w (provider, lang, encoding, variety, extopts,
                    envs, suponly, maxsugg, spanrep):
    """
    Worker for C{check_spell*} hook factories.
    """

    # FIXME: It is said that no fancy word-splitting is done on the text,
    # but still, best to split it assuming plain text?
    wsplit_rx = re.compile(r"[^\W\d_]+", re.U)
    def wsplit (text, msg, cat):
        word_spans = []
        for m in wsplit_rx.finditer(text):
            word, span = m.group(0), m.span()
            word_spans.append((word, span))
        # ...could have been a single comprehension, but may need expansion.
        return word_spans

    # Resolve provider.
    if provider != "aspell-raw":
        enchant_cfg = pology.config.section("enchant")
        if not provider:
            provider = enchant_cfg.string("provider")
            if not provider:
                raise PologyError(_("@info", "Enchant provider not set."))

    # Cache for constructed checkers.
    checkers = {}

    # The checker itself.
    def spcheck (text, msg, cat):

        # Check if new spell checker should be constructed.
        if lang is not None:
            clang = lang
        elif cat.language() is not None:
            clang = cat.language()
        elif provider != "aspell-raw":
            clang = enchant_cfg.string("language")
        else:
            clang = None
        if not clang:
            raise PologyError(
                _("@info",
                  "Cannot determine language for catalog '%(file)s'.",
                  file=cat.filename))
        if envs is not None:
            cenvs = envs
        elif cat.environment() is not None:
            cenvs = cat.environment()
        elif provider != "aspell-raw":
            envs_str = enchant_cfg.string("environment")
            cenvs = envs_str.split(",") if envs_str else []
        else:
            cenvs = []
        ckey = (clang, tuple(cenvs))
        if ckey not in checkers:
            if provider != "aspell-raw":
                checkers[ckey] = _construct_enchant(provider, clang, cenvs,
                                                    encoding, variety, suponly)
            else:
                checkers[ckey] = _construct_aspell(clang, cenvs, encoding,
                                                   variety, extopts, suponly)

        checker = checkers[ckey]

        # Prepare shortcut reports.
        if spanrep: defret = []
        else: defret = 0

        # Skip message if explicitly requested.
        if flag_no_check_spell in manc_parse_flag_list(msg, "|"):
            return defret

        # Split text into words and spans: [(word, (start, end)), ...]
        word_spans = wsplit(text, msg, cat)

        # Ignore words explicitly listed as good.
        ignored_words = set(manc_parse_list(msg, elist_well_spelled, ","))
        word_spans = [x for x in word_spans if x[0] not in ignored_words]

        spans = []
        for word, span in word_spans:
            encword = word.encode(encoding)
            if not checker.check(encword):
                encsuggs = checker.suggest(encword)
                maxsugg = 5 # limit to some reasonable number
                incmp = False
                if maxsugg > 0 and len(encsuggs) > maxsugg:
                    encsuggs = encsuggs[:maxsugg]
                    incmp = True
                suggs = [x.decode(encoding) for x in encsuggs]
                if maxsugg != 0 and suggs:
                    fmtsuggs = format_item_list(suggs, incmp=incmp)
                    snote = _("@info",
                              "Unknown word '%(word)s' "
                              "(suggestions: %(wordlist)s).",
                              word=word, wordlist=fmtsuggs)
                else:
                    snote = _("@info",
                              "Unknown word '%(word)s'.",
                              word=word)
                spans.append(span + (snote,))

        if spanrep:
            return spans
        else:
            for span in spans:
                if span[2:]:
                    report_on_msg(span[2], msg, cat)
            return len(spans)

    return spcheck


# Construct Aspell checker for given langenv.
def _construct_aspell (lang, envs, encoding, variety, extopts, suponly):

    # Get Pology's internal personal dictonary for this language.
    dictpath, temporary = _compose_personal_dict(lang, envs)

    if not suponly:
        # Prepare Aspell options.
        aopts = {}
        aopts["lang"] = lang
        aopts["encoding"] = encoding
        if variety:
            aopts["variety"] = variety
        if dictpath:
            aopts["personal-path"] = dictpath
        if extopts:
            aopts.update(extopts)

        aopts = dict([(x, y.encode(encoding)) for x, y in list(aopts.items())])

        # Create Aspell object.
        import pology.external.pyaspell as A
        try:
            checker = A.Aspell(list(aopts.items()))
        except A.AspellConfigError as e:
            raise PologyError(
                _("@info",
                  "Aspell configuration error:\n%(msg)s",
                  msg=e))
        except A.AspellError as e:
            raise PologyError(
                _("@info",
                  "Cannot initialize Aspell:\n%(msg)s",
                  msg=e))
    else:
        # Create simple internal checker that only checks against
        # internal supplemental dictionaries.
        if not dictpath:
            raise PologyError(
                _("@info",
                  "No supplemental dictionaries found."))
        checker = _QuasiSpell(dictpath, encoding)

    # Composited dictionary read by now, remove if temporary file.
    if temporary:
        os.unlink(dictpath)

    return checker


# Collect all personal dictionaries found for given language/environment
# and composit them into one file to pass to Aspell.
# Environment is given as a relative subpath into the language directory;
# a dictionary belongs to that environment if it is in the directory
# pointed by the subpath, or any of the parent directories.
# Return the path to composited file or None if there were no dictionaries,
# and whether the file is really a temporary composition or not.
def _compose_personal_dict (lang, envs):

    # Collect all applicable dictionary files
    # (for a given environment, in its subdirectiory and all above).
    dictpaths = set()
    spell_root = os.path.join(datadir(), "lang", lang, "spell")
    for env in (envs or [""]):
        spell_sub = os.path.join(".", env)
        while spell_sub:
            spell_dir = os.path.join(spell_root, spell_sub)
            if os.path.isdir(spell_dir):
                for item in os.listdir(spell_dir):
                    if item.endswith(".aspell"):
                        dictpaths.add(os.path.join(spell_dir, item))
            spell_sub = os.path.dirname(spell_sub)
    dictpaths = list(dictpaths)
    dictpaths.sort()

    if not dictpaths:
        return None, False

    # If only one dictionary found, Aspell can use it as-is.
    if len(dictpaths) == 1:
        return dictpaths[0], False

    # Composit all dictionary files into one temporary.
    words = []
    for dictpath in dictpaths:
        words.extend(_read_dict_file(dictpath))
    tmpf = tempfile.NamedTemporaryFile()
    tmpf.close()
    try:
        tmpf = codecs.open(tmpf.name, "w", "UTF-8")
        tmpf.write("personal_ws-1.1 %s %d UTF-8\n" % (lang, len(words)))
        tmpf.writelines([x + "\n" for x in words])
        tmpf.close()
    except Exception as e:
        raise PologyError(
            _("@info",
              "Cannot create composited spelling dictionary "
              "in current working directory:\n%(msg)s",
              msg=e))

    return tmpf.name, True


# Read words from Aspell personal dictionary.
def _read_dict_file (filepath):

    # Parse the header for encoding.
    enc_def = "UTF-8"
    file = codecs.open(filepath, "r", enc_def)
    header = file.readline()
    m = re.search(r"^(\S+)\s+(\S+)\s+(\d+)\s+(\S+)\s*", header)
    if not m:
        raise PologyError(
            _("@info",
              "Malformed header in dictionary file '%(file)s'.",
              file=filepath))
    enc = m.group(4)
    # Reopen in correct encoding if not the default.
    if enc.lower() != enc_def.lower():
        file.close()
        file = codecs.open(filepath, "r", enc)

    # Read words.
    words = []
    for line in file:
        word = line.strip()
        if word:
            words.append(word)
    return words


# Simple spell checker which reads Aspell's personal dictionary file.
class _QuasiSpell (object):

    def __init__ (self, dictpath, enc="UTF-8"):

        self._words = _read_dict_file(dictpath)
        self._enc = enc # of the raw text sent in for checking


    def check (self, encword):

        word = str.decode(encword, self._enc)
        return (   word in self._words
                or word.lower() in self._words)


    def suggest (self, encword):

        return []


def check_spell_ec (provider=None, lang=None, encoding="UTF-8", variety=None,
                    envs=None, suponly=False, maxsugg=5):
    """
    Check spelling using Enchant [hook factory].

    Enchant provider and language are selected by the C{lang} parameter,
    which should be a language code of one of the installed spelling
    dictionaries. Text encoding used by the dictionary is provided by the
    C{encoding} parameter. If the dictionary comes in several varieties,
    a non-default one is selected using the C{variety} parameter.
    If C{provider} is not given, it will be attempted to fetch it from
    C{[enchant]/provider} user configuration field.

    Pology may contain internal supplemental dictionaries for selected
    language in C{lang/<lang>/spell/} directory, and these are automatically
    picked up. Any subdirectories in C{lang/<lang>/spell/} are considered
    as to contain supplemental dictionaries in special "environments"
    (e.g. jargon, certain projects, etc.), and are not included by default.
    Such environments can be included by the C{envs} parameter, which
    is a list of relative paths added to C{lang/<lang>/spell/} directory.
    All supplemental dictionaries from such paths are included, as well as
    from all their parent directories up to C{lang/<lang>/spell/}
    (this makes supplemental dictionaries hierarchical, e.g.
    environment C{foo/bar} is a child of C{foo}, and thus when C{foo/bar}
    is requested, both its and supplements of C{foo} are used).

    If C{lang} is C{None}, then automatic detection of the language based
    on the catalog of the message is attempted
    (see catalog L{language()<catalog.Catalog.language>} method).
    Similar is attempted for environments if C{env} is C{None}
    (see catalog L{environment()<catalog.Catalog.environment>} method).
    If automatic detection of language does not succeed, finally
    C{[enchant]/language} user configuration field is consulted;
    for environments, C{[enchant]/environment} field is consulted.

    Provider's system dictionary can be completely excluded from the check
    by the C{suponly} parameter, when the check will use only internal
    supplemental dictionaries.

    Misspelled words are reported to stdout, with suggestions if available.
    Maximum number of suggestions to display is selected by the C{maxsugg}
    parameter; if negative, all suggestions are shown.

    Spell checking is performed by internally splitting text into words, and
    querying provider word by word. Spliting is performed in a simple fashion;
    it is assumed that text has been appropriately filtered down to plain text,
    e.g. that any XML-like markup and other literals have been removed
    (see L{pology.remove} for filtering possibilities).

    Spell checking can be skipped entirely on a message by issuing
    the C{no-check-spell} L{sieve flag<sieve.parse_sieve_flags>}.
    Alternatively, only certain words may be declared well spelled
    by adding a manual comment starting with C{well-spelled:}
    and followed by comma-separated list of words. Example::

        # |, no-check-spell
        msgid "Aaaargh, gahhh, khh..."
        msgstr ""

        # well-spelled: Aaaargh, kh
        msgid "Aaaargh, kh, kh... I have been defeated...!"
        msgstr ""

    @param provider: the spell-checking provider to use
    @type provider: string
    @param lang: language of spelling dictionary
    @type lang: string
    @param encoding: encoding used by the dictionary
    @type encoding: string
    @param variety: variety of dictionary
    @type variety: string
    @param envs: environments for supplemental dictionaries
    @type envs: list of strings
    @param suponly: whether to use only supplemental dictionaries
    @type suponly: bool
    @param maxsugg: maximum number of suggestions to show for misspelled word
    @type maxsugg: int

    @return: type S3A hook
    @rtype: C{(text, msg, cat) -> numerr}
    """

    extopts = {}
    return _check_spell_w(provider, lang, encoding, variety, extopts,
                          envs, suponly, maxsugg, False)


def check_spell_ec_sp (provider=None, lang=None, encoding="UTF-8", variety=None,
                       envs=None, suponly=False, maxsugg=5):
    """
    Like L{check_spell_ec}, except that erroneous spans are returned
    instead of reporting problems to stdout [hook factory].

    @return: type V3A hook
    @rtype: C{(text, msg, cat) -> spans}
    """

    extopts = {}
    return _check_spell_w(provider, lang, encoding, variety, extopts,
                          envs, suponly, maxsugg, True)


# Construct Enchant checker for given langenv.
def _construct_enchant (provider, lang, envs, encoding, variety, suponly):

    # Get Pology's internal personal dictonary for this language.
    dictpath, temporary = _compose_personal_dict(lang, envs)

    if not suponly:
        try:
            import enchant
        except ImportError:
            pkgs = ["python-enchant"]
            raise PologyError(_("@info",
                                "Python wrapper for Enchant not found, "
                                "please install it (possible package names: "
                                "%(pkglist)s).",
                                pkglist=format_item_list(pkgs)))

        # Create Enchant broker.
        try:
            broker = enchant.Broker()
        except Exception as e:
            raise PologyError(
                _("@info",
                  "Cannot initialize Enchant:\n%(msg)s",
                  msg=e))

        # Find Enchant language.
        e_langs = list(filter(broker.dict_exists, [variety, lang]))
        if e_langs:
            e_lang = e_langs[0]
        else:
            if variety is not None:
                raise PologyError(
                    _("@info",
                      "Language '%(lang)s' and variety '%(var)s' "
                      "not known to Enchant.",
                      lang=lang, var=variety))
            else:
                raise PologyError(
                    _("@info",
                      "Language '%(lang)s' not known to Enchant.",
                      lang=lang))

        # Choose the provider for the selected language.
        try:
            broker.set_ordering((e_lang or "*"), provider)
        except Exception as e:
            raise PologyError(
                _("@info",
                  "Cannot configure Enchant for provider '%(pvd)s':\n%(msg)s",
                  pvd=provider, msg=e))

        # Create checker and test functionality.
        try:
            if dictpath is None:
                checker = enchant.Dict(e_lang, broker)
            else:
                checker = enchant.DictWithPWL(e_lang, dictpath, None, broker)
            checker.check(".")
        except:
            raise PologyError(
                _("@info",
                  "Enchant test check for language '%(lang)s' failed.",
                  lang=e_lang))
    else:
        # Create simple internal checker that only checks against
        # internal supplemental dictionaries.
        if not dictpath:
            raise PologyError(
                _("@info",
                  "No supplemental dictionaries found."))
        checker = _QuasiSpell(dictpath, encoding)

    # Composited dictionary read by now, remove if temporary file.
    if temporary:
        os.unlink(dictpath)

    return checker


