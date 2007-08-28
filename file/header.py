# -*- coding: UTF-8 -*-

from pology.misc.wrap import wrap_field
from pology.misc.monitored import Monitored, Monlist, Monpair
from message import Message

import time
import re

_Header_spec = {
    "title" : {"type" : Monlist,
               "spec" : {"*" : {"type" : unicode}}},
    "copyright" : {"type" : unicode},
    "license" : {"type" : unicode},
    "author" : {"type" : Monlist,
                "spec" : {"*" : {"type" : unicode}}},
    "comment" : {"type" : Monlist,
                 "spec" : {"*" : {"type" : unicode}}},
    "field" : {"type" : Monlist,
               "spec" : {"*" : {"type" : Monpair,
                                "spec" : {"first" : {"type" : unicode},
                                          "second" : {"type" : unicode}}}}},
    # Dummies for summary iteration in catalog:
    "obsolete" : {"type" : bool, "derived" : True},
    "key" : {"type" : bool, "derived" : True},
}

class Header (Monitored):

    def __init__ (self, msg=None):

        if msg: # parse header message
            # Comments.
            self._title = Monlist()
            self._copyright = u""
            self._license = u""
            self._author = Monlist()
            self._comment = Monlist()
            intitle = True
            for c in msg.manual_comment:
                if 0: pass
                elif not self._copyright and re.search("copyright", c, re.I):
                    self._copyright = c
                    intitle = False
                elif not self._license and re.search("license", c, re.I):
                    self._license = c
                    intitle = False
                elif re.search("<.*@.*>", c):
                    self._author.append(c)
                    intitle = False
                elif intitle:
                    self._title.append(c)
                else:
                    self._comment.append(c)

            # Header fields.
            self._field = Monlist()
            for field in msg.msgstr[0].split("\n"):
                m = re.match(r"(.*?): ?(.*)", field)
                if m: self._field.append(Monpair(*m.groups()))

            # Store the message.
            self._message = msg

        else: # create default fields
            self._title = Monlist([u"SOME DESCRIPTIVE TITLE."]);
            self._copyright = u"Copyright (C) YEAR THE PACKAGE'S COPYRIGHT HOLDER"
            self._license = u"This file is distributed under the same license as the PACKAGE package."
            self._author = Monlist([u"FIRST AUTHOR <EMAIL@ADDRESS>, YEAR."])
            self._comment = Monlist([u""])

            self._field = Monlist([
                Monpair(u"Project-Id-Version", u"PACKAGE VERSION"),
                Monpair(u"Report-Msgid-Bugs-To", u""),
                Monpair(u"POT-Creation-Date", unicode(time.strftime("%Y-%m-%d %H:%M%z"))),
                Monpair(u"PO-Revision-Date", u"YEAR-MO-DA HO:MI+ZONE"),
                Monpair(u"Last-Translator", u"FULL NAME <EMAIL@ADDRESS>"),
                Monpair(u"Language-Team", u"LANGUAGE <LL@li.org>"),
                Monpair(u"MIME-Version", u"1.0"),
                Monpair(u"Content-Type", u"text/plain; charset=CHARSET"),
                Monpair(u"Content-Transfer-Encoding", u"8bit"),
                Monpair(u"Plural-Forms", u"nplurals=INTEGER; plural=EXPRESSION;"),
            ])

            # Create the message.
            self._message = Message()
            self._remake_msg(force=True)

        self.assert_spec_init(_Header_spec)

        # Unmodify all monitored members.
        self.modcount = 0

    def __getattr__ (self, att):
        if att == "obsolete":
            return False
        elif att == "key":
            return Message().key # key of an empty-msgid message
        else:
            return Monitored.__getattr__(self, att)

    def _remake_msg (self, force=False):
        m = self._message

        if force \
        or self.title_modcount or self.title.modcount \
        or self.copyright_modcount \
        or self.license_modcount \
        or self.author_modcount or self.author.modcount \
        or self.comment_modcount or self.comment.modcount:
            m.manual_comment = Monlist()
            for t in self.title:
                m.manual_comment.append(t)
            if self.copyright:
                m.manual_comment.append(self.copyright)
            if self.license:
                m.manual_comment.append(self.license)
            for a in self.author:
                m.manual_comment.append(a)
            for c in self.comment:
                m.manual_comment.append(c)

        if force or self.field_modcount or self.field.modcount:
            m.msgstr = Monlist([u""])
            for field in self.field:
                m.msgstr[0] += "%s: %s\\n" % tuple(field)

    def to_msg (self, force=False):
        self._remake_msg(force)
        return self._message

    def to_lines (self, wrapf=wrap_field, force=False):
        return self.to_msg(force).to_lines(wrapf, force)

    def to_string (self, wrapf=wrap_field, force=False):
        return self.to_msg(force).to_string(wrapf, force)

    def select_fields (self, name):
        """Find header fields with the given name.

        Return a list of references to field-value pairs matching the name.
        """
        fields = []
        for pair in self.field:
            if pair.first == name:
                fields.append(pair)
        return fields

