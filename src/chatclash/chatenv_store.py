"""ChatEnv integration for ChatClash operator config."""

from __future__ import annotations

import os
from dataclasses import dataclass

from chatenv import BaseEnvConfig, EnvStore, get_paths

from .config import ChatClashConfig
from .utils import clean, mask


@dataclass(frozen=True)
class OperatorConfig:
    home: str | None = None
    subscription_url: str | None = None
    proxy_auth: str | None = None
    subconverter_url: str | None = None


def load_chatenv() -> None:
    BaseEnvConfig.load_all(get_paths().envs_dir)


def _value(env_key: str, field) -> str | None:
    load_chatenv()
    return clean(os.getenv(env_key) or str(field.value or ""))


def read_operator_config() -> OperatorConfig:
    return OperatorConfig(
        home=_value("CHATCLASH_HOME", ChatClashConfig.CHATCLASH_HOME),
        subscription_url=_value("CHATCLASH_SUBSCRIPTION_URL", ChatClashConfig.CHATCLASH_SUBSCRIPTION_URL),
        proxy_auth=_value("CHATCLASH_PROXY_AUTH", ChatClashConfig.CHATCLASH_PROXY_AUTH),
        subconverter_url=_value("CHATCLASH_SUBCONVERTER_URL", ChatClashConfig.CHATCLASH_SUBCONVERTER_URL),
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
        load_chatenv()
    return changed


def operator_status() -> dict[str, str]:
    cfg = read_operator_config()
    return {
        "home": cfg.home or "<not set>",
        "subscription_url": "present" if cfg.subscription_url else "<not set>",
        "proxy_auth": "present" if cfg.proxy_auth else "<not set>",
        "subconverter_url": mask(cfg.subconverter_url),
    }
