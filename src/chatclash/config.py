"""ChatClash ChatEnv schema."""

from __future__ import annotations

from chatenv import BaseEnvConfig, EnvField


class ChatClashConfig(BaseEnvConfig):
    """Operator config owned by ChatClash and stored through ChatEnv."""

    _title = "ChatClash"
    _aliases = ["chatclash"]
    _storage_dir = "chatclash"

    CHATCLASH_SUBSCRIPTION_URL = EnvField(
        "CHATCLASH_SUBSCRIPTION_URL",
        desc="Subscription URL used to generate the runtime proxy config.",
        is_sensitive=True,
    )
    CHATCLASH_PROXY_AUTH = EnvField(
        "CHATCLASH_PROXY_AUTH",
        desc="Proxy authentication in user:password format.",
        is_sensitive=True,
    )
    CHATCLASH_SUBCONVERTER_URL = EnvField(
        "CHATCLASH_SUBCONVERTER_URL",
        desc="Optional subconverter service base URL.",
    )
    CHATCLASH_SUBSCRIPTION_FETCH_PROXY = EnvField(
        "CHATCLASH_SUBSCRIPTION_FETCH_PROXY",
        desc="Proxy used to fetch subscription URL; use 'local' for this machine's ChatClash proxy.",
    )

    @classmethod
    def test(cls) -> None:
        required = {
            "CHATCLASH_SUBSCRIPTION_URL",
            "CHATCLASH_PROXY_AUTH",
            "CHATCLASH_SUBCONVERTER_URL",
            "CHATCLASH_SUBSCRIPTION_FETCH_PROXY",
        }
        actual = {field.env_key for field in cls.get_fields().values()}
        missing = sorted(required - actual)
        if missing:
            raise RuntimeError(f"missing ChatClash env fields: {', '.join(missing)}")
        print("OK")


__all__ = ["ChatClashConfig"]
