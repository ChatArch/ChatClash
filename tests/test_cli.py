from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import yaml
from click.testing import CliRunner

from chatclash.cli import main


def test_setup_clash_dry_run_does_not_write(tmp_path):
    target = tmp_path / "clash"
    result = CliRunner().invoke(main, ["setup", "clash", str(target), "--dry-run"])

    assert result.exit_code == 0
    assert "dry-run only" in result.output
    assert not target.exists()


def test_setup_clash_generates_compose_and_placeholder_config(tmp_path):
    target = tmp_path / "clash"
    result = CliRunner().invoke(main, ["setup", "clash", str(target), "-y"])

    assert result.exit_code == 0
    assert (target / "docker-compose.yaml").exists()
    assert (target / "config.yaml").exists()
    assert (target / "ui").is_dir()
    assert (target / "backups").is_dir()

    compose = yaml.safe_load((target / "docker-compose.yaml").read_text())
    config = yaml.safe_load((target / "config.yaml").read_text())
    assert set(compose["services"]) == {"clash", "yacd"}
    assert config["port"] == 7890
    assert config["socks-port"] == 7891
    assert config["rules"] == ["MATCH,DIRECT"]
    assert not (target / "chatclash.toml").exists()


def test_setup_clash_requires_confirmation_before_overwrite(tmp_path):
    target = tmp_path / "clash"
    target.mkdir()
    (target / "docker-compose.yaml").write_text("existing: compose\n", encoding="utf-8")

    result = CliRunner().invoke(main, ["setup", "clash", str(target)], input="n\n")

    assert result.exit_code != 0
    assert "already exists" in result.output
    assert (target / "docker-compose.yaml").read_text(encoding="utf-8") == "existing: compose\n"


def test_setup_clash_requires_confirmation_for_srv_clash():
    result = CliRunner().invoke(main, ["setup", "clash", "/srv/clash"], input="n\n")

    assert result.exit_code != 0
    assert "/srv/clash is a real service directory" in result.output


def test_status_prints_redacted_summary_not_raw_proxy_details(tmp_path):
    target = tmp_path / "clash"
    CliRunner().invoke(main, ["setup", "clash", str(target), "-y"])

    result = CliRunner().invoke(main, ["status", str(target)])

    assert result.exit_code == 0
    assert "docker-compose.yaml: present" in result.output
    assert "proxies: 0" in result.output
    assert "external-controller: :9090" in result.output
    assert "password" not in result.output.lower()


def test_proxy_env_outputs_shell_exports():
    result = CliRunner().invoke(main, ["proxy", "env"])

    assert result.exit_code == 0
    assert "export http_proxy=http://127.0.0.1:7890" in result.output
    assert "export all_proxy=socks5://127.0.0.1:7891" in result.output
    assert "export no_proxy=localhost,127.0.0.1,::1" in result.output


def test_sub_status_masks_subscription_env(monkeypatch):
    monkeypatch.setenv("CHATCLASH_SUBSCRIPTION_URL", "https://example.test/sub-token")
    monkeypatch.setenv("CHATCLASH_SUBCONVERTER_URL", "http://127.0.0.1:25500")

    result = CliRunner().invoke(main, ["sub", "status"])

    assert result.exit_code == 0
    assert "https://example.test/..." in result.output
    assert "sub-token" not in result.output
    assert "http://127.0.0.1:25500" in result.output


def test_sub_url_redacts_positional_subscription():
    subscription = "https://subscribe.example.test/secret-token"
    result = CliRunner().invoke(
        main,
        [
            "sub",
            "url",
            subscription,
            "-s",
            "http://127.0.0.1:25500",
            "-I",
        ],
    )

    assert result.exit_code == 0
    assert "target=clash" in result.output
    assert "secret-token" not in result.output
    assert "subscribe.example.test" not in result.output


def test_sub_url_missing_values_fails_non_interactive(tmp_path, monkeypatch):
    monkeypatch.setenv("CHATARCH_HOME", str(tmp_path / "chatarch-home"))
    monkeypatch.delenv("CHATCLASH_SUBSCRIPTION_URL", raising=False)
    monkeypatch.delenv("CHATCLASH_SUBCONVERTER_URL", raising=False)

    result = CliRunner().invoke(main, ["sub", "url", "-I"])

    assert result.exit_code != 0
    assert "Missing subscription URL" in result.output


def test_sub_generate_dry_run_does_not_write(tmp_path):
    output = tmp_path / "config.yaml"
    result = CliRunner().invoke(
        main,
        [
            "sub",
            "generate",
            "https://subscribe.example.test/secret-token",
            "-s",
            "http://127.0.0.1:25500",
            "-o",
            str(output),
            "--dry-run",
            "-I",
        ],
    )

    assert result.exit_code == 0
    assert "dry-run only" in result.output
    assert "secret-token" not in result.output
    assert not output.exists()


class _SubconverterHandler(BaseHTTPRequestHandler):
    seen_path = ""

    def do_GET(self):  # noqa: N802 - stdlib API name
        type(self).seen_path = self.path
        body = """\
proxies:
  - name: local-direct
    type: http
    server: 127.0.0.1
    port: 8080
proxy-groups:
  - name: Proxy
    type: select
    proxies:
      - local-direct
rules:
  - MATCH,Proxy
"""
        self.send_response(200)
        self.send_header("Content-Type", "text/yaml; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def log_message(self, format, *args):  # noqa: A002 - stdlib API name
        return


def test_sub_generate_fetches_subconverter_writes_config_and_backup(tmp_path):
    server = HTTPServer(("127.0.0.1", 0), _SubconverterHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    output = tmp_path / "config.yaml"
    output.write_text("old: config\n", encoding="utf-8")
    subscription = "https://subscribe.example.test/secret-token"

    try:
        result = CliRunner().invoke(
            main,
            [
                "sub",
                "generate",
                subscription,
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
    assert parsed["port"] == 7890
    assert parsed["socks-port"] == 7891
    assert parsed["proxies"][0]["name"] == "local-direct"
    assert list((tmp_path / "backups").glob("config.yaml.*.bak"))
    assert _SubconverterHandler.seen_path.startswith("/sub?")


def test_top_level_version_works():
    result = CliRunner().invoke(main, ["--version"])

    assert result.exit_code == 0
    assert "0.1.0" in result.output
