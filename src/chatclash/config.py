"""ChatClash chatenv schema."""

from chatenv import BaseEnvConfig, EnvField


class ChatClashConfig(BaseEnvConfig):
    """Values that are useful across machines and profiles."""

    _title = "ChatClash"
    _aliases = ["chatclash"]
    _storage_dir = "chatclash"

    CHATCLASH_SUBSCRIPTION_URL = EnvField(
        "CHATCLASH_SUBSCRIPTION_URL",
        desc="Subscription URL used by subconverter.",
        is_sensitive=True,
    )
    CHATCLASH_SUBCONVERTER_URL = EnvField(
        "CHATCLASH_SUBCONVERTER_URL",
        desc="subconverter service base URL.",
    )


__all__ = ["ChatClashConfig"]
