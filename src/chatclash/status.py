"""Top-level ChatClash status API."""

from __future__ import annotations

from .chatenv_store import read_operator_config
from .mihomo import get_mihomo_status
from .paths import clash_dir, controller_port, http_port, proxy_host, read_local_config, socks_port
from .utils import load_yaml_file


def _active_controller(config: dict[str, object], config_path) -> str:
    fallback = f"127.0.0.1:{controller_port(config)}"
    try:
        controller = load_yaml_file(config_path).get("external-controller")
    except Exception:
        return "<unreadable>"
    return str(controller).strip() if controller else fallback


def get_status() -> dict[str, str]:
    config = read_local_config()
    op = read_operator_config()
    runtime = get_mihomo_status()
    cfg_path = clash_dir(config) / "config.yaml"
    backup_dir = clash_dir(config) / "backups"
    backups = list(backup_dir.glob("config.yaml.*.bak")) if backup_dir.exists() else []
    host = proxy_host(config)
    return {
        "home": str(config.get("home")),
        "mihomo_installed": runtime["installed"],
        "mihomo_running": runtime["running"],
        "mihomo_autostart": runtime["autostart"],
        "subscription_set": "yes" if op.subscription_url else "no",
        "proxy_auth_set": "yes" if op.proxy_auth else "no",
        "config_exists": "yes" if cfg_path.exists() else "no",
        "http_proxy": f"http://{host}:{http_port(config)}",
        "socks_proxy": f"socks5://{host}:{socks_port(config)}",
        "controller": _active_controller(config, cfg_path),
        "backups": str(len(backups)),
    }
