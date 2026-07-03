"""Local ChatClash paths and machine-local config."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .constants import (
    DEFAULT_BIND_HOST,
    DEFAULT_CONTROLLER_PORT,
    DEFAULT_FETCH_MODE,
    DEFAULT_HTTP_PORT,
    DEFAULT_PROXY_HOST,
    DEFAULT_SOCKS_PORT,
)
from .models import InitResult
from .utils import load_yaml_file, write_yaml_file


def chatclash_home() -> Path:
    return Path(os.getenv("CHATCLASH_HOME") or (Path.home() / ".chatarch" / "chatclash"))


def local_config_path() -> Path:
    return chatclash_home() / "config.yaml"


def default_local_config(*, home: Path | None = None) -> dict[str, Any]:
    root = home or chatclash_home()
    clash_dir = root / "clash"
    return {
        "home": str(root),
        "clash_dir": str(clash_dir),
        "fetch_mode": DEFAULT_FETCH_MODE,
        "engine_path": str(root / "bin" / "mihomo"),
        "pid_file": str(root / "run" / "mihomo.pid"),
        "log_file": str(root / "logs" / "mihomo.log"),
        "http_port": DEFAULT_HTTP_PORT,
        "socks_port": DEFAULT_SOCKS_PORT,
        "controller_port": DEFAULT_CONTROLLER_PORT,
        "bind_host": DEFAULT_BIND_HOST,
        "proxy_host": DEFAULT_PROXY_HOST,
    }


def read_local_config() -> dict[str, Any]:
    path = local_config_path()
    config = default_local_config(home=path.parent)
    if path.exists():
        config.update(load_yaml_file(path))
    return config


def write_local_config(config: dict[str, Any]) -> None:
    write_yaml_file(local_config_path(), config, mode=0o600)


def clash_dir(config: dict[str, Any] | None = None) -> Path:
    cfg = config or read_local_config()
    return Path(str(cfg.get("clash_dir") or chatclash_home() / "clash"))


def engine_path(config: dict[str, Any] | None = None) -> Path:
    cfg = config or read_local_config()
    return Path(str(cfg.get("engine_path") or chatclash_home() / "bin" / "mihomo"))


def pid_file(config: dict[str, Any] | None = None) -> Path:
    cfg = config or read_local_config()
    return Path(str(cfg.get("pid_file") or chatclash_home() / "run" / "mihomo.pid"))


def log_file(config: dict[str, Any] | None = None) -> Path:
    cfg = config or read_local_config()
    return Path(str(cfg.get("log_file") or chatclash_home() / "logs" / "mihomo.log"))


def http_port(config: dict[str, Any] | None = None) -> int:
    return int((config or read_local_config()).get("http_port") or DEFAULT_HTTP_PORT)


def socks_port(config: dict[str, Any] | None = None) -> int:
    return int((config or read_local_config()).get("socks_port") or DEFAULT_SOCKS_PORT)


def controller_port(config: dict[str, Any] | None = None) -> int:
    return int((config or read_local_config()).get("controller_port") or DEFAULT_CONTROLLER_PORT)


def bind_host(config: dict[str, Any] | None = None) -> str:
    return str((config or read_local_config()).get("bind_host") or DEFAULT_BIND_HOST)


def proxy_host(config: dict[str, Any] | None = None) -> str:
    return str((config or read_local_config()).get("proxy_host") or DEFAULT_PROXY_HOST)


def initialize_home(*, home: Path | None = None, dry_run: bool = False) -> InitResult:
    root = home or chatclash_home()
    target = root / "clash"
    if dry_run:
        return InitResult(home=root, clash_dir=target, dry_run=True, changed=[])
    for path in (root, root / "bin", root / "run", root / "logs", root / "cache", target, target / "backups"):
        path.mkdir(parents=True, exist_ok=True)
    cfg = default_local_config(home=root)
    write_yaml_file(root / "config.yaml", cfg, mode=0o600)
    config_path = target / "config.yaml"
    if not config_path.exists():
        config_path.write_text(
            "port: 7890\nsocks-port: 7891\nallow-lan: true\nmode: Rule\nlog-level: info\nrules:\n  - MATCH,DIRECT\n",
            encoding="utf-8",
        )
    return InitResult(home=root, clash_dir=target, changed=["home", "config", "clash_config"])
