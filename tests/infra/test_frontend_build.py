from __future__ import annotations

import importlib
import os
import subprocess
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


@pytest.mark.parametrize(
    "changed",
    [
        "src/App.jsx",
        "public/sw.js",
        "vite.config.js",
        "package-lock.json",
        "index.html",
    ],
)
def test_frontend_rebuilds_when_any_build_input_changes(tmp_path, monkeypatch, changed):
    main = importlib.import_module("aespa.main")
    frontend = tmp_path / "frontend"
    built = tmp_path / "web"
    built.mkdir()
    (built / "index.html").write_text("built", encoding="utf-8")
    for relative in (
        "src/App.jsx",
        "public/sw.js",
        "vite.config.js",
        "package.json",
        "package-lock.json",
        "index.html",
    ):
        source = frontend / relative
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("source", encoding="utf-8")
        os.utime(source, (100, 100))
    os.utime(built / "index.html", (200, 200))
    monkeypatch.setattr(main, "__file__", str(tmp_path / "src/aespa/main.py"))
    monkeypatch.setattr(main, "get_settings", lambda: SimpleNamespace(web_dir=built))
    build = Mock()
    monkeypatch.setattr(subprocess, "run", build)

    main._build_frontend_if_stale()
    build.assert_not_called()

    os.utime(frontend / changed, (300, 300))
    main._build_frontend_if_stale()
    build.assert_called_once_with(["npm", "run", "build"], cwd=frontend, check=True)
