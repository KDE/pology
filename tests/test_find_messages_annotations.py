# -*- coding: UTF-8 -*-

from pology.match import make_matcher, make_msg_matcher
from pology.message import Message


class _Params:
    case = False


def _annotation_msg():
    return Message({
        "msgid": "test",
        "manual_comment": [
            "skip-rule: trasno-plug-in(2), term-foo",
            "well-spelled: quux.bar, frobnicate",
        ],
    })


def _match(name, value, neg=False):
    return make_matcher(name, value, [], _Params(), neg=neg)


def test_skiprule_matches_multiple_exact_annotations():
    msg = _annotation_msg()
    assert _match("skiprule", "trasno-plug-in(2)")(msg, msg, None)
    assert _match("skiprule", "term-foo")(msg, msg, None)
    assert not _match("skiprule", "plug-in(2)")(msg, msg, None)


def test_wellspelled_matches_multiple_exact_annotations():
    msg = _annotation_msg()
    assert _match("wellspelled", "quux.bar")(msg, msg, None)
    assert _match("wellspelled", "frobnicate")(msg, msg, None)
    assert not _match("wellspelled", "quuxXbar")(msg, msg, None)


def test_annotation_negative_matchers():
    msg = _annotation_msg()
    assert not _match("skiprule", "term-foo", neg=True)(msg, msg, None)
    assert _match("skiprule", "missing", neg=True)(msg, msg, None)
    assert not _match("wellspelled", "frobnicate", neg=True)(msg, msg, None)
    assert _match("wellspelled", "missing", neg=True)(msg, msg, None)


def test_annotation_fexpr_with_regex_special_rule_id():
    msg = _annotation_msg()
    matcher = make_msg_matcher("skiprule/trasno-plug-in(2)/")
    assert matcher(msg, msg, None)
    matcher = make_msg_matcher(
        "skiprule/trasno-plug-in(2)/ or wellspelled/quux.bar/")
    assert matcher(msg, msg, None)
