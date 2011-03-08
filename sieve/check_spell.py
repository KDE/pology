# -*- coding: UTF-8 -*-

"""
Spell-check translation using GNU Aspell (U{http://aspell.net/}).

Documented in C{doc/user/sieving.docbook}.

@author: Sébastien Renard <sebastien.renard@digitalfox.org>
@license: GPLv3
"""

from codecs import open
import locale
import os
from os.path import abspath, basename, dirname, isfile, isdir, join
import re
import sys
from time import strftime

from pology import rootdir, _, n_
from pology.spell import flag_no_check_spell, elist_well_spelled
from pology.colors import cjoin
from pology.comments import manc_parse_list, manc_parse_flag_list
import pology.config as cfg
from pology.getfunc import get_hook_ireq
from pology.msgreport import spell_error, spell_xml_error
from pology.msgreport import report_msg_to_lokalize
from pology.report import report, warning, format_item_list
from pology.sieve import SieveError, SieveCatalogError
from pology.split import proper_words
from pology.sieve import add_param_spellcheck


def setup_sieve (p):

    p.set_desc(_("@info sieve discription",
    "Spell-check translation using Aspell."
    ))

    add_param_spellcheck(p)

    p.add_param("enc", unicode,
                metavar=_("@info sieve parameter value placeholder",
                          "ENCODING"),
                desc=_("@info sieve parameter discription",
    "Encoding for text sent to Aspell."
    ))
    p.add_param("var", unicode,
                metavar=_("@info sieve parameter value placeholder",
                          "VARIETY"),
                desc=_("@info sieve parameter discription",
    "Variety of the Aspell dictionary."
    ))
    p.add_param("xml", unicode,
                metavar=_("@info sieve parameter value placeholder", "FILE"),
                desc=_("@info sieve parameter discription",
    "Build XML report file at given path."
    ))
    p.add_param("simsp", bool, defval=False,
                desc=_("@info sieve parameter discription",
    "Split text into words in a simpler way (deprecated,)."
    ))


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
                #TODO: create nice api to manage xml file and move it to rules.py
                self.xmlFile=open(xmlPath, "w", "utf-8")
                self.xmlFile.write('<?xml version="1.0" encoding="UTF-8"?>\n')
                self.xmlFile.write('<pos date="%s">\n' % strftime('%c').decode(locale.getpreferredencoding()))
            else:
                warning(_("@info",
                          "Cannot open file '%(file)s'. XML output disabled.",
                          file=xmlPath))

        self.accel = params.accel
        self.markup = params.markup

        self.skipRx = None
        if params.skip:
            self.skipRx = re.compile(params.skip, re.U|re.I)

        self.pfilters = [[get_hook_ireq(x, abort=True), x]
                         for x in (params.filter or [])]

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
        clang = self.lang or cat.language()
        if not clang:
            raise SieveCatalogError(
                _("@info",
                  "Cannot determine language for catalog '%(file)s'.",
                  file=cat.filename))
        cenvs = self.envs or cat.environment() or []
        ckey = (clang, tuple(cenvs))
        if ckey not in self.aspells:
            # New language.
            self.aspellOptions["lang"] = str(clang)

            # Get Pology's internal personal dictonary for this langenv.
            if ckey not in self.personalDicts: # may be in but None
                self.personalDicts[ckey] = self._get_personal_dict(clang, cenvs)
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
                    raise SieveError(
                        _("@info",
                          "Aspell configuration error:\n%(msg)s",
                          msg=e))
                except A.AspellError, e:
                    raise SieveError(
                        _("@info",
                          "Cannot initialize Aspell:\n%(msg)s",
                          msg=e))
            else:
                # Create simple internal checker that only checks against
                # internal supplemental dictionaries.
                personalDict=self.personalDicts[ckey]
                if not personalDict:
                    raise SieveError(_("@info",
                                       "No supplemental dictionaries found."))
                self.aspells[ckey]=_QuasiSpell(personalDict, self.encoding)

            # Load list of contexts by which to ignore messages.
            self.ignoredContexts[ckey] = []
            ignoredContextFile=join(rootdir(), "lang", clang, "spell", "ignoredContext")
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
                for comment in msg.auto_comment:
                    if context in comment.lower():
                        skip=True
                        break
                if skip:
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
                        raise SieveError(
                            _("@info",
                              "Cannot execute filter '%(filt)s'.",
                              filt=pfname))

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
                        warning(_("@info",
                                  "Cannot encode word '%(word)s' in "
                                  "selected encoding '%(enc)s'.",
                                  word=word, enc=self.encoding))
            id+=1 # Increase msgstr id count

        if failedSuggs and self.lokalize:
            repls=[_("@label", "Spelling errors:")]
            for word, suggs in failedSuggs:
                if suggs:
                    fmtsuggs=format_item_list(suggs)
                    repls.append(_("@item",
                                   "%(word)s (suggestions: %(wordlist)s)",
                                   word=word, wordlist=fmtsuggs))
                else:
                    repls.append("%s" % (word))
            report_msg_to_lokalize(msg, cat, cjoin(repls, "\n"))


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
                msg = n_("@info:progress",
                         "Encountered %(num)d unknown word.",
                         "Encountered %(num)d unknown words.",
                         num=self.nmatch)
                report("===== " + msg)
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
        spellRoot=join(rootdir(), "lang", lang, "spell")
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
        warning(_("@info",
                  "Malformed header in dictionary file '%(file)s'.",
                  file=filepath))
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

