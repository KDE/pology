#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import os
import re
import sys

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name
from pygments.lexer import RegexLexer, bygroups, include
from pygments.token import Keyword, Comment, Name, String, Text, Number, Generic
from pygments.util import ClassNotFound


_cmd = os.path.basename(sys.argv[0])


def main ():

    for infile in sys.argv[1:]:
        add_html_highlight(infile)


def add_html_highlight (infile):

    ifh = open(infile)
    htmlstr = ifh.read().decode("utf8")
    ifh.close()

    pre_rx = re.compile(r"(<pre .*?>)"
                        r"\s*<!--\s*language:\s*(\S*)\s*-->\s*"
                        r"(.*?)"
                        r"(</pre>)",
                        re.S|re.U)
    p = 0
    segs = []
    while True:
        m = pre_rx.search(htmlstr, p)
        if m is None:
            segs.append(htmlstr[p:])
            break
        p1, p2 = m.span()
        segs.append(htmlstr[p:p1])
        otag, language, snippet, ctag = m.groups()
        try:
            lexer = get_custom_lexer_by_name(language)
            if lexer is None:
                lexer = get_lexer_by_name(language)
        except ClassNotFound:
            seg = snippet
            warning("Unknown language '%s'." % language)
            lexer = None
        if lexer:
            snippet, tags = hide_tags(snippet)
            snippet = unescape_xml(snippet)
            seg = highlight(snippet, lexer, HtmlFormatter(nowrap=True))
            seg = unhide_tags(seg, tags)
        segs.extend((otag, seg, ctag))
        p = p2
    htmlstr_mod = "".join(segs)

    ofh = open(infile, "w")
    ofh.write(htmlstr_mod.encode("utf8"))
    ofh.close()


def warning (msg):

    sys.stderr.write("%s: [warning] %s\n" % (_cmd, msg))


def unescape_xml (s):

    s = s.replace("&lt;", "<")
    s = s.replace("&gt;", ">")
    s = s.replace("&apos;", "'")
    s = s.replace("&quot;", '"')
    s = s.replace("&amp;", "&")
    return s


_hide_tags_rx = re.compile(r"<.*?>", re.S|re.U)
_hide_tags_rseq = u"⌒"

def hide_tags (s):

    tags = _hide_tags_rx.findall(s)
    s = _hide_tags_rx.sub(_hide_tags_rseq, s)
    return s, tags


def unhide_tags (s, tags):

    segs = []
    i = 0
    p1 = 0
    while True:
        p2 = s.find(_hide_tags_rseq, p1)
        if p2 < 0:
            p2 = len(s)
        segs.append(s[p1:p2])
        if p2 == len(s):
            break
        assert i < len(tags)
        segs.append(tags[i])
        i += 1
        p1 = p2 + len(_hide_tags_rseq)
    assert i == len(tags)
    s = "".join(segs)
    return s


_custom_lexers = set()

def get_custom_lexer_by_name (language):

    for lexer_type in _custom_lexers:
        if language in lexer_type.aliases:
            return lexer_type()
    return None


from pygments.lexers import GettextLexer
class GettextXLexer (GettextLexer):
    pass
GettextXLexer.tokens = {
    'root': [
        (r'^#,\s.*?$', Name.Decorator),
        (r'^#:\s.*?$', Name.Label),
        (r'^#\|\s*(msgid_plural|msgid)\s*"', Comment.Single, 'prevstring'),
        (r'^(#|#\.\s|#\|\s|#~\s|#\s).*$', Comment.Single),
        (r'^(msgstr\[)(\d)(\])',
            bygroups(Name.Variable, Number.Integer, Name.Variable)),
        (r'^(msgctxt|msgid_plural|msgid|msgstr|msgscr)',
            bygroups(Name.Variable)),
        (r'"', String, 'string'),
        (r'^\.\.\.$', Text), # for cutting out intermediate messages
        (ur'\u2060', Text), # for not splitting on empty line in POT extraction
        (r'\s+', Text),
    ],
    'string': [
        (r'\\.', String.Escape),
        (r'\{\{|\}\}', String.Escape),
        (r'\{-.*?-\}', Generic.Deleted),
        (r'\{\+.*?\+\}', Generic.Inserted),
        (r'\{([a-z].*?|)\}', String.Interpol),
        (r'%[ -+]?\d*\.?\d*[idufFgGeEcs%]', String.Interpol),
        (r'<(?=[\w/])', String.Other, 'tag'),
        (r'~~', String.Escape),
        (r'~', String.Other),
        (r'\$\[', String.Symbol, 'script'),
        (r'"', String, '#pop'),
        (r'.', String),
    ],
    'prevstring': [
        (r'\{-.*?-\}', Generic.Deleted),
        (r'\{\+.*?\+\}', Generic.Inserted),
        (r'"', Comment.Single, '#pop'),
        (r'.', Comment.Single),
    ],
    'tag': [
        (r'>', String.Other, '#pop'),
        (r'.', String.Other),
    ],
    'script': [
        (r'\]', String.Symbol, '#pop'),
        (r"''", String.Escape),
        (r"'", String.Symbol, 'scriptquote'),
        include('string'),
    ],
    'scriptquote': [
        (r"''", String.Escape),
        (r"'", String.Symbol, '#pop'),
        include('string'),
    ],
}
_custom_lexers.add(GettextXLexer)


from pygments.lexers import CppLexer
class CppXLexer (CppLexer):
    pass
CppXLexer.tokens = CppLexer.tokens.copy()
CppXLexer.tokens.update({
    'string': [
        (r'"', String, '#pop'),
        (r'\\([\\abfnrtv"\']|x[a-fA-F0-9]{2,4}|[0-7]{1,3})', String.Escape),
        (r'%(\([a-zA-Z0-9_]+\))?[-#0 +]*([0-9]+|[*])?(\.([0-9]+|[*]))?'
         r'[hlL]?[diouxXeEfFgGcrs%]', String.Interpol),
        (r'\{\{|\}\}', String.Escape),
        (r'\{.*?\}', String.Interpol),
        (r'%\d+', String.Interpol),
        (r'[^\\"\n%{}]+', String), # all other characters
        (r'\\\n', String), # line continuation
        (r'\\', String), # stray backslash
        (r'[%{}]', String),
    ],
})
_custom_lexers.add(CppXLexer)


from pygments.lexers import PythonLexer
class PythonXLexer (PythonLexer):
    pass
PythonXLexer.tokens.update({
    'strings': [
        (r'%(\([a-zA-Z0-9_]+\))?[-#0 +]*([0-9]+|[*])?(\.([0-9]+|[*]))?'
         r'[hlL]?[diouxXeEfFgGcrs%]', String.Interpol),
        (r'\{\{|\}\}', String.Escape),
        (r'\{.*?\}', String.Interpol),
        (r'[^\\\'"%{}\n]+', String),
        (r'[\'"\\]', String),
        (r'[%{}]', String),
    ],
})
_custom_lexers.add(PythonXLexer)


if __name__ == "__main__":
    main()
