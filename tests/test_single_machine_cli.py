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
    assert saved["http_port"] == 7890
    assert "subscription_url" not in saved


def test_config_set_and_show_masks_sensitive_values(tmp_path, monkeypatch):
    home = tmp_path / "chatclash-home"
    monkeypatch.setenv("CHATCLASH_HOME", str(home))
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

    show = runner.invoke(main, ["config", "show"])
    assert show.exit_code == 0, show.output
    assert "secret-token" not in show.output
    assert "secret-pass" not in show.output
    assert "subscription_url: present" in show.output
    assert "proxy_auth: present" in show.output
    assert "subconverter_url: http://127.0.0.1:25500" in show.output


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
    monkeypatch.setenv("CHATCLASH_HOME", str(home))
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

        update = runner.invoke(main, ["update", "--no-validate", "-y"])
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



def test_service_commands_support_dry_run(tmp_path, monkeypatch):
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


def test_verify_and_ip_api_support_dry_run(tmp_path, monkeypatch):
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



def test_engine_install_dry_run_selects_mihomo_binary_target(tmp_path, monkeypatch):
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
