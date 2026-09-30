"""Exercise Windows state changes without touching the host registry/processes."""

from contextlib import contextmanager, nullcontext
from copy import deepcopy
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from chatclash import mihomo, windows


class Registry:
    HKEY_CURRENT_USER = "HKCU"
    KEY_READ = 1
    KEY_WRITE = 2
    REG_SZ = 1
    REG_EXPAND_SZ = 2
    REG_DWORD = 4

    def __init__(self):
        self.values = {}
        self.writes = []

    @contextmanager
    def CreateKeyEx(self, root, path, reserved, access):
        yield path

    def QueryValueEx(self, key, name):
        try:
            return self.values[key, name]
        except KeyError:
            raise FileNotFoundError(name) from None

    def SetValueEx(self, key, name, reserved, kind, value):
        self.writes.append((key, name, value))
        self.values[key, name] = (value, kind)

    def DeleteValue(self, key, name):
        self.writes.append((key, name, None))
        if (key, name) not in self.values:
            raise FileNotFoundError(name)
        del self.values[key, name]


@pytest.fixture
def settings(tmp_path, monkeypatch):
    registry = Registry()
    state = SimpleNamespace(registry=registry, flags=13, home=tmp_path / "settings")
    state.home.mkdir()
    monkeypatch.setattr(windows, "is_windows", lambda: True)
    monkeypatch.setattr(windows, "_winreg", lambda: registry)
    monkeypatch.setattr(windows, "chatclash_home", lambda: state.home)
    monkeypatch.setattr(windows, "local_proxy_ready", lambda: True)
    monkeypatch.setattr(windows, "proxy_host", lambda: "127.0.0.1")
    monkeypatch.setattr(windows, "http_port", lambda: 7890)
    monkeypatch.setattr(windows, "_wininet_connection_flags", lambda: state.flags)
    monkeypatch.setattr(windows, "_broadcast_settings_change", lambda: None)

    def set_flags(value):
        registry.writes.append(("wininet", "flags", value))
        state.flags = value

    monkeypatch.setattr(windows, "_set_wininet_connection_flags", set_flags)
    return state


@pytest.mark.parametrize("existing", [False, True])
def test_repeated_enable_restores_original_values_and_connection_flags(settings, existing):
    registry = settings.registry
    key = windows.INTERNET_SETTINGS
    registry.values[key, "AutoConfigURL"] = ("https://example.test/proxy.pac", registry.REG_SZ)
    if existing:
        registry.values[key, "ProxyEnable"] = (1, registry.REG_DWORD)
        registry.values[key, "ProxyServer"] = ("old.proxy.test:8080", registry.REG_SZ)
        registry.values[key, "ProxyOverride"] = ("*.internal", registry.REG_SZ)
    original = deepcopy(registry.values)
    windows.enable_system_proxy()
    backup = settings.home / windows.SYSTEM_PROXY_BACKUP
    saved = backup.read_bytes()
    assert settings.flags == windows.PROXY_TYPE_DIRECT | windows.PROXY_TYPE_PROXY
    assert registry.values[key, "ProxyEnable"] == (1, registry.REG_DWORD)
    assert "127.0.0.1:7890" in registry.values[key, "ProxyServer"][0]
    windows.enable_system_proxy()
    assert backup.read_bytes() == saved
    windows.restore_system_proxy()
    assert registry.values == original
    assert settings.flags == 13
    assert not backup.exists()
    writes = list(registry.writes)
    windows.restore_system_proxy()
    assert registry.writes == writes


@pytest.mark.parametrize("bad_value", [
    {"present": True, "kind": "broken", "value": "old"},
    {"present": True, "kind": 1},
    {"present": True, "kind": 1, "value": 123},
])
def test_corrupt_backup_rejected_before_restore_or_reenable_writes(settings, bad_value):
    snapshot = {
        "ProxyEnable": {"present": True, "kind": 4, "value": 0},
        "ProxyServer": bad_value,
        "ProxyOverride": {"present": False},
        "wininet_flags": 9,
    }
    backup = settings.home / windows.SYSTEM_PROXY_BACKUP
    backup.write_text(json.dumps(snapshot), encoding="utf-8")
    saved = backup.read_bytes()
    for operation in (windows.restore_system_proxy, windows.enable_system_proxy):
        with pytest.raises(RuntimeError, match="backup"):
            operation()
        assert not settings.registry.writes
        assert backup.read_bytes() == saved


@pytest.mark.parametrize("operation", [windows.enable_system_proxy, windows.persist_proxy_environment])
def test_unready_proxy_does_not_change_settings_or_save_backup(settings, monkeypatch, operation):
    monkeypatch.setattr(windows, "local_proxy_ready", lambda: False)
    with pytest.raises(RuntimeError, match="not listening"):
        operation()
    assert not settings.registry.writes
    assert not list(settings.home.iterdir())


