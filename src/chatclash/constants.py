"""Shared ChatClash constants."""

from __future__ import annotations

DEFAULT_HTTP_PORT = 7890
DEFAULT_SOCKS_PORT = 7891
DEFAULT_CONTROLLER_PORT = 9090
DEFAULT_BIND_HOST = "0.0.0.0"
DEFAULT_PROXY_HOST = "127.0.0.1"
DEFAULT_SUBCONVERTER_HOST = "127.0.0.1"
DEFAULT_SUBCONVERTER_PORT = 25500
DEFAULT_FETCH_MODE = "direct-clash-yaml"
DEFAULT_SUBCONVERTER_CONFIG_URL = (
    "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/config/"
    "ACL4SSR_Online.ini"
)
DEFAULT_CHECK_URLS = (
    "http://example.com",
    "https://example.com",
    "https://github.com",
    "https://www.gstatic.com/generate_204",
)
