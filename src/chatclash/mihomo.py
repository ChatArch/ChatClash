"""Mihomo runtime APIs."""

from __future__ import annotations

import gzip
import json
import platform
import shutil
import tempfile
import urllib.request
from pathlib import Path

from .chatenv_store import read_operator_config
from .models import CommandResult
from .paths import clash_dir, engine_path, log_file, pid_file, read_local_config
from .utils import redact_text, run_shell

UNIT_NAME = "chatclash-mihomo.service"


def daemon_unit_path() -> Path:
    return Path.home() / ".config" / "systemd" / "user" / UNIT_NAME


def daemon_unit_text() -> str:
    config = read_local_config()
    return "\n".join([
        "[Unit]",
        "Description=ChatClash Mihomo proxy service",
        "After=network-online.target",
        "",
        "[Service]",
        f"ExecStart={engine_path(config)} -d {clash_dir(config)}",
        "Restart=on-failure",
        f"WorkingDirectory={clash_dir(config)}",
        "",
        "[Install]",
        "WantedBy=default.target",
        "",
    ])


def systemctl_user(*args: str, check: bool = True) -> str:
    return run_shell(["systemctl", "--user", *args], check=check)


def install_daemon_unit() -> Path:
    unit = daemon_unit_path()
    unit.parent.mkdir(parents=True, exist_ok=True)
    unit.write_text(daemon_unit_text(), encoding="utf-8")
    systemctl_user("daemon-reload")
    systemctl_user("enable", unit.name)
    return unit


def remove_daemon_unit() -> Path:
    unit = daemon_unit_path()
    if unit.exists():
        systemctl_user("disable", unit.name, check=False)
        systemctl_user("stop", unit.name, check=False)
        unit.unlink(missing_ok=True)
        systemctl_user("daemon-reload", check=False)
    return unit


def daemon_active() -> bool:
    if not daemon_unit_path().exists():
        return False
    try:
        systemctl_user("is-active", "--quiet", daemon_unit_path().name)
        return True
    except RuntimeError:
        return False


def pid_running(path: Path | None = None) -> bool:
    target = path or pid_file()
    if not target.exists():
        return False
    pid = target.read_text(encoding="utf-8").strip()
    return bool(pid and Path(f"/proc/{pid}").exists())


def get_mihomo_status() -> dict[str, str]:
    config = read_local_config()
    engine = engine_path(config)
    return {
        "path": str(engine),
        "installed": "yes" if engine.exists() else "no",
        "running": "yes" if (daemon_active() or pid_running(pid_file(config))) else "no",
        "autostart": "enabled" if daemon_unit_path().exists() else "disabled",
        "pid_file": str(pid_file(config)),
    }


def install_mihomo(*, repo: str = "MetaCubeX/mihomo", version: str = "latest", dry_run: bool = False, force: bool = False, daemon: bool = False) -> CommandResult:
    config = read_local_config()
    target = engine_path(config)
    lines = ["install: mihomo binary", f"target: {target}"]
    if daemon:
        lines += ["daemon: install", f"unit: {daemon_unit_path()}"]
    if dry_run:
        return CommandResult(action="install_mihomo", dry_run=True, lines=lines)
    if target.exists() and not force:
        raise RuntimeError(f"mihomo already exists: {target}; pass --force to replace")
    machine = platform.machine().lower()
    if machine in {"x86_64", "amd64"}:
        arch = "amd64"
    elif machine in {"aarch64", "arm64"}:
        arch = "arm64"
    else:
        raise RuntimeError(f"unsupported architecture: {machine}")
    release_url = f"https://api.github.com/repos/{repo}/releases/latest" if version == "latest" else f"https://api.github.com/repos/{repo}/releases/tags/{version}"
    req = urllib.request.Request(release_url, headers={"User-Agent": "chatclash/0.1"})
    with urllib.request.urlopen(req, timeout=60) as response:
        release = json.loads(response.read().decode("utf-8"))
    candidates = [a for a in (release.get("assets") or []) if "linux" in (a.get("name") or "") and arch in (a.get("name") or "") and (a.get("name") or "").endswith(".gz") and "compatible" not in (a.get("name") or "")]
    if not candidates:
        candidates = [a for a in (release.get("assets") or []) if "linux" in (a.get("name") or "") and arch in (a.get("name") or "") and (a.get("name") or "").endswith(".gz")]
    if not candidates:
        raise RuntimeError(f"no linux {arch} .gz asset found for {repo} {release.get('tag_name')}")
    asset = candidates[0]
    download_url = asset.get("browser_download_url")
    if not download_url:
        raise RuntimeError("selected release asset has no download URL")
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        urllib.request.urlretrieve(download_url, tmp_path)
        with gzip.open(tmp_path, "rb") as src, target.open("wb") as dst:
            shutil.copyfileobj(src, dst)
        target.chmod(0o755)
    finally:
        tmp_path.unlink(missing_ok=True)
    if daemon:
        install_daemon_unit()
    return CommandResult(action="install_mihomo", lines=lines + [f"installed: {asset.get('name')}"])


def uninstall_mihomo(*, dry_run: bool = False, daemon: bool = False) -> CommandResult:
    target = engine_path()
    lines = [f"remove: {target}"]
    if daemon:
        lines += ["daemon: uninstall", f"unit: {daemon_unit_path()}"]
    if dry_run:
        return CommandResult(action="uninstall_mihomo", dry_run=True, lines=lines)
    target.unlink(missing_ok=True)
    if daemon:
        remove_daemon_unit()
    return CommandResult(action="uninstall_mihomo", lines=lines + ["mihomo uninstalled"])


def start_mihomo(*, dry_run: bool = False) -> CommandResult:
    cmd = [str(engine_path()), "-d", str(clash_dir())]
    if daemon_unit_path().exists():
        cmd = ["systemctl", "--user", "start", daemon_unit_path().name]
    if dry_run:
        return CommandResult(action="start_mihomo", dry_run=True, lines=[" ".join(cmd)])
    run_shell(cmd)
    return CommandResult(action="start_mihomo", lines=["started"])


def stop_mihomo(*, dry_run: bool = False) -> CommandResult:
    if dry_run:
        return CommandResult(action="stop_mihomo", dry_run=True, lines=["systemctl --user stop / pkill mihomo"])
    if daemon_unit_path().exists():
        systemctl_user("stop", daemon_unit_path().name, check=False)
    else:
        run_shell(["pkill", "-f", str(engine_path())], check=False)
    return CommandResult(action="stop_mihomo", lines=["stopped"])


def restart_mihomo(*, dry_run: bool = False) -> CommandResult:
    if dry_run:
        return CommandResult(action="restart_mihomo", dry_run=True, lines=["restart mihomo"])
    stop_mihomo()
    start_mihomo()
    return CommandResult(action="restart_mihomo", lines=["restarted"])


def read_mihomo_logs(*, tail: int = 100, dry_run: bool = False) -> CommandResult:
    path = log_file()
    if dry_run:
        return CommandResult(action="logs", dry_run=True, lines=[f"tail -n {tail} {path}"])
    if daemon_unit_path().exists():
        text = systemctl_user("status", daemon_unit_path().name, "--no-pager", "-l", check=False)
    elif path.exists():
        text = "".join(path.read_text(encoding="utf-8", errors="ignore").splitlines(True)[-tail:])
    else:
        text = "<no logs>"
    op = read_operator_config()
    return CommandResult(action="logs", lines=[redact_text(text, op.subscription_url, op.proxy_auth, op.subconverter_url, op.subscription_fetch_proxy)])
