# -*- coding: UTF-8 -*-

"""
Spell-check messages using GNU Aspell (U{http://aspell.net/}).

This sieve is a more specific counterpart to
L{check-spell-ec<sieve.check_spell_ec>}, which deals only with GNU Aspell
spell checker. Compared to C{check-spell-ec}, it exposes some options specific
to Aspell, and requires no external Python modules, only Aspell installation.

This sieve behaves mostly same as C{check-spell-ec},
and accepts all the same parameters with same meanings;
the exception is the C{provider} parameter,
which is not present here since Aspell is the fixed provider.

Sieve parameters specific to this sieve:
  - C{enc:<encoding>}: encoding for text sent to Aspell
  - C{var:<variety>}: variety of the Aspell dictionary
  - C{xml:<filename>}: build XML report file

The following user configuration fields are considered:
  - C{[aspell]/language}: language of the Aspell dictionary
  - C{[aspell]/encoding}: encoding for text sent to Aspell
  - C{[aspell]/variety}: variety of the Aspell dictionary
  - C{[aspell]/supplements-only}: use only internal dictionaries

@author: Sébastien Renard <sebastien.renard@digitalfox.org>
@license: GPLv3
"""

from pology.sieve import SieveError
from pology.misc.report import report, warning
from pology.misc.msgreport import spell_error, spell_xml_error
from pology.misc.split import proper_words
from pology import rootdir
import pology.misc.config as cfg
from pology.misc.langdep import get_hook_lreq
from pology.misc.comments import manc_parse_list, manc_parse_flag_list
from pology.hook.check_lingo import flag_no_check_spell, elist_well_spelled
from pology.misc.msgreport import report_msg_to_lokalize
import os, re, sys
from os.path import abspath, basename, dirname, isfile, isdir, join
from codecs import open
from time import strftime
import locale

from pology.sieve.check_spell_ec import add_general_spellcheck_params


def setup_sieve (p):

    p.set_desc(
    "Spell-check translation using Aspell."
    )

    add_general_spellcheck_params(p)

    p.add_param("enc", unicode,
                metavar="ENCODING",
                desc=
    "Encoding for text sent to Aspell."
    )
    p.add_param("var", unicode,
                metavar="VARIETY",
                desc=
    "Variety of the Aspell dictionary."
    )
    p.add_param("xml", unicode,
                metavar="FILENAME",
                desc=
    "Build XML report file at given path."
    )
    p.add_param("simsp", bool, defval=False,
                desc=
    "Split text into words in a simpler way "
    "(deprecated, may be removed in the future)."
    )


