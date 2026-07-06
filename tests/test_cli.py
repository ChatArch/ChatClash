from __future__ import annotations

import threading
import urllib.parse
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer

import yaml
from click.testing import CliRunner

from chatclash.cli import main


OLD_TOP_LEVEL = {
    "config",
    "deploy",
    "down",
    "engine",
    "ip-api",
    "logs",
    "restart",
    "setup",
    "subscription",
    "up",
    "update",
    "verify",
    "check",
}
TARGET_TOP_LEVEL = {"init", "status", "sub", "proxy", "mihomo"}


def _help_command_names(output: str) -> set[str]:
    names: set[str] = set()
    in_commands = False
    for line in output.splitlines():
        if line.strip() == "Commands:":
            in_commands = True
            continue
        if not in_commands:
            continue
        if line.startswith("  ") and line.strip() and not line.strip().startswith("-"):
            names.add(line.strip().split()[0])
    return names


def _clean_env(monkeypatch, tmp_path):
    monkeypatch.setenv("CHATCLASH_HOME", str(tmp_path / "chatclash-home"))
    monkeypatch.setenv("CHATARCH_HOME", str(tmp_path / "chatarch-home"))
    for key in (
        "CHATCLASH_SUBSCRIPTION_URL",
        "CHATCLASH_PROXY_AUTH",
        "CHATCLASH_SUBCONVERTER_URL",
    ):
        monkeypatch.delenv(key, raising=False)


def test_cli_tree_is_concise_and_old_commands_removed():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])

    assert result.exit_code == 0, result.output
    command_lines = _help_command_names(result.output)
    assert TARGET_TOP_LEVEL <= command_lines
    assert OLD_TOP_LEVEL.isdisjoint(command_lines)

    expected_groups = {
        "sub": {"set", "status", "update", "url", "generate", "converter"},
        "proxy": {"show", "env", "set", "validate"},
        "mihomo": {"install", "uninstall", "update", "start", "stop", "restart", "reload", "status", "logs"},
    }
    for group, commands in expected_groups.items():
        help_result = runner.invoke(main, [group, "--help"])
        assert help_result.exit_code == 0, help_result.output
        assert _help_command_names(help_result.output) == commands

    converter_help = runner.invoke(main, ["sub", "converter", "--help"])
    assert converter_help.exit_code == 0, converter_help.output
    assert _help_command_names(converter_help.output) == {"install", "start", "stop", "status", "logs"}


def test_removed_old_commands_fail_nonzero():
    runner = CliRunner()
    for command in sorted(OLD_TOP_LEVEL):
        result = runner.invoke(main, [command, "--help"])
        assert result.exit_code != 0, command
        assert "No such command" in result.output


def test_init_status_proxy_show_and_env_use_machine_local_config(tmp_path, monkeypatch):
    _clean_env(monkeypatch, tmp_path)
    home = tmp_path / "chatclash-home"
    runner = CliRunner()

    init = runner.invoke(
        main,
        [
            "init",
            "--subscription-url",
            "https://subscribe.example.test/secret-token",
            "--proxy-auth",
            "user:secret-pass",
            "-I",
        ],
    )
    assert init.exit_code == 0, init.output
    assert (home / "config.yaml").exists()
    assert (home / "clash" / "config.yaml").exists()
    assert not (home / "clash" / "docker-compose.yaml").exists()

    local = yaml.safe_load((home / "config.yaml").read_text(encoding="utf-8"))
    assert local["http_port"] == 7890
    assert local["socks_port"] == 7891
    assert "subscription_url" not in local
    assert "proxy_auth" not in local

    env_text = (tmp_path / "chatarch-home" / "envs" / "chatclash" / ".env").read_text(encoding="utf-8")
    assert "CHATCLASH_HOME" in env_text
    assert str(home) in env_text
    assert "CHATCLASH_SUBSCRIPTION_URL" in env_text
    assert "CHATCLASH_PROXY_AUTH" in env_text

    show = runner.invoke(main, ["proxy", "show"])
    assert show.exit_code == 0, show.output
    assert "HTTP proxy: http://user:***@127.0.0.1:7890" in show.output
    assert "SOCKS proxy: socks5://user:***@127.0.0.1:7891" in show.output
    assert "auth_present: yes" in show.output
    assert "auth_user: user" in show.output
    assert "proxy_auth: user:***" in show.output
    assert "secret-pass" not in show.output

    env_masked = runner.invoke(main, ["proxy", "env"])
    assert env_masked.exit_code == 0, env_masked.output
    assert "--no-mask" in env_masked.output
    assert "user:***@127.0.0.1:7890" in env_masked.output
    assert "secret-pass" not in env_masked.output
    env_plain = runner.invoke(main, ["proxy", "env", "--no-mask"])
    assert env_plain.exit_code == 0, env_plain.output
    assert "export http_proxy=http://user:secret-pass@127.0.0.1:7890" in env_plain.output

    status = runner.invoke(main, ["status"])
    assert status.exit_code == 0, status.output
    assert "mihomo_installed: no" in status.output
    assert "subscription_set: yes" in status.output
    assert "http_proxy: http://127.0.0.1:7890" in status.output


