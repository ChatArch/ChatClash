"""Mihomo runtime APIs."""

from __future__ import annotations

import gzip
import json
import os
import platform
import shutil
import signal
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

import yaml

from .chatenv_store import read_operator_config
from .models import CommandResult
from .paths import clash_dir, controller_port, engine_path, http_port, log_file, pid_file, proxy_host, read_local_config
from .utils import redact_text, run_shell

UNIT_NAME = "chatclash-mihomo.service"


def is_windows() -> bool:
    return platform.system().lower() == "windows"


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
    raw = target.read_text(encoding="utf-8").strip()
    if is_windows():
        try:
            state = json.loads(raw)
            pid = int(state["pid"])
            expected_path = str(state["path"])
            expected_created = int(state["created"])
        except (ValueError, KeyError, TypeError, json.JSONDecodeError):
            return False
        details = _windows_process_details(pid)
        return bool(details and details["path"].lower() == expected_path.lower() and details["created"] == expected_created)
    pid = raw
    if not pid.isdigit():
        return False
    return Path(f"/proc/{pid}").exists()


def _windows_process_details(pid: int) -> dict[str, object] | None:
    """Return stable identity fields without accepting a reused Windows PID."""
    if not is_windows():
        return None
    try:
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.windll.kernel32
        kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
        kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
        kernel32.GetProcessTimes.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.FILETIME), ctypes.POINTER(wintypes.FILETIME), ctypes.POINTER(wintypes.FILETIME), ctypes.POINTER(wintypes.FILETIME)]
        kernel32.GetProcessTimes.restype = wintypes.BOOL
        kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        kernel32.GetExitCodeProcess.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL
        process = kernel32.OpenProcess(0x1000 | 0x00100000, False, pid)  # QUERY_LIMITED_INFORMATION | SYNCHRONIZE
        if not process:
            return None
        try:
            exit_code = wintypes.DWORD()
            if not kernel32.GetExitCodeProcess(process, ctypes.byref(exit_code)) or exit_code.value != 259:  # STILL_ACTIVE
                return None
            size = wintypes.DWORD(32768)
            buffer = ctypes.create_unicode_buffer(size.value)
            if not kernel32.QueryFullProcessImageNameW(process, 0, buffer, ctypes.byref(size)):
                return None
            created = wintypes.FILETIME()
            exited = wintypes.FILETIME()
            kernel = wintypes.FILETIME()
            user = wintypes.FILETIME()
            if not kernel32.GetProcessTimes(process, ctypes.byref(created), ctypes.byref(exited), ctypes.byref(kernel), ctypes.byref(user)):
                return None
            created_value = (created.dwHighDateTime << 32) | created.dwLowDateTime
            return {"path": str(Path(buffer.value).resolve()), "created": created_value}
        finally:
            kernel32.CloseHandle(process)
    except Exception:
        return None


def get_mihomo_status() -> dict[str, str]:
    config = read_local_config()
    engine = engine_path(config)
    return {
        "path": str(engine),
        "installed": "yes" if engine.exists() else "no",
        "running": "yes" if ((not is_windows() and daemon_active()) or pid_running(pid_file(config))) else "no",
        "autostart": "not supported" if is_windows() else ("enabled" if daemon_unit_path().exists() else "disabled"),
        "pid_file": str(pid_file(config)),
    }


