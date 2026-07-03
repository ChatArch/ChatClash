"""Structured result models for ChatClash APIs."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class InitResult:
    home: Path
    clash_dir: Path
    dry_run: bool = False
    changed: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ProxyEndpoints:
    http: str
    https: str
    socks: str
    no_proxy: str


@dataclass(frozen=True)
class CheckItem:
    url: str
    ok: bool
    detail: str


@dataclass(frozen=True)
class CheckResult:
    proxy: str
    auth_present: bool
    results: list[CheckItem]
    success_count: int


@dataclass(frozen=True)
class CommandResult:
    action: str
    dry_run: bool = False
    lines: list[str] = field(default_factory=list)
