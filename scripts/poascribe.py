#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import fallback_import_paths

import os
import sys
import re
import codecs
import time
from optparse import OptionParser
from ConfigParser import SafeConfigParser

from pology.misc.report import error, warning
from pology.misc.fsops import collect_catalogs, mkdirpath
from pology.misc.vcs import make_vcs
from pology.file.catalog import Catalog
from pology.file.message import Message
from pology.misc.monitored import Monlist, Monset
from pology.misc.wrap import wrap_field_ontag_unwrap
from pology.misc.tabulate import tabulate

wrapf = wrap_field_ontag_unwrap


def main ():

    # Setup options and parse the command line.
    usage = (
        u"%prog [OPTIONS] [PATHS...]")
    description = (
        u"Keep track of who, when, and how, has translated, modified, "
        u"or reviewed messages in a collection of PO files.")
    version = (
        u"%prog (Pology) experimental\n"
        u"Copyright © 2008 Chusslove Illich (Часлав Илић) "
        u"<caslav.ilic@gmx.net>\n")

    opars = OptionParser(usage=usage, description=description, version=version)
    opars.add_option(
        "--no-psyco",
        action="store_false", dest="use_psyco", default=True,
        help="do not try to use Psyco specializing compiler")
    opars.add_option(
        "-u", "--updated", metavar="USER",
        action="store", dest="updated", default=None,
        help="ascribe all updated entries to this user")
    opars.add_option(
        "-m", "--mark",
        action="store_true", dest="mark", default=False,
        help="mark entries in original catalogs that match certain criteria")
    opars.add_option(
        "-v", "--verbose",
        action="store_true", dest="verbose", default=False,
        help="output more detailed progress info")
    (options, free_args) = opars.parse_args()

    options.paths = [os.path.normpath(x) for x in free_args]

    # Could use some speedup.
    if options.use_psyco:
        try:
            import psyco
            psyco.full()
        except ImportError:
            pass

    # For each path:
    # - determine its associated ascription config,
    # - collect all catalogs.
    configs_loaded = {}
    configs_catpaths = []
    for path in options.paths:
        # Look for the first config file up the directory tree.
        parent = os.path.abspath(path)
        if os.path.isfile(parent):
            parent = os.path.dirname(parent)
        while True:
            cfgpath = os.path.join(parent, "ascribe")
            if os.path.isfile(cfgpath):
                break
            else:
                cfgpath = ""
            pparent = parent
            parent = os.path.dirname(parent)
            if parent == pparent:
                break
        if not cfgpath:
            error("cannot find ascription configuration for path: %s" % path)
        cfgpath = rel_path(os.getcwd(), cfgpath) # for nicer message output
        config = configs_loaded.get(cfgpath, None)
        if not config:
            # New config, load.
            config = Config(cfgpath)
            configs_loaded[cfgpath] = config

        # Collect PO files.
        if os.path.isdir(path):
            catpaths = collect_catalogs(path)
        else:
            catpaths = [path]

        # Collect the config and corresponding catalogs.
        configs_catpaths.append((config, catpaths))

    if options.updated:
        ascribe_updated(options, configs_catpaths, options.updated)
    else:
        examine_state(options, configs_catpaths)


def rel_path (ref_path, rel_path):

    if os.path.isabs(rel_path):
        path = rel_path
    else:
        ref_dir = os.path.dirname(ref_path)
        path = os.path.abspath(os.path.join(ref_dir, rel_path))
    cwd = os.getcwd() + os.path.sep
    if path.startswith(cwd):
        path = path[len(cwd):]
    return path


class Config:

    def __init__ (self, cpath):

        config = SafeConfigParser()
        ifl = codecs.open(cpath, "r", "UTF-8")
        config.readfp(ifl)
        ifl.close()

        self.path = cpath

        gsect = dict(config.items("global"))
        self.catroot = rel_path(cpath, gsect.get("catalog-root", ""))
        self.ascroot = rel_path(cpath, gsect.get("ascript-root", ""))
        if self.catroot == self.ascroot:
            error("%s: catalog root and ascription root "
                  "resolve to same path: %s" % (cpath, self.catroot))

        self.lang_team = gsect.get("language-team")
        self.team_email = gsect.get("team-email")
        self.plural_header = gsect.get("plural-header")

        self.vcs = make_vcs(gsect.get("version-control", "noop"))

        class UserData: pass
        self.udata = {}
        self.users = []
        userst = "user-"
        for section in config.sections():
            if section.startswith(userst):
                user = section[len(userst):]
                usect = dict(config.items(section))
                if user in self.users:
                    error("%s: repeated user: %s" % (cpath, user))
                udat = UserData()
                self.udata[user] = udat
                self.users.append(user)
                udat.ascroot = os.path.join(self.ascroot, user)
                if "name" not in usect:
                    error("%s: user '%s' misses the name" % (cpath, user))
                udat.name = usect.get("name")
                udat.oname = usect.get("original-name")
                udat.email = usect.get("email")
        self.users.sort()


