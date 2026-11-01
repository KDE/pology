import io
import json

try:
    from mock import MagicMock, patch
except ImportError:
    from unittest.mock import MagicMock, patch

import pology.msgreport as msgreport
from pology.message import Message
from pology.msgreport import report_msg_to_lokalize, rule_json_error, spell_json_error


def _msg(**kwargs):
    init = {
        "refline": 12,
        "refentry": 3,
        "msgid": "Source string",
        "msgstr": [""],
    }
    init.update(kwargs)
    return Message(init)


def _records(out):
    return [json.loads(line) for line in out.getvalue().splitlines()]


def test_rule_json_error_with_context_and_plurals():
    msg = _msg(
        msgctxt="menu",
        msgid="%d file",
        msgid_plural="%d files",
        msgstr=["%d ficheiro", "%d ficheiros"],
    )
    cat = MagicMock(filename="po/gl.po")
    rule = MagicMock(ident="plural-number")
    out = io.StringIO()

    rule_json_error(msg, cat, rule, [("msgstr", 1, [(3, 6), (7, 12)])], file=out)

    assert _records(out) == [{
        "file": "po/gl.po",
        "line": 12,
        "entry": 3,
        "msgctxt": "menu",
        "msgid": "%d file",
        "field": "msgstr",
        "plural": 1,
        "spans": [[3, 6], [7, 12]],
        "rule": "plural-number",
    }]


def test_rule_json_error_offsets_are_characters():
    msg = _msg(msgstr=["acción incompleta"])
    cat = MagicMock(filename="po/gl.po")
    out = io.StringIO()

    rule_json_error(msg, cat, MagicMock(ident="accent"), [("msgstr", 0, [(0, 6)])],
                    file=out)

    record = _records(out)[0]
    assert record["field"] == "msgstr"
    assert record["plural"] == 0
    assert msg.msgstr[0][slice(*record["spans"][0])] == "acción"


def test_spell_json_error():
    msg = _msg(msgctxt="menu", msgid="%d file", msgid_plural="%d files",
               msgstr=["%d ficheiro", "%d ficheiros"])
    cat = MagicMock(filename="po/gl.po")
    out = io.StringIO()

    spell_json_error(msg, cat, "ficheiros", pluralId=1, spans=[(3, 12)], file=out)

    assert _records(out) == [{
        "file": "po/gl.po",
        "line": 12,
        "entry": 3,
        "msgctxt": "menu",
        "msgid": "%d file",
        "field": "msgstr",
        "plural": 1,
        "spans": [[3, 12]],
        "word": "ficheiros",
    }]


def test_report_msg_to_lokalize_highlight_spec():
    msg = _msg(msgstr=["ficheiro mal escrito"])
    cat = MagicMock(filename="po/gl.po")

    methods = {}
    dbus = MagicMock()
    bus = dbus.SessionBus.return_value
    bus.list_names.return_value = ["org.kde.lokalize-test"]
    lokalizeobj = bus.get_object.return_value
    lokalizeobj.get_dbus_method.side_effect = (
        lambda name, iface=None: methods.setdefault(name, MagicMock()))
    methods["openFileInEditor"] = MagicMock(return_value=0)

    try:
        with patch.object(msgreport, "_get_module", return_value=dbus):
            report_msg_to_lokalize(
                msg, cat, [("msgstr", 0, [(3, 10, "bad word")])])
    finally:
        for key in ("lokalizeobj", "lokalizeinst", "openFileInEditor",
                    "visitedcats"):
            msgreport.__dict__.pop(key, None)

    methods["gotoEntry"].assert_called_once_with(msg.refentry - 1)
    methods["setEntryFilteredOut"].assert_called_once_with(
        msg.refentry - 1, False)
