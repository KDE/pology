# -*- coding: UTF-8 -*-

"""
Spell-check messages using GNU Aspell (http://aspell.net/).

For spell-checking, messages are split into words, which are then fed
to Aspell one by one. Misspelled words can be reported to stdout
(either verbosely with suggestions, or succinctly as pure list),
or into a rich XML file with a lot of context information.

Sieve options:
  - C{lang:<language>}: language of the Aspell dictionary
  - C{enc:<encoding>}: encoding for text sent to Aspell
  - C{var:<variety>}: variety of the Aspell dictionary
  - C{list}: only report wrong words to stdout, one per line
  - C{xml:<filename>}: build XML report file
  - C{accel:<char>}: strip this character as accelerator marker
  - C{skip:<regex>}: do not check words which match given regular expression
  - C{filter:[<lang>:]<name>,...}: apply filters prior to spell checking

When dictionary language, encoding, or variety are not explicitly given,
they are extracted, in the following order of priority, from: 
current PO file (language only), user configuration, current system locale
(language and encoding only).

If accelerator character is not explicitly given, it may be inferred from the
PO header; otherwise, some usual accelerator characters are removed by default.

The C{filter} option specifies text-transformation filters to apply before
the text is spell-checked. These are the filters found in C{pology.filters}
and C{pology.l10n.<lang>.filters}, and are specified as comma-separated list
of C{[<lang>:]<name>} (language stated when a filter is language-specific).

The following user configuration fields are considered:
  - C{[aspell]/language}: language of the Aspell dictionary
  - C{[aspell]/encoding}: encoding for text sent to Aspell
  - C{[aspell]/variety}: variety of the Aspell dictionary

@author: Sébastien Renard <sebastien.renard@digitalfox.org>
@license: GPLv3
"""

from pology.misc.colors import RED, RESET
from pology.external.pyaspell import Aspell, AspellConfigError, AspellError
from pology.misc.report import spell_error, spell_xml_error, error
from pology.misc.split import proper_words
from pology import rootdir
import pology.misc.config as cfg
from pology.misc.langdep import get_filter_lreq
import os, re, sys
from os.path import abspath, basename, dirname, isfile, join
from codecs import open
from time import strftime
import locale


