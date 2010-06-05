# -*- coding: UTF-8 -*-

"""
Report info, warning and error messages.

Functions for Pology tools to issue reports to the user at runtime.
May colorize some output.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import os
import sys
import locale
import time

from pology import _, n_
import pology.misc.colors as C


_prev_text_cr = [None, None]

def encwrite (file, text):
    """
    Write unicode text to file using best encoding guess.

    If the file has been opened with explicit encoding, that encoding is used.
    Otherwise a guess is made based on the environment locale.

    @param file: file to write to
    @type file: C{file}
    @param text: text to write
    @type text: string or unicode
    """

    enc = getattr(file, "encoding", None) or locale.getpreferredencoding()
    text = text.encode(enc, "replace")

    # If last output was returning to line start with CR, clean up the line.
    if _prev_text_cr[0] is not None and not _prev_text_cr[1].closed:
        cstr = "\r%s\r" % (" " * len(_prev_text_cr[0]))
        _prev_text_cr[0] = None
        _prev_text_cr[1].write(cstr)
        _prev_text_cr[1] = None

    # If current output is returning to line start with CR, record it.
    if text.endswith("\r"):
        cstr = text
        if "\n" in cstr:
            cstr = cstr[cstr.rfind("\n") + 1:]
        _prev_text_cr[0] = cstr
        _prev_text_cr[1] = file

    file.write(text)


def report (text, showcmd=False, subsrc=None, file=sys.stdout, newline=True):
    """
    Generic report.

    Text is output to the file descriptor,
    with one newline appended by default.

    @param text: text to report
    @type text: string
    @param showcmd: whether to show the command name
    @type showcmd: bool
    @param subsrc: more detailed source of the text
    @type subsrc: C{None} or string
    @param file: send output to this file descriptor
    @type file: C{file}
    @param newline: whether to append newline to output
    @type newline: bool
    """

    cmdname = None
    if showcmd:
        cmdname = os.path.basename(sys.argv[0])

    lines = text.split("\n")
    for i in range(len(lines)):
        if i == 0:
            if cmdname and subsrc:
                head = "%s (%s): " % (cmdname, subsrc)
            elif cmdname:
                head = "%s: " % cmdname
            elif subsrc:
                head = "(%s): " % subsrc
            else:
                head = ""
            lhead = len(head)
        else:
            if lhead:
                head = "... "
            else:
                head = ""
        lines[i] = head + lines[i]

    if newline:
        lines.append("")

    text = "\n".join(lines)
    encwrite(file, text)


def warning (text, showcmd=True, subsrc=None, file=sys.stderr):
    """
    Generic warning.

    @param text: text to report
    @type text: string
    @param showcmd: whether to show the command name
    @type showcmd: bool
    @param subsrc: more detailed source of the text
    @type subsrc: C{None} or string
    @param file: send output to this file descriptor
    @type file: C{file}
    """

    pref = "warning"
    if file.isatty():
        np = _nonws_after_colreset(text)
        text = text[:np] + C.ORANGE + text[np:] + C.RESET
        pref = C.BOLD + pref + C.RESET
    report("%s: %s" % (pref, text), showcmd=showcmd, subsrc=subsrc, file=file)


def error (text, code=1, showcmd=True, subsrc=None, file=sys.stderr):
    """
    Generic error (aborts the execution).

    Exits with the given code.

    @param text: text to report
    @type text: string
    @param code: the exit code
    @type code: int
    @param showcmd: whether to show the command name
    @type showcmd: bool
    @param file: send output to this file descriptor
    @type file: C{file}
    """

    pref = "error"
    if file.isatty():
        np = _nonws_after_colreset(text)
        text = text[:np] + C.RED + text[np:] + C.RESET
        pref = C.BOLD + pref + C.RESET
    report("%s: %s" % (pref, text), showcmd=showcmd, subsrc=subsrc, file=file)
    sys.exit(code)


# Position in text of first non-whitespace after first whitespace sequence
# after last shell color reset.
# 0 if no color reset, len(text) if no conforming non-whitespace after reset.
def _nonws_after_colreset (text):

    p = text.rfind(C.RESET)
    if p >= 0:
        p += len(C.RESET)
        while p < len(text) and text[p].isspace():
            p += 1
        while p < len(text) and not text[p].isspace():
            p += 1
        return p
    else:
        return 0


def init_file_progress (fpaths, timeint=0.5, stream=sys.stderr, addfmt=None):
    """
    Create a function to output progress bar while processing files.

    When a collection of files is about to be processed,
    this function can be used to construct a progress update function,
    which shows and updates the progress bar in the terminal.
    The progress update function can be called as frequently as desired
    during processing of a particular file, with file path as argument.
    For example::

        update_progress == init_file_progress(file_paths)
        for file_path in file_paths:
            for line in open(file_path).readlines():
                update_progress(file_path)
                # ...
                # Processing.
                # ...
        update_progress() # clears last progress line

    Parameter C{timeint} determines the frequency of update, in seconds.
    It should be chosen such that the progress updates themselves
    (formatting, writing out to shell) are only a small fraction
    of total processing time.

    The output stream for the progress bar can be specified
    by the C{stream} parameter.

    Additional formatting for the progress bar may be supplied
    by the C{addfmt} parameter. It can be either a function taking one
    string parameter (the basic progress bar) and returning a string,
    or a string with single C{%(file)s} formatting directive.

    @param fpaths: collection of file paths
    @type fpaths: list of strings
    @param timeint: update interval in seconds
    @type timeint: float
    @param stream: the stream to output progress to
    @type stream: file
    @param addfmt: additional format for the progress line
    @type addfmt: (text) -> text or string

    @returns: progress updating function
    @rtype: (file_path, last_time, time_interval) -> new_last_time
    """

    if not fpaths or not stream.isatty():
        return lambda x=None: x

    try:
        import curses
        curses.setupterm()
    except:
        return lambda x=None: x

    def postfmt (pstr):
        if callable(addfmt):
            pstr = addfmt(pstr)
        elif addfmt:
            pstr = addfmt % dict(file=pstr)
        return pstr

    pfmt = ("%%1s %%%dd/%d %%s" % (len(str(len(fpaths))), len(fpaths)))
    pspins = [u"–", u"\\", u"|", u"/"]
    i_spin = [0]
    i_file = [0]
    seen_fpaths = set()
    otime = [-timeint]
    enc = getattr(stream, "encoding", None) or locale.getpreferredencoding()
    minenclen = len(postfmt(pfmt % (pspins[0], 0, "")).encode(enc, "replace"))

    def update_progress (fpath=None):

        ntime = time.time()
        if ntime - otime[0] >= timeint:
            otime[0] = ntime
        elif fpath in seen_fpaths:
            return

        if fpath:
            i_spin[0] = (i_spin[0] + 1) % len(pspins)
            if fpath not in seen_fpaths:
                seen_fpaths.add(fpath)
                i_file[0] += 1

            # Squeeze file path to fit into the terminal width.
            curses.setupterm()
            acolfp = curses.tigetnum("cols") - minenclen - 2 # 2 for \r\r
            rfpath = fpath
            infix = "..."
            lenred = 1
            while len(rfpath.encode(enc, "replace")) > acolfp:
                hlfp = (len(fpath) - len(infix)) // 2 - lenred
                lenred += 1
                rfpath = fpath[:hlfp] + infix + fpath[-hlfp:]

            pstr = postfmt(pfmt % (pspins[i_spin[0]], i_file[0], rfpath))
            encwrite(stream, "\r%s\r" % pstr)
        else:
            encwrite(stream, "")
        stream.flush()

    return update_progress


def list_options (optparser, short=False, both=False):
    """
    Simple list of all option names found in the option parser.

    The list is composed of option names delimited by newlines.

    If an option is having both short and long name, the behavior
    is determined by parameters C{short} and C{both}.
    If neither is C{True}, only the long name is added to list.
    If only C{short} is C{True}, only the short name is added to list.
    If C{both} is C{True} both names are added to the list, in the order
    determined by C{short} -- if C{True}, short name is listed first.

    The list is sorted by long option names where available,
    with short name listed before or after the long name,
    depending on C{short} (C{True} for before).

    @param optparser: option parser
    @type optparser: OptionParser
    @param short: whether to prefer short names
    @type short: bool
    @param both: whether to show both long and short name of an option
    @type both: bool

    @returns: formated list of option names
    @rtype: string
    """

    optnames = []
    for opt in optparser.option_list:
        if str(opt) != opt.get_opt_string():
            sname, lname = str(opt).split("/")
            if both:
                onames = [sname, lname] if short else [lname, sname]
            else:
                onames = [sname] if short else [lname]
        else:
            onames = [opt.get_opt_string()]
        optnames.append(onames)

    elind = -1 if short else 0
    optnames.sort(key=lambda x: x[elind].lstrip("-"))
    fmtlist = "\n".join(sum(optnames, []))

    return fmtlist


def format_item_list (items, incmp=False):
    """
    Format inline item list, for insertion into text.

    @param items: items to list
    @type items: sequence of elements convertible to string by unicode()
    @param incmp: whether some items are omitted from the list
    @type incmp: bool
    @returns: inline formatted list of items
    @rtype: string
    """

    sep = _("@item:intext general separator for inline lists of items, "
            "e.g. \", \" in \"apples, bananas, cherries, and plums\"",
            ", ")
    sep_last = _("@item:intext last separator for inline lists of items, "
                 "e.g. \", and \" in \"apples, bananas, cherries, and plums\"",
                 ", and ")
    sep_two = _("@item:intext separator for inline list of exactly two items, "
                 "e.g. \" and \" in \"apples and bananas\"",
                 " and ")
    ellipsis = _("@item:intext trailing string for incomplete lists, "
                 "e.g. \"...\" in \"apples, bananas, cherries...\"",
                 "...")
    itemstrs = map(unicode, items)
    if not incmp:
        if len(itemstrs) == 0:
            return u""
        elif len(itemstrs) == 1:
            return itemstrs[0]
        elif len(itemstrs) == 2:
            return sep_two.join(itemstrs)
        else:
            return sep.join(itemstrs[:-1]) + sep_last + itemstrs[-1]
    else:
        return sep.join(itemstrs) + ellipsis

