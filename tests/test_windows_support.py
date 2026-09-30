"""Platform-independent contracts for the Windows-specific implementation."""

from __future__ import annotations

import zipfile
import os

import pytest
from click.testing import CliRunner

from chatclash.cli import main
from chatclash.mihomo import _extract_windows_engine, _platform_asset
from chatclash.windows import powershell_proxy_commands


def test_windows_asset_selection_prefers_baseline_zip(monkeypatch):
    monkeypatch.setattr("chatclash.mihomo.is_windows", lambda: True)
    release = {
        "tag_name": "v1.0.0",
        "assets": [
            {"name": "mihomo-windows-amd64-compatible-v1.0.0.zip"},
            {"name": "mihomo-windows-amd64-v1-go125-v1.0.0.zip"},
            {"name": "mihomo-windows-amd64-v1.0.0.zip"},
        ],
    }
    assert _platform_asset(release, "amd64")["name"] == "mihomo-windows-amd64-v1.0.0.zip"


def test_windows_archive_extracts_only_mihomo_exe(tmp_path):
    archive = tmp_path / "mihomo.zip"
    target = tmp_path / "mihomo.exe"
    with zipfile.ZipFile(archive, "w") as zipped:
        zipped.writestr("mihomo.exe", b"MZ test executable")
    _extract_windows_engine(archive, target)
    assert target.read_bytes() == b"MZ test executable"


def test_windows_archive_rejects_missing_or_duplicate_engine(tmp_path):
    missing = tmp_path / "missing.zip"
    with zipfile.ZipFile(missing, "w") as zipped:
        zipped.writestr("other.exe", b"nope")
    with pytest.raises(RuntimeError, match="exactly one"):
        _extract_windows_engine(missing, tmp_path / "mihomo.exe")


def test_powershell_output_escapes_single_quotes(monkeypatch):
    monkeypatch.setattr(
        "chatclash.windows.get_powershell_proxy_env",
        lambda **_: {"HTTP_PROXY": "http://user:o'connor@127.0.0.1:7890"},
    )
    assert powershell_proxy_commands(no_mask=True) == ["$env:HTTP_PROXY = 'http://user:o''connor@127.0.0.1:7890'"]


def test_windows_commands_are_documented_by_cli_help():
    runner = CliRunner()
    result = runner.invoke(main, ["proxy", "system", "--help"])
    assert result.exit_code == 0, result.output
    assert {"show", "enable", "disable"} <= {line.strip().split()[0] for line in result.output.splitlines() if line.startswith("  ") and line.strip() and not line.strip().startswith("-")}
    env_help = runner.invoke(main, ["proxy", "env", "--help"])
    assert env_help.exit_code == 0, env_help.output
    assert "--shell" in env_help.output
    assert "--persist" in env_help.output
    assert "--restore" in env_help.output


def test_proxy_check_uses_platform_null_device(monkeypatch):
    from chatclash import checks

    commands: list[list[str]] = []
    monkeypatch.setattr(checks, "run_shell", lambda command: commands.append(command) or "200")
    result = checks.check_proxy(urls=("https://example.test",), min_success=1)
    assert result.success_count == 1
    assert commands[0][commands[0].index("-o") + 1] == os.devnull