class Sieve (object):
    """Process messages through the Aspell spell checker"""
    
    def __init__ (self, options, global_options):
    
        self.nmatch = 0 # Number of match for finalize
        self.list=None # If not None, only list of faulty word is display (to ease copy/paste into personal dictionary)
        self.filename=""     # File name we are processing
        self.xmlFile=None # File handle to write XML output

        # Build Aspell options.
        self.aspellOptions = {}

        # - assume markup in messages (provide option to disable?)
        self.aspellOptions["mode"] = "sgml"
        # FIXME: In fact not needed? The words are sent parsed to checker.

        # - dictionary specifiers (by priority)
        self.lang, self.encoding, self.variety = [None] * 3

        if "lang" in options:
            options.accept("lang")
            self.lang = options["lang"]
        if "enc" in options:
            options.accept("enc")
            self.encoding = options["enc"]
        if "var" in options:
            options.accept("var")
            self.variety = options["var"]

        cfgs = cfg.section("aspell")
        if not self.lang:
            self.lang = cfgs.string("language")
        if not self.encoding:
            self.encoding = cfgs.string("encoding")
        if not self.variety:
            self.variety = cfgs.string("variety")

        loc_lang, loc_encoding = locale.getdefaultlocale()
        if not self.lang:
            self.lang = loc_lang
        if not self.encoding:
            self.encoding = loc_encoding

        if not self.lang:
            self.lang = "fr" # historical default
        if not self.encoding:
            self.encoding = "UTF-8"

        self.encoding = self._encoding_for_aspell(self.encoding)
        self.aspellOptions["lang"] = str(self.lang)
        self.aspellOptions["encoding"] = str(self.encoding)
        if self.variety:
            self.aspellOptions["variety"] = str(self.variety)

        # Simple list output of misspelled words?
        if "list" in options:
            options.accept("list")
            self.list = []

        # Also output in XML file ?
        if "xml" in options:
            options.accept("xml")
            xmlPath=options["xml"]
            if os.access(dirname(abspath(xmlPath)), os.W_OK):
                #TODO: create nice api to manage xml file and move it to misc/
                self.xmlFile=open(xmlPath, "w", "utf-8")
                self.xmlFile.write('<?xml version="1.0" encoding="UTF-8"?>\n')
                self.xmlFile.write('<pos date="%s">\n' % strftime('%c').decode(locale.getpreferredencoding()))
            else:
                print "Cannot open %s file. XML output disabled" % xmlPath

        # Remove accelerators?
        self.accel_explicit = False
        self.accel_usual = "&_~"
        self.accel = ""
        if "accel" in options:
            options.accept("accel")
            self.accel = options["accel"]
            self.accel_explicit = True

        # Pattern for words to skip.
        self.skipRx = None
        if "skip" in options:
            options.accept("skip")
            self.skipRx = re.compile(options["skip"], re.U|re.I)

        # Precheck filters for message text.
        self.pfilters = []
        if "filter" in options:
            options.accept("filter")
            freqs = options["filter"].split(",")
            self.pfilters = [get_filter_lreq(x, abort=True) for x in freqs]

        # Language-dependent elements built along the way.
        self.aspells = {}
        self.ignoredContexts = {}

        # Indicators to the caller:
        self.caller_sync = False # no need to sync catalogs
        self.caller_monitored = False # no need for monitored messages


    def process_header (self, hdr, cat):

        # Check if the catalog itself states the language, and if yes,
        # create the language-dependent stuff if not already created
        # for this language.
        clang = cat.language() or self.lang
        if clang not in self.aspells:
            # New language.
            self.aspellOptions["lang"] = str(clang)

            # Get Pology's internal personal dictonary for this language.
            self.aspellOptions.pop("personal-path", None) # remove previous
            pd_langs = [clang] # language codes to try
            # - also try with bare language code,
            # unless the language came from the PO itself.
            p = clang.find("_")
            if p > 0 and not cat.language():
                pd_langs.append(clang[:p])
            for pd_lang in pd_langs:
                personalDict = join(rootdir(), "l10n", pd_lang, "spell", "dict.aspell")
                if isfile(personalDict):
                    #print "Using language-specific dictionary (%s)" % personalDict
                    self.aspellOptions["personal-path"] = str(personalDict)
                    break

            # Create Aspell object.
            try:
                self.aspells[clang] = Aspell(self.aspellOptions.items())
            except AspellConfigError, e:
                error("Aspell configuration error:\n"
                      "%s" % e)
            except AspellError, e:
                error("cannot initialize Aspell for language '%s':\n"
                      "\t- check if Aspell and the language dictionary are correctly installed\n"
                      "\t- check if there are any special characters in the personal dictionary\n"
                      % clang)

            # Load list of contexts by which to ignore messages.
            self.ignoredContexts[clang] = []
            ignoredContextFile=join(rootdir(), "l10n", clang, "spell", "ignoredContext")
            if isfile(ignoredContextFile):
                for line in open(ignoredContextFile, "r", "utf-8"):
                    line=line.strip()
                    if line.startswith("#") or line=="":
                        continue
                    else:
                        self.ignoredContexts[clang].append(line.lower())

        # Get language-dependent stuff.
        self.aspell = self.aspells[clang]
        self.ignoredContext = self.ignoredContexts[clang]

        # Check if the catalog itself states the shortcut character,
        # unless specified explicitly by the command line.
        if not self.accel_explicit:
            accel = cat.possible_accelerator()
            if accel is not None:
                self.accel = accel
            else:
                self.accel = self.accel_usual

        # Close previous/open new XML section.
        if self.xmlFile:
            filename = os.path.basename(cat.filename)
            #print "(Processing %s)" % filename # better not contaminate stdout?
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

        for msgstr in msg.msgstr:
            # Skip message with context in the ignoredContext list
            msg.msgctxt.lower()
            skip=False
            for context in self.ignoredContext:
                if context in msg.msgctxt.lower():
                    skip=True
                    break
            if skip:
                break

            # Apply precheck filters.
            for pfilter in self.pfilters:
                msgstr = pfilter(msgstr)

            # Split text into words.
            words = proper_words(msgstr, True, self.accel, msg.format)

            # Possibly eliminate some words from checking.
            if self.skipRx:
                words = [x for x in words if not self.skipRx.search(x)]

            for word in words:
                # Encode word for Aspell.
                encodedWord=word.encode(self.encoding)
                spell=self.aspell.check(encodedWord)
                if spell is False:
                    try:
                        self.nmatch+=1
                        if self.list is not None:
                            if word not in self.list:
                                self.list.append(word)
                        else:
                            suggestions=self.aspell.suggest(encodedWord)
                            if self.xmlFile:
                                xmlError=spell_xml_error(msg, cat, word, suggestions, id)
                                self.xmlFile.writelines(xmlError)
                            else:
                                spell_error(msg, cat, word, [i.encode(self.encoding) for i in suggestions])
                    except UnicodeEncodeError:
                        print "Cannot encode this word in your codec (%s)" % self.encoding
            id+=1 # Increase msgstr id count


    def finalize (self):
        if self.list is not None:
            slist = [i.decode(locale.getdefaultlocale()[1]) for i in self.list]
            slist.sort(lambda x, y: locale.strcoll(x.lower(), y.lower()))
            if slist:
                print "\n".join(slist)
        else:
            if self.nmatch:
                print "----------------------------------------------------"
                print "Total matching: %d" % self.nmatch
        if self.xmlFile:
            self.xmlFile.write("</po>\n")
            self.xmlFile.write("</pos>\n")
            self.xmlFile.close()


    def _encoding_for_aspell (self, enc):

        if re.search(r"utf.*8", enc, re.I):
            return "UTF-8"

        return enc

