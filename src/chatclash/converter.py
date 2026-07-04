"""Subconverter runtime APIs."""

from __future__ import annotations

import json
import os
import platform
import shutil
import signal
import subprocess
import tarfile
import tempfile
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

from .constants import DEFAULT_SUBCONVERTER_HOST, DEFAULT_SUBCONVERTER_PORT
from .models import CommandResult
from .paths import chatclash_home, read_local_config
from .utils import run_shell

DEFAULT_SUBCONVERTER_REPO = "tindy2013/subconverter"


def converter_path(config: dict | None = None) -> Path:
    cfg = config or read_local_config()
    return Path(str(cfg.get("converter_path") or chatclash_home() / "bin" / "subconverter"))


def converter_work_dir(config: dict | None = None) -> Path:
    cfg = config or read_local_config()
    return Path(str(cfg.get("converter_dir") or chatclash_home() / "subconverter"))


def converter_pid_file(config: dict | None = None) -> Path:
    cfg = config or read_local_config()
    return Path(str(cfg.get("converter_pid_file") or chatclash_home() / "run" / "subconverter.pid"))


def converter_log_file(config: dict | None = None) -> Path:
    cfg = config or read_local_config()
    return Path(str(cfg.get("converter_log_file") or chatclash_home() / "logs" / "subconverter.log"))


def converter_state_file(config: dict | None = None) -> Path:
    cfg = config or read_local_config()
    return Path(str(cfg.get("converter_state_file") or chatclash_home() / "run" / "subconverter.json"))


def _pid_running(pid_path: Path) -> bool:
    if not pid_path.exists():
        return False
    pid = pid_path.read_text(encoding="utf-8").strip()
    if not pid:
        return False
    try:
        os.kill(int(pid), 0)
        return True
    except (ValueError, ProcessLookupError):
        return False
    except PermissionError:
        return True


def _write_pref_ini(*, host: str, port: int, config: dict | None = None) -> Path:
    work_dir = converter_work_dir(config)
    work_dir.mkdir(parents=True, exist_ok=True)
    pref = work_dir / "pref.ini"
    pref.write_text(
        "\n".join([
            "[common]",
            f"api_mode=true",
            f"listen={host}",
            f"port={port}",
            "",
        ]),
        encoding="utf-8",
    )
    pref.chmod(0o600)
    return pref



def _safe_archive_target(root: Path, member_name: str) -> Path:
    raw = Path(member_name)
    if raw.is_absolute() or ".." in raw.parts:
        raise RuntimeError(f"unsafe archive member: {member_name}")
    target = (root / raw).resolve()
    root_resolved = root.resolve()
    if target != root_resolved and root_resolved not in target.parents:
        raise RuntimeError(f"unsafe archive member: {member_name}")
    return target


def _archive_binary_candidates(root: Path) -> list[Path]:
    candidates = [p for p in root.rglob("subconverter") if p.is_file()]
    if candidates:
        return candidates
    return [p for p in root.rglob("*") if p.is_file() and os.access(p, os.X_OK)]


def _safe_extract_tar(source_path: Path, root: Path) -> None:
    with tarfile.open(source_path) as tar:
        for member in tar.getmembers():
            if member.isdir():
                _safe_archive_target(root, member.name).mkdir(parents=True, exist_ok=True)
                continue
            if not member.isfile():
                raise RuntimeError(f"unsafe archive member: {member.name}")
            target = _safe_archive_target(root, member.name)
            target.parent.mkdir(parents=True, exist_ok=True)
            extracted = tar.extractfile(member)
            if extracted is None:
                raise RuntimeError(f"unable to read archive member: {member.name}")
            with extracted, target.open("wb") as dst:
                shutil.copyfileobj(extracted, dst)
            target.chmod(member.mode & 0o777 or 0o755)


