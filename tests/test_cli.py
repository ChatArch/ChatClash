from __future__ import annotations

import threading
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
}
TARGET_TOP_LEVEL = {"init", "status", "sub", "proxy", "mihomo", "check"}


def _clean_env(monkeypatch, tmp_path):
    monkeypatch.setenv("CHATCLASH_HOME", str(tmp_path / "chatclash-home"))
    monkeypatch.setenv("CHATARCH_HOME", str(tmp_path / "chatarch-home"))
    for key in (
        "CHATCLASH_SUBSCRIPTION_URL",
        "CHATCLASH_PROXY_AUTH",
        "CHATCLASH_SUBCONVERTER_URL",
        "CHATCLASH_SUBSCRIPTION_FETCH_PROXY",
    ):
        monkeypatch.delenv(key, raising=False)


def test_cli_tree_is_concise_and_old_commands_removed():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])

    assert result.exit_code == 0, result.output
    command_lines = {line.strip().split()[0] for line in result.output.splitlines() if line.startswith("  ") and line.strip() and not line.strip().startswith("--")}
    assert TARGET_TOP_LEVEL <= command_lines
    assert OLD_TOP_LEVEL.isdisjoint(command_lines)

    expected_groups = {
        "sub": {"set", "status", "update", "url", "generate"},
        "proxy": {"set", "show", "env"},
        "mihomo": {"install", "uninstall", "update", "start", "stop", "restart", "status", "logs"},
        "check": {"proxy", "ip"},
    }
    for group, commands in expected_groups.items():
        help_result = runner.invoke(main, [group, "--help"])
        assert help_result.exit_code == 0, help_result.output
        for command in commands:
            assert command in help_result.output


def test_removed_old_commands_fail_nonzero():
    runner = CliRunner()
    for command in sorted(OLD_TOP_LEVEL):
        result = runner.invoke(main, [command, "--help"])
        assert result.exit_code != 0, command
        assert "No such command" in result.output


def test_init_status_proxy_set_and_env_use_machine_local_config(tmp_path, monkeypatch):
    _clean_env(monkeypatch, tmp_path)
    home = tmp_path / "chatclash-home"
    runner = CliRunner()

    init = runner.invoke(main, ["init", "-y"])
    assert init.exit_code == 0, init.output
    assert (home / "config.yaml").exists()
    assert (home / "clash" / "config.yaml").exists()
    assert not (home / "clash" / "docker-compose.yaml").exists()

    proxy_set = runner.invoke(
        main,
        ["proxy", "set", "--http-port", "18090", "--socks-port", "18091", "--controller-port", "19090"],
    )
    assert proxy_set.exit_code == 0, proxy_set.output

    local = yaml.safe_load((home / "config.yaml").read_text(encoding="utf-8"))
    assert local["http_port"] == 18090
    assert local["socks_port"] == 18091
    assert local["controller_port"] == 19090
    assert "subscription_url" not in local
    assert "proxy_auth" not in local

    show = runner.invoke(main, ["proxy", "show"])
    assert show.exit_code == 0, show.output
    assert "HTTP proxy: http://127.0.0.1:18090" in show.output
    assert "SOCKS proxy: socks5://127.0.0.1:18091" in show.output

    env = runner.invoke(main, ["proxy", "env"])
    assert env.exit_code == 0, env.output
    assert "export http_proxy=http://127.0.0.1:18090" in env.output
    assert "export all_proxy=socks5://127.0.0.1:18091" in env.output

    status = runner.invoke(main, ["status"])
    assert status.exit_code == 0, status.output
    assert "mihomo_installed: no" in status.output
    assert "subscription_set: no" in status.output
    assert "http_proxy: http://127.0.0.1:18090" in status.output


