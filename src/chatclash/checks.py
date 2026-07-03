"""Proxy check APIs."""

from __future__ import annotations

import urllib.parse

from .chatenv_store import read_operator_config
from .constants import DEFAULT_CHECK_URLS
from .models import CheckItem, CheckResult
from .paths import http_port, read_local_config
from .utils import run_shell


def local_proxy_url(*, include_auth: bool = True) -> tuple[str, bool]:
    config = read_local_config()
    auth = read_operator_config().proxy_auth
    if include_auth and auth:
        return f"http://{urllib.parse.quote(auth, safe=':')}@127.0.0.1:{http_port(config)}", True
    return f"http://127.0.0.1:{http_port(config)}", bool(auth)


def check_proxy(*, urls: tuple[str, ...] | None = None, min_success: int = 2, timeout: int = 30, dry_run: bool = False) -> CheckResult:
    urls = urls or DEFAULT_CHECK_URLS
    proxy, auth_present = local_proxy_url()
    if dry_run:
        items = [CheckItem(url=u, ok=True, detail="dry-run") for u in urls]
        return CheckResult(proxy=proxy.split('@')[-1] if '@' in proxy else proxy, auth_present=auth_present, results=items, success_count=len(items))
    items: list[CheckItem] = []
    for url in urls:
        try:
            code = run_shell(["curl", "-fsSL", "--max-time", str(timeout), "--proxy", proxy, "-o", "/dev/null", "-w", "%{http_code}", url])
            items.append(CheckItem(url=url, ok=True, detail=code.strip()))
        except Exception as exc:
            items.append(CheckItem(url=url, ok=False, detail=str(exc)))
    success = sum(1 for item in items if item.ok)
    if success < min_success:
        raise RuntimeError(f"proxy check failed: success_count={success}, min_success={min_success}")
    return CheckResult(proxy=proxy.split('@')[-1] if '@' in proxy else proxy, auth_present=auth_present, results=items, success_count=success)


def check_ip(*, lang: str = "zh-CN", timeout: int = 20, dry_run: bool = False) -> str:
    proxy, _ = local_proxy_url()
    url = f"http://ip-api.com/json/?fields=status,country,countryCode,regionName,city,isp,org,as,query,timezone&lang={lang}"
    if dry_run:
        return f"dry-run: curl --proxy http://127.0.0.1:{http_port()} {url}"
    return run_shell(["curl", "-fsSL", "--max-time", str(timeout), "--proxy", proxy, url])