def _safe_extract_zip(source_path: Path, root: Path) -> None:
    with zipfile.ZipFile(source_path) as zf:
        for info in zf.infolist():
            if info.is_dir():
                _safe_archive_target(root, info.filename).mkdir(parents=True, exist_ok=True)
                continue
            target = _safe_archive_target(root, info.filename)
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, target.open("wb") as dst:
                shutil.copyfileobj(src, dst)
            mode = (info.external_attr >> 16) & 0o777
            if mode:
                target.chmod(mode)


def _copy_converter_artifact(source_path: Path, target: Path) -> str:
    """Install a converter binary from a direct file or common release archive."""
    target.parent.mkdir(parents=True, exist_ok=True)
    name = source_path.name
    lower = name.lower()
    if lower.endswith((".tar.gz", ".tgz", ".tar")):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _safe_extract_tar(source_path, root)
            candidates = _archive_binary_candidates(root)
            if not candidates:
                raise RuntimeError(f"no subconverter binary found in archive: {source_path}")
            shutil.copy2(candidates[0], target)
    elif lower.endswith(".zip"):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            _safe_extract_zip(source_path, root)
            candidates = _archive_binary_candidates(root)
            if not candidates:
                raise RuntimeError(f"no subconverter binary found in archive: {source_path}")
            shutil.copy2(candidates[0], target)
    else:
        shutil.copy2(source_path, target)
    target.chmod(0o755)
    return name


def _download_latest_asset(*, repo: str, version: str) -> tuple[str, Path]:
    release_url = f"https://api.github.com/repos/{repo}/releases/latest" if version == "latest" else f"https://api.github.com/repos/{repo}/releases/tags/{version}"
    req = urllib.request.Request(release_url, headers={"User-Agent": "chatclash/0.1"})
    with urllib.request.urlopen(req, timeout=60) as response:
        release = json.loads(response.read().decode("utf-8"))
    machine = platform.machine().lower()
    arch_terms = ["linux64", "linux-amd64", "linux_x64", "x86_64", "amd64"] if machine in {"x86_64", "amd64"} else ["linux-arm64", "aarch64", "arm64"]
    assets = release.get("assets") or []
    candidates = []
    for asset in assets:
        name = asset.get("name") or ""
        lower = name.lower()
        if "linux" in lower and any(term in lower for term in arch_terms):
            candidates.append(asset)
    if not candidates:
        raise RuntimeError(f"no linux asset found for {repo} {release.get('tag_name')}")
    asset = candidates[0]
    url = asset.get("browser_download_url")
    if not url:
        raise RuntimeError("selected release asset has no download URL")
    asset_name = asset.get("name") or "subconverter"
    with tempfile.NamedTemporaryFile(delete=False, suffix="-" + asset_name) as tmp:
        tmp_path = Path(tmp.name)
    urllib.request.urlretrieve(url, tmp_path)
    return asset_name, tmp_path


def install_converter(
    *,
    source: str | None = None,
    repo: str = DEFAULT_SUBCONVERTER_REPO,
    version: str = "latest",
    dry_run: bool = False,
    force: bool = False,
) -> CommandResult:
    config = read_local_config()
    target = converter_path(config)
    lines = ["install: subconverter", f"target: {target}"]
    if source:
        lines.append(f"source: {source}")
    else:
        lines.append(f"release: {repo}@{version}")
    if dry_run:
        return CommandResult(action="install_converter", dry_run=True, lines=lines)
    if target.exists() and not force:
        raise RuntimeError(f"converter already exists: {target}; pass --force to replace")
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp_path: Path | None = None
    try:
        if source:
            if source.startswith(("http://", "https://")):
                source_name = Path(urllib.parse.urlparse(source).path).name or "subconverter"
                with tempfile.NamedTemporaryFile(delete=False, suffix="-" + source_name) as tmp:
                    tmp_path = Path(tmp.name)
                urllib.request.urlretrieve(source, tmp_path)
            else:
                tmp_path = Path(source)
                if not tmp_path.exists():
                    raise RuntimeError(f"source not found: {source}")
            asset_name = _copy_converter_artifact(tmp_path, target)
        else:
            asset_name, tmp_path = _download_latest_asset(repo=repo, version=version)
            asset_name = _copy_converter_artifact(tmp_path, target)
    finally:
        if tmp_path and source and source.startswith(("http://", "https://")):
            tmp_path.unlink(missing_ok=True)
        elif tmp_path and not source:
            tmp_path.unlink(missing_ok=True)
    return CommandResult(action="install_converter", lines=lines + [f"installed: {asset_name}"])


