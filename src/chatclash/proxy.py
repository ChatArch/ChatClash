"""Proxy endpoint and authentication APIs."""

from __future__ import annotations

import urllib.parse
from dataclasses import dataclass

from .chatenv_store import read_operator_config, write_operator_config
from .models import ProxyEndpoints
from .paths import http_port, proxy_host, read_local_config, socks_port, write_local_config
from .utils import clean


@dataclass(frozen=True)
class ProxyAuthStatus:
    present: bool
    user: str | None
    auth: str | None


def _split_proxy_auth(auth: str | None) -> tuple[str | None, str | None]:
    auth = clean(auth)
    if not auth:
        return None, None
    if ":" not in auth:
        return auth, None
    user, password = auth.split(":", 1)
    return clean(user), password


def _mask_proxy_auth(auth: str | None) -> str:
    user, password = _split_proxy_auth(auth)
    if not user and not password:
        return "<not set>"
    if password is None:
        return f"{user}:***" if user else "***"
    return f"{user or '<empty-user>'}:***"


def proxy_auth_status(*, no_mask: bool = False) -> ProxyAuthStatus:
    auth = read_operator_config().proxy_auth
    user, _ = _split_proxy_auth(auth)
    shown_auth = auth if no_mask else _mask_proxy_auth(auth)
    return ProxyAuthStatus(present=bool(clean(auth)), user=user, auth=shown_auth if auth else None)


def set_proxy_auth(*, auth: str | None = None, username: str | None = None, password: str | None = None) -> list[str]:
    resolved = clean(auth)
    if not resolved:
        username = clean(username)
        if username and password is not None:
            resolved = f"{username}:{password}"
    if not resolved:
        raise ValueError("missing proxy authentication; pass --auth or --auth-env")
    return write_operator_config(proxy_auth=resolved)


def _auth_for_url(*, no_mask: bool) -> str | None:
    auth = read_operator_config().proxy_auth
    if not auth:
        return None
    return auth if no_mask else _mask_proxy_auth(auth)


def _with_auth(url: str, *, no_mask: bool) -> str:
    auth = _auth_for_url(no_mask=no_mask)
    if not auth:
        return url
    parsed = urllib.parse.urlsplit(url)
    quoted = urllib.parse.quote(auth, safe=":") if no_mask else auth
    host = parsed.hostname or parsed.netloc
    if parsed.port:
        host = f"{host}:{parsed.port}"
    return urllib.parse.urlunsplit((parsed.scheme, f"{quoted}@{host}", parsed.path, parsed.query, parsed.fragment))


def get_proxy_endpoints(*, include_auth: bool = False, no_mask: bool = False) -> ProxyEndpoints:
    config = read_local_config()
    host = proxy_host(config)
    http = f"http://{host}:{http_port(config)}"
    socks = f"socks5://{host}:{socks_port(config)}"
    if include_auth:
        http = _with_auth(http, no_mask=no_mask)
        socks = _with_auth(socks, no_mask=no_mask)
    return ProxyEndpoints(http=http, https=http, socks=socks, no_proxy="localhost,127.0.0.1,::1")


def get_proxy_env(*, include_auth: bool = True, no_mask: bool = False) -> dict[str, str]:
    endpoints = get_proxy_endpoints(include_auth=include_auth, no_mask=no_mask)
    return {
        "http_proxy": endpoints.http,
        "https_proxy": endpoints.https,
        "all_proxy": endpoints.socks,
        "no_proxy": endpoints.no_proxy,
    }


def set_proxy_config(
    *,
    http_port_value: int | None = None,
    socks_port_value: int | None = None,
    controller_port_value: int | None = None,
    bind_host: str | None = None,
    proxy_host_value: str | None = None,
) -> list[str]:
    config = read_local_config()
    changed: list[str] = []
    updates = {
        "http_port": http_port_value,
        "socks_port": socks_port_value,
        "controller_port": controller_port_value,
        "bind_host": bind_host,
        "proxy_host": proxy_host_value,
    }
    for key, value in updates.items():
        if value is not None:
            config[key] = value
            changed.append(key)
    if changed:
        write_local_config(config)
    return changed