def _platform_asset(release: dict[str, object], arch: str) -> dict[str, object]:
    assets = [asset for asset in (release.get("assets") or []) if isinstance(asset, dict)]
    system = "windows" if is_windows() else "linux"
    suffix = ".zip" if is_windows() else ".gz"
    candidates = [asset for asset in assets if system in str(asset.get("name") or "").lower() and arch in str(asset.get("name") or "").lower() and str(asset.get("name") or "").lower().endswith(suffix)]
    if not candidates:
        raise RuntimeError(f"no {system} {arch} {suffix} asset found for release {release.get('tag_name')}")
    tag = str(release.get("tag_name") or "")
    baseline = f"mihomo-{system}-{arch}-{tag}{suffix}".lower()

    def priority(asset: dict[str, object]) -> tuple[int, str]:
        name = str(asset.get("name") or "").lower()
        if name == baseline:
            return (0, name)
        if "compatible" in name:
            return (3, name)
        if "-go" in name:
            return (2, name)
        return (1, name)

    # Prefer the exact MetaCubeX baseline build over ISA, compatibility, and Go variants.
    candidates.sort(key=priority)
    return candidates[0]


def _verify_asset_digest(path: Path, asset: dict[str, object]) -> None:
    digest = str(asset.get("digest") or "")
    if not digest:
        return
    algorithm, separator, expected = digest.partition(":")
    if algorithm.lower() != "sha256" or not separator or not expected:
        return
    import hashlib

    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual.lower() != expected.lower():
        raise RuntimeError("downloaded Mihomo asset digest does not match the release metadata")


def _extract_windows_engine(archive: Path, target: Path) -> None:
    with zipfile.ZipFile(archive) as zipped:
        members = [member for member in zipped.infolist() if not member.is_dir() and Path(member.filename).name.lower().startswith("mihomo") and Path(member.filename).suffix.lower() == ".exe"]
        if len(members) != 1:
            raise RuntimeError("Windows Mihomo archive must contain exactly one Mihomo executable")
        member = members[0]
        if Path(member.filename).is_absolute() or ".." in Path(member.filename).parts:
            raise RuntimeError("unsafe Mihomo archive member")
        with zipped.open(member) as src, target.open("wb") as dst:
            shutil.copyfileobj(src, dst)
    if target.stat().st_size == 0:
        raise RuntimeError("extracted Mihomo executable is empty")


def install_mihomo(*, repo: str = "MetaCubeX/mihomo", version: str = "latest", dry_run: bool = False, force: bool = False, daemon: bool = False) -> CommandResult:
    config = read_local_config()
    target = engine_path(config)
    lines = ["install: mihomo binary", f"target: {target}"]
    if daemon and not is_windows():
        lines += ["daemon: install", f"unit: {daemon_unit_path()}"]
    elif daemon:
        lines += ["daemon: Windows uses per-user process management"]
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
    asset = _platform_asset(release, arch)
    download_url = asset.get("browser_download_url")
    if not download_url:
        raise RuntimeError("selected release asset has no download URL")
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        urllib.request.urlretrieve(download_url, tmp_path)
        _verify_asset_digest(tmp_path, asset)
        with tempfile.NamedTemporaryFile(delete=False, dir=target.parent) as staged_file:
            staged = Path(staged_file.name)
        if is_windows():
            _extract_windows_engine(tmp_path, staged)
        else:
            with gzip.open(tmp_path, "rb") as src, staged.open("wb") as dst:
                shutil.copyfileobj(src, dst)
            staged.chmod(0o755)
        staged.replace(target)
    finally:
        tmp_path.unlink(missing_ok=True)
        if "staged" in locals():
            staged.unlink(missing_ok=True)
    if daemon and not is_windows():
        install_daemon_unit()
    return CommandResult(action="install_mihomo", lines=lines + [f"installed: {asset.get('name')}"])


def uninstall_mihomo(*, dry_run: bool = False, daemon: bool = False) -> CommandResult:
    target = engine_path()
    lines = [f"remove: {target}"]
    if daemon and not is_windows():
        lines += ["daemon: uninstall", f"unit: {daemon_unit_path()}"]
    elif daemon:
        lines += ["daemon: Windows uses per-user process management"]
    if dry_run:
        return CommandResult(action="uninstall_mihomo", dry_run=True, lines=lines)
    target.unlink(missing_ok=True)
    if daemon and not is_windows():
        remove_daemon_unit()
    return CommandResult(action="uninstall_mihomo", lines=lines + ["mihomo uninstalled"])


