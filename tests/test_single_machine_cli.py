from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import yaml
from click.testing import CliRunner

from chatclash.cli import main


def test_init_dry_run_does_not_write(tmp_path, monkeypatch):
    home = tmp_path / "chatclash-home"
    monkeypatch.setenv("CHATCLASH_HOME", str(home))

    result = CliRunner().invoke(main, ["init", "--dry-run"])

    assert result.exit_code == 0, result.output
    assert "dry-run only" in result.output
    assert not home.exists()


def test_init_uses_chatclash_home_env_without_touching_real_home(tmp_path, monkeypatch):
    home = tmp_path / "chatclash-home"
    monkeypatch.setenv("CHATCLASH_HOME", str(home))

    result = CliRunner().invoke(main, ["init", "-y"])

    assert result.exit_code == 0, result.output
    assert (home / "config.yaml").exists()
    assert not (home / "clash" / "docker-compose.yaml").exists()
    assert (home / "clash" / "config.yaml").exists()
    assert (home / "clash" / "backups").is_dir()
    assert (home / "bin").is_dir()
    assert (home / "run").is_dir()
    assert (home / "logs").is_dir()
    assert (home / "cache").is_dir()
    saved = yaml.safe_load((home / "config.yaml").read_text(encoding="utf-8"))
    assert saved["engine"] == "binary"
    assert saved["engine_path"] == str(home / "bin" / "mihomo")
    assert saved["clash_dir"] == str(home / "clash")
    assert "http_port" not in saved
    assert "socks_port" not in saved
    assert "controller_port" not in saved
    assert "subscription_url" not in saved


def legacy_test_config_set_and_show_masks_sensitive_values(tmp_path, monkeypatch):
    home = tmp_path / "chatclash-home"
    arch_home = tmp_path / "chatarch-home"
    monkeypatch.setenv("CHATCLASH_HOME", str(home))
    monkeypatch.setenv("CHATARCH_HOME", str(arch_home))
    runner = CliRunner()
    assert runner.invoke(main, ["init", "-y"]).exit_code == 0

    result = runner.invoke(
        main,
        [
            "config",
            "set",
            "--subscription-url",
            "https://subscribe.example.test/secret-token",
            "--proxy-auth",
            "user:secret-pass",
            "--subconverter-url",
            "http://127.0.0.1:25500",
        ],
    )
    assert result.exit_code == 0, result.output

    show = runner.invoke(main, ["subscription", "status"])
    assert show.exit_code == 0, show.output
    assert "secret-token" not in show.output
    assert "secret-pass" not in show.output
    assert "subscription_url: present" in show.output
    assert "proxy_auth: present" in show.output
    assert "subconverter_url: http://127.0.0.1:25500" in show.output
    env_file = arch_home / "envs" / "chatclash" / ".env"
    assert env_file.exists()
    env_text = env_file.read_text(encoding="utf-8")
    assert "CHATCLASH_SUBSCRIPTION_URL='https://subscribe.example.test/secret-token'" in env_text
    assert "CHATCLASH_PROXY_AUTH='user:secret-pass'" in env_text
    assert "CHATCLASH_SUBCONVERTER_URL='http://127.0.0.1:25500'" in env_text
    local = yaml.safe_load((home / "config.yaml").read_text(encoding="utf-8"))
    assert "subscription_url" not in local
    assert "proxy_auth" not in local
    assert "subconverter_url" not in local


class _DirectClashYamlHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 - stdlib API name
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

    def log_message(self, format, *args):  # noqa: A002 - stdlib API name
        return