def test_authenticated_environment_persistence_requires_real_values_and_restores(settings, monkeypatch):
    registry = settings.registry
    registry.values[windows.USER_ENVIRONMENT, "HTTP_PROXY"] = ("%OLD_PROXY%", registry.REG_EXPAND_SZ)
    registry.values[windows.USER_ENVIRONMENT, "NO_PROXY"] = ("*.internal", registry.REG_SZ)
    original = deepcopy(registry.values)
    monkeypatch.setenv("CHATCLASH_PROXY_AUTH", "test-user:test-password")
    with pytest.raises(RuntimeError, match="masked"):
        windows.persist_proxy_environment()
    assert not registry.writes
    assert not list(settings.home.iterdir())
    lines = windows.persist_proxy_environment(no_mask=True)
    stored = registry.values[windows.USER_ENVIRONMENT, "HTTP_PROXY"][0]
    assert "test-user:test-password@" in stored
    assert "test-password" not in "\n".join(lines)
    backup = settings.home / windows.USER_ENV_BACKUP
    saved = backup.read_bytes()
    windows.persist_proxy_environment(no_mask=True)
    assert backup.read_bytes() == saved
    windows.restore_proxy_environment()
    assert registry.values == original
    assert not backup.exists()


def test_invalid_environment_backup_never_partially_restores(settings):
    snapshot = {name: {"present": False} for name in windows.PROXY_ENV_NAMES}
    snapshot["HTTPS_PROXY"] = {"present": True, "kind": 4, "value": 123}
    backup = settings.home / windows.USER_ENV_BACKUP
    backup.write_text(json.dumps(snapshot), encoding="utf-8")
    for operation in (windows.restore_proxy_environment, windows.persist_proxy_environment):
        with pytest.raises(RuntimeError, match="backup"):
            operation()
        assert not settings.registry.writes
        assert backup.exists()


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    engine = tmp_path / "mihomo.exe"
    engine.touch()
    config = {
        "engine_path": str(engine),
        "clash_dir": str(tmp_path),
        "pid_file": str(tmp_path / "mihomo.pid"),
        "log_file": str(tmp_path / "mihomo.log"),
        "proxy_host": "127.0.0.1",
        "http_port": 17890,
    }
    monkeypatch.setattr(mihomo, "is_windows", lambda: True)
    monkeypatch.setattr(mihomo, "read_local_config", lambda: config)
    monkeypatch.setattr(mihomo.time, "sleep", lambda _: None)
    return config


@pytest.mark.parametrize("mismatch", ["path", "created"])
def test_stale_pid_never_terminates_an_unrelated_process(runtime, monkeypatch, mismatch):
    state = {"pid": 1234, "path": runtime["engine_path"], "created": 100}
    pid_path = mihomo.pid_file(runtime)
    pid_path.write_text(json.dumps(state), encoding="utf-8")
    actual = {"path": state["path"], "created": state["created"]}
    actual[mismatch] = "different.exe" if mismatch == "path" else 200
    monkeypatch.setattr(mihomo, "_windows_process_details", lambda _: actual)
    kill = Mock(side_effect=AssertionError("must not kill an unrelated process"))
    monkeypatch.setattr(mihomo.os, "kill", kill)
    assert not mihomo.pid_running(pid_path)
    mihomo.stop_mihomo()
    kill.assert_not_called()
    assert not pid_path.exists()


def test_occupied_http_port_rejects_start_before_spawning(runtime, monkeypatch):
    monkeypatch.setattr(mihomo.socket, "create_connection", lambda *args, **kwargs: nullcontext())
    spawn = Mock(side_effect=AssertionError("must not spawn with occupied listener"))
    monkeypatch.setattr(mihomo.subprocess, "Popen", spawn)
    with pytest.raises(RuntimeError, match="already in use"):
        mihomo.start_mihomo()
    spawn.assert_not_called()
    assert not mihomo.pid_file(runtime).exists()


def test_startup_identity_failure_cleans_up_spawned_process(runtime, monkeypatch):
    monkeypatch.setattr(mihomo.socket, "create_connection", Mock(side_effect=ConnectionRefusedError))
    process = Mock(pid=1234)
    process.poll.return_value = None
    monkeypatch.setattr(mihomo.subprocess, "Popen", Mock(return_value=process))
    monkeypatch.setattr(mihomo, "_windows_process_details", lambda _: None)
    with pytest.raises(RuntimeError, match="startup"):
        mihomo.start_mihomo()
    process.terminate.assert_called_once()
    process.wait.assert_called_once()
    assert not mihomo.pid_file(runtime).exists()
