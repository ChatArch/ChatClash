"""General utilities shared by ChatClash APIs."""

from __future__ import annotations

import subprocess
import urllib.parse
from pathlib import Path
from typing import Any

import yaml


def clean(value: str | None) -> str | None:
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def mask(value: str | None) -> str:
    value = clean(value)
    if not value:
        return "<not set>"
    if len(value) <= 12:
        return "***"
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme and parsed.netloc:
        host = parsed.hostname or parsed.netloc
        if parsed.port:
            host = f"{host}:{parsed.port}"
        if parsed.username or parsed.password:
            return f"{parsed.scheme}://***@{host}"
        suffix = value[-6:] if parsed.path or parsed.query else ""
        return f"{parsed.scheme}://{host}/...{suffix}" if suffix else f"{parsed.scheme}://{host}"
    return f"{value[:4]}...{value[-4:]}"


def redact_text(text: str, *secrets: str | None) -> str:
    for value in secrets:
        value = clean(value)
        if not value:
            continue
        text = text.replace(value, mask(value))
        text = text.replace(urllib.parse.quote(value, safe=""), "<redacted>")
        text = text.replace(urllib.parse.quote_plus(value), "<redacted>")
    return text


def load_yaml_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        raise ValueError(f"expected YAML object in {path}")
    return loaded


def write_yaml_file(path: Path, data: dict[str, Any], *, mode: int | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=False), encoding="utf-8")
    if mode is not None:
        path.chmod(mode)


def run_shell(command: list[str], *, cwd: Path | None = None, check: bool = True) -> str:
    proc = subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if check and proc.returncode != 0:
        raise RuntimeError(proc.stdout.strip() or f"command failed: {' '.join(command)}")
    return proc.stdout
