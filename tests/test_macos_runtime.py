"""The frozen runtime must not read OpenSSL config from the build environment."""

import os
import runpy
import sys
from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / "packaging/macos/hooks/runtime_openssl.py"


def test_frozen_openssl_uses_bundled_configuration(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    monkeypatch.delenv("OPENSSL_CONF", raising=False)
    runpy.run_path(str(HOOK))
    assert os.environ["OPENSSL_CONF"] == str(tmp_path / "openssl.cnf")


def test_explicit_openssl_configuration_is_respected(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    monkeypatch.setenv("OPENSSL_CONF", "/custom/openssl.cnf")
    runpy.run_path(str(HOOK))
    assert os.environ["OPENSSL_CONF"] == "/custom/openssl.cnf"