def start_mihomo(*, dry_run: bool = False) -> CommandResult:
    config = read_local_config()
    engine = engine_path(config)
    runtime_dir = pid_file(config).parent
    cmd = [str(engine), "-d", str(clash_dir(config))]
    if not is_windows() and daemon_unit_path().exists():
        cmd = ["systemctl", "--user", "start", daemon_unit_path().name]
    if dry_run:
        return CommandResult(action="start_mihomo", dry_run=True, lines=[" ".join(cmd)])
    if is_windows():
        if not engine.exists():
            raise RuntimeError(f"mihomo binary does not exist: {engine}")
        if pid_running(pid_file(config)):
            return CommandResult(action="start_mihomo", lines=["already running"])
        try:
            with socket.create_connection((proxy_host(config), http_port(config)), timeout=0.1):
                raise RuntimeError(f"HTTP proxy port is already in use: {proxy_host(config)}:{http_port(config)}")
        except ConnectionRefusedError:
            pass
        except OSError:
            pass
        runtime_dir.mkdir(parents=True, exist_ok=True)
        log = log_file(config)
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("a", encoding="utf-8") as output:
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            process = subprocess.Popen(cmd, cwd=str(clash_dir(config)), stdout=output, stderr=subprocess.STDOUT, creationflags=flags)
        # A PID alone can be reused; store immutable process identity before later stop.
        time.sleep(0.1)
        details = _windows_process_details(process.pid)
        if process.poll() is not None or details is None:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=3)
            raise RuntimeError(f"Mihomo exited during startup; inspect {log}")
        pid_file(config).write_text(json.dumps({"pid": process.pid, **details}), encoding="utf-8")
        for _ in range(50):
            try:
                with socket.create_connection((proxy_host(config), http_port(config)), timeout=0.1):
                    break
            except OSError:
                if process.poll() is not None:
                    pid_file(config).unlink(missing_ok=True)
                    raise RuntimeError(f"Mihomo exited during startup; inspect {log}")
                time.sleep(0.1)
        else:
            stop_mihomo()
            raise RuntimeError(f"Mihomo did not open its HTTP listener within 5 seconds; inspect {log}")
        return CommandResult(action="start_mihomo", lines=["started", f"pid: {process.pid}"])
    run_shell(cmd)
    return CommandResult(action="start_mihomo", lines=["started"])


def stop_mihomo(*, dry_run: bool = False) -> CommandResult:
    if dry_run:
        if is_windows():
            return CommandResult(action="stop_mihomo", dry_run=True, lines=[f"terminate verified PID from {pid_file()}"])
        return CommandResult(action="stop_mihomo", dry_run=True, lines=["systemctl --user stop / pkill mihomo"])
    config = read_local_config()
    pid_path = pid_file(config)
    if is_windows():
        if not pid_path.exists():
            return CommandResult(action="stop_mihomo", lines=["already stopped"])
        state = json.loads(pid_path.read_text(encoding="utf-8"))
        pid = int(state["pid"])
        if pid_running(pid_path):
            try:
                os.kill(pid, signal.SIGTERM)
            except OSError as exc:
                raise RuntimeError(f"could not stop Mihomo process {pid}: {exc}") from exc
            for _ in range(30):
                if not pid_running(pid_path):
                    break
                time.sleep(0.1)
            else:
                raise RuntimeError(f"Mihomo process {pid} did not stop within 3 seconds")
        pid_path.unlink(missing_ok=True)
        return CommandResult(action="stop_mihomo", lines=["stopped"])
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


LOOPBACK_BIND_HOSTS = {"127.0.0.1", "localhost", "::1"}


def _active_config_exposes_lan(active: dict[str, object]) -> bool:
    if active.get("allow-lan") is not True:
        return False
    bind_address = str(active.get("bind-address") or "0.0.0.0").strip()
    return bind_address not in LOOPBACK_BIND_HOSTS


