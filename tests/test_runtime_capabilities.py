from __future__ import annotations

from pathlib import Path

from aespa import runtime_capabilities


def test_non_linux_hosts_always_support_graphical_display(monkeypatch):
    monkeypatch.setattr(runtime_capabilities.sys, "platform", "darwin")
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)

    assert runtime_capabilities.graphical_display_available() is True


def test_linux_without_display_environment_is_headless(monkeypatch):
    monkeypatch.setattr(runtime_capabilities.sys, "platform", "linux")
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    monkeypatch.delenv("XDG_RUNTIME_DIR", raising=False)

    assert runtime_capabilities.graphical_display_available() is False


def test_linux_wayland_requires_a_connectable_socket(monkeypatch, tmp_path):
    monkeypatch.setattr(runtime_capabilities.sys, "platform", "linux")
    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))
    monkeypatch.delenv("DISPLAY", raising=False)
    checked = []
    monkeypatch.setattr(
        runtime_capabilities,
        "_unix_socket_available",
        lambda path: checked.append(path) or True,
    )

    assert runtime_capabilities.graphical_display_available() is True
    assert checked == [Path(tmp_path) / "wayland-0"]


def test_linux_wayland_accepts_an_absolute_socket_path(monkeypatch, tmp_path):
    display = tmp_path / "custom-wayland"
    monkeypatch.setattr(runtime_capabilities.sys, "platform", "linux")
    monkeypatch.setenv("WAYLAND_DISPLAY", str(display))
    monkeypatch.delenv("XDG_RUNTIME_DIR", raising=False)
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.setattr(
        runtime_capabilities,
        "_unix_socket_available",
        lambda path: path == display,
    )

    assert runtime_capabilities.graphical_display_available() is True


def test_linux_x11_requires_a_connectable_local_socket(monkeypatch):
    monkeypatch.setattr(runtime_capabilities.sys, "platform", "linux")
    monkeypatch.setenv("DISPLAY", ":3.0")
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    checked = []
    monkeypatch.setattr(
        runtime_capabilities,
        "_unix_socket_available",
        lambda path: checked.append(path) or True,
    )

    assert runtime_capabilities.graphical_display_available() is True
    assert checked == [Path("/tmp/.X11-unix/X3")]