def test_proxy_set_rerenders_active_config_and_runtime_commands_are_explicit(tmp_path, monkeypatch):
    _clean_env(monkeypatch, tmp_path)
    home = tmp_path / "chatclash-home"
    runner = CliRunner()
    init = runner.invoke(main, ["init", "--local-only", "-I", "-y"])
    assert init.exit_code == 0, init.output

    result = runner.invoke(
        main,
        [
            "proxy",
            "set",
            "--http-port",
            "18080",
            "--socks-port",
            "18081",
            "--controller-port",
            "19090",
            "--bind-host",
            "127.0.0.1",
            "--proxy-host",
            "10.0.0.5",
            "-I",
            "-y",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "updated: http_port, socks_port, controller_port, bind_host, proxy_host" in result.output
    assert "chatclash mihomo restart" in result.output

    local = yaml.safe_load((home / "config.yaml").read_text(encoding="utf-8"))
    assert local["http_port"] == 18080
    assert local["socks_port"] == 18081
    assert local["controller_port"] == 19090
    assert local["bind_host"] == "127.0.0.1"
    assert local["proxy_host"] == "10.0.0.5"

    active = yaml.safe_load((home / "clash" / "config.yaml").read_text(encoding="utf-8"))
    assert active["port"] == 18080
    assert active["socks-port"] == 18081
    assert active["bind-address"] == "127.0.0.1"
    assert active["external-controller"] == ":19090"
    assert active["rules"] == ["MATCH,DIRECT"]

    validate = runner.invoke(main, ["proxy", "validate", "--dry-run"])
    assert validate.exit_code == 0, validate.output
    assert "validate:" in validate.output
    assert "dry-run only" in validate.output

    reload_result = runner.invoke(main, ["mihomo", "reload", "--dry-run"])
    assert reload_result.exit_code == 0, reload_result.output
    assert "controller: http://127.0.0.1:19090/configs" in reload_result.output
    assert "PUT /configs" in reload_result.output


def test_sub_set_status_uses_chatenv_and_masks_output(tmp_path, monkeypatch):
    _clean_env(monkeypatch, tmp_path)
    arch_home = tmp_path / "chatarch-home"
    monkeypatch.setenv("CLASH_SUB_URL", "https://subscribe.example.test/secret-token")
    monkeypatch.setenv("CLASH_PROXY_AUTH", "user:secret-pass")
    runner = CliRunner()
    assert runner.invoke(main, ["init", "--local-only", "-I", "-y"]).exit_code == 0

    result = runner.invoke(
        main,
        [
            "sub",
            "set",
            "--url-env",
            "CLASH_SUB_URL",
            "--subconverter-url",
            "http://127.0.0.1:25500",
            "-I",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "secret-token" not in result.output
    assert "secret-pass" not in result.output

    status = runner.invoke(main, ["sub", "status"])
    assert status.exit_code == 0, status.output
    assert "subscription_url: present" in status.output
    assert "proxy_auth: <not set>" in status.output
    assert "secret-token" not in status.output
    assert "secret-pass" not in status.output

    auth_set = runner.invoke(main, ["init", "--proxy-auth-env", "CLASH_PROXY_AUTH", "-I"])
    assert auth_set.exit_code == 0, auth_set.output
    assert "secret-pass" not in auth_set.output
    auth_show = runner.invoke(main, ["proxy", "show"])
    assert auth_show.exit_code == 0, auth_show.output
    assert "auth_present: yes" in auth_show.output
    assert "auth_user: user" in auth_show.output
    assert "proxy_auth: user:***" in auth_show.output
    assert "secret-pass" not in auth_show.output
    auth_plain = runner.invoke(main, ["proxy", "show", "--no-mask"])
    assert auth_plain.exit_code == 0, auth_plain.output
    assert "proxy_auth: user:secret-pass" in auth_plain.output

    env_text = (arch_home / "envs" / "chatclash" / ".env").read_text(encoding="utf-8")
    assert "CHATCLASH_SUBSCRIPTION_URL" in env_text
    assert "secret-token" in env_text  # ChatEnv is the intended system of record.
    local = yaml.safe_load((tmp_path / "chatclash-home" / "config.yaml").read_text(encoding="utf-8"))
    assert "subscription_url" not in local
    assert "proxy_auth" not in local


def test_sub_url_redacts_by_default_and_can_show_full_url(tmp_path, monkeypatch):
    _clean_env(monkeypatch, tmp_path)
    subscription = "https://subscribe.example.test/secret-token"
    runner = CliRunner()

    redacted = runner.invoke(main, ["sub", "url", subscription, "-s", "http://127.0.0.1:25500", "-I"])
    assert redacted.exit_code == 0, redacted.output
    assert "secret-token" not in redacted.output
    assert "subconverter_url:" in redacted.output

    full = runner.invoke(main, ["sub", "url", subscription, "-s", "http://127.0.0.1:25500", "--show", "-I"])
    assert full.exit_code == 0, full.output
    assert "target=clash" in full.output
    assert "secret-token" in full.output


class _ClashYamlHandler(BaseHTTPRequestHandler):
    seen_path = ""

    def do_GET(self):  # noqa: N802
        type(self).seen_path = self.path
        body = """\
port: 9999
socks-port: 9998
allow-lan: false
mode: Global
log-level: debug
external-controller: 127.0.0.1:9990
proxies:
  - name: direct-node
    type: http
    server: 127.0.0.1
    port: 8080
proxy-groups:
  - name: Proxy
    type: select
    proxies:
      - direct-node
rules:
  - MATCH,Proxy
"""
        self.send_response(200)
        self.send_header("Content-Type", "text/yaml; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def log_message(self, format, *args):  # noqa: A002
        return


class _SubconverterHandler(_ClashYamlHandler):
    pass


class _ProxiesOnlySubconverterHandler(BaseHTTPRequestHandler):
    seen_query = {}

    def do_GET(self):  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        type(self).seen_query = urllib.parse.parse_qs(parsed.query)
        body = """\
proxies:
  - name: node-a
    type: http
    server: 127.0.0.1
    port: 8080
  - name: node-b
    type: http
    server: 127.0.0.2
    port: 8081
"""
        self.send_response(200)
        self.send_header("Content-Type", "text/yaml; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def log_message(self, format, *args):  # noqa: A002
        return


class _LegacyProxySubconverterHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        body = """\
Proxy:
  - name: legacy-node
    type: http
    server: 127.0.0.3
    port: 8082
"""
        self.send_response(200)
        self.send_header("Content-Type", "text/yaml; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def log_message(self, format, *args):  # noqa: A002
        return


class _EmptySubconverterHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        self.send_response(200)
        self.send_header("Content-Type", "text/yaml; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"proxies: []\n")

    def log_message(self, format, *args):  # noqa: A002
        return


def _serve(handler):
    server = HTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def test_sub_generate_writes_config_and_backup(tmp_path, monkeypatch):
    import stat

    _clean_env(monkeypatch, tmp_path)
    server, thread = _serve(_SubconverterHandler)
    output = tmp_path / "config.yaml"
    output.write_text("old: config\n", encoding="utf-8")
    output.chmod(0o644)
    runner = CliRunner()
    assert runner.invoke(main, ["init", "--local-only", "-I", "-y"]).exit_code == 0
    set_result = runner.invoke(main, ["init", "--subscription-url", "https://subscribe.example.test/secret-token", "--proxy-auth", "user:secret-pass", "-I"])
    assert set_result.exit_code == 0, set_result.output
    try:
        result = runner.invoke(
            main,
            [
                "sub",
                "generate",
                "https://subscribe.example.test/secret-token",
                "-s",
                f"http://127.0.0.1:{server.server_port}",
                "-o",
                str(output),
                "-y",
                "-I",
            ],
        )
    finally:
        server.shutdown()
        thread.join(timeout=5)

    assert result.exit_code == 0, result.output
    assert "proxies: 1" in result.output
    assert "secret-token" not in result.output
    parsed = yaml.safe_load(output.read_text(encoding="utf-8"))
    assert parsed["authentication"] == ["user:secret-pass"]
    assert parsed["port"] == 7890
    assert parsed["socks-port"] == 7891
    assert parsed["external-controller"] == ":9090"
    assert parsed["proxies"][0]["name"] == "direct-node"
    assert stat.S_IMODE(output.stat().st_mode) == 0o600
    backups = list((tmp_path / "backups").glob("config.yaml.*.bak"))
    assert backups
    for backup in backups:
        assert stat.S_IMODE(backup.stat().st_mode) == 0o600
    assert _SubconverterHandler.seen_path.startswith("/sub?")


def test_sub_generate_uses_documented_subconverter_params_and_composes_groups(tmp_path, monkeypatch):
    _clean_env(monkeypatch, tmp_path)
    server, thread = _serve(_ProxiesOnlySubconverterHandler)
    output = tmp_path / "config.yaml"
    runner = CliRunner()
    assert runner.invoke(main, ["init", "--local-only", "-I", "-y"]).exit_code == 0
    set_result = runner.invoke(main, ["init", "--subscription-url", "https://subscribe.example.test/secret-token", "--proxy-auth", "user:secret-pass", "-I"])
    assert set_result.exit_code == 0, set_result.output
    try:
        result = runner.invoke(
            main,
            [
                "sub",
                "generate",
                "https://subscribe.example.test/secret-token",
                "-s",
                f"http://127.0.0.1:{server.server_port}",
                "-o",
                str(output),
                "-y",
                "-I",
            ],
        )
    finally:
        server.shutdown()
        thread.join(timeout=5)

    assert result.exit_code == 0, result.output
    assert "proxies: 2" in result.output
    query = _ProxiesOnlySubconverterHandler.seen_query
    assert query["target"] == ["clash"]
    assert query["insert"] == ["false"]
    assert query["emoji"] == ["true"]
    assert query["list"] == ["false"]
    assert query["tfo"] == ["false"]
    assert query["scv"] == ["false"]
    assert query["fdn"] == ["false"]
    assert query["sort"] == ["false"]
    assert query["new_name"] == ["true"]
    assert "ACL4SSR_Online.ini" in query["config"][0]
    parsed = yaml.safe_load(output.read_text(encoding="utf-8"))
    assert parsed["authentication"] == ["user:secret-pass"]
    assert [p["name"] for p in parsed["proxies"]] == ["node-a", "node-b"]
    assert [g["name"] for g in parsed["proxy-groups"]] == ["AUTO", "PROXY", "AI"]
    assert parsed["proxy-groups"][0]["proxies"] == ["node-a", "node-b"]
    assert "MATCH,PROXY" in parsed["rules"]


def test_sub_generate_normalizes_legacy_subconverter_proxy_key(tmp_path, monkeypatch):
    _clean_env(monkeypatch, tmp_path)
    server, thread = _serve(_LegacyProxySubconverterHandler)
    output = tmp_path / "config.yaml"
    runner = CliRunner()
    assert runner.invoke(main, ["init", "--local-only", "-I", "-y"]).exit_code == 0
    try:
        result = runner.invoke(
            main,
            [
                "sub",
                "generate",
                "https://subscribe.example.test/secret-token",
                "-s",
                f"http://127.0.0.1:{server.server_port}",
                "-o",
                str(output),
                "-y",
                "-I",
            ],
        )
    finally:
        server.shutdown()
        thread.join(timeout=5)

    assert result.exit_code == 0, result.output
    parsed = yaml.safe_load(output.read_text(encoding="utf-8"))
    assert "Proxy" not in parsed
    assert parsed["proxies"][0]["name"] == "legacy-node"
    assert parsed["proxy-groups"][0]["name"] == "AUTO"


def test_sub_generate_rejects_zero_proxy_converter_output(tmp_path, monkeypatch):
    _clean_env(monkeypatch, tmp_path)
    server, thread = _serve(_EmptySubconverterHandler)
    output = tmp_path / "config.yaml"
    runner = CliRunner()
    assert runner.invoke(main, ["init", "--local-only", "-I", "-y"]).exit_code == 0
    try:
        result = runner.invoke(
            main,
            [
                "sub",
                "generate",
                "https://subscribe.example.test/secret-token",
                "-s",
                f"http://127.0.0.1:{server.server_port}",
                "-o",
                str(output),
                "-y",
                "-I",
            ],
        )
    finally:
        server.shutdown()
        thread.join(timeout=5)

    assert result.exit_code != 0
    assert "did not produce any usable proxies" in result.output
    assert not output.exists()


def test_sub_update_fetches_direct_yaml_preserves_auth_and_writes_backup(tmp_path, monkeypatch):
    _clean_env(monkeypatch, tmp_path)
    home = tmp_path / "chatclash-home"
    server, thread = _serve(_ClashYamlHandler)
    runner = CliRunner()
    try:
        assert runner.invoke(main, ["init", "--local-only", "-I", "-y"]).exit_code == 0
        set_result = runner.invoke(
            main,
            [
                "sub",
                "set",
                "--subscription-url",
                f"http://127.0.0.1:{server.server_port}/clash.yaml",
                "-I",
            ],
        )
        assert set_result.exit_code == 0, set_result.output
        auth_result = runner.invoke(
            main,
            [
                "init",
                "--subscription-url",
                f"http://127.0.0.1:{server.server_port}/clash.yaml",
                "--proxy-auth",
                "user:secret-pass",
                "-I",
            ],
        )
        assert auth_result.exit_code == 0, auth_result.output
        update = runner.invoke(main, ["sub", "update", "--no-validate"])
    finally:
        server.shutdown()
        thread.join(timeout=5)

    assert update.exit_code == 0, update.output
    clash_config = yaml.safe_load((home / "clash" / "config.yaml").read_text(encoding="utf-8"))
    assert clash_config["authentication"] == ["user:secret-pass"]
    assert clash_config["port"] == 7890
    assert clash_config["socks-port"] == 7891
    assert clash_config["external-controller"] == ":9090"
    assert clash_config["proxies"][0]["name"] == "direct-node"
    assert list((home / "clash" / "backups").glob("config.yaml.*.bak"))


def test_sub_converter_dry_run_lifecycle_uses_default_and_overridden_host_port(tmp_path, monkeypatch):
    _clean_env(monkeypatch, tmp_path)
    home = tmp_path / "chatclash-home"
    runner = CliRunner()
    assert runner.invoke(main, ["init", "--local-only", "-I", "-y"]).exit_code == 0

    install = runner.invoke(main, ["sub", "converter", "install", "--dry-run", "-I"])
    assert install.exit_code == 0, install.output
    assert str(home / "bin" / "subconverter") in install.output
    assert "dry-run only" in install.output

    start_default = runner.invoke(main, ["sub", "converter", "start", "--dry-run", "-I"])
    assert start_default.exit_code == 0, start_default.output
    assert "host: 127.0.0.1" in start_default.output
    assert "port: 25500" in start_default.output
    assert f"url: http://127.0.0.1:25500" in start_default.output
    assert str(home / "run" / "subconverter.pid") in start_default.output
    assert str(home / "logs" / "subconverter.log") in start_default.output

    start_custom = runner.invoke(main, ["sub", "converter", "start", "--host", "0.0.0.0", "--port", "26666", "--dry-run", "-I"])
    assert start_custom.exit_code == 0, start_custom.output
    assert "host: 0.0.0.0" in start_custom.output
    assert "port: 26666" in start_custom.output
    assert "url: http://0.0.0.0:26666" in start_custom.output

    status = runner.invoke(main, ["sub", "converter", "status", "-I"])
    assert status.exit_code == 0, status.output
    assert "running: no" in status.output
    assert "host: 127.0.0.1" in status.output
    assert "port: 25500" in status.output

    for command in ("stop", "logs"):
        result = runner.invoke(main, ["sub", "converter", command, "--dry-run", "-I"])
        assert result.exit_code == 0, result.output
        assert "dry-run only" in result.output


def test_sub_converter_install_rejects_tar_path_traversal(tmp_path, monkeypatch):
    import io
    import tarfile

    _clean_env(monkeypatch, tmp_path)
    runner = CliRunner()
    assert runner.invoke(main, ["init", "--local-only", "-I", "-y"]).exit_code == 0

    archive = tmp_path / "evil.tar.gz"
    payload = b"bad"
    with tarfile.open(archive, "w:gz") as tar:
        info = tarfile.TarInfo("../../evil")
        info.size = len(payload)
        tar.addfile(info, io.BytesIO(payload))

    result = runner.invoke(main, ["sub", "converter", "install", "--source", str(archive), "-I"])
    assert result.exit_code != 0
    assert "unsafe archive member" in result.output
    assert not (tmp_path.parent / "evil").exists()


def test_sub_converter_install_rejects_zip_path_traversal(tmp_path, monkeypatch):
    import zipfile

    _clean_env(monkeypatch, tmp_path)
    runner = CliRunner()
    assert runner.invoke(main, ["init", "--local-only", "-I", "-y"]).exit_code == 0

    archive = tmp_path / "evil.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("../evil", "bad")

    result = runner.invoke(main, ["sub", "converter", "install", "--source", str(archive), "-I"])
    assert result.exit_code != 0
    assert "unsafe archive member" in result.output
    assert not (tmp_path.parent / "evil").exists()


def test_sub_converter_install_extracts_tar_gz_source(tmp_path, monkeypatch):
    import tarfile

    _clean_env(monkeypatch, tmp_path)
    home = tmp_path / "chatclash-home"
    runner = CliRunner()
    assert runner.invoke(main, ["init", "--local-only", "-I", "-y"]).exit_code == 0

    payload_dir = tmp_path / "payload"
    payload_dir.mkdir()
    binary = payload_dir / "subconverter"
    binary.write_text("#!/bin/sh\necho extracted-converter\n", encoding="utf-8")
    binary.chmod(0o755)
    archive = tmp_path / "subconverter_linux64.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(binary, arcname="subconverter/subconverter")

    result = runner.invoke(main, ["sub", "converter", "install", "--source", str(archive), "-I"])
    assert result.exit_code == 0, result.output
    target = home / "bin" / "subconverter"
    assert target.exists()
    assert target.read_text(encoding="utf-8").startswith("#!/bin/sh")
    assert target.stat().st_mode & 0o111


def test_sub_converter_install_source_start_status_stop_with_fake_binary(tmp_path, monkeypatch):
    _clean_env(monkeypatch, tmp_path)
    home = tmp_path / "chatclash-home"
    runner = CliRunner()
    assert runner.invoke(main, ["init", "--local-only", "-I", "-y"]).exit_code == 0

    fake = tmp_path / "fake-subconverter"
    fake.write_text("#!/bin/sh\necho converter-ready\nsleep 30\n", encoding="utf-8")
    fake.chmod(0o755)

    install = runner.invoke(main, ["sub", "converter", "install", "--source", str(fake), "-I"])
    assert install.exit_code == 0, install.output
    target = home / "bin" / "subconverter"
    assert target.exists()
    assert target.stat().st_mode & 0o111

    start = runner.invoke(main, ["sub", "converter", "start", "--host", "127.0.0.1", "--port", "26666", "-I"])
    assert start.exit_code == 0, start.output
    assert "started" in start.output
    pref = home / "subconverter" / "pref.ini"
    assert "listen=127.0.0.1" in pref.read_text(encoding="utf-8")
    assert "port=26666" in pref.read_text(encoding="utf-8")

    status = runner.invoke(main, ["sub", "converter", "status", "-I"])
    assert status.exit_code == 0, status.output
    assert "running: yes" in status.output
    assert "host: 127.0.0.1" in status.output
    assert "port: 26666" in status.output

    stop = runner.invoke(main, ["sub", "converter", "stop", "-I"])
    assert stop.exit_code == 0, stop.output
    assert "stopped" in stop.output
    assert not (home / "run" / "subconverter.pid").exists()


def test_mihomo_dry_run_paths(tmp_path, monkeypatch):
    _clean_env(monkeypatch, tmp_path)
    home = tmp_path / "chatclash-home"
    runner = CliRunner()
    assert runner.invoke(main, ["init", "--local-only", "-I", "-y"]).exit_code == 0

    install = runner.invoke(main, ["mihomo", "install", "--daemon", "--dry-run"])
    assert install.exit_code == 0, install.output
    assert str(home / "bin" / "mihomo") in install.output
    assert "daemon: install" in install.output
    for command in ("start", "stop", "restart", "logs"):
        result = runner.invoke(main, ["mihomo", command, "--dry-run"])
        assert result.exit_code == 0, result.output
        assert "dry-run only" in result.output


def test_all_public_commands_expose_shared_interactive_option():
    runner = CliRunner()
    commands = [
        [],
        ["sub"],
        ["proxy"],
        ["mihomo"],
        ["init"],
        ["status"],
        ["sub", "set"],
        ["sub", "status"],
        ["sub", "update"],
        ["sub", "url"],
        ["sub", "generate"],
        ["sub", "converter"],
        ["sub", "converter", "install"],
        ["sub", "converter", "start"],
        ["sub", "converter", "stop"],
        ["sub", "converter", "status"],
        ["sub", "converter", "logs"],
        ["proxy", "show"],
        ["proxy", "env"],
        ["proxy", "set"],
        ["proxy", "validate"],
        ["mihomo", "install"],
        ["mihomo", "uninstall"],
        ["mihomo", "update"],
        ["mihomo", "start"],
        ["mihomo", "stop"],
        ["mihomo", "restart"],
        ["mihomo", "reload"],
        ["mihomo", "status"],
        ["mihomo", "logs"],
    ]

    for command in commands:
        result = runner.invoke(main, [*command, "--help"])
        assert result.exit_code == 0, " ".join(command) + "\n" + result.output
        assert "-i, --interactive / -I, --no-interactive" in result.output, " ".join(command)


def test_top_level_version_works():
    result = CliRunner().invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "0.1.5" in result.output



def test_init_home_option_writes_config_under_requested_home(tmp_path, monkeypatch):
    _clean_env(monkeypatch, tmp_path)
    explicit_home = tmp_path / "explicit-home"
    default_home = tmp_path / "chatclash-home"
    result = CliRunner().invoke(main, ["init", "--home", str(explicit_home), "--local-only", "-I", "-y"])

    assert result.exit_code == 0, result.output
    assert (explicit_home / "config.yaml").exists()
    assert (explicit_home / "clash" / "config.yaml").exists()
    assert not (default_home / "config.yaml").exists()


def test_secret_bearing_runtime_config_and_backups_are_private(tmp_path, monkeypatch):
    import stat

    _clean_env(monkeypatch, tmp_path)
    home = tmp_path / "chatclash-home"
    server, thread = _serve(_ClashYamlHandler)
    runner = CliRunner()
    try:
        assert runner.invoke(main, ["init", "--local-only", "-I", "-y"]).exit_code == 0
        first = runner.invoke(
            main,
            [
                "sub",
                "set",
                "--subscription-url",
                f"http://127.0.0.1:{server.server_port}/clash.yaml",
                "-I",
            ],
        )
        assert first.exit_code == 0, first.output
        assert runner.invoke(main, ["sub", "update", "--no-validate"]).exit_code == 0
        assert runner.invoke(main, ["sub", "update", "--no-validate"]).exit_code == 0
    finally:
        server.shutdown()
        thread.join(timeout=5)

    config_path = home / "clash" / "config.yaml"
    assert stat.S_IMODE(config_path.stat().st_mode) == 0o600
    backups = list((home / "clash" / "backups").glob("config.yaml.*.bak"))
    assert backups
    for backup in backups:
        assert stat.S_IMODE(backup.stat().st_mode) == 0o600


def test_sub_url_non_interactive_missing_values_fails_cleanly(tmp_path, monkeypatch):
    _clean_env(monkeypatch, tmp_path)
    result = CliRunner().invoke(main, ["sub", "url", "-I"])

    assert result.exit_code != 0
    assert "Missing subscription URL" in result.output


def test_mihomo_logs_redact_configured_operator_secrets(tmp_path, monkeypatch):
    _clean_env(monkeypatch, tmp_path)
    home = tmp_path / "chatclash-home"
    runner = CliRunner()
    assert runner.invoke(main, ["init", "--local-only", "-I", "-y"]).exit_code == 0
    set_result = runner.invoke(
        main,
        [
            "sub",
            "set",
            "--subscription-url",
            "https://subscribe.example.test/secret-token",
            "-I",
        ],
    )
    assert set_result.exit_code == 0, set_result.output
    auth_result = runner.invoke(main, ["init", "--subscription-url", "https://subscribe.example.test/secret-token", "--proxy-auth", "user:secret-pass", "-I"])
    assert auth_result.exit_code == 0, auth_result.output
    log_file = home / "logs" / "mihomo.log"
    log_file.write_text("url=https://subscribe.example.test/secret-token auth=user:secret-pass\n", encoding="utf-8")
    monkeypatch.setattr("chatclash.mihomo.daemon_unit_path", lambda: home / "run" / "missing.service")

    logs = runner.invoke(main, ["mihomo", "logs"])
    assert logs.exit_code == 0, logs.output
    assert "secret-token" not in logs.output
    assert "secret-pass" not in logs.output
    assert "subscribe.example.test" in logs.output



def test_init_interactive_flags_are_respected(tmp_path, monkeypatch):
    _clean_env(monkeypatch, tmp_path)
    runner = CliRunner()

    forced = runner.invoke(main, ["init", "-i"])
    assert forced.exit_code != 0
    assert "Interactive mode was requested" in forced.output

    missing = runner.invoke(main, ["init", "-I"])
    assert missing.exit_code != 0
    assert "Missing subscription URL" in missing.output
    assert not (tmp_path / "chatclash-home" / "config.yaml").exists()

    configured = runner.invoke(
        main,
        [
            "init",
            "--subscription-url",
            "https://subscribe.example.test/secret-token",
            "--proxy-auth",
            "user:secret-pass",
            "-I",
        ],
    )
    assert configured.exit_code == 0, configured.output
    assert (tmp_path / "chatclash-home" / "config.yaml").exists()
    assert "secret-token" not in configured.output
    assert "secret-pass" not in configured.output
    env_text = (tmp_path / "chatarch-home" / "envs" / "chatclash" / ".env").read_text(encoding="utf-8")
    assert "CHATCLASH_SUBSCRIPTION_URL" in env_text
    assert "CHATCLASH_PROXY_AUTH" in env_text


def test_init_reuses_existing_chatenv_values_without_input_aliases(tmp_path, monkeypatch):
    _clean_env(monkeypatch, tmp_path)
    runner = CliRunner()
    seed = runner.invoke(
        main,
        [
            "sub",
            "set",
            "--subscription-url",
            "https://subscribe.example.test/secret-token",
            "-I",
        ],
    )
    assert seed.exit_code == 0, seed.output
    auth = runner.invoke(main, ["init", "--subscription-url", "https://subscribe.example.test/secret-token", "--proxy-auth", "user:secret-pass", "-I"])
    assert auth.exit_code == 0, auth.output

    init = runner.invoke(main, ["init", "-I"])
    assert init.exit_code == 0, init.output
    assert "chat_env_updated:" in init.output
    assert "secret-token" not in init.output
    assert "secret-pass" not in init.output


def test_chatenv_cat_can_read_chatclash_active_profile(tmp_path, monkeypatch):
    _clean_env(monkeypatch, tmp_path)
    from chatenv.cli import cli as chatenv_cli

    result = CliRunner().invoke(
        main,
        [
            "sub",
            "set",
            "--subscription-url",
            "https://subscribe.example.test/secret-token",
            "--subconverter-url",
            "http://127.0.0.1:25500",
            "-I",
        ],
    )
    assert result.exit_code == 0, result.output
    auth_result = CliRunner().invoke(main, ["init", "--subscription-url", "https://subscribe.example.test/secret-token", "--proxy-auth", "user:secret-pass", "-I"])
    assert auth_result.exit_code == 0, auth_result.output

    cat = CliRunner().invoke(chatenv_cli, ["--home", str(tmp_path / "chatarch-home"), "cat", "-t", "chatclash"])
    assert cat.exit_code == 0, cat.output
    assert "CHATCLASH_SUBSCRIPTION_URL" in cat.output
    assert "CHATCLASH_PROXY_AUTH" in cat.output
    assert "secret-token" not in cat.output
    assert "secret-pass" not in cat.output


def test_chatenv_test_invokes_chatclash_proxy_check(tmp_path, monkeypatch):
    _clean_env(monkeypatch, tmp_path)
    from types import SimpleNamespace
    from chatenv.cli import cli as chatenv_cli

    calls = []

    def fake_check_proxy(*, min_success=2, timeout=30, urls=None, dry_run=False):
        calls.append({"min_success": min_success, "timeout": timeout, "urls": urls, "dry_run": dry_run})
        return SimpleNamespace(success_count=1)

    monkeypatch.setattr("chatclash.checks.check_proxy", fake_check_proxy)
    result = CliRunner().invoke(chatenv_cli, ["--home", str(tmp_path / "chatarch-home"), "test", "-t", "chatclash", "-I"])

    assert result.exit_code == 0, result.output
    assert calls == [{"min_success": 1, "timeout": 10, "urls": None, "dry_run": False}]
    assert "OK proxy success_count=1" in result.output


def test_proxy_validate_rejects_lan_proxy_without_authentication(tmp_path, monkeypatch):
    _clean_env(monkeypatch, tmp_path)
    home = tmp_path / "chatclash-home"
    runner = CliRunner()
    assert runner.invoke(main, ["init", "--local-only", "-I", "-y"]).exit_code == 0

    active_path = home / "clash" / "config.yaml"
    active = yaml.safe_load(active_path.read_text(encoding="utf-8"))
    active["allow-lan"] = True
    active["bind-address"] = "0.0.0.0"
    active.pop("authentication", None)
    active_path.write_text(yaml.safe_dump(active, sort_keys=False), encoding="utf-8")

    result = runner.invoke(main, ["proxy", "validate", "--dry-run", "-I"])

    assert result.exit_code != 0
    assert "LAN proxy is enabled" in result.output
    assert "CHATCLASH_PROXY_AUTH" in result.output


def test_proxy_set_refresh_restores_proxy_authentication(tmp_path, monkeypatch):
    _clean_env(monkeypatch, tmp_path)
    home = tmp_path / "chatclash-home"
    runner = CliRunner()
    assert runner.invoke(
        main,
        ["init", "--subscription-url", "https://subscribe.example.test/secret-token", "--proxy-auth", "user:secret-pass", "-I"],
    ).exit_code == 0

    active_path = home / "clash" / "config.yaml"
    active = yaml.safe_load(active_path.read_text(encoding="utf-8"))
    active["allow-lan"] = True
    active["bind-address"] = "0.0.0.0"
    active.pop("authentication", None)
    active_path.write_text(yaml.safe_dump(active, sort_keys=False), encoding="utf-8")

    refresh = runner.invoke(main, ["proxy", "set", "--http-port", "18080", "-I", "-y"])
    assert refresh.exit_code == 0, refresh.output
    refreshed = yaml.safe_load(active_path.read_text(encoding="utf-8"))
    assert refreshed["authentication"] == ["user:secret-pass"]

    validate = runner.invoke(main, ["proxy", "validate", "--dry-run", "-I"])
    assert validate.exit_code == 0, validate.output
    assert "proxy_auth: validated" in validate.output
