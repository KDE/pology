import os
import sys
import types

import pology


SRCDIR = os.path.dirname(os.path.dirname(os.path.abspath(pology.__file__)))


def _fake_install(tmp_path, monkeypatch):
    pkgdir = tmp_path / "site-packages" / "pology"
    pkgdir.mkdir(parents=True)
    monkeypatch.setattr(pology, "__file__", str(pkgdir / "__init__.py"))
    monkeypatch.setattr(pology, "datadir", lambda: str(tmp_path / "datadir"))
    return pkgdir


def test_version_from_source_checkout():
    with open(os.path.join(SRCDIR, "VERSION"), encoding="utf-8") as f:
        expected = f.read().strip()

    assert pology.version() == expected


def test_version_from_installed_package_file(tmp_path, monkeypatch):
    pkgdir = _fake_install(tmp_path, monkeypatch)
    (pkgdir / "VERSION").write_text("1.2.3\n", encoding="utf-8")

    assert pology.version() == "1.2.3"
    assert pology.version_info() == (1, 2, 3, "")


def test_version_from_installed_package_metadata(tmp_path, monkeypatch):
    _fake_install(tmp_path, monkeypatch)
    metadata = types.ModuleType("importlib.metadata")
    metadata.version = lambda name: "4.5.6" if name == "pology" else None
    monkeypatch.setitem(sys.modules, "importlib.metadata", metadata)

    assert pology.version() == "4.5.6"
