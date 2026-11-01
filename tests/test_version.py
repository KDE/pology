import sys
import types

import pology


UNCONFIGURED = "@CONFIG_VERSION@" # as in a source checkout or a wheel


def _fake_tree(tmp_path, monkeypatch):
    pkgdir = tmp_path / "site-packages" / "pology"
    pkgdir.mkdir(parents=True)
    datadir = tmp_path / "share" / "pology"
    datadir.mkdir(parents=True)
    monkeypatch.setattr(pology, "__file__", str(pkgdir / "__init__.py"))
    monkeypatch.setattr(pology, "datadir", lambda: str(datadir))
    return pkgdir, datadir


def test_version_from_source_checkout(tmp_path, monkeypatch):
    _, datadir = _fake_tree(tmp_path, monkeypatch)
    (datadir / "VERSION").write_text("0.13\n", encoding="utf-8")

    assert pology._resolve_version(UNCONFIGURED) == "0.13"


def test_version_from_installed_package(tmp_path, monkeypatch):
    pkgdir, _ = _fake_tree(tmp_path, monkeypatch)
    (pkgdir / "VERSION").write_text("1.2.3\n", encoding="utf-8")

    # The copy inside the package wins over the data directory, and an empty
    # configured version (CMake installs) still falls through to it.
    assert pology._resolve_version(UNCONFIGURED) == "1.2.3"
    assert pology._resolve_version("") == "1.2.3"


def test_version_from_installed_package_metadata(tmp_path, monkeypatch):
    _fake_tree(tmp_path, monkeypatch)
    metadata = types.ModuleType("importlib.metadata")
    metadata.version = lambda name: "4.5.6" if name == "pology" else None
    monkeypatch.setitem(sys.modules, "importlib.metadata", metadata)

    assert pology._resolve_version(UNCONFIGURED) == "4.5.6"
