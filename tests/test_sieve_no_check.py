from types import SimpleNamespace

from pology.message import Message
from pology.sieve import flag_no_check, msg_no_check
from sieve.check_docbook4 import Sieve as Docbook4Sieve
from sieve.check_kde4 import Sieve as Kde4Sieve
from sieve.check_rules import Sieve as RulesSieve
from sieve.check_tp_kde import Sieve as TpKdeSieve
from sieve.check_tp_kde import _known_checks as tp_kde_checks
from sieve.check_tp_wesnoth import Sieve as TpWesnothSieve
from sieve.check_tp_wesnoth import _known_checks as wesnoth_checks


NO_CHECK_COMMENT = "|, " + flag_no_check


def _message (msgid, msgstr, no_check=False):

    init = {"msgid": msgid, "msgstr": [msgstr]}
    if no_check:
        init["manual_comment"] = [NO_CHECK_COMMENT]
    return Message(init)


def test_msg_no_check():

    assert not msg_no_check(_message("Original", "Translation"))
    assert msg_no_check(_message("Original", "Translation", no_check=True))


def test_check_kde4_skips_marked_message():

    sieve = Kde4Sieve(SimpleNamespace(strict=True, lokalize=False))
    cat = SimpleNamespace(filename="test.po")

    sieve.process(_message("<emphasis>Original</emphasis>",
                           "<emphasis>Translation"), cat)
    assert sieve.nproblems == 1

    sieve.nproblems = 0
    sieve.process(_message("<emphasis>Original</emphasis>",
                           "<emphasis>Translation", no_check=True), cat)
    assert sieve.nproblems == 0


def test_check_docbook4_skips_marked_message():

    sieve = Docbook4Sieve(SimpleNamespace(showmsg=False, lokalize=False))
    cat = SimpleNamespace(filename="test.po")

    sieve.process(_message("<emphasis>Original</emphasis>",
                           "<emphasis>Translation"), cat)
    assert sieve.nproblems == 1

    sieve.nproblems = 0
    sieve.process(_message("<emphasis>Original</emphasis>",
                           "<emphasis>Translation", no_check=True), cat)
    assert sieve.nproblems == 0


def test_check_tp_kde_skips_marked_message():

    sieve = TpKdeSieve(SimpleNamespace(strict=True, showmsg=False,
                                       lokalize=False, check=None))
    sieve.current_checks = [tp_kde_checks["kde4markup"]]
    sieve.pcache = {"strict": True}
    cat = SimpleNamespace(filename="test.po")

    sieve.process(_message("<emphasis>Original</emphasis>",
                           "<emphasis>Translation"), cat)
    assert sieve.nproblems == 1

    sieve.nproblems = 0
    sieve.process(_message("<emphasis>Original</emphasis>",
                           "<emphasis>Translation", no_check=True), cat)
    assert sieve.nproblems == 0


def test_check_tp_wesnoth_skips_marked_message():

    sieve = TpWesnothSieve(SimpleNamespace(check=None, showmsg=False,
                                           lokalize=False))
    sieve.current_checks = [wesnoth_checks["interp"]]
    cat = SimpleNamespace(filename="test.po")

    sieve.process(_message("Hello $name", "Ola"), cat)
    assert sieve.nproblems == 1

    sieve.nproblems = 0
    sieve.process(_message("Hello $name", "Ola", no_check=True), cat)
    assert sieve.nproblems == 0


class _RecordingRule (object):
    """Rule which records each application and never fails."""

    ident = "test-rule"
    disabled = False
    environ = None
    manual = False
    mfilter = None

    def __init__ (self):
        self.ncalls = 0

    def process (self, msg, cat, envs=None, nofilter=False):
        self.ncalls += 1
        return []


def _rules_sieve ():

    sieve = RulesSieve(SimpleNamespace(
        lang="en", env=None, envonly=False, accel=None, markup=None,
        rule=None, rulerx=None, norule=None, norulerx=None,
        stat=False, showfmsg=False, showmsg=False, lokalize=False,
        mark=False, byrule=False, ruleinfo=False, branch=None,
        rfile=None, rdir=None, xml=None,
    ))
    sieve.envs = []
    sieve.ruleFilters = [None]
    rule = _RecordingRule()
    sieve.rules = [rule]
    return sieve, rule


def test_check_rules_skips_marked_message():

    cat = SimpleNamespace(filename="test.po")

    sieve, rule = _rules_sieve()
    sieve.process(_message("Original", "Translation"), cat)
    assert rule.ncalls == 1

    sieve, rule = _rules_sieve()
    sieve.process(_message("Original", "Translation", no_check=True), cat)
    assert rule.ncalls == 0