def examine_state (options, configs_catpaths):

    cmon = options.mark is True

    # Count unascribed messages through catalogs.
    # Mark them if requested.
    unasc_by_cat = {}
    for config, catpaths in configs_catpaths:
        for catpath in catpaths:
            # Open current and all ascription catalogs.
            cat = Catalog(catpath, monitored=cmon, wrapf=wrapf)
            acats = collect_asc_cats(config, cat.name)
            # Count non-ascribed.
            for msg in cat:
                if not msg.translated:
                    continue
                if not is_ascribed(msg, acats):
                    if catpath not in unasc_by_cat:
                        unasc_by_cat[catpath] = 0
                    unasc_by_cat[catpath] += 1
                    if options.mark:
                        msg.flag.add(u"unascribed")
            if options.mark:
                sync_and_rep(cat)

    # Present findings.
    if unasc_by_cat:
        nunasc = reduce(lambda s, x: s + x, unasc_by_cat.itervalues())
        ncats = len(unasc_by_cat)
        print "===? Unascribed: %d entries in %d catalogs" % (nunasc, ncats)
        catnames = unasc_by_cat.keys()
        catnames.sort()
        rown = catnames
        data = [[unasc_by_cat[x] for x in catnames]]
        print tabulate(data=data, rown=rown, indent="  ")


def ascribe_updated (options, configs_catpaths, user):

    nasc = 0
    for config, catpaths in configs_catpaths:
        if user not in config.users:
            error("unknown user '%s' in config '%s'" % (user, config.path))

        mkdirpath(config.udata[user].ascroot)

        for catpath in catpaths:
            nasc += ascribe_updated_cat(options, config, user, catpath)

    if nasc > 0:
        print "===! Ascribed as modified: %d entries" % nasc


def ascribe_updated_cat (options, config, user, catpath):

    # Open current catalog and all ascription catalogs.
    cat = Catalog(catpath, monitored=False, wrapf=wrapf)
    acats = collect_asc_cats(config, cat.name, user)

    # Collect all translated and unascribed messages.
    unasc_msgs = []
    for msg in cat:
        if not msg.translated:
            continue
        if not is_ascribed(msg, acats):
            unasc_msgs.append(msg)

    if not unasc_msgs:
        # No messages to ascribe.
        return 0

    if not config.vcs.is_clear(cat.filename):
        warning("%s: VCS state not clear, skipping ascription" % cat.filename)
        return 0

    # Create ascription catalog for this user if not existing already.
    acat = acats.get(user)
    if not acat:
        acat = init_asc_cat(cat.name, user, config)
    else:
        update_asc_hdr(acat, user, config)

    # Current VCS revision of the catalog.
    catrev = config.vcs.revision(cat.filename)

    # Ascribe messages: add or modify if existing.
    for msg in unasc_msgs:
        if msg not in acat:
            # Copy desired elements of the original message.
            amsg = Message()
            amsg.msgctxt = msg.msgctxt
            amsg.msgid = msg.msgid
            amsg.msgid_plural = msg.msgid_plural
            amsg.msgstr = Monlist(msg.msgstr)
            # Append to the end of catalog.
            pos = acat.add(amsg, -1)
        else:
            # Copy translation.
            amsg = acat[msg]
            amsg.msgstr = Monlist(msg.msgstr)

        # Ascribe modification of the message.
        ascribe_msg_mod(amsg, user, config, catrev)

    if sync_and_rep(acat):
        config.vcs.add(acat.filename)

    return len(unasc_msgs)


