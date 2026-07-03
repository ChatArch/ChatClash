"""Proxy endpoint APIs."""

from __future__ import annotations

from .models import ProxyEndpoints
from .paths import http_port, proxy_host, read_local_config, socks_port, write_local_config


def get_proxy_endpoints() -> ProxyEndpoints:
    config = read_local_config()
    host = proxy_host(config)
    http = f"http://{host}:{http_port(config)}"
    socks = f"socks5://{host}:{socks_port(config)}"
    return ProxyEndpoints(http=http, https=http, socks=socks, no_proxy="localhost,127.0.0.1,::1")


def get_proxy_env() -> dict[str, str]:
    endpoints = get_proxy_endpoints()
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