def validate_proxy_auth_header(active: dict[str, object]) -> list[str]:
    """Validate that LAN-shared proxies use the ChatClash proxy auth source."""
    op = read_operator_config()
    auth_entries = active.get("authentication") or []
    if isinstance(auth_entries, str):
        auth_entries = [auth_entries]
    if not isinstance(auth_entries, list):
        raise RuntimeError("active config authentication must be a list")

    exposes_lan = _active_config_exposes_lan(active)
    if exposes_lan and not op.proxy_auth:
        raise RuntimeError("LAN proxy is enabled but CHATCLASH_PROXY_AUTH is not configured")
    if exposes_lan and not auth_entries:
        raise RuntimeError("LAN proxy is enabled but active config has no authentication; refresh config with ChatClash before restart")
    if op.proxy_auth and auth_entries != [op.proxy_auth]:
        raise RuntimeError("active config authentication does not match ChatClash proxy auth; refresh config before restart")
    return ["proxy_auth: validated" if auth_entries else "proxy_auth: not required"]


def validate_mihomo_config(*, dry_run: bool = False) -> CommandResult:
    config = read_local_config()
    target_dir = clash_dir(config)
    target = target_dir / "config.yaml"
    cmd = [str(engine_path(config)), "-t", "-d", str(target_dir)]
    lines = [f"config: {target}", "validate: " + " ".join(cmd)]
    if not target.exists():
        if dry_run:
            return CommandResult(action="validate_mihomo", dry_run=True, lines=lines)
        raise RuntimeError(f"active config does not exist: {target}")
    active = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
    if not isinstance(active, dict):
        raise RuntimeError("active config is not a Clash YAML object")
    lines += validate_proxy_auth_header(active)
    if dry_run:
        return CommandResult(action="validate_mihomo", dry_run=True, lines=lines)
    if not engine_path(config).exists():
        raise RuntimeError(f"mihomo binary does not exist: {engine_path(config)}")
    output = run_shell(cmd)
    return CommandResult(action="validate_mihomo", lines=lines + [output.strip() or "validation passed"])


def reload_mihomo(*, dry_run: bool = False) -> CommandResult:
    config = read_local_config()
    target = clash_dir(config) / "config.yaml"
    url = f"http://127.0.0.1:{controller_port(config)}/configs"
    lines = [f"config: {target}", f"controller: {url}"]
    if dry_run:
        return CommandResult(action="reload_mihomo", dry_run=True, lines=lines + ["PUT /configs"])
    if not target.exists():
        raise RuntimeError(f"active config does not exist: {target}")
    active = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
    secret = active.get("secret") if isinstance(active, dict) else None
    payload = json.dumps({"path": str(target)}).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if secret:
        headers["Authorization"] = f"Bearer {secret}"
    req = urllib.request.Request(url, data=payload, headers=headers, method="PUT")
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            body = response.read().decode("utf-8", errors="replace").strip()
            return CommandResult(action="reload_mihomo", lines=lines + [f"status: {response.status}", body or "reloaded"])
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"mihomo reload failed: HTTP {exc.code} {body}") from exc


def read_mihomo_logs(*, tail: int = 100, dry_run: bool = False) -> CommandResult:
    path = log_file()
    if dry_run:
        return CommandResult(action="logs", dry_run=True, lines=[f"tail -n {tail} {path}"])
    if not is_windows() and daemon_unit_path().exists():
        text = systemctl_user("status", daemon_unit_path().name, "--no-pager", "-l", check=False)
    elif path.exists():
        text = "".join(path.read_text(encoding="utf-8", errors="ignore").splitlines(True)[-tail:])
    else:
        text = "<no logs>"
    op = read_operator_config()
    return CommandResult(action="logs", lines=[redact_text(text, op.subscription_url, op.proxy_auth, op.subconverter_url)])
