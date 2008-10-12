# -*- coding: UTF-8 -*-

"""
Check linguistic, language-dependent correctness of text.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import os
import codecs
import re

from pology import rootdir
from pology.external.pyaspell import Aspell, AspellConfigError, AspellError
from pology.misc.report import warning, error
from pology.misc.comments import manc_parse_flag_list, manc_parse_list
from pology.misc.msgreport import report_on_msg


# Pipe flag to manually prevent spellcheck for a particular message.
flag_no_check_spell = "no-check-spell"

# Embedded list of words manually declared valid for a particular message.
elist_well_spelled = "well-spelled:"


def check_spell (lang, encoding="UTF-8", variety=None, extopts={},
                 env=None, suponly=False, maxsugg=5):
    """
    Check spelling using Aspell.

    Aspell language is selected by the C{lang} parameter, which should be
    a language code of one of the installed spelling dictionaries.
    Text encoding used by the dictionary is provided by the C{encoding}
    parameter. If the dictionary comes in several varieties, a non-default
    one is selected using the C{variety} parameter.
    Any additional options from the set of Aspell configuration fields can
    be passed in as (name, value) dictionary by the C{extopts} parameter.

    Pology may contain internal supplemental dictionaries for selected
    language in C{l10n/<lang>/spell/} directory, and these are automatically
    picked up. Any subdirectories in C{l10n/<lang>/spell/} are considered
    as to contain supplemental dictionaries in special "environments"
    (e.g. jargon, certain projects, etc.), and are not included by default.
    A certain environment can be included by the C{env} parameter, which
    is a relative path of subdirectory, i.e. C{l10n/<lang>/spell/<env>}.
    When environment is selected, all supplemental dictionaries in its
    directory and all parent directories are included.

    Aspell's system dictionary can be completely excluded from the check
    by the C{suponly} parameter, when the check will use only internal
    supplemental dictionaries.

    Misspelled words are reported to stdout, with suggestions if available.
    Maximum number of suggestions to display is selected by the C{maxsugg}
    parameter; if negative, all suggestions are shown.

    Spelling is performed by internally splitting text into words, and
    querying Aspell word by word. Spliting is performed in a simple fashion;
    it is assumed that text has been appropriately filtered down to plain text,
    e.g. that any XML-like markup and other literals have been removed
    (see L{hook.remove_subs} for filtering possibilities).

    @param lang: language of spelling dictionary
    @type lang: string
    @param encoding: encoding used by the dictionary
    @type encoding: string
    @param variety: variety of dictionary
    @type variety: string
    @param extopts: additional options to send to Aspell
    @type extopts: dict
    @param env: environment for supplemental dictionaries
    @type env: string
    @param suponly: whether to use only supplemental dictionaries
    @type suponly: bool
    @param maxsugg: maximum number of suggestions to show for misspelled word
    @type maxsugg: int

    @note: Hook type factory: C{(cat, msg, text) -> None}
    """

    return _check_spell_w(lang, encoding, variety, extopts,
                          env, suponly, maxsugg, False)


def check_spell_sp (lang, encoding="UTF-8", variety=None, extopts={},
                    env=None, suponly=False, maxsugg=5):
    """
    Like L{check_spell}, except that erroneous spans are returned
    instead of reporting problems to stdout.

    @note: Hook type factory: C{(cat, msg, text) -> spans}
    """

    return _check_spell_w(lang, encoding, variety, extopts,
                          env, suponly, maxsugg, True)


def _check_spell_w (lang, encoding, variety, extopts,
                    env, suponly, maxsugg, spanrep):
    """
    Worker for C{check_spell*} hook factories.
    """

    # Get Pology's internal personal dictonary for this language.
    dictpath, temporary = _compose_personal_dict(lang, env)

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

        aopts = dict([(x, y.encode(encoding)) for x, y in aopts.items()])

        # Create Aspell object.
        try:
            checker = Aspell(aopts.items())
        except AspellConfigError, e:
            error("Aspell configuration error:\n%s" % e)
        except AspellError, e:
            error("cannot initialize Aspell given configuration:\n%s" % e)
    else:
        # Create simple internal checker that only checks against
        # internal supplemental dictionaries.
        if not dictpath:
            error("no supplemental dictionaries found")
            raise Exception
        checker = _QuasiSpell(dictpath, encoding)

    # Composited dictionary read by now, remove if temporary file.
    if temporary:
        os.unlink(dictpath)

    # FIXME: It is said that no fancy word-splitting is done on the text,
    # but still, best to split it assuming plain text?
    wsplit_rx = re.compile("\w+", re.U)
    purenum_rx = re.compile("^\d*$", re.U)
    def wsplit (cat, msg, text):
        word_spans = []
        for m in wsplit_rx.finditer(text):
            word, span = m.group(0), m.span()
            if not purenum_rx.search(word):
                word_spans.append((word, span))
        return word_spans

    # The hook itself.
    def hook (cat, msg, msgstr):

        if spanrep: defret = ([],)
        else: defret = None

        # Skip message if explicitly requested.
        if flag_no_check_spell in manc_parse_flag_list(msg, "|"):
            return defret

        # Split text into words and spans: [(word, (start, end)), ...]
        word_spans = wsplit(cat, msg, msgstr)

        # Ignore words explicitly listed as good.
        ignored_words = set(manc_parse_list(msg, elist_well_spelled, ","))
        word_spans = [x for x in word_spans if x[0] not in ignored_words]

        spans = []
        for word, span in word_spans:
            encword = word.encode(encoding)
            if not checker.check(encword):
                encsuggs = checker.suggest(encword)
                maxsugg = 5 # limit to some reasonable number
                if maxsugg > 0 and len(encsuggs) > maxsugg:
                    encsuggs = encsuggs[:maxsugg] + ["..."]
                suggs = [x.decode(encoding) for x in encsuggs]
                if maxsugg != 0:
                    snote = ("unknown word '%s' (suggestions: %s)"
                             % (word, ", ".join(suggs)))
                else:
                    snote = ("unknown word '%s'" % word)
                spans.append(span + (snote,))

        if spanrep:
            return (spans,)
        else:
            for span in spans:
                if span[2:]:
                    report_on_msg(span[2], msg, cat)

    return hook


# Collect all personal dictionaries found for given language/environment
# and composit them into one file to pass to Aspell.
# Environment is given as a relative subpath into the language directory;
# a dictionary belongs to that environment if it is in the directory
# pointed by the subpath, or any of the parent directories.
# Return the path to composited file or None if there were no dictionaries,
# and whether the file is really a temporary composition or not.
def _compose_personal_dict (lang, env=None):

    # Collect all applicable dictionary files.
    # those in the given environment subdirectory and all above it.
    dictpaths = set()
    spell_root = os.path.join(rootdir(), "l10n", lang, "spell")
    spell_sub = os.path.join(".", (env or ""))
    while spell_sub:
        spell_dir = os.path.join(spell_root, spell_sub)
        if os.path.isdir(spell_dir):
            for item in os.listdir(spell_dir):
                if item.endswith(".aspell"):
                    dictpaths.add(os.path.join(spell_dir, item))
        spell_sub = os.path.dirname(spell_sub)
    dictpaths = list(dictpaths)

    if not dictpaths:
        return None, False

    # If only one dictionary found, Aspell can use it as-is.
    if len(dictpaths) == 1:
        return dictpaths[0], False

    # Composit all dictionary files into one temporary.
    words = []
    for dictpath in dictpaths:
        words.extend(_read_dict_file(dictpath))
    # FIXME: A better location/name for the temporary file?
    dictpath_comp = ".comp-pers-dict.aspell"
    try:
        file = codecs.open(dictpath_comp, "w", "UTF-8")
        file.write("personal_ws-1.1 %s %d UTF-8\n" % (lang, len(words)))
        file.writelines([x + "\n" for x in words])
        file.close()
    except Exception, e:
        error("cannot create composited spelling dictionary "
              "in current working directory:\n%s" % e)

    return dictpath_comp, True


# Read words from Aspell personal dictionary.
def _read_dict_file (filepath):

    # Parse the header for encoding.
    enc_def = "UTF-8"
    file = codecs.open(filepath, "r", enc_def)
    header = file.readline()
    m = re.search(r"^(\S+)\s+(\S+)\s+(\d+)\s+(\S+)\s*", header)
    if not m:
        error("malformed header in dictionary file '%s'" % filepath)
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

