from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_macos_pyinstaller_inputs_are_rooted_when_spec_is_written_to_build() -> None:
    script = (REPO_ROOT / "scripts" / "build_mac.sh").read_text()
    data_arguments = [line.strip() for line in script.splitlines() if "--add-data" in line]

    assert "--specpath build" in script
    assert len(data_arguments) == 6
    assert all('--add-data "$REPO_ROOT/' in argument for argument in data_arguments)
    assert '--icon "$REPO_ROOT/$ICNS"' in script
    assert '"$REPO_ROOT/src/aespa/desktop.py"' in script


def test_windows_pyinstaller_inputs_are_rooted_and_failure_is_checked() -> None:
    script = (REPO_ROOT / "scripts" / "build_win.ps1").read_text()
    data_arguments = [line.strip() for line in script.splitlines() if "--add-data" in line]

    assert "--specpath build" in script
    assert len(data_arguments) == 6
    assert all('--add-data "$RepoRoot\\' in argument for argument in data_arguments)
    assert '--icon "$RepoRoot\\$Ico"' in script
    assert '"$RepoRoot\\src\\aespa\\desktop_win.py"' in script
    assert 'throw "PyInstaller failed with exit code $LASTEXITCODE"' in script