def test_update_fetches_direct_clash_yaml_preserves_auth_and_writes_backup(tmp_path, monkeypatch):
    home = tmp_path / "chatclash-home"
    arch_home = tmp_path / "chatarch-home"
    monkeypatch.setenv("CHATCLASH_HOME", str(home))
    monkeypatch.setenv("CHATARCH_HOME", str(arch_home))
    server = HTTPServer(("127.0.0.1", 0), _DirectClashYamlHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    runner = CliRunner()
    try:
        assert runner.invoke(main, ["init", "-y"]).exit_code == 0
        result = runner.invoke(
            main,
            [
                "config",
                "set",
                "--subscription-url",
                f"http://127.0.0.1:{server.server_port}/clash.yaml",
                "--proxy-auth",
                "user:secret-pass",
            ],
        )
        assert result.exit_code == 0, result.output

        update = runner.invoke(main, ["subscription", "update", "--no-validate", "-y"])
    finally:
        server.shutdown()
        thread.join(timeout=5)

    assert update.exit_code == 0, update.output
    assert "update=OK" in update.output
    clash_config = yaml.safe_load((home / "clash" / "config.yaml").read_text(encoding="utf-8"))
    assert clash_config["authentication"] == ["user:secret-pass"]
    assert clash_config["port"] == 7890
    assert clash_config["socks-port"] == 7891
    assert clash_config["external-controller"] == ":9090"
    assert clash_config["proxies"][0]["name"] == "direct-node"
    assert list((home / "clash" / "backups").glob("config.yaml.*.bak"))



def legacy_test_service_commands_support_dry_run(tmp_path, monkeypatch):
    home = tmp_path / "chatclash-home"
    monkeypatch.setenv("CHATCLASH_HOME", str(home))
    runner = CliRunner()
    assert runner.invoke(main, ["init", "-y"]).exit_code == 0

    up = runner.invoke(main, ["up", "--dry-run"])
    assert up.exit_code == 0, up.output
    assert str(home / "bin" / "mihomo") in up.output
    assert "docker compose" not in up.output
    assert "dry-run only" in up.output

    for command in ("down", "restart", "logs"):
        result = runner.invoke(main, [command, "--dry-run"])
        assert result.exit_code == 0, result.output
        assert "docker compose" not in result.output
        assert "dry-run only" in result.output


def legacy_test_verify_and_ip_api_support_dry_run(tmp_path, monkeypatch):
    home = tmp_path / "chatclash-home"
    monkeypatch.setenv("CHATCLASH_HOME", str(home))
    runner = CliRunner()
    assert runner.invoke(main, ["init", "-y"]).exit_code == 0

    verify = runner.invoke(main, ["verify", "--dry-run"])
    assert verify.exit_code == 0, verify.output
    assert "127.0.0.1:7890" in verify.output
    assert "dry-run only" in verify.output

    ip_api = runner.invoke(main, ["ip-api", "--dry-run"])
    assert ip_api.exit_code == 0, ip_api.output
    assert "ip-api.com" in ip_api.output
    assert "dry-run only" in ip_api.output



def legacy_test_engine_install_dry_run_selects_mihomo_binary_target(tmp_path, monkeypatch):
    home = tmp_path / "chatclash-home"
    monkeypatch.setenv("CHATCLASH_HOME", str(home))
    runner = CliRunner()
    assert runner.invoke(main, ["init", "-y"]).exit_code == 0

    result = runner.invoke(main, ["engine", "install", "--dry-run"])

    assert result.exit_code == 0, result.output
    assert "mihomo" in result.output
    assert str(home / "bin" / "mihomo") in result.output
    assert "dry-run only" in result.output
    assert not (home / "bin" / "mihomo").exists()



def test_check_group_aliases_verify_and_ip_api(tmp_path, monkeypatch):
    home = tmp_path / "chatclash-home"
    arch_home = tmp_path / "chatarch-home"
    monkeypatch.setenv("CHATCLASH_HOME", str(home))
    monkeypatch.setenv("CHATARCH_HOME", str(arch_home))
    runner = CliRunner()
    assert runner.invoke(main, ["init", "-y"]).exit_code == 0

    proxy = runner.invoke(main, ["check", "proxy", "--dry-run"])
    assert proxy.exit_code == 0, proxy.output
    assert "127.0.0.1:7890" in proxy.output
    assert "dry-run only" in proxy.output

    ip = runner.invoke(main, ["check", "ip", "--dry-run"])
    assert ip.exit_code == 0, ip.output
    assert "ip-api.com" in ip.output
    assert "dry-run only" in ip.output



def test_subscription_set_status_and_update_are_the_main_subscription_path(tmp_path, monkeypatch):
    home = tmp_path / "chatclash-home"
    arch_home = tmp_path / "chatarch-home"
    monkeypatch.setenv("CHATCLASH_HOME", str(home))
    monkeypatch.setenv("CHATARCH_HOME", str(arch_home))
    monkeypatch.setenv("CLASH_SUB_URL", "https://subscribe.example.test/secret-token")
    monkeypatch.setenv("CLASH_PROXY_AUTH", "user:secret-pass")
    runner = CliRunner()
    assert runner.invoke(main, ["init", "-y"]).exit_code == 0

    result = runner.invoke(
        main,
        [
            "subscription",
            "set",
            "--url-env",
            "CLASH_SUB_URL",
            "--proxy-auth-env",
            "CLASH_PROXY_AUTH",
            "--subconverter-url",
            "http://127.0.0.1:25500",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "CHATCLASH_SUBSCRIPTION_URL" in result.output
    assert "secret-token" not in result.output
    status = runner.invoke(main, ["subscription", "status"])
    assert status.exit_code == 0, status.output
    assert "subscription_url: present" in status.output
    assert "proxy_auth: present" in status.output
    assert "secret-token" not in status.output
    local = yaml.safe_load((home / "config.yaml").read_text(encoding="utf-8"))
    assert "subscription_url" not in local
    assert "proxy_auth" not in local


def test_mihomo_group_owns_install_runtime_and_autostart_options(tmp_path, monkeypatch):
    home = tmp_path / "chatclash-home"
    monkeypatch.setenv("CHATCLASH_HOME", str(home))
    runner = CliRunner()
    assert runner.invoke(main, ["init", "-y"]).exit_code == 0

    install = runner.invoke(main, ["mihomo", "install", "--daemon", "--dry-run"])
    assert install.exit_code == 0, install.output
    assert str(home / "bin" / "mihomo") in install.output
    assert "daemon: install" in install.output
    assert "dry-run only" in install.output

    for command in ("start", "stop", "restart", "logs"):
        result = runner.invoke(main, ["mihomo", command, "--dry-run"])
        assert result.exit_code == 0, result.output
        assert "dry-run only" in result.output
        assert "docker compose" not in result.output

    update = runner.invoke(main, ["mihomo", "update", "--dry-run"])
    assert update.exit_code == 0, update.output
    assert "update: mihomo binary" in update.output

    uninstall = runner.invoke(main, ["mihomo", "uninstall", "--daemon", "--dry-run"])
    assert uninstall.exit_code == 0, uninstall.output
    assert "daemon: uninstall" in uninstall.output


def test_top_level_status_summarizes_single_machine_state(tmp_path, monkeypatch):
    home = tmp_path / "chatclash-home"
    arch_home = tmp_path / "chatarch-home"
    monkeypatch.setenv("CHATCLASH_HOME", str(home))
    monkeypatch.setenv("CHATARCH_HOME", str(arch_home))
    monkeypatch.setenv("CLASH_SUB_URL", "https://subscribe.example.test/secret-token")
    runner = CliRunner()
    assert runner.invoke(main, ["init", "-y"]).exit_code == 0
    assert runner.invoke(main, ["subscription", "set", "--url-env", "CLASH_SUB_URL"]).exit_code == 0

    result = runner.invoke(main, ["status"])

    assert result.exit_code == 0, result.output
    assert f"ChatClash home: {home}" in result.output
    assert "mihomo installed: no" in result.output
    assert "subscription set: yes" in result.output
    assert "http proxy: http://127.0.0.1:7890" in result.output
    assert "secret-token" not in result.output


def test_proxy_show_and_env_use_http_and_socks_ports(tmp_path, monkeypatch):
    home = tmp_path / "chatclash-home"
    monkeypatch.setenv("CHATCLASH_HOME", str(home))
    runner = CliRunner()
    assert runner.invoke(main, ["init", "-y"]).exit_code == 0

    show = runner.invoke(main, ["proxy", "show"])
    assert show.exit_code == 0, show.output
    assert "HTTP proxy: http://127.0.0.1:7890" in show.output
    assert "SOCKS proxy: socks5://127.0.0.1:7891" in show.output

    env = runner.invoke(main, ["proxy", "env"])
    assert env.exit_code == 0, env.output
    assert "export http_proxy=http://127.0.0.1:7890" in env.output
    assert "export https_proxy=http://127.0.0.1:7890" in env.output
    assert "export all_proxy=socks5://127.0.0.1:7891" in env.output



def test_usable_ports_are_chatenv_backed_not_local_config(tmp_path, monkeypatch):
    home = tmp_path / "chatclash-home"
    arch_home = tmp_path / "chatarch-home"
    monkeypatch.setenv("CHATCLASH_HOME", str(home))
    monkeypatch.setenv("CHATARCH_HOME", str(arch_home))
    runner = CliRunner()

    result = runner.invoke(
        main,
        [
            "init",
            "--http-port",
            "18090",
            "--socks-port",
            "18091",
            "--controller-port",
            "19090",
            "-y",
        ],
    )

    assert result.exit_code == 0, result.output
    env_text = (arch_home / "envs" / "chatclash" / ".env").read_text(encoding="utf-8")
    assert "CHATCLASH_HTTP_PORT='18090'" in env_text
    assert "CHATCLASH_SOCKS_PORT='18091'" in env_text
    assert "CHATCLASH_CONTROLLER_PORT='19090'" in env_text
    local = yaml.safe_load((home / "config.yaml").read_text(encoding="utf-8"))
    assert "http_port" not in local
    assert "socks_port" not in local
    assert "controller_port" not in local

    status = runner.invoke(main, ["status"])
    assert status.exit_code == 0, status.output
    assert "http proxy: http://127.0.0.1:18090" in status.output
    assert "socks proxy: socks5://127.0.0.1:18091" in status.output

    env = runner.invoke(main, ["proxy", "env"])
    assert env.exit_code == 0, env.output
    assert "export http_proxy=http://127.0.0.1:18090" in env.output
    assert "export all_proxy=socks5://127.0.0.1:18091" in env.output


def test_subscription_set_uses_chatstyle_interactive_flags_and_can_update_chatenv_ports(tmp_path, monkeypatch):
    home = tmp_path / "chatclash-home"
    arch_home = tmp_path / "chatarch-home"
    monkeypatch.setenv("CHATCLASH_HOME", str(home))
    monkeypatch.setenv("CHATARCH_HOME", str(arch_home))
    runner = CliRunner()
    assert runner.invoke(main, ["init", "-y"]).exit_code == 0

    result = runner.invoke(
        main,
        [
            "subscription",
            "set",
            "-I",
            "--http-port",
            "28090",
            "--socks-port",
            "28091",
            "--controller-port",
            "29090",
            "--fetch-proxy",
            "local",
        ],
    )

    assert result.exit_code == 0, result.output
    env_text = (arch_home / "envs" / "chatclash" / ".env").read_text(encoding="utf-8")
    assert "CHATCLASH_HTTP_PORT='28090'" in env_text
    assert "CHATCLASH_SOCKS_PORT='28091'" in env_text
    assert "CHATCLASH_CONTROLLER_PORT='29090'" in env_text
    assert "CHATCLASH_SUBSCRIPTION_FETCH_PROXY='local'" in env_text
    assert "secret-token" not in env_text
    assert "CHATCLASH_SUBSCRIPTION_URL='https" not in env_text



def test_masked_fetch_proxy_does_not_print_proxy_auth(tmp_path, monkeypatch):
    from chatclash.cli import _mask

    assert _mask("http://cube:secret-pass@127.0.0.1:7890") == "http://***@127.0.0.1:7890"



def test_chatenv_schema_has_all_operator_config_fields():
    from chatclash.config import ChatClashConfig

    fields = {field.env_key: field for field in ChatClashConfig.get_fields().values()}
    assert fields["CHATCLASH_SUBSCRIPTION_URL"].is_sensitive is True
    assert fields["CHATCLASH_PROXY_AUTH"].is_sensitive is True
    for key in (
        "CHATCLASH_SUBCONVERTER_URL",
        "CHATCLASH_SUBSCRIPTION_FETCH_PROXY",
        "CHATCLASH_HTTP_PORT",
        "CHATCLASH_SOCKS_PORT",
        "CHATCLASH_CONTROLLER_PORT",
    ):
        assert key in fields
    ChatClashConfig.test()
