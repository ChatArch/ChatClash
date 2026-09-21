"""ChatEnv integration for ChatClash operator config."""

from __future__ import annotations

import os
from dataclasses import dataclass

from chatenv import EnvStore, get_paths

from .config import ChatClashConfig
from .utils import clean, mask


@dataclass(frozen=True)
class OperatorConfig:
    home: str | None = None
    subscription_url: str | None = None
    proxy_auth: str | None = None
    subconverter_url: str | None = None


def load_chatenv() -> dict[str, str]:
    """Read only this provider's current active profile through ChatEnv."""
    return EnvStore(get_paths().envs_dir).load_active(ChatClashConfig)


def _value(env_key: str, values: dict[str, str]) -> str | None:
    return clean(os.getenv(env_key) or values.get(env_key) or "")


def read_operator_config() -> OperatorConfig:
    values = load_chatenv()
    return OperatorConfig(
        home=_value("CHATCLASH_HOME", values) or str(get_paths().home_dir / "chatclash"),
        subscription_url=_value("CHATCLASH_SUBSCRIPTION_URL", values),
        proxy_auth=_value("CHATCLASH_PROXY_AUTH", values),
        subconverter_url=_value("CHATCLASH_SUBCONVERTER_URL", values),
    )


def write_operator_config(
    *,
    home: str | None = None,
    subscription_url: str | None = None,
    proxy_auth: str | None = None,
    subconverter_url: str | None = None,
) -> list[str]:
    store = EnvStore(get_paths().envs_dir)
    values = store.load_active(ChatClashConfig)
    changed: list[str] = []
    updates = {
        "CHATCLASH_HOME": home,
        "CHATCLASH_SUBSCRIPTION_URL": subscription_url,
        "CHATCLASH_PROXY_AUTH": proxy_auth,
        "CHATCLASH_SUBCONVERTER_URL": subconverter_url,
    }
    for key, value in updates.items():
        if value is not None:
            values[key] = value
            changed.append(key)
    if changed:
        store.save_active(ChatClashConfig, values)
    return changed


def operator_status() -> dict[str, str]:
    cfg = read_operator_config()
    return {
        "home": cfg.home or "<not set>",
        "subscription_url": "present" if cfg.subscription_url else "<not set>",
        "proxy_auth": "present" if cfg.proxy_auth else "<not set>",
        "subconverter_url": mask(cfg.subconverter_url),
    }