def start_converter(*, host: str = DEFAULT_SUBCONVERTER_HOST, port: int = DEFAULT_SUBCONVERTER_PORT, dry_run: bool = False) -> CommandResult:
    config = read_local_config()
    target = converter_path(config)
    work_dir = converter_work_dir(config)
    pid_path = converter_pid_file(config)
    log_path = converter_log_file(config)
    state_path = converter_state_file(config)
    pref = work_dir / "pref.ini"
    url = f"http://{host}:{port}"
    lines = [
        f"path: {target}",
        f"host: {host}",
        f"port: {port}",
        f"url: {url}",
        f"work_dir: {work_dir}",
        f"pref: {pref}",
        f"pid_file: {pid_path}",
        f"log_file: {log_path}",
        f"state_file: {state_path}",
    ]
    if dry_run:
        return CommandResult(action="start_converter", dry_run=True, lines=lines)
    if not target.exists():
        raise RuntimeError(f"converter not installed: {target}; run `chatclash sub converter install` first")
    if _pid_running(pid_path):
        raise RuntimeError(f"converter already running: {pid_path}")
    _write_pref_ini(host=host, port=port, config=config)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    pid_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("ab") as log:
        process = subprocess.Popen([str(target)], cwd=work_dir, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    pid_path.write_text(str(process.pid), encoding="utf-8")
    state_path.write_text(json.dumps({"host": host, "port": port, "url": url}, ensure_ascii=False), encoding="utf-8")
    state_path.chmod(0o600)
    return CommandResult(action="start_converter", lines=lines + ["started"])


def stop_converter(*, dry_run: bool = False) -> CommandResult:
    pid_path = converter_pid_file()
    state_path = converter_state_file()
    lines = [f"pid_file: {pid_path}"]
    if dry_run:
        return CommandResult(action="stop_converter", dry_run=True, lines=lines + ["stop converter process"])
    if not pid_path.exists():
        return CommandResult(action="stop_converter", lines=lines + ["not running"])
    pid_text = pid_path.read_text(encoding="utf-8").strip()
    try:
        os.kill(int(pid_text), signal.SIGTERM)
    except (ValueError, ProcessLookupError):
        pass
    pid_path.unlink(missing_ok=True)
    state_path.unlink(missing_ok=True)
    return CommandResult(action="stop_converter", lines=lines + ["stopped"])


def converter_status(*, host: str = DEFAULT_SUBCONVERTER_HOST, port: int = DEFAULT_SUBCONVERTER_PORT) -> dict[str, str]:
    config = read_local_config()
    target = converter_path(config)
    pid_path = converter_pid_file(config)
    state_path = converter_state_file(config)
    if state_path.exists():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
            host = str(state.get("host") or host)
            port = int(state.get("port") or port)
        except Exception:
            pass
    return {
        "path": str(target),
        "installed": "yes" if target.exists() else "no",
        "running": "yes" if _pid_running(pid_path) else "no",
        "host": host,
        "port": str(port),
        "url": f"http://{host}:{port}",
        "pid_file": str(pid_path),
        "log_file": str(converter_log_file(config)),
    }


def read_converter_logs(*, tail: int = 100, dry_run: bool = False) -> CommandResult:
    path = converter_log_file()
    if dry_run:
        return CommandResult(action="logs", dry_run=True, lines=[f"tail -n {tail} {path}"])
    if path.exists():
        text = "".join(path.read_text(encoding="utf-8", errors="ignore").splitlines(True)[-tail:])
    else:
        text = "<no logs>"
    return CommandResult(action="logs", lines=[text])
