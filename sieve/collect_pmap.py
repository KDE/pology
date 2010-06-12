# -*- coding: UTF-8 -*-

"""
Assemble a property map from entries embedded into manual comments.

I{Property maps} (short I{pmaps}) are a component of
U{Transcript<http://techbase.kde.org/Localization/Concepts/Transcript>},
translation scripting system of KDE 4, by which properties of certain phrases
can be defined for use in scripted translations.

A property map is a text file, containing a number of entries each
with one or more keys, followed by any number of key-value properties.
An example entry, with grammatical declinations of a city name::

    =/Athens/Atina/nom=Atina/gen=Atine/dat=Atini/acc=Atinu//

The first two characters define, respectively, the key-value separator
(here C{=}) and the property separator (here C{/}) for the current entry,
and must not be alphanumeric.
This is followed by a number of entry keys delimited by property separators,
and then by a number of key-value properties each internaly delimited by
the key-value separator.
The entry is terminated by double property separator.
Properties of an entry defined like this can later be fetched in
the scripting system by any of the entry keys;
keys are case- and whitespace-insensitive.

This sieve will parse pmap entries out of manual comments in messages,
collect them and write out a property map file.
Entry keys should not be specified, because the contents of
C{msgid} and C{msgstr} are automatically added as keys.

Since each manual comment is one line, it is also allowed to drop
the final double separator which would normally terminate the entry.
The above example would thus look like this in PO message::

    # pmap: =/nom=Atina/gen=Atine/dat=Atini/acc=Atinu/
    msgctxt "Greece/city"
    msgid "Athens"
    msgstr "Atina"

The manual comment starts with C{pmap:} keyword, followed by normal pmap entry
(except for default keys; only additional keys should be specified).
It is also possible to split the entry into several comments,
with only condition that all share the same set of separators::

    # pmap: =/nom=Atina/gen=Atine/
    # pmap: =/dat=Atini/acc=Atinu/

In case two or more parsed entries have same keys extracted from translation,
they are all thrown out of the collection and a warning is reported.

Entries are collected only from translated non-plural messages.

Sieve parameters:

  - C{outfile}: file path into which to write the property map
  - C{propcons}: file defining constraints on property keys and values,
        used to validate parsed entries
  - C{extrakeys}: allow defining extra entry keys
  - C{derivs:<file>}: path to the file defining derivators for synder entries
  - C{pmhead}: prefix for pmap entries (instead of default C{pmap:})
  - C{sdhead}: prefix for synder entries (instead of default C{synder:})

If output file is not specified by C{outfile} parameter,
nothing is written out. Such runs are useful for validation of entries.

Defining additional entry keys (other than C{msgid} and C{msgstr})
is by default not allowed; issuing the C{extrakeys} parameter allows it.

Derivating Entries
==================

There is another, more succint way to define pmap entries in comments.
Instead of writting out all key-value combinations, it is possible instead
to generate them through use of I{syntagma derivators}, or synders for short.
In the earlier example::

    # pmap: =/nom=Atina/gen=Atine/dat=Atini/acc=Atinu/

it can be observed that each form has the same root, C{Atin}, followed
by the appropriate ending for the given form. This makes it convenient
to reformulate it as syntagma derivation::

    # synder: Atin|a

Here C{|a} is a I{derivator}; all such derivators are defined in
a separate synder file (having {.sd} extension by convention),
and made known to the sieve through the C{derivs} parameter.
The derivator in this example would be defined like this::

    |a: nom=a, gen=e, dat=i, acc=u

After the derivator name, the definition lists the keys as in the pmap,
but followed only by the appropriate endings for the given declination.
For details about syntagma derivation, see documentation to
L{pology.misc.synder} module.

It is possible to mix pmap (C{# pmap: ...}) and synder C{# synder: ...} entries
throughout comments, in a single or collection of PO files.
For example, synder entries may be used to cover majority of cases, which
follow the general rules, while pmap entries can be used for exceptions.

On the other hand, a pmap entry can also be directly reformulated as
a synder entry, without using a derivator::

    # synder: nom=Atina, gen=Atine, dat=Atini, acc=Atinu

A question may come to mind here: why have pmap entries at all,
if synder entries can be used in the same capacity and beyond?
Because syntagma derivations have a lot of special syntax and rules
(e.g. what if the phrase itself contains a comma?) to keep in mind,
while raw pmaps have none past what was described above.

Validating Entries
==================

The C{propcons} parameter can be used to provide a file defining
constraints on acceptable property keys, and values by each key.
Its format is the following::

    # Full-line comment.
    /key-regex-1/value-regex-1/flags # a trailing comment
    /key-regex-2/value-regex-2/flags
    :key-regex-3:value-regex-3:flags # different separator
    ...

Regular expressions for keys and values are delimited by a separator
defined by first non-whitespace character in the line,
which must also be non-alphanumeric.
Before being applied, regular expressions are automatically wrapped
as C{^(<regex>)$}, so e.g. an expression to require a prefix is given
as C{<prefix>.*} and a suffix as C{.*<suffix>}.

For example, a constraint file defining no constraints on either
property keys or values is this::

    /.*/.*/

A constraint definition file stating all allowed property keys,
and constraining values for some::

    /nom|gen|dat|acc/.*/
    /gender/m|f|n/
    /number/s|p/

Flags following the trailing separator are a string of single-character
indicators. The following are defined:
  - C{i}: case-insensitive matching for the value
  - C{I}: case-insensitive matching for the key
  - C{t}: the value must both match the regular expression I{and}
        be equal to C{msgstr} (if C{i} is in effect too, equality
        check is also case-insensitive)
  - C{r}: regular expression for the key must match at least one key
        among all defined properties

Constraint definition file must be UTF-8 encoded.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import os
import re

from pology import _, n_
from pology.sieve import SieveError
from pology.misc.msgreport import warning_on_msg
from pology.misc.report import report, format_item_list
from pology.misc.synder import Synder


def setup_sieve (p):

    p.set_desc(_("@info sieve discription",
    "Assemble a property map from entries embedded into manual comments."
    ))

    p.add_param("outfile", unicode,
                metavar=_("@info sieve parameter value placeholder", "FILE"),
                desc=_("@info sieve parameter discription",
    "File to output the property map into. "
    "If not given, nothing is output (useful for validation runs)."
    ))
    p.add_param("propcons", unicode,
                metavar=_("@info sieve parameter value placeholder", "FILE"),
                desc=_("@info sieve parameter discription",
    "File defining the constraints on property keys and values."
    ))
    p.add_param("extrakeys", bool, defval=False,
                desc=_("@info sieve parameter discription",
    "Allow defining additional entry keys."
    ))
    p.add_param("derivs", unicode,
                metavar=_("@info sieve parameter value placeholder", "FILE"),
                desc=_("@info sieve parameter discription",
    "File defining the derivators used in derived entries."
    ))
    p.add_param("pmhead", unicode, defval=u"pmap:",
                metavar=_("@info sieve parameter value placeholder", "STRING"),
                desc=_("@info sieve parameter discription",
    "Prefix which starts property map entries in comments."
    ))
    p.add_param("sdhead", unicode, defval=u"synder:",
                metavar=_("@info sieve parameter value placeholder", "STRING"),
                desc=_("@info sieve parameter discription",
    "Prefix which starts syntagma derivator entries in comments."
    ))


class Sieve (object):

    def __init__ (self, params):

        self.caller_sync = False
        self.caller_monitored = False

        self.propcons = None
        if params.propcons:
            self.propcons = self._read_propcons(params.propcons)

        self.p = params

        if not params.pmhead:
            raise SieveError(_("@info",
                               "Prefix which starts property map entries "
                               "in comments cannot be empty."))
        if not params.sdhead:
            raise SieveError(_("@info",
                               "Prefix which starts syntagma derivator entries "
                               "in comments cannot be empty."))

        # Collected entries.
        # Each element is a tuple of the form:
        # (ekeys, props, psep, kvsep, msg, cat)
        self.entries = []

        # Syntagma derivator, for synder entries.
        self.synder = Synder()
        self.sdord = 0


    def process (self, msg, cat):

        if not msg.translated or msg.obsolete:
            return
        if msg.msgid_plural is not None:
            return

        # Parse property map entries from the message.
        psep, kvsep = None, None
        ekeys = set()
        props = {}
        for i in range(len(msg.manual_comment)):
            ind = i + 1
            manc = (msg.manual_comment[i]).strip()
            if manc.startswith(self.p.pmhead):
                # Parse and check consistency of separators.
                espec = manc[len(self.p.pmhead):].lstrip()
                lkvsep, lpsep = espec[:2]
                if lkvsep.isalnum() or lpsep.isalnum():
                    warning_on_msg(_("@info",
                                     "An alphanumeric separator is used for "
                                     "property map entry in comment "
                                     "no. %(ord)d.")
                                   % dict(ord=ind), msg, cat)
                    return
                if not psep:
                    psep, kvsep = lpsep, lkvsep
                elif (psep, kvsep) != (lpsep, lkvsep):
                    warning_on_msg(_("@info",
                                     "Inconsistent separators for "
                                     "continued property map entry in comment "
                                     "no. %(ord)d.")
                                   % dict(ord=ind), msg, cat)
                    return
                # Remove leading and trailing separators.
                respec = espec[2:]
                if respec.endswith(psep + psep):
                    respec = respec[:-2]
                elif respec.endswith(psep):
                    respec = respec[:-1]
                else:
                    warning_on_msg(_("@info",
                                     "Missing terminating separator for "
                                     "property map entry in comment "
                                     "no. %(ord)d.")
                                   % dict(ord=ind), msg, cat)
                    return
                # Parse entry keys and key-value pairs.
                for elspec in respec.split(psep):
                    if kvsep in elspec:
                        pkey, pval = elspec.split(kvsep, 1)
                        props[pkey] = pval
                    else:
                        ekey = elspec
                        if not self.p.extrakeys:
                            warning_on_msg(_("@info",
                                             "Additional entry key '%(key)s' "
                                             "is defined but not allowed for "
                                             "property map entry in comment "
                                             "no. %(ord)d.")
                                           % dict(key=ekey, ord=ind), msg, cat)
                            return
                        ekeys.add(ekey)

            elif manc.startswith(self.p.sdhead):
                sddef = manc[len(self.p.sdhead):].lstrip()
                sdkey = str(self.sdord)
                sdexpr = sdkey + ":" + sddef
                if self.p.derivs:
                    sdexpr = ">" + self.p.derivs + "\n" + sdexpr
                try:
                    self.synder.import_string(sdexpr)
                    cprops = self.synder.props(sdkey)
                except Exception, e:
                    errmsg = unicode(e)
                    warning_on_msg(_("@info",
                                     "Invalid derivation '%(deriv)s':\n"
                                     "%(msg)s")
                                   % dict(deriv=sddef, msg=errmsg), msg, cat)
                    return

                jumble = "".join(["".join(x) for x in cprops.items()])
                if not psep:
                    psep = self._pick_sep(jumble, u"/|¦")
                    kvsep = self._pick_sep(jumble, u"=:→")
                    if not psep or not kvsep:
                        warning_on_msg(_("@info",
                                         "No known separator are applicable "
                                         "to keys and values derived from "
                                         "'%(deriv)s'.")
                                       % dict(deriv=sddef), msg, cat)
                        return
                else:
                    if psep in jumble or kvsep in jumble:
                        warning_on_msg(_("@info",
                                         "Previously selected separators "
                                         "are not applicable to "
                                         "keys and values derived from "
                                         "'%(deriv)s'.")
                                       % dict(deriv=sddef), msg, cat)
                        return

                props.update(cprops)

        if not props:
            if ekeys:
                warning_on_msg(_("@info",
                                 "Some additional entry keys "
                                 "are defined for property map entry, "
                                 "but there are no properties."),
                               msg, cat)
            return
        props = sorted(props.items()) # no need for dictionary any more

        # Add default keys.
        ekeys.add(msg.msgid)
        ekeys.add(msg.msgstr[0])

        # Validate entry if requested.
        if self.propcons:
            errs = self._validate_props(props, msg, cat, self.propcons)
            if errs:
                problems = "\n".join(["  %s" % x for x in errs])
                warning_on_msg(_("@info",
                                 "Property map entry fails validation:\n"
                                 "%(msgs)s")
                               % dict(msgs=problems), msg, cat)
                return

        # Entry parsed.
        ekeys = sorted(ekeys)
        props = sorted(props)
        self.entries.append((ekeys, props, psep, kvsep, msg, cat))


    def finalize (self):

        # Check cross-entry validity, select valid.
        msgs_by_seen_msgstr = {}
        unique_entries = []
        for entry in self.entries:
            d1, props, d3, d4, msg, cat = entry
            msgstr = msg.msgstr[0]
            if msgstr not in msgs_by_seen_msgstr:
                msgs_by_seen_msgstr[msgstr] = []
            else:
                for d1, d2, oprops in msgs_by_seen_msgstr[msgstr]:
                    if props == oprops:
                        props = None
                        break
            if props:
                unique_entries.append(entry)
                msgs_by_seen_msgstr[msgstr].append((msg, cat, props))
        good_entries = []
        for ekeys, props, psep, kvsep, msg, cat in unique_entries:
            eq_msgstr_set = msgs_by_seen_msgstr.get(msg.msgstr[0])
            if eq_msgstr_set is not None:
                if len(eq_msgstr_set) > 1:
                    cmsgcats = msgs_by_seen_msgstr.pop(msg.msgstr[0])
                    msg0, cat0, d3 = cmsgcats[0]
                    warning_on_msg(_("@info split to link below",
                                     "Property map entries removed due "
                                     "to translation conflict with..."),
                                     msg0, cat0)
                    for msg, cat, d3 in cmsgcats[1:]:
                        warning_on_msg(_("@info continuation from above",
                                         "...this message."),
                                       msg, cat)
                else:
                    good_entries.append((ekeys, props, psep, kvsep))

        # If output file has not been given, only validation was expected.
        if not self.p.outfile:
            return

        # Serialize entries.
        good_entries.sort(key=lambda x: x[0])
        lines = []
        for ekeys, props, psep, kvsep in good_entries:
            # Do Unicode, locale-unaware sorting,
            # for equal results over different systems;
            # they are not to be read by humans anyway.
            propstr = psep.join([kvsep.join(x) for x in sorted(props)])
            ekeystr = psep.join(sorted(ekeys))
            estr = kvsep + psep + ekeystr + psep + propstr + psep + psep
            lines.append(estr)

        # Write out the property map.
        lines.append("")
        fstr = "\n".join(lines)
        fstr = fstr.encode("UTF-8")
        fh = open(self.p.outfile, "w")
        fh.write(fstr)
        fh.close()

        msg = (n_("@info:progress",
                  "Collected %(num)d entry for the property map.",
                  "Collected %(num)d entries for the property map.",
                  len(good_entries))
                % dict(num=len(good_entries)))
        report("===== %s" % msg)


    def _pick_sep (self, teststr, seps):

        good = False
        for sep in seps:
            if sep not in teststr:
                good = True
                break
        return sep if good else None


    def _read_propcons (self, fpath):

        if not os.path.isfile(fpath):
            raise SieveError(_("@info",
                               "Property constraint file '%(file)s' "
                               "does not exist.")
                             % dict(file=fpath))
        lines = open(fpath).read().decode("UTF-8").split("\n")
        if not lines[-1]:
            lines.pop()

        cmrx = re.compile(r"#.*")
        # Constraints collected as list of tuples:
        # (compiled key regex, string key regex,
        #  compiled value regex, string value regex,
        #  string of flags)
        propcons = []
        lno = 0
        def mkerr (problem):
            return (_("@info",
                      "Invalid property map constraint "
                      "at %(file)s:%(line)d: %(snippet)s.")
                    % dict(file=fpath, line=lno, snippet=problem))
        known_flags = set(("i", "I", "t", "r"))
        for line in lines:
            lno += 1
            line = cmrx.sub("", line).strip()
            if not line:
                continue

            sep = line[0]
            if sep.isalnum():
                raise SieveError(mkerr(_("@item:intext",
                                         "alphanumeric separators "
                                         "not allowed")))
            lst = line.split(sep)
            if len(lst) < 4:
                raise SieveError(mkerr(_("@item:intext",
                                         "too few separators")))
            elif len(lst) > 4:
                raise SieveError(mkerr(_("@item:intext",
                                         "too many separators")))

            d1, keyrxstr, valrxstr, flags = lst

            unknown_flags = set(flags).difference(known_flags)
            if unknown_flags:
                fmtflags = format_item_list(sorted(unknown_flags))
                raise SieveError(mkerr(_("@item:intext",
                                         "unknown flags %(flaglist)s")
                                       % dict(flaglist=fmtflags)))

            rxs = []
            for rxstr, iflag in ((keyrxstr, "I"), (valrxstr, "i")):
                rxfls = re.U
                if iflag in flags:
                    rxfls |= re.I
                wrxstr = r"^(?:%s)$" % rxstr
                try:
                    rx = re.compile(wrxstr, rxfls)
                except:
                    raise SieveError(mkerr(_("@item:intext",
                                             "invalid regular expression "
                                             "'%(regex)s'")
                                           % dict(regex=rxstr)))
                rxs.append(rx)
            keyrx, valrx = rxs

            propcons.append((keyrx, keyrxstr, valrx, valrxstr, flags))

        return propcons


    def _validate_props (self, props, msg, cat, propcons):

        matched_cons = set()
        errs = []
        adderr = lambda err: errs.append(err)
        for prop, ip in zip(props, range(len(props))):
            key, val = prop
            key_matched = False
            for propcon, ic in zip(propcons, range(len(propcons))):
                keyrx, keyrxstr, valrx, valrxstr, flags = propcon
                if keyrx.search(key):
                    key_matched = True
                    matched_cons.add(ic)
                    if not valrx.search(val):
                        pattern = valrx
                        adderr(_("@info",
                                 "Value '%(val)s' to key '%(key)s' "
                                 "does not match '%(pattern)s'.")
                               % dict(val=val, key=key, pattern=pattern))
                    if "t" in flags:
                        if "i" in flags:
                            eq = (val.lower() == msg.msgstr[0].lower())
                        else:
                            eq = (val == msg.msgstr[0])
                        if not eq:
                            adderr(_("@info",
                                     "Value '%(val)s' to key '%(key)s' "
                                     "does not match translation "
                                     "of the message.")
                                   % dict(val=val, key=key))
            if not key_matched:
                adderr(_("@info",
                         "Key '%(key)s' does not match any constraint.")
                       % dict(key=key))

        for propcon, ic in zip(propcons, range(len(propcons))):
            pattern, rlags = propcon[1], propcon[-1]
            if "r" in flags and ic not in matched_cons:
                adderr(_("@info",
                         "No key matched required constraint '%(pattern)s'.")
                       % dict(pattern=pattern))

        return errs

