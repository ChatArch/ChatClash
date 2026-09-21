from pathlib import Path

import pytest

from chatclash.chatenv_store import write_operator_config
from chatclash.paths import initialize_home, read_local_config, write_local_config
from chatclash import subscription


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "user"))
    monkeypatch.setenv("CHATARCH_HOME", str(tmp_path / "arch"))
    monkeypatch.setenv("CHATCLASH_HOME", str(tmp_path / "arch" / "chatclash"))
    for key in ("CHATCLASH_SUBSCRIPTION_URL", "CHATCLASH_PROXY_AUTH", "CHATCLASH_SUBCONVERTER_URL"):
        monkeypatch.delenv(key, raising=False)
    result = initialize_home()
    write_operator_config(subscription_url="https://example.invalid/sub", proxy_auth="fixture:password")
    config = read_local_config()
    engine = Path(config["engine_path"])
    engine.write_text("# fixture; never executed")
    target = result.clash_dir / "config.yaml"
    original = b"# original working configuration\n"
    target.write_bytes(original)
    monkeypatch.setattr(subscription, "_fetch_url", lambda *args, **kwargs: "proxies:\n  - {name: fixture, type: ss, server: example.invalid, port: 443, cipher: aes-128-gcm, password: fixture}\n")
    return target, original, engine


def test_validation_failure_preserves_active_config(runtime, monkeypatch):
    target, original, engine = runtime
    def reject(command):
        raise RuntimeError("candidate validation failed")
    monkeypatch.setattr(subscription, "run_shell", reject)
    with pytest.raises(RuntimeError, match="validation failed"):
        subscription.update_subscription_config()
    assert target.read_bytes() == original
    assert list(target.parent.glob(".chatclash-*")) == []


def test_validation_targets_staged_file_before_replacement(runtime, monkeypatch):
    target, original, engine = runtime
    observed = []
    def validate(command):
        assert target.read_bytes() == original
        assert command[:3] == [str(engine), "-t", "-d"]
        assert "-f" in command
        staged = Path(command[command.index("-f") + 1])
        assert staged != target and staged.parent == target.parent
        assert "authentication:" in staged.read_text()
        observed.append(staged)
        return "valid"
    monkeypatch.setattr(subscription, "run_shell", validate)
    result = subscription.update_subscription_config()
    assert result["validated"] is True
    assert "proxies:" in target.read_text()
    assert all(not path.exists() for path in observed)
    assert any(path.read_bytes() == original for path in (target.parent / "backups").glob("*.bak"))


def test_missing_engine_requires_explicit_no_validate(runtime, monkeypatch):
    target, original, engine = runtime
    engine.unlink()
    with pytest.raises(ValueError, match="mihomo|Mihomo"):
        subscription.update_subscription_config()
    assert target.read_bytes() == original
    result = subscription.update_subscription_config(no_validate=True)
    assert result["validated"] is False
    assert "proxies:" in target.read_text()


def test_failed_atomic_replace_preserves_active_config(runtime, monkeypatch):
    import os
    target, original, _ = runtime
    monkeypatch.setattr(subscription, "run_shell", lambda command: "valid")
    def reject(*args):
        raise OSError("replace failed")
    monkeypatch.setattr(os, "replace", reject)
    with pytest.raises(OSError, match="replace failed"):
        subscription.update_subscription_config()
    assert target.read_bytes() == original
    assert list(target.parent.glob(".chatclash-*")) == []


def test_proxy_render_replace_failure_preserves_active_config(runtime, monkeypatch):
    import os

    target, original, _ = runtime

    def reject(*args):
        raise OSError("replace failed")

    monkeypatch.setattr(os, "replace", reject)
    with pytest.raises(OSError, match="replace failed"):
        subscription.render_active_config_from_local()

    assert target.read_bytes() == original
    assert list(target.parent.glob(".chatclash-*")) == []


def test_generate_replace_failure_preserves_output(runtime, monkeypatch, tmp_path):
    import os

    _, _, _ = runtime
    output = tmp_path / "generated.yaml"
    original = b"# original generated output\n"
    output.write_bytes(original)
    write_operator_config(subconverter_url="http://127.0.0.1:25500")
    monkeypatch.setattr(subscription, "_fetch_url", lambda *args, **kwargs: "proxies:\n  - {name: fixture, type: ss, server: example.invalid, port: 443, cipher: aes-128-gcm, password: fixture}\n")

    def reject(*args):
        raise OSError("replace failed")

    monkeypatch.setattr(os, "replace", reject)
    with pytest.raises(OSError, match="replace failed"):
        subscription.generate_subscription_config(output=output)

    assert output.read_bytes() == original
    assert list(output.parent.glob(".chatclash-*")) == []


def test_network_bind_without_proxy_auth_is_rejected_before_replacement(runtime, monkeypatch):
    target, original, _ = runtime
    config = read_local_config()
    config["bind_host"] = "0.0.0.0"
    write_local_config(config)
    write_operator_config(proxy_auth="")
    monkeypatch.setattr(subscription, "run_shell", lambda command: "valid")

    with pytest.raises(ValueError, match="proxy authentication is required"):
        subscription.update_subscription_config()

    assert target.read_bytes() == original
    assert list(target.parent.glob(".chatclash-*")) == []