def is_ascribed (msg, acats):

    ascribed = False
    for ouser, acat in acats.iteritems():
        if msg in acat and  asc_eq(msg, acat[msg]):
            ascribed = True
            break
    return ascribed


def collect_asc_cats (config, catname, muser=None):

    acats = {}
    for ouser in config.users:
        amon = False
        if muser and ouser == muser:
            amon = True
        acatpath = os.path.join(config.udata[ouser].ascroot, catname + ".po")
        if os.path.isfile(acatpath):
            acats[ouser] = Catalog(acatpath, monitored=amon, wrapf=wrapf)

    return acats


def init_asc_cat (catname, user, config):

    udat = config.udata[user]
    acatpath = os.path.join(udat.ascroot, catname + ".po")
    acat = Catalog(acatpath, create=True, wrapf=wrapf)
    ahdr = acat.header

    ahdr.title = Monlist([u"Ascription shadow for %s.po" % catname])

    if udat.oname and udat.email:
        author = u"%s (%s) <%s>" % (udat.name, udat.oname, udat.email)
    elif udat.oname:
        author = u"%s (%s)" % (udat.name, udat.oname)
    elif udat.email:
        author = u"%s <%s>" % (udat.name, udat.email)
    else:
        author = u"%s" % udat.name
    ahdr.author = Monlist([author])

    ahdr.copyright = u"Copyright same as for the original catalog."
    ahdr.license = u"License same as for the original catalog."
    ahdr.comment = Monlist([u"===== DO NOT EDIT MANUALLY ====="])

    rfv = ahdr.replace_field_value # shortcut

    rfv("Project-Id-Version", unicode(catname))
    rfv("Report-Msgid-Bugs-To", unicode(udat.email or ""))
    rfv("PO-Revision-Date", unicode(date_now()))
    rfv("Content-Type", u"text/plain; charset=UTF-8")

    if udat.email:
        ltr = "%s <%s>" % (udat.name, udat.email)
    else:
        ltr = udat.name
    rfv("Last-Translator", unicode(ltr))

    if config.lang_team:
        if config.team_email:
            tline = u"%s <%s>" % (config.lang_team, config.team_email)
        else:
            tline = config.lang_team
        rfv("Language-Team", unicode(tline))
    else:
        ahdr.remove_field("Language-Team")

    if config.plural_header:
        rfv("Plural-Forms", unicode(config.plural_header))
    else:
        ahdr.remove_field("Plural-Forms")

    return acat


def update_asc_hdr (acat, user, config):

    acat.header.replace_field_value("PO-Revision-Date", unicode(date_now()))


def ascribe_msg_mod (amsg, user, config, catrev):

    modstr = date_now()
    if catrev:
        modstr += " | " + catrev
    asc_append_field(amsg, "modified", modstr)


def asc_eq (msg1, msg2):
    """
    Whether two messages are equal from the ascription viewpoint.
    """

    return (    msg1.msgctxt == msg2.msgctxt
            and msg1.msgid == msg2.msgid
            and msg1.msgid_plural == msg2.msgid_plural
            and msg1.msgstr == msg2.msgstr)


fld_sep = ":"


def asc_get_fields (msg, field, defvals=[]):

    values = []
    for text in msg.manual_comment:
        text = text.strip()
        lst = [x.strip() for x in text.split(fld_sep, 1)]
        if lst and lst[0] == field:
            if len(lst) == 2:
                values.append(lst[1])
            else:
                values.append("")
    if not values:
        values = defvals
    return values


def asc_set_field (msg, field, value):

    stext = u"".join([field, fld_sep, " ", str(value)])

    # Try to find the field and replace its value.
    replaced = False
    for i in range(len(msg.manual_comment)):
        text = msg.manual_comment[i].strip()
        lst = [x.strip() for x in text.split(fld_sep, 1)]
        if lst and lst[0] == field:
            msg.manual_comment[i] = stext
            replaced = True
            break

    # Field not found, append.
    if not replaced:
        msg.manual_comment.append(stext)


def asc_append_field (msg, field, value):

    stext = u"".join([field, fld_sep, " ", str(value)])
    msg.manual_comment.append(stext)


def sync_and_rep (cat):

    modified = cat.sync()
    if modified:
        print "!    " + cat.filename

    return modified


def date_now ():

    return time.strftime("%Y-%m-%d %H:%M%z")


if __name__ == "__main__":
    main()