def test_sub_set_status_uses_chatenv_and_masks_output(tmp_path, monkeypatch):
    _clean_env(monkeypatch, tmp_path)
    arch_home = tmp_path / "chatarch-home"
    monkeypatch.setenv("CLASH_SUB_URL", "https://subscribe.example.test/secret-token")
    monkeypatch.setenv("CLASH_PROXY_AUTH", "user:secret-pass")
    runner = CliRunner()
    assert runner.invoke(main, ["init", "-y"]).exit_code == 0

    result = runner.invoke(
        main,
        [
            "sub",
            "set",
            "--url-env",
            "CLASH_SUB_URL",
            "--proxy-auth-env",
            "CLASH_PROXY_AUTH",
            "--subconverter-url",
            "http://127.0.0.1:25500",
            "--fetch-proxy",
            "local",
            "-I",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "secret-token" not in result.output
    assert "secret-pass" not in result.output

    status = runner.invoke(main, ["sub", "status"])
    assert status.exit_code == 0, status.output
    assert "subscription_url: present" in status.output
    assert "proxy_auth: present" in status.output
    assert "secret-token" not in status.output
    assert "secret-pass" not in status.output

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
    assert runner.invoke(main, ["init", "-y"]).exit_code == 0
    set_result = runner.invoke(main, ["sub", "set", "--proxy-auth", "user:secret-pass", "-I"])
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


def test_sub_update_fetches_direct_yaml_preserves_auth_and_writes_backup(tmp_path, monkeypatch):
    _clean_env(monkeypatch, tmp_path)
    home = tmp_path / "chatclash-home"
    server, thread = _serve(_ClashYamlHandler)
    runner = CliRunner()
    try:
        assert runner.invoke(main, ["init", "-y"]).exit_code == 0
        set_result = runner.invoke(
            main,
            [
                "sub",
                "set",
                "--subscription-url",
                f"http://127.0.0.1:{server.server_port}/clash.yaml",
                "--proxy-auth",
                "user:secret-pass",
                "-I",
            ],
        )
        assert set_result.exit_code == 0, set_result.output
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


def test_check_and_mihomo_dry_run_paths(tmp_path, monkeypatch):
    _clean_env(monkeypatch, tmp_path)
    home = tmp_path / "chatclash-home"
    runner = CliRunner()
    assert runner.invoke(main, ["init", "-y"]).exit_code == 0

    proxy = runner.invoke(main, ["check", "proxy", "--dry-run"])
    assert proxy.exit_code == 0, proxy.output
    assert "success_count:" in proxy.output
    assert "dry-run only" in proxy.output

    ip = runner.invoke(main, ["check", "ip", "--dry-run"])
    assert ip.exit_code == 0, ip.output
    assert "ip-api.com" in ip.output

    install = runner.invoke(main, ["mihomo", "install", "--daemon", "--dry-run"])
    assert install.exit_code == 0, install.output
    assert str(home / "bin" / "mihomo") in install.output
    assert "daemon: install" in install.output
    for command in ("start", "stop", "restart", "logs"):
        result = runner.invoke(main, ["mihomo", command, "--dry-run"])
        assert result.exit_code == 0, result.output
        assert "dry-run only" in result.output


def test_top_level_version_works():
    result = CliRunner().invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output



def test_init_home_option_writes_config_under_requested_home(tmp_path, monkeypatch):
    _clean_env(monkeypatch, tmp_path)
    explicit_home = tmp_path / "explicit-home"
    default_home = tmp_path / "chatclash-home"
    result = CliRunner().invoke(main, ["init", "--home", str(explicit_home), "-y"])

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
        assert runner.invoke(main, ["init", "-y"]).exit_code == 0
        first = runner.invoke(
            main,
            [
                "sub",
                "set",
                "--subscription-url",
                f"http://127.0.0.1:{server.server_port}/clash.yaml",
                "--proxy-auth",
                "user:secret-pass",
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
    assert runner.invoke(main, ["init", "-y"]).exit_code == 0
    set_result = runner.invoke(
        main,
        [
            "sub",
            "set",
            "--subscription-url",
            "https://subscribe.example.test/secret-token",
            "--proxy-auth",
            "user:secret-pass",
            "-I",
        ],
    )
    assert set_result.exit_code == 0, set_result.output
    log_file = home / "logs" / "mihomo.log"
    log_file.write_text("url=https://subscribe.example.test/secret-token auth=user:secret-pass\n", encoding="utf-8")
    monkeypatch.setattr("chatclash.mihomo.daemon_unit_path", lambda: home / "run" / "missing.service")

    logs = runner.invoke(main, ["mihomo", "logs"])
    assert logs.exit_code == 0, logs.output
    assert "secret-token" not in logs.output
    assert "secret-pass" not in logs.output
    assert "subscribe.example.test" in logs.output
