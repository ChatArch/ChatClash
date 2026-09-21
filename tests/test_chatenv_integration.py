from pathlib import Path

import pytest
from click.testing import CliRunner
from chatenv import EnvStore, get_paths

from chatclash.chatenv_store import read_operator_config, write_operator_config
from chatclash.config import ChatClashConfig
from chatclash.paths import chatclash_home, initialize_home


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    home = tmp_path / "user"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setenv("CHATARCH_HOME", str(tmp_path / "arch"))
    for key in ChatClashConfig.get_fields():
        monkeypatch.delenv(key, raising=False)


def test_default_runtime_follows_effective_chatarch_home():
    expected = get_paths().home_dir / "chatclash"
    assert chatclash_home() == expected
    result = initialize_home()
    assert result.home == expected
    assert (expected / "config.yaml").is_file()


def test_active_profile_home_expands_user_and_process_override_wins(monkeypatch):
    store = EnvStore(get_paths().envs_dir)
    store.save_active(ChatClashConfig, {"CHATCLASH_HOME": "~/profile-runtime"})
    assert chatclash_home() == Path.home() / "profile-runtime"
    monkeypatch.setenv("CHATCLASH_HOME", "~/process-runtime")
    assert chatclash_home() == Path.home() / "process-runtime"


def test_switching_chatarch_home_does_not_reuse_prior_profile(tmp_path, monkeypatch):
    store = EnvStore(get_paths().envs_dir)
    store.save_active(ChatClashConfig, {"CHATCLASH_SUBSCRIPTION_URL": "https://example.invalid/first"})
    assert read_operator_config().subscription_url == "https://example.invalid/first"
    monkeypatch.setenv("CHATARCH_HOME", str(tmp_path / "second"))
    assert read_operator_config().subscription_url is None
    assert chatclash_home() == tmp_path / "second" / "chatclash"


def test_profile_reads_do_not_load_other_providers(monkeypatch):
    from chatenv import BaseEnvConfig

    def forbidden(*args, **kwargs):
        raise AssertionError("ChatClash must only read its own typed profile")
    monkeypatch.setattr(BaseEnvConfig, "load_all", forbidden)
    assert read_operator_config().subscription_url is None


def test_explicit_store_write_preserves_other_profile_values(monkeypatch):
    store = EnvStore(get_paths().envs_dir)
    original = {"CHATCLASH_SUBSCRIPTION_URL": "https://example.invalid/saved", "CHATCLASH_PROXY_AUTH": "fixture:saved"}
    store.save_active(ChatClashConfig, original)
    monkeypatch.setenv("CHATCLASH_SUBSCRIPTION_URL", "https://example.invalid/process")
    write_operator_config(subconverter_url="http://127.0.0.1:25500")
    values = store.load_active(ChatClashConfig)
    assert values["CHATCLASH_SUBSCRIPTION_URL"] == original["CHATCLASH_SUBSCRIPTION_URL"]
    assert values["CHATCLASH_PROXY_AUTH"] == original["CHATCLASH_PROXY_AUTH"]
    assert values["CHATCLASH_SUBCONVERTER_URL"] == "http://127.0.0.1:25500"


def test_named_profile_requires_activation_before_chatclash_uses_it():
    store = EnvStore(get_paths().envs_dir)
    store.save_profile(ChatClashConfig, "work", {"CHATCLASH_SUBSCRIPTION_URL": "https://example.invalid/named"})
    assert read_operator_config().subscription_url is None
    store.use_profile(ChatClashConfig, "work")
    assert read_operator_config().subscription_url == "https://example.invalid/named"


def test_chatenv_test_hook_uses_current_profile_without_install_or_restart(monkeypatch):
    from chatclash import checks
    from chatclash.models import CheckResult

    captured = []
    def check(**kwargs):
        captured.append((kwargs, chatclash_home()))
        return CheckResult(proxy="http://127.0.0.1:7890", auth_present=True, results=[], success_count=1)
    monkeypatch.setattr(checks, "check_proxy", check)
    from chatenv.cli import cli as chatenv_main
    result = CliRunner().invoke(chatenv_main, ["test", "-t", "chatclash", "-I"])
    assert result.exit_code == 0, result.output
    assert captured == [({"min_success": 1, "timeout": 10}, get_paths().home_dir / "chatclash")]


def test_real_chatenv_profile_cli_discovery_import_and_activation():
    from chatenv.cli import cli as chatenv_cli

    runner = CliRunner()
    for args in (["list", "-t", "chatclash"], ["new", "work", "-t", "chatclash", "-I", "--yes"]):
        result = runner.invoke(chatenv_cli, args)
        assert result.exit_code == 0, result.output
    payload = "CHATCLASH_SUBSCRIPTION_URL=https://example.invalid/fixture\nCHATCLASH_PROXY_AUTH=fixture:password\n"
    result = runner.invoke(chatenv_cli, ["paste", "--stdin", "--profile", "work", "-I", "--yes"], input=payload)
    assert result.exit_code == 0, result.output
    result = runner.invoke(chatenv_cli, ["use", "work", "-t", "chatclash", "-I"])
    assert result.exit_code == 0, result.output
    assert read_operator_config().subscription_url == "https://example.invalid/fixture"
    assert read_operator_config().proxy_auth == "fixture:password"
    assert (get_paths().envs_dir / "chatclash" / ".env").is_file()
    result = runner.invoke(chatenv_cli, ["cat", "-t", "chatclash"])
    assert result.exit_code == 0, result.output
    assert "https://example.invalid/fixture" not in result.output
    assert "fixture:password" not in result.output


def test_initialize_home_starts_loopback_only_without_proxy_auth():
    result = initialize_home()
    active = (result.clash_dir / "config.yaml").read_text(encoding="utf-8")

    assert "allow-lan: false" in active
    assert "bind-address: 127.0.0.1" in active