class Sieve (object):
    """Process messages through the Aspell spell checker"""
    
    def __init__ (self, params):
    
        self.nmatch = 0 # Number of match for finalize
        self.unknownWords=None # If not None, only list of faulty word is display (to ease copy/paste into personal dictionary)
        self.filename=""     # File name we are processing
        self.xmlFile=None # File handle to write XML output

        # Build Aspell options.
        self.aspellOptions = {}

        # - assume markup in messages (provide option to disable?)
        self.aspellOptions["mode"] = "sgml"
        # FIXME: In fact not needed? The words are sent parsed to checker.

        self.lang = params.lang
        self.encoding = params.enc
        self.variety = params.var

        cfgs = cfg.section("aspell")
        if not self.lang:
            self.lang = cfgs.string("language")
        if not self.encoding:
            self.encoding = cfgs.string("encoding")
        if not self.variety:
            self.variety = cfgs.string("variety")

        loc_encoding = locale.getlocale()[1]
        if not self.encoding:
            self.encoding = loc_encoding
        if not self.encoding:
            self.encoding = "UTF-8"

        self.encoding = self._encoding_for_aspell(self.encoding)
        self.aspellOptions["lang"] = str(self.lang)
        self.aspellOptions["encoding"] = str(self.encoding)
        if self.variety:
            self.aspellOptions["variety"] = str(self.variety)

        self.unknownWords = None
        if params.list:
            self.unknownWords = set()

        if params.xml:
            xmlPath=params.xml
            if os.access(dirname(abspath(xmlPath)), os.W_OK):
                #TODO: create nice api to manage xml file and move it to misc/
                self.xmlFile=open(xmlPath, "w", "utf-8")
                self.xmlFile.write('<?xml version="1.0" encoding="UTF-8"?>\n')
                self.xmlFile.write('<pos date="%s">\n' % strftime('%c').decode(locale.getpreferredencoding()))
            else:
                warning("Cannot open %s file. XML output disabled" % xmlPath)

        self.accel = params.accel
        self.markup = params.markup

        self.skipRx = None
        if params.skip:
            self.skipRx = re.compile(params.skip, re.U|re.I)

        self.pfilters = []
        for hreq in params.filter or []:
            pfilter = get_hook_lreq(hreq)
            if pfilter:
                self.pfilters.append((pfilter, hreq))
            else:
                warning("Cannot load filter '%s'." % hreq)

        self.envs = None
        if self.envs is None and params.env is not None:
            self.envs = params.env
        if self.envs is None and cfgs.string("environment") is not None:
            self.envs = cfgs.string("environment").split(",")
        if self.envs is None:
            self.envs = []
        self.envs = [x.strip() for x in self.envs]

        self.suponly = params.suponly
        if not self.suponly:
            self.suponly = cfgs.boolean("supplements-only", False)

        # NOTE: Temporary hack, remove when word splitting becomes smarter.
        self.simsp = params.simsp
        if not self.simsp:
            self.simsp = cfgs.boolean("simple-split", False)

        self.lokalize = params.lokalize

        # Language-dependent elements built along the way.
        self.aspells = {}
        self.ignoredContexts = {}
        self.personalDicts = {}
        self.tmpDictFiles = {}

        # Indicators to the caller:
        self.caller_sync = False # no need to sync catalogs
        self.caller_monitored = False # no need for monitored messages


    def process_header (self, hdr, cat):

        # Check if the catalog itself states the language, and if yes,
        # create the language-dependent stuff if not already created
        # for this language.
        clang = self.lang or cat.language() or locale.getlocale()[0] or "fr"
        cenvs = self.envs or cat.environment() or []
        ckey = (clang, tuple(cenvs))
        if ckey not in self.aspells:
            # New language.
            self.aspellOptions["lang"] = str(clang)

            # Get Pology's internal personal dictonary for this langenv.
            if ckey not in self.personalDicts:
                self.personalDicts[ckey] = None
                pd_langs = [clang] # language codes to try
                # - also try with bare language code,
                # unless the language came from the PO itself.
                p = clang.find("_")
                if p > 0 and not cat.language():
                    pd_langs.append(clang[:p])
                for pd_lang in pd_langs:
                    personalDict = self._get_personal_dict(pd_lang, cenvs)
                    if personalDict:
                        self.personalDicts[ckey] = personalDict
                        break
            if self.personalDicts[ckey]:
                self.aspellOptions["personal-path"] = str(self.personalDicts[ckey])
            else:
                self.aspellOptions.pop("personal-path", None) # remove previous

            if not self.suponly:
                # Create Aspell object.
                import pology.external.pyaspell as A
                try:
                    self.aspells[ckey] = A.Aspell(self.aspellOptions.items())
                except A.AspellConfigError, e:
                    raise SieveError("Aspell configuration error:\n"
                                     "%s" % e)
                except A.AspellError, e:
                    raise SieveError(
                        "Cannot initialize Aspell for language '%s':\n"
                        "\t- check if Aspell and the language dictionary are correctly installed\n"
                        "\t- check if there are any special characters in the personal dictionary\n"
                        % clang)
            else:
                # Create simple internal checker that only checks against
                # internal supplemental dictionaries.
                personalDict=self.personalDicts[ckey]
                if not personalDict:
                    raise SieveError("No supplemental dictionaries found for language '%s'."
                                     % clang)
                self.aspells[ckey]=_QuasiSpell(personalDict, self.encoding)

            # Load list of contexts by which to ignore messages.
            self.ignoredContexts[ckey] = []
            ignoredContextFile=join(rootdir(), "l10n", clang, "spell", "ignoredContext")
            if isfile(ignoredContextFile):
                for line in open(ignoredContextFile, "r", "utf-8"):
                    line=line.strip()
                    if line.startswith("#") or line=="":
                        continue
                    else:
                        self.ignoredContexts[ckey].append(line.lower())

        # Get language-dependent stuff.
        self.aspell = self.aspells[ckey]
        self.ignoredContext = self.ignoredContexts[ckey]

        # Force explicitly given accelerators and markup.
        if self.accel is not None:
            cat.set_accelerator(self.accel)
        if self.markup is not None:
            cat.set_markup(self.markup)

        # Close previous/open new XML section.
        if self.xmlFile:
            filename = os.path.basename(cat.filename)
            # Close previous PO.
            if self.filename != "":
                self.xmlFile.write("</po>\n")
            self.filename = filename
            # Open new PO.
            poTag='<po name="%s">\n' % filename
            self.xmlFile.write(poTag) # Write to result


    def process (self, msg, cat):

        if msg.obsolete:
            return

        id=0 # Count msgstr plural forms
        failedSuggs=[] # pairs of wrong words and suggestions

        for msgstr in msg.msgstr:
            # Skip message with context in the ignoredContext list
            skip=False
            for context in self.ignoredContext:
                if context in (msg.msgctxt or u"").lower():
                    skip=True
                    break
            if skip:
                break

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
                        warning("cannot execute filter '%s'" % pfname)
                        raise

            # Split text into words.
            if not self.simsp:
                words=proper_words(msgstr, True, cat.accelerator(), msg.format)
            else:
                # NOTE: Temporary, remove when proper_words becomes smarter.
                words=msgstr.split()

            # Eliminate from checking words matching the skip regex.
            if self.skipRx:
                words = [x for x in words if not self.skipRx.search(x)]

            # Eliminate from checking words explicitly listed as good.
            locally_ignored = manc_parse_list(msg, elist_well_spelled, ",")
            words = [x for x in words if x not in locally_ignored]

            for word in words:
                # Encode word for Aspell.
                encodedWord=word.encode(self.encoding)
                spell=self.aspell.check(encodedWord)
                if spell is False:
                    try:
                        self.nmatch+=1
                        if self.unknownWords is not None:
                            self.unknownWords.add(word)
                        else:
                            encodedSuggestions=self.aspell.suggest(encodedWord)
                            suggestions=[i.decode(self.encoding) for i in encodedSuggestions]
                            failedSuggs.append((word, suggestions))
                            if self.xmlFile:
                                xmlError=spell_xml_error(msg, cat, word, suggestions, id)
                                self.xmlFile.writelines(xmlError)
                            else:
                                spell_error(msg, cat, word, suggestions)
                    except UnicodeEncodeError:
                        warning("Cannot encode this word in your codec (%s)" % self.encoding)
            id+=1 # Increase msgstr id count

        if failedSuggs and self.lokalize:
            repls=["Spelling errors:"]
            for word, suggs in failedSuggs:
                if suggs:
                    repls.append("%s (suggestions: %s)"
                                 % (word, ", ".join(suggs)))
                else:
                    repls.append("%s" % (word))
            report_msg_to_lokalize(msg, cat, "\n".join(repls))


    def finalize (self):
        # Remove composited personal dictionaries.
        for tmpDictFile in self.tmpDictFiles.values():
            if isfile(tmpDictFile):
                os.unlink(tmpDictFile)

        if self.unknownWords is not None:
            slist = list(self.unknownWords)
            if slist:
                slist.sort(lambda x, y: locale.strcoll(x.lower(), y.lower()))
                report("\n".join(slist))
        else:
            if self.nmatch:
                report("-"*40)
                report("Total matching: %d" % self.nmatch)
        if self.xmlFile:
            self.xmlFile.write("</po>\n")
            self.xmlFile.write("</pos>\n")
            self.xmlFile.close()


    def _encoding_for_aspell (self, enc):

        if re.search(r"utf.*8", enc, re.I):
            return "UTF-8"

        return enc


    def _get_personal_dict (self, lang, envs):
        # Collect all personal dictionaries found for given
        # language/environment and composit them into one to pass to Aspell.

        dictFiles=set()
        for env in (envs or [""]):
            dictFiles.update(self._get_word_list_files(lang, env))
        dictFiles=list(dictFiles)
        dictFiles.sort()

        if not dictFiles:
            return None

        # If only one, Aspell can just use it.
        if len(dictFiles)<2:
            return dictFiles[0]

        # Composite all dictionary files into one temporary.
        words=[]
        for dictFile in dictFiles:
            words.extend(_read_dict_file(dictFile))
        tmpDictFile=("compdict-%d.aspell" % os.getpid())
        self.tmpDictFiles[lang]=tmpDictFile
        file=open(tmpDictFile, "w", "UTF-8")
        file.write("personal_ws-1.1 %s %d UTF-8\n" % (lang, len(words)))
        file.writelines([x+"\n" for x in words])
        file.close()
        return tmpDictFile


    def _get_word_list_files (self, lang, env):
        # Collect all applicable dictionaries.

        dictFiles=set()
        spellRoot=join(rootdir(), "l10n", lang, "spell")
        spellSub=join(".", (env or ""))
        while spellSub:
            spellDir=join(spellRoot, spellSub)
            if isdir(spellDir):
                for item in os.listdir(spellDir):
                    if item.endswith(".aspell"):
                        dictFiles.add(join(spellDir, item))
            spellSub=dirname(spellSub)
        return dictFiles


# Read words from an Aspell personal dictionary.
def _read_dict_file (fname):

    # Parse the header for encoding.
    encDefault="UTF-8"
    file=open(fname, "r", encDefault)
    header=file.readline()
    m=re.search(r"^(\S+)\s+(\S+)\s+(\d+)\s+(\S+)\s*", header)
    if not m:
        warning("Malformed header in dictionary file '%s', skipping reading." % fname)
        return []
    enc=m.group(4)
    # Reopen in correct encoding if not the default.
    if enc.lower() != encDefault.lower():
        file.close()
        file=open(fname, "r", enc)

    # Read words.
    words=[]
    for line in file:
        word=line.strip()
        if word:
            words.append(word)
    return words


# Simple spell checker which reads Aspell's personal dictionary file.
class _QuasiSpell (object):

    def __init__ (self, dictfile, encoding="UTF-8"):

        self.validWords = _read_dict_file(dictfile)
        self.encoding = encoding # of the raw text sent in for checking


    def check (self, encWord):

        word=str.decode(encWord, self.encoding)
        if (    word not in self.validWords
            and word.lower() not in self.validWords
        ):
            return False
        return True


    def suggest (self, encWord):

        return []

