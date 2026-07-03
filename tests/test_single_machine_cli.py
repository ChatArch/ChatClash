from __future__ import annotations

from pathlib import Path

import yaml


def test_python_api_modules_are_importable_and_structured(tmp_path, monkeypatch):
    monkeypatch.setenv("CHATCLASH_HOME", str(tmp_path / "chatclash-home"))
    monkeypatch.setenv("CHATARCH_HOME", str(tmp_path / "chatarch-home"))

    from chatclash.checks import check_ip, check_proxy
    from chatclash.mihomo import get_mihomo_status, install_mihomo
    from chatclash.paths import initialize_home, read_local_config
    from chatclash.proxy import get_proxy_endpoints, get_proxy_env, set_proxy_config
    from chatclash.status import get_status
    from chatclash.subscription import build_subscription_url, set_subscription_config

    init = initialize_home()
    assert init.home == tmp_path / "chatclash-home"
    assert read_local_config()["clash_dir"] == str(init.clash_dir)

    changed = set_proxy_config(http_port_value=18090, socks_port_value=18091)
    assert set(changed) == {"http_port", "socks_port"}
    endpoints = get_proxy_endpoints()
    assert endpoints.http == "http://127.0.0.1:18090"
    assert get_proxy_env()["all_proxy"] == "socks5://127.0.0.1:18091"

    set_subscription_config(subscription_url="https://subscribe.example.test/secret-token", subconverter_url="http://127.0.0.1:25500")
    url = build_subscription_url()
    assert "target=clash" in url
    assert "secret-token" in url

    dry_proxy = check_proxy(dry_run=True)
    assert dry_proxy.success_count >= 1
    assert "ip-api.com" in check_ip(dry_run=True)

    dry_install = install_mihomo(dry_run=True, daemon=True)
    assert dry_install.dry_run is True
    assert any("mihomo" in line for line in dry_install.lines)

    status = get_status()
    assert status["subscription_set"] == "yes"
    assert get_mihomo_status()["installed"] == "no"


def test_chatenv_schema_has_operator_config_only():
    from chatclash.config import ChatClashConfig

    fields = {field.env_key: field for field in ChatClashConfig.get_fields().values()}
    assert fields["CHATCLASH_SUBSCRIPTION_URL"].is_sensitive is True
    assert fields["CHATCLASH_PROXY_AUTH"].is_sensitive is True
    assert "CHATCLASH_SUBCONVERTER_URL" in fields
    assert "CHATCLASH_SUBSCRIPTION_FETCH_PROXY" in fields
    assert "CHATCLASH_HTTP_PORT" not in fields
    assert "CHATCLASH_SOCKS_PORT" not in fields
    assert "CHATCLASH_CONTROLLER_PORT" not in fields
    ChatClashConfig.test()


def test_local_config_keeps_runtime_facts_not_secrets(tmp_path, monkeypatch):
    monkeypatch.setenv("CHATCLASH_HOME", str(tmp_path / "chatclash-home"))
    monkeypatch.setenv("CHATARCH_HOME", str(tmp_path / "chatarch-home"))

    from chatclash.paths import initialize_home, read_local_config
    from chatclash.subscription import set_subscription_config

    initialize_home()
    set_subscription_config(subscription_url="https://subscribe.example.test/secret-token", proxy_auth="user:secret-pass")
    local = read_local_config()
    assert "subscription_url" not in local
    assert "proxy_auth" not in local
    text = Path(tmp_path / "chatclash-home" / "config.yaml").read_text(encoding="utf-8")
    assert "secret-token" not in text
    assert "secret-pass" not in text
