"""Subscription and config-generation APIs."""

from __future__ import annotations

import datetime as dt
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import yaml

from .chatenv_store import read_operator_config, write_operator_config, operator_status
from .constants import DEFAULT_SUBCONVERTER_CONFIG_URL
from .paths import bind_host, clash_dir, controller_port, http_port, read_local_config, socks_port
from .utils import clean, load_yaml_file, mask, redact_text, run_shell, write_yaml_file


def set_subscription_config(
    *,
    subscription_url: str | None = None,
    proxy_auth: str | None = None,
    subconverter_url: str | None = None,
    fetch_proxy: str | None = None,
) -> list[str]:
    return write_operator_config(
        subscription_url=subscription_url,
        proxy_auth=proxy_auth,
        subconverter_url=subconverter_url,
        subscription_fetch_proxy=fetch_proxy,
    )


def get_subscription_status() -> dict[str, str]:
    return operator_status()


def build_subscription_url(
    subscription_url: str | None = None,
    *,
    subconverter_url: str | None = None,
    config_url: str = DEFAULT_SUBCONVERTER_CONFIG_URL,
) -> str:
    cfg = read_operator_config()
    sub = clean(subscription_url) or cfg.subscription_url
    converter = clean(subconverter_url) or cfg.subconverter_url
    if not sub:
        raise ValueError("missing subscription URL")
    if not converter:
        raise ValueError("missing subconverter URL")
    base = converter.rstrip("/") + "/sub"
    query = urllib.parse.urlencode({"target": "clash", "url": sub, "config": config_url}, safe=":/")
    return f"{base}?{query}"


def _looks_like_clash_yaml(text: str) -> bool:
    return ("proxies:" in text or "proxy-providers:" in text) and ("proxy-groups:" in text or "rules:" in text)


def _extract_clash_body(text: str) -> str:
    markers = ("proxy-providers:", "proxies:", "proxy-groups:", "rule-providers:", "rules:")
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.strip() in markers and not line.startswith((" ", "\t")):
            return "\n".join(lines[index:]) + "\n"
    return text


def _fetch_url(url: str, *, timeout: int = 60, proxy: str | None = None) -> str:
    opener = urllib.request.build_opener()
    if proxy:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({"http": proxy, "https": proxy}))
    req = urllib.request.Request(url, headers={"User-Agent": "chatclash/0.1"})
    with opener.open(req, timeout=timeout) as response:
        return response.read().decode("utf-8")


def _header(config: dict[str, Any], proxy_auth: str | None) -> dict[str, Any]:
    data: dict[str, Any] = {
        "port": http_port(config),
        "socks-port": socks_port(config),
        "allow-lan": True,
        "bind-address": bind_host(config),
        "mode": "Rule",
        "log-level": "info",
        "external-controller": f":{controller_port(config)}",
    }
    if proxy_auth:
        data["authentication"] = [proxy_auth]
    return data


def _merge_config(remote_text: str, *, config: dict[str, Any], proxy_auth: str | None) -> str:
    body_text = _extract_clash_body(remote_text)
    body = yaml.safe_load(body_text) or {}
    if not isinstance(body, dict):
        raise ValueError("subscription did not produce a Clash YAML object")
    merged = _header(config, proxy_auth)
    merged.update(body)
    # Local listener header wins even if remote YAML had its own ports/auth.
    merged.update(_header(config, proxy_auth))
    return yaml.safe_dump(merged, sort_keys=False, allow_unicode=True)


def _backup(path: Path) -> Path | None:
    if not path.exists():
        return None
    backup_dir = path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    target = backup_dir / f"{path.name}.{stamp}.bak"
    target.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
    target.chmod(0o600)
    return target


def generate_subscription_config(
    *,
    subscription_url: str | None = None,
    subconverter_url: str | None = None,
    output: Path,
    dry_run: bool = False,
    yes: bool = False,
) -> dict[str, Any]:
    url = build_subscription_url(subscription_url, subconverter_url=subconverter_url)
    if dry_run:
        return {"output": str(output), "dry_run": True, "proxies": 0, "url": mask(url)}
    op = read_operator_config()
    remote_text = _fetch_url(url)
    config = read_local_config()
    merged = _merge_config(remote_text, config=config, proxy_auth=op.proxy_auth)
    parsed = yaml.safe_load(merged) or {}
    result = {"output": str(output), "dry_run": dry_run, "proxies": len(parsed.get("proxies") or [])}
    _backup(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(merged, encoding="utf-8")
    output.chmod(0o600)
    return result


def update_subscription_config(*, dry_run: bool = False, no_validate: bool = False) -> dict[str, Any]:
    op = read_operator_config()
    if not op.subscription_url:
        raise ValueError("missing subscription URL; run sub set first")
    config = read_local_config()
    proxy = None
    if op.subscription_fetch_proxy == "local":
        proxy = f"http://127.0.0.1:{http_port(config)}"
    elif op.subscription_fetch_proxy:
        proxy = op.subscription_fetch_proxy
    if dry_run:
        target = clash_dir(config) / "config.yaml"
        return {"target": str(target), "dry_run": True, "validated": False}
    remote_text = _fetch_url(op.subscription_url, proxy=proxy)
    if not _looks_like_clash_yaml(remote_text) and op.subconverter_url:
        remote_text = _fetch_url(build_subscription_url(op.subscription_url, subconverter_url=op.subconverter_url), proxy=proxy)
    if not _looks_like_clash_yaml(remote_text):
        raise ValueError("subscription did not return Clash YAML")
    merged = _merge_config(remote_text, config=config, proxy_auth=op.proxy_auth)
    target = clash_dir(config) / "config.yaml"
    result = {"target": str(target), "dry_run": dry_run, "validated": False}
    if dry_run:
        return result
    _backup(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(merged, encoding="utf-8")
    target.chmod(0o600)
    if not no_validate:
        engine = Path(str(config.get("engine_path") or "mihomo"))
        if engine.exists():
            run_shell([str(engine), "-t", "-d", str(target.parent)])
            result["validated"] = True
    return result
