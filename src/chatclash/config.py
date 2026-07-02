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
    CHATCLASH_PROXY_AUTH = EnvField(
        "CHATCLASH_PROXY_AUTH",
        desc="Proxy authentication in user:password format.",
        is_sensitive=True,
    )
    CHATCLASH_SUBCONVERTER_URL = EnvField(
        "CHATCLASH_SUBCONVERTER_URL",
        desc="subconverter service base URL.",
    )
    CHATCLASH_SUBSCRIPTION_FETCH_PROXY = EnvField(
        "CHATCLASH_SUBSCRIPTION_FETCH_PROXY",
        desc="Proxy used to fetch subscription URL; use 'local' for this machine's ChatClash proxy.",
    )
    CHATCLASH_HTTP_PORT = EnvField(
        "CHATCLASH_HTTP_PORT",
        default="7890",
        desc="Local HTTP proxy port.",
    )
    CHATCLASH_SOCKS_PORT = EnvField(
        "CHATCLASH_SOCKS_PORT",
        default="7891",
        desc="Local SOCKS proxy port.",
    )
    CHATCLASH_CONTROLLER_PORT = EnvField(
        "CHATCLASH_CONTROLLER_PORT",
        default="9090",
        desc="Local Mihomo external-controller port.",
    )

    @classmethod
    def test(cls) -> None:
        """Validate that the ChatClash ChatEnv schema is discoverable."""

        print("Testing ChatClash...")
        required = {
            "CHATCLASH_SUBSCRIPTION_URL",
            "CHATCLASH_PROXY_AUTH",
            "CHATCLASH_SUBCONVERTER_URL",
            "CHATCLASH_SUBSCRIPTION_FETCH_PROXY",
            "CHATCLASH_HTTP_PORT",
            "CHATCLASH_SOCKS_PORT",
            "CHATCLASH_CONTROLLER_PORT",
        }
        actual = {field.env_key for field in cls.get_fields().values()}
        missing = sorted(required - actual)
        if missing:
            raise RuntimeError(f"missing ChatClash env fields: {', '.join(missing)}")
        print("OK")


__all__ = ["ChatClashConfig"]
