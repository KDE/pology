from pology.catalog import Catalog
from pology.uiref import _norm_ui_cat


UI_PO = '''msgid ""
msgstr ""
"Content-Type: text/plain; charset=UTF-8\\n"
"X-Accelerator-Marker: &\\n"

msgctxt "@action"
msgid "&Save"
msgstr "Сачувај"

msgctxt "@action"
msgid "S&ave"
msgstr "Сними"
'''


def test_duplicate_ui_keys_are_disambiguated(tmp_path):
    """Both messages normalize to "Save" but differ in translation, so the
    contexts get a hash tail to keep them apart."""
    path = tmp_path / "ui.po"
    path.write_text(UI_PO, encoding="utf-8")
    cat = Catalog(str(path), monitored=False)
    contexts = [m.msgctxt for m in _norm_ui_cat(cat, False)]
    assert len(set(contexts)) == 2
    assert all(c.startswith("@action~") for c in contexts)
