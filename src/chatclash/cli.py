"""CLI entrypoint for chatclash."""

from __future__ import annotations

import datetime as _dt
import os
import shutil
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import click
import yaml
from chatenv import BaseEnvConfig, EnvStore, get_paths
from chatstyle import (
    CommandField,
    CommandSchema,
    add_interactive_option,
    render_success,
    render_warning,
    resolve_command_inputs,
)

from .config import ChatClashConfig


DEFAULT_CLASH_DIR = Path("/tmp/clash")
DEFAULT_HTTP_PORT = 7890
DEFAULT_SOCKS_PORT = 7891
DEFAULT_CONTROLLER_PORT = 7900
DEFAULT_YACD_PORT = 9135
DEFAULT_CLASH_IMAGE = "dreamacro/clash"
DEFAULT_YACD_IMAGE = "haishanh/yacd:master"
DEFAULT_PROXY_URL = "http://127.0.0.1:7890"
DEFAULT_CONFIG_URL = (
    "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/config/"
    "ACL4SSR_Online.ini"
)


def _chatclash_home() -> Path:
    """Return this machine's ChatClash home directory."""

    return Path(os.getenv("CHATCLASH_HOME") or (Path.home() / ".chatarch" / "chatclash"))


def _local_config_path() -> Path:
    return _chatclash_home() / "config.yaml"


def _default_local_config(*, home: Path | None = None) -> dict[str, Any]:
    root = home or _chatclash_home()
    clash_dir = root / "clash"
    return {
        "home": str(root),
        "clash_dir": str(clash_dir),
        "http_port": DEFAULT_HTTP_PORT,
        "socks_port": DEFAULT_SOCKS_PORT,
        "controller_port": DEFAULT_CONTROLLER_PORT,
        "yacd_port": DEFAULT_YACD_PORT,
        "clash_image": DEFAULT_CLASH_IMAGE,
        "yacd_image": DEFAULT_YACD_IMAGE,
        "fetch_mode": "direct-clash-yaml",
        "engine": "binary",
        "engine_path": str(root / "bin" / "mihomo"),
        "pid_file": str(root / "run" / "mihomo.pid"),
        "log_file": str(root / "logs" / "mihomo.log"),
    }


def _read_local_config() -> dict[str, Any]:
    path = _local_config_path()
    config = _default_local_config(home=path.parent)
    if path.exists():
        loaded = _load_yaml_file(path)
        config.update(loaded)
    return config


def _write_local_config(config: dict[str, Any]) -> None:
    path = _local_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(config, sort_keys=False, allow_unicode=False), encoding="utf-8")
    path.chmod(0o600)


def _clash_dir_from_local(config: dict[str, Any]) -> Path:
    return Path(str(config.get("clash_dir") or (_chatclash_home() / "clash")))


def _looks_like_clash_yaml(text: str) -> bool:
    return ("proxies:" in text or "proxy-providers:" in text) and (
        "proxy-groups:" in text or "rules:" in text
    )


def _extract_clash_body(text: str) -> str:
    """Return Clash YAML body without remote header keys."""

    markers = ("proxy-providers:", "proxies:", "proxy-groups:", "rule-providers:", "rules:")
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.strip() in markers and not line.startswith((" ", "\t")):
            return "\n".join(lines[index:]) + "\n"
    return text


def _load_chatenv() -> None:
    BaseEnvConfig.load_all(get_paths().envs_dir)


def _subscription_url() -> str | None:
    _load_chatenv()
    return os.getenv("CHATCLASH_SUBSCRIPTION_URL") or str(
        ChatClashConfig.CHATCLASH_SUBSCRIPTION_URL.value or ""
    )


def _subconverter_url() -> str | None:
    _load_chatenv()
    return os.getenv("CHATCLASH_SUBCONVERTER_URL") or str(
        ChatClashConfig.CHATCLASH_SUBCONVERTER_URL.value or ""
    )


def _proxy_auth() -> str | None:
    _load_chatenv()
    return os.getenv("CHATCLASH_PROXY_AUTH") or str(
        ChatClashConfig.CHATCLASH_PROXY_AUTH.value or ""
    )


def _write_chatclash_env(*, subscription_url: str | None = None, proxy_auth: str | None = None, subconverter_url: str | None = None) -> list[str]:
    """Persist ChatClash variables through ChatEnv's explicit store API."""

    paths = get_paths()
    store = EnvStore(paths.envs_dir)
    values = store.load_active(ChatClashConfig)
    changed: list[str] = []
    if subscription_url is not None:
        values["CHATCLASH_SUBSCRIPTION_URL"] = subscription_url
        changed.append("CHATCLASH_SUBSCRIPTION_URL")
    if proxy_auth is not None:
        values["CHATCLASH_PROXY_AUTH"] = proxy_auth
        changed.append("CHATCLASH_PROXY_AUTH")
    if subconverter_url is not None:
        values["CHATCLASH_SUBCONVERTER_URL"] = subconverter_url
        changed.append("CHATCLASH_SUBCONVERTER_URL")
    if changed:
        store.save_active(ChatClashConfig, values)
        _load_chatenv()
    return changed


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def _mask(value: str | None) -> str:
    value = _clean(value)
    if not value:
        return "<not set>"
    if len(value) <= 12:
        return "***"
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme and parsed.netloc:
        host = parsed.netloc
        return f"{parsed.scheme}://{host}/...{value[-6:]}"
    return f"{value[:4]}...{value[-4:]}"


def _redact_text(text: str, *extra_secrets: str | None) -> str:
    for value in (_subscription_url(), _proxy_auth(), *extra_secrets):
        value = _clean(value)
        if value:
            text = text.replace(value, _mask(value))
            text = text.replace(urllib.parse.quote(value, safe=""), "<subscription-url>")
            text = text.replace(urllib.parse.quote_plus(value), "<subscription-url>")
    return text


def _compose_yaml(
    *,
    http_port: int,
    socks_port: int,
    controller_port: int,
    yacd_port: int,
    clash_image: str,
    yacd_image: str,
) -> str:
    data = {
        "version": "3",
        "services": {
            "clash": {
                "image": clash_image,
                "container_name": "clash",
                "restart": "unless-stopped",
                "ports": [
                    f"{http_port}:{http_port}",
                    f"{socks_port}:{socks_port}",
                    f"{controller_port}:9090",
                ],
                "volumes": ["./config.yaml:/root/.config/clash/config.yaml:ro"],
            },
            "yacd": {
                "image": yacd_image,
                "container_name": "yacd",
                "restart": "unless-stopped",
                "ports": [f"{yacd_port}:80"],
            },
        },
    }
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=False)


def _config_header(
    *,
    http_port: int = DEFAULT_HTTP_PORT,
    socks_port: int = DEFAULT_SOCKS_PORT,
    controller_port: int = DEFAULT_CONTROLLER_PORT,
    auth: str | None = None,
) -> dict[str, Any]:
    header: dict[str, Any] = {
        "port": http_port,
        "socks-port": socks_port,
        "allow-lan": True,
        "mode": "Rule",
        "log-level": "info",
        "external-controller": f":{controller_port}",
    }
    if _clean(auth):
        header["authentication"] = [auth]
    return header


def _placeholder_config(*, http_port: int, socks_port: int, auth: str | None) -> str:
    data = _config_header(http_port=http_port, socks_port=socks_port, auth=auth)
    data.update(
        {
            "proxies": [],
            "proxy-groups": [
                {
                    "name": "AUTO",
                    "type": "select",
                    "proxies": ["DIRECT"],
                }
            ],
            "rules": ["MATCH,DIRECT"],
        }
    )
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=False)


def _load_yaml_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    content = path.read_text(encoding="utf-8")
    if not content.strip():
        return {}
    loaded = yaml.safe_load(content)
    return loaded if isinstance(loaded, dict) else {}


def _counts(config: dict[str, Any]) -> tuple[int, int, int]:
    return (
        len(config.get("proxies") or []),
        len(config.get("proxy-groups") or []),
        len(config.get("rules") or []),
    )


def _sensitive_path(path: Path) -> bool:
    try:
        return path.resolve().is_relative_to(Path("/srv/clash"))
    except AttributeError:  # pragma: no cover - py310 compatibility guard
        resolved = str(path.resolve())
        return resolved == "/srv/clash" or resolved.startswith("/srv/clash/")


def _confirm_write(path: Path, *, yes: bool, reason: str) -> None:
    if yes:
        return
    if not click.confirm(f"{reason}. Continue?", default=False):
        raise click.Abort()


def _backup_existing(path: Path) -> Path | None:
    if not path.exists():
        return None
    backup_dir = path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    target = backup_dir / f"{path.name}.{stamp}.bak"
    shutil.copy2(path, target)
    return target


def _build_subconverter_url(
    subscription_url: str,
    subconverter_url: str,
    config_url: str,
) -> str:
    base = subconverter_url.rstrip("/")
    query = urllib.parse.urlencode(
        {
            "target": "clash",
            "url": subscription_url,
            "insert": "false",
            "config": config_url,
            "emoji": "true",
            "list": "false",
            "tfo": "false",
            "scv": "false",
            "fdn": "false",
            "sort": "false",
            "new_name": "true",
        }
    )
    return f"{base}/sub?{query}"


def _fetch_url(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "chatclash/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:500]
        raise click.ClickException(
            _redact_text(f"subconverter request failed: HTTP {exc.code}: {body}")
        ) from exc
    except urllib.error.URLError as exc:
        raise click.ClickException(
            _redact_text(f"subconverter request failed: {exc.reason}")
        ) from exc


def _merge_header(converted_yaml: str) -> tuple[str, dict[str, Any]]:
    header = yaml.safe_dump(_config_header(), sort_keys=False, allow_unicode=False)
    content = f"{header}\n{converted_yaml.lstrip()}"
    try:
        parsed = yaml.safe_load(content)
    except yaml.YAMLError as exc:
        raise click.ClickException(f"subconverter returned invalid YAML: {exc}") from exc
    if not isinstance(parsed, dict):
        raise click.ClickException("subconverter returned invalid Clash config YAML")
    return content, parsed


SUB_INPUT_SCHEMA = CommandSchema(
    name="sub-input",
    fields=(
        CommandField(
            "subscription_url",
            prompt="Subscription URL",
            required=True,
            sensitive=True,
            default_factory=_subscription_url,
            missing_message=(
                "Missing subscription URL. Configure CHATCLASH_SUBSCRIPTION_URL "
                "with chatenv or pass SUBSCRIPTION_URL."
            ),
        ),
        CommandField(
            "subconverter_url",
            prompt="subconverter URL",
            required=True,
            default_factory=_subconverter_url,
            missing_message=(
                "Missing subconverter URL. Configure CHATCLASH_SUBCONVERTER_URL "
                "with chatenv or pass -s/--subconverter-url."
            ),
        ),
    ),
)


def _run_shell(command: list[str], *, cwd: Path | None = None) -> str:
    import subprocess

    proc = subprocess.run(command, cwd=str(cwd) if cwd else None, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if proc.returncode != 0:
        raise click.ClickException(proc.stdout.strip() or f"command failed: {' '.join(command)}")
    return proc.stdout


def _docker_compose_command(clash_dir: Path, *args: str) -> list[str]:
    compose_file = clash_dir / "docker-compose.yaml"
    return ["docker", "compose", "-f", str(compose_file), *args]


def _local_proxy_url(config: dict[str, Any]) -> str:
    auth = _proxy_auth()
    port = int(config.get("http_port") or DEFAULT_HTTP_PORT)
    if auth:
        return f"http://{auth}@127.0.0.1:{port}"
    return f"http://127.0.0.1:{port}"


def _masked_proxy_url(config: dict[str, Any]) -> str:
    port = int(config.get("http_port") or DEFAULT_HTTP_PORT)
    if _clean(_proxy_auth()):
        return f"http://***@127.0.0.1:{port}"
    return f"http://127.0.0.1:{port}"


def _curl_head(proxy_url: str, url: str, timeout: int) -> str:
    return _run_shell(["curl", "-sS", "-m", str(timeout), "--proxy", proxy_url, "-I", url])


def _curl_get(proxy_url: str, url: str, timeout: int) -> str:
    return _run_shell(["curl", "-sS", "-m", str(timeout), "--proxy", proxy_url, url])



def _engine_path(config: dict[str, Any]) -> Path:
    return Path(str(config.get("engine_path") or (_chatclash_home() / "bin" / "mihomo")))


def _pid_file(config: dict[str, Any]) -> Path:
    return Path(str(config.get("pid_file") or (_chatclash_home() / "run" / "mihomo.pid")))


def _log_file(config: dict[str, Any]) -> Path:
    return Path(str(config.get("log_file") or (_chatclash_home() / "logs" / "mihomo.log")))


def _http_proxy_url(config: dict[str, Any], *, host: str = "127.0.0.1") -> str:
    return f"http://{host}:{int(config.get('http_port') or DEFAULT_HTTP_PORT)}"


def _socks_proxy_url(config: dict[str, Any], *, host: str = "127.0.0.1") -> str:
    return f"socks5://{host}:{int(config.get('socks_port') or DEFAULT_SOCKS_PORT)}"


def _daemon_unit_path() -> Path:
    return Path.home() / ".config" / "systemd" / "user" / "chatclash-mihomo.service"


def _daemon_unit_text(config: dict[str, Any]) -> str:
    return "\n".join([
        "[Unit]",
        "Description=ChatClash Mihomo proxy service",
        "After=network-online.target",
        "",
        "[Service]",
        f"ExecStart={_engine_path(config)} -d {_clash_dir_from_local(config)}",
        "Restart=on-failure",
        f"WorkingDirectory={_clash_dir_from_local(config)}",
        "",
        "[Install]",
        "WantedBy=default.target",
        "",
    ])


def _systemctl_user(*args: str, check: bool = True) -> str:
    import subprocess

    result = subprocess.run(
        ["systemctl", "--user", *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if check and result.returncode != 0:
        raise click.ClickException(result.stdout.strip() or f"systemctl --user {' '.join(args)} failed")
    return result.stdout


def _install_daemon_unit(config: dict[str, Any]) -> Path:
    unit = _daemon_unit_path()
    unit.parent.mkdir(parents=True, exist_ok=True)
    unit.write_text(_daemon_unit_text(config), encoding="utf-8")
    _systemctl_user("daemon-reload")
    _systemctl_user("enable", unit.name)
    return unit


def _remove_daemon_unit() -> Path:
    unit = _daemon_unit_path()
    if unit.exists():
        _systemctl_user("disable", unit.name, check=False)
        _systemctl_user("stop", unit.name, check=False)
        unit.unlink(missing_ok=True)
        _systemctl_user("daemon-reload", check=False)
    return unit


def _daemon_unit_active() -> bool:
    if not _daemon_unit_path().exists():
        return False
    try:
        _systemctl_user("is-active", "--quiet", _daemon_unit_path().name)
        return True
    except click.ClickException:
        return False


def _pid_running(pid_file: Path) -> bool:
    if not pid_file.exists():
        return False
    pid = pid_file.read_text(encoding="utf-8").strip()
    if not pid:
        return False
    return Path(f"/proc/{pid}").exists()


def _show_single_machine_status() -> None:
    config = _read_local_config()
    engine = _engine_path(config)
    clash_config = _clash_dir_from_local(config) / "config.yaml"
    pid_file = _pid_file(config)
    click.echo(f"ChatClash home: {_chatclash_home()}")
    click.echo(f"mihomo installed: {'yes' if engine.exists() else 'no'}")
    click.echo(f"mihomo running: {'yes' if (_daemon_unit_active() or _pid_running(pid_file)) else 'no'}")
    click.echo(f"mihomo autostart: {'enabled' if _daemon_unit_path().exists() else 'disabled'}")
    click.echo(f"subscription set: {'yes' if _clean(_subscription_url()) else 'no'}")
    click.echo(f"proxy auth set: {'yes' if _clean(_proxy_auth()) else 'no'}")
    click.echo(f"config exists: {'yes' if clash_config.exists() else 'no'}")
    click.echo(f"http proxy: {_http_proxy_url(config)}")
    click.echo(f"socks proxy: {_socks_proxy_url(config)}")
    backups = list((_clash_dir_from_local(config) / "backups").glob("config.yaml.*.bak")) if (_clash_dir_from_local(config) / "backups").exists() else []
    click.echo(f"backups: {len(backups)}")


@click.group()
def main() -> None:
    """ChatArch CLI for Clash, subconverter, and proxy operations."""


@main.command(name="init")
@click.option("--home", type=click.Path(path_type=Path, file_okay=False, dir_okay=True), default=None)
@click.option("--clash-dir", type=click.Path(path_type=Path, file_okay=False, dir_okay=True), default=None)
@click.option("--http-port", default=DEFAULT_HTTP_PORT, show_default=True, type=int)
@click.option("--socks-port", default=DEFAULT_SOCKS_PORT, show_default=True, type=int)
@click.option("--controller-port", default=DEFAULT_CONTROLLER_PORT, show_default=True, type=int)
@click.option("--yacd-port", default=DEFAULT_YACD_PORT, show_default=True, type=int)
@click.option("--clash-image", default=DEFAULT_CLASH_IMAGE, show_default=True)
@click.option("--yacd-image", default=DEFAULT_YACD_IMAGE, show_default=True)
@click.option("--dry-run", is_flag=True, help="Show the init plan without writing.")
@click.option("-y", "--yes", is_flag=True, help="Skip write confirmations.")
def init_command(
    home: Path | None,
    clash_dir: Path | None,
    http_port: int,
    socks_port: int,
    controller_port: int,
    yacd_port: int,
    clash_image: str,
    yacd_image: str,
    dry_run: bool,
    yes: bool,
) -> None:
    """Initialize this machine's ChatClash home and binary runtime layout."""

    root = home or _chatclash_home()
    target = clash_dir or (root / "clash")
    click.echo(f"home: {root}")
    click.echo(f"clash_dir: {target}")
    if dry_run:
        render_success("dry-run only; no files changed")
        return
    if _sensitive_path(target):
        _confirm_write(target, yes=yes, reason=f"{target} is a real service directory")
    root.mkdir(parents=True, exist_ok=True)
    (root / "bin").mkdir(exist_ok=True)
    (root / "run").mkdir(exist_ok=True)
    (root / "logs").mkdir(exist_ok=True)
    (root / "cache").mkdir(exist_ok=True)
    target.mkdir(parents=True, exist_ok=True)
    (target / "ui").mkdir(exist_ok=True)
    (target / "backups").mkdir(exist_ok=True)
    config_path = target / "config.yaml"
    if not config_path.exists():
        config_path.write_text(
            _placeholder_config(http_port=http_port, socks_port=socks_port, auth=None),
            encoding="utf-8",
        )
    _write_local_config(
        {
            "home": str(root),
            "clash_dir": str(target),
            "http_port": http_port,
            "socks_port": socks_port,
            "controller_port": controller_port,
            "yacd_port": yacd_port,
            "clash_image": clash_image,
            "yacd_image": yacd_image,
            "fetch_mode": "direct-clash-yaml",
            "engine": "binary",
            "engine_path": str(root / "bin" / "mihomo"),
            "pid_file": str(root / "run" / "mihomo.pid"),
            "log_file": str(root / "logs" / "mihomo.log"),
        }
    )
    render_success(f"initialized ChatClash home at {root}")



@main.group(name="subscription")
def subscription_group() -> None:
    """Configure and refresh this machine's subscription-backed config."""


@subscription_group.command(name="set")
@click.option("--url-env", default=None, help="Name of an environment variable containing the subscription URL.")
@click.option("--proxy-auth-env", default=None, help="Name of an environment variable containing user:password auth.")
@click.option("--subconverter-url-env", default=None, help="Name of an environment variable containing the subconverter URL.")
@click.option("--subscription-url", default=None, help="Subscription URL. Prefer --url-env to avoid shell history leaks.")
@click.option("--proxy-auth", default=None, help="Proxy auth. Prefer --proxy-auth-env to avoid shell history leaks.")
@click.option("--subconverter-url", default=None)
@click.option("-i", "--interactive", is_flag=True, help="Prompt for missing values when supported.")
def subscription_set(
    url_env: str | None,
    proxy_auth_env: str | None,
    subconverter_url_env: str | None,
    subscription_url: str | None,
    proxy_auth: str | None,
    subconverter_url: str | None,
    interactive: bool,
) -> None:
    """Store ChatClash subscription values through ChatEnv."""

    _ = interactive
    if url_env:
        subscription_url = os.getenv(url_env)
        if subscription_url is None:
            raise click.ClickException(f"environment variable not set: {url_env}")
    if proxy_auth_env:
        proxy_auth = os.getenv(proxy_auth_env)
        if proxy_auth is None:
            raise click.ClickException(f"environment variable not set: {proxy_auth_env}")
    if subconverter_url_env:
        subconverter_url = os.getenv(subconverter_url_env)
        if subconverter_url is None:
            raise click.ClickException(f"environment variable not set: {subconverter_url_env}")
    changed = _write_chatclash_env(
        subscription_url=subscription_url,
        proxy_auth=proxy_auth,
        subconverter_url=subconverter_url,
    )
    click.echo("updated: " + (", ".join(changed) if changed else "<none>"))


@subscription_group.command(name="status")
def subscription_status() -> None:
    """Show redacted subscription configuration state."""

    subscription = _subscription_url()
    proxy_auth = _proxy_auth()
    subconverter = _subconverter_url()
    click.echo(f"subscription_url: {'present' if _clean(subscription) else '<not set>'}")
    click.echo(f"proxy_auth: {'present' if _clean(proxy_auth) else '<not set>'}")
    click.echo(f"subconverter_url: {subconverter if _clean(subconverter) else '<not set>'}")


@subscription_group.command(name="update")
@click.option("--dry-run", is_flag=True, help="Show the update plan without writing.")
@click.option("--no-validate", is_flag=True, help="Skip Mihomo config validation.")
@click.option("-y", "--yes", is_flag=True, help="Skip write confirmations.")
def subscription_update(dry_run: bool, no_validate: bool, yes: bool) -> None:
    """Refresh this machine's Clash config from the configured subscription."""

    update_command.callback(dry_run=dry_run, no_validate=no_validate, yes=yes)


@main.group(name="mihomo")
def mihomo_group() -> None:
    """Install, run, update, and inspect the local Mihomo service."""


@mihomo_group.command(name="install")
@click.option("--repo", default="MetaCubeX/mihomo", show_default=True)
@click.option("--version", default="latest", show_default=True)
@click.option("--dry-run", is_flag=True)
@click.option("--force", is_flag=True)
@click.option("--daemon", is_flag=True, help="Also install user-level service/autostart metadata.")
def mihomo_install(repo: str, version: str, dry_run: bool, force: bool, daemon: bool) -> None:
    """Install Mihomo. Use --daemon to also install autostart metadata."""

    config = _read_local_config()
    target = _engine_path(config)
    click.echo("install: mihomo binary")
    if daemon:
        click.echo("daemon: install")
        click.echo(f"unit: {_daemon_unit_path()}")
    if target.exists() and not force:
        click.echo(f"mihomo binary already installed: {target}")
        if dry_run:
            render_success("dry-run only; no files changed")
    else:
        engine_install.callback(repo=repo, version=version, dry_run=dry_run, force=force)
    if daemon and not dry_run:
        unit = _install_daemon_unit(config)
        click.echo(f"daemon-unit-written: {unit}")


@mihomo_group.command(name="uninstall")
@click.option("--dry-run", is_flag=True)
@click.option("--daemon", is_flag=True, help="Remove user-level service/autostart metadata too.")
def mihomo_uninstall(dry_run: bool, daemon: bool) -> None:
    """Uninstall Mihomo binary, optionally removing daemon metadata."""

    config = _read_local_config()
    target = _engine_path(config)
    click.echo(f"remove: {target}")
    if daemon:
        click.echo("daemon: uninstall")
        click.echo(f"unit: {_daemon_unit_path()}")
    if dry_run:
        render_success("dry-run only; no files changed")
        return
    target.unlink(missing_ok=True)
    if daemon:
        _remove_daemon_unit()
    render_success("mihomo uninstalled")


@mihomo_group.command(name="update")
@click.option("--repo", default="MetaCubeX/mihomo", show_default=True)
@click.option("--version", default="latest", show_default=True)
@click.option("--dry-run", is_flag=True)
def mihomo_update(repo: str, version: str, dry_run: bool) -> None:
    """Update the Mihomo binary version; subscription updates are separate."""

    click.echo("update: mihomo binary")
    engine_install.callback(repo=repo, version=version, dry_run=dry_run, force=True)


@mihomo_group.command(name="start")
@click.option("--dry-run", is_flag=True)
def mihomo_start(dry_run: bool) -> None:
    """Start Mihomo on this machine."""

    service_up.callback(dry_run=dry_run)


@mihomo_group.command(name="stop")
@click.option("--dry-run", is_flag=True)
def mihomo_stop(dry_run: bool) -> None:
    """Stop Mihomo on this machine."""

    service_down.callback(dry_run=dry_run)


@mihomo_group.command(name="restart")
@click.option("--dry-run", is_flag=True)
def mihomo_restart(dry_run: bool) -> None:
    """Restart Mihomo on this machine."""

    service_restart.callback(dry_run=dry_run)


@mihomo_group.command(name="status")
def mihomo_status() -> None:
    """Show Mihomo binary/process/autostart state."""

    config = _read_local_config()
    engine = _engine_path(config)
    pid_file = _pid_file(config)
    click.echo(f"mihomo path: {engine}")
    click.echo(f"installed: {'yes' if engine.exists() else 'no'}")
    click.echo(f"running: {'yes' if (_daemon_unit_active() or _pid_running(pid_file)) else 'no'}")
    click.echo(f"pid_file: {pid_file}")
    click.echo(f"autostart: {'enabled' if _daemon_unit_path().exists() else 'disabled'}")


@mihomo_group.command(name="logs")
@click.option("--tail", default=100, show_default=True, type=int)
@click.option("--dry-run", is_flag=True)
def mihomo_logs(tail: int, dry_run: bool) -> None:
    """Show redacted Mihomo logs."""

    service_logs.callback(tail=tail, dry_run=dry_run)


@main.group(name="engine")
def engine_group() -> None:
    """Install or inspect the lightweight Clash-compatible engine."""


@engine_group.command(name="install")
@click.option("--repo", default="MetaCubeX/mihomo", show_default=True)
@click.option("--version", default="latest", show_default=True)
@click.option("--dry-run", is_flag=True)
@click.option("--force", is_flag=True)
def engine_install(repo: str, version: str, dry_run: bool, force: bool) -> None:
    """Install Mihomo as a local single-file binary under ChatClash home."""

    config = _read_local_config()
    target = Path(str(config.get("engine_path") or (_chatclash_home() / "bin" / "mihomo")))
    click.echo(f"engine: mihomo")
    click.echo(f"target: {target}")
    if dry_run:
        render_success("dry-run only; no files changed")
        return
    if target.exists() and not force:
        raise click.ClickException(f"engine already exists: {target}; pass --force to replace")
    import gzip
    import json
    import platform
    import tempfile

    machine = platform.machine().lower()
    if machine in {"x86_64", "amd64"}:
        arch = "amd64"
    elif machine in {"aarch64", "arm64"}:
        arch = "arm64"
    else:
        raise click.ClickException(f"unsupported architecture: {machine}")
    release_url = f"https://api.github.com/repos/{repo}/releases/latest" if version == "latest" else f"https://api.github.com/repos/{repo}/releases/tags/{version}"
    request = urllib.request.Request(release_url, headers={"User-Agent": "chatclash/0.1"})
    with urllib.request.urlopen(request, timeout=60) as response:
        release = json.loads(response.read().decode("utf-8"))
    assets = release.get("assets") or []
    candidates = []
    for asset in assets:
        name = asset.get("name") or ""
        if "linux" in name and arch in name and name.endswith(".gz") and "compatible" not in name:
            candidates.append(asset)
    if not candidates:
        for asset in assets:
            name = asset.get("name") or ""
            if "linux" in name and arch in name and name.endswith(".gz"):
                candidates.append(asset)
    if not candidates:
        raise click.ClickException(f"no linux {arch} .gz asset found for {repo} {release.get('tag_name')}")
    asset = candidates[0]
    download_url = asset.get("browser_download_url")
    if not download_url:
        raise click.ClickException("selected release asset has no download URL")
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        urllib.request.urlretrieve(download_url, tmp_path)
        with gzip.open(tmp_path, "rb") as src, target.open("wb") as dst:
            shutil.copyfileobj(src, dst)
        target.chmod(0o755)
    finally:
        tmp_path.unlink(missing_ok=True)
    render_success(f"installed {asset.get('name')} to {target}")


@main.group(name="config")
def config_group() -> None:
    """Show or update this machine's ChatClash configuration."""


@config_group.command(name="show")
def config_show() -> None:
    """Show a redacted summary of the local ChatClash config."""

    config = _read_local_config()
    click.echo(f"home: {config.get('home')}")
    click.echo(f"clash_dir: {config.get('clash_dir')}")
    for key in ("http_port", "socks_port", "controller_port", "yacd_port", "fetch_mode"):
        click.echo(f"{key}: {config.get(key)}")
    subscription = _subscription_url()
    proxy_auth = _proxy_auth()
    subconverter = _subconverter_url()
    click.echo(f"subscription_url: {'present' if _clean(subscription) else '<not set>'}")
    click.echo(f"proxy_auth: {'present' if _clean(proxy_auth) else '<not set>'}")
    click.echo(f"subconverter_url: {subconverter if _clean(subconverter) else '<not set>'}")


@config_group.command(name="set")
@click.option("--subscription-url", default=None)
@click.option("--proxy-auth", default=None)
@click.option("--subconverter-url", default=None)
@click.option("--http-port", type=int, default=None)
@click.option("--socks-port", type=int, default=None)
@click.option("--controller-port", type=int, default=None)
@click.option("--yacd-port", type=int, default=None)
def config_set(
    subscription_url: str | None,
    proxy_auth: str | None,
    subconverter_url: str | None,
    http_port: int | None,
    socks_port: int | None,
    controller_port: int | None,
    yacd_port: int | None,
) -> None:
    """Set local ChatClash configuration values."""

    config = _read_local_config()
    changed = _write_chatclash_env(
        subscription_url=subscription_url,
        proxy_auth=proxy_auth,
        subconverter_url=subconverter_url,
    )
    for key, value in {
        "http_port": http_port,
        "socks_port": socks_port,
        "controller_port": controller_port,
        "yacd_port": yacd_port,
    }.items():
        if value is not None:
            config[key] = value
            changed.append(key)
    _write_local_config(config)
    click.echo("updated: " + (", ".join(changed) if changed else "<none>"))


@main.command(name="update")
@click.option("--dry-run", is_flag=True, help="Show the update plan without writing.")
@click.option("--no-validate", is_flag=True, help="Skip docker/clash config validation.")
@click.option("-y", "--yes", is_flag=True, help="Skip write confirmations.")
def update_command(dry_run: bool, no_validate: bool, yes: bool) -> None:
    """Refresh this machine's Clash config from the configured subscription."""

    config = _read_local_config()
    target_dir = _clash_dir_from_local(config)
    output = target_dir / "config.yaml"
    subscription_url = _subscription_url()
    if not subscription_url:
        raise click.ClickException("Missing subscription URL. Run `chatclash subscription set`.")
    click.echo(f"output: {output}")
    click.echo(f"subscription_url: {_mask(subscription_url)}")
    if dry_run:
        render_success("dry-run only; no files changed")
        return
    if _sensitive_path(output):
        _confirm_write(output, yes=yes, reason=f"{output} is in /srv/clash")
    fetched = _fetch_url(subscription_url)
    if not _looks_like_clash_yaml(fetched):
        subconverter = _subconverter_url()
        if not subconverter:
            raise click.ClickException("Subscription did not look like Clash YAML and no subconverter URL is configured.")
        fetched = _fetch_url(_build_subconverter_url(subscription_url, subconverter, DEFAULT_CONFIG_URL))
    header = _config_header(
        http_port=int(config.get("http_port") or DEFAULT_HTTP_PORT),
        socks_port=int(config.get("socks_port") or DEFAULT_SOCKS_PORT),
        controller_port=int(config.get("controller_port") or DEFAULT_CONTROLLER_PORT),
        auth=_proxy_auth(),
    )
    content = yaml.safe_dump(header, sort_keys=False, allow_unicode=False) + "\n" + _extract_clash_body(fetched).lstrip()
    parsed = yaml.safe_load(content)
    if not isinstance(parsed, dict):
        raise click.ClickException("Generated Clash config is not a YAML object")
    if not no_validate:
        # First phase keeps validation optional for CI and machines without Docker.
        render_warning("validation skipped unless --no-validate is removed in a Docker-enabled environment")
    target_dir.mkdir(parents=True, exist_ok=True)
    (target_dir / "backups").mkdir(exist_ok=True)
    backup = _backup_existing(output)
    output.write_text(content, encoding="utf-8")
    proxies, groups, rules = _counts(parsed)
    click.echo(f"proxies: {proxies}")
    click.echo(f"proxy-groups: {groups}")
    click.echo(f"rules: {rules}")
    if backup:
        click.echo(f"backup-written: {backup}")
    click.echo("update=OK")


@main.command(name="up")
@click.option("--dry-run", is_flag=True)
def service_up(dry_run: bool) -> None:
    """Start this machine's Clash service."""

    config = _read_local_config()
    clash_dir = _clash_dir_from_local(config)
    engine_path = Path(str(config.get("engine_path") or (_chatclash_home() / "bin" / "mihomo")))
    pid_file = Path(str(config.get("pid_file") or (_chatclash_home() / "run" / "mihomo.pid")))
    log_file = Path(str(config.get("log_file") or (_chatclash_home() / "logs" / "mihomo.log")))
    command = [str(engine_path), "-d", str(clash_dir)]
    if _daemon_unit_path().exists():
        click.echo(f"systemctl --user start {_daemon_unit_path().name}")
        if dry_run:
            render_success("dry-run only; no files changed")
            return
        _systemctl_user("start", _daemon_unit_path().name)
        render_success("mihomo started")
        return
    click.echo(" ".join(command))
    if dry_run:
        render_success("dry-run only; no files changed")
        return
    if not engine_path.exists():
        raise click.ClickException(f"mihomo binary missing: {engine_path}. Run `chatclash mihomo install` first.")
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    import subprocess

    with log_file.open("ab") as log:
        proc = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    pid_file.write_text(str(proc.pid), encoding="utf-8")
    render_success("mihomo started")


@main.command(name="down")
@click.option("--dry-run", is_flag=True)
def service_down(dry_run: bool) -> None:
    """Stop this machine's Clash service."""

    config = _read_local_config()
    pid_file = Path(str(config.get("pid_file") or (_chatclash_home() / "run" / "mihomo.pid")))
    if _daemon_unit_path().exists():
        click.echo(f"systemctl --user stop {_daemon_unit_path().name}")
        if dry_run:
            render_success("dry-run only; no files changed")
            return
        _systemctl_user("stop", _daemon_unit_path().name, check=False)
        render_success("mihomo stopped")
        return
    click.echo(f"kill pid from {pid_file}")
    if dry_run:
        render_success("dry-run only; no files changed")
        return
    if pid_file.exists():
        pid = pid_file.read_text(encoding="utf-8").strip()
        if pid:
            _run_shell(["kill", pid])
        pid_file.unlink(missing_ok=True)
    render_success("mihomo stopped")


@main.command(name="restart")
@click.option("--dry-run", is_flag=True)
def service_restart(dry_run: bool) -> None:
    """Restart this machine's Clash service."""

    config = _read_local_config()
    if _daemon_unit_path().exists():
        click.echo(f"systemctl --user restart {_daemon_unit_path().name}")
        if dry_run:
            render_success("dry-run only; no files changed")
            return
        _systemctl_user("restart", _daemon_unit_path().name)
        render_success("mihomo restarted")
        return
    click.echo("chatclash mihomo stop && chatclash mihomo start")
    if dry_run:
        render_success("dry-run only; no files changed")
        return
    pid_file = Path(str(config.get("pid_file") or (_chatclash_home() / "run" / "mihomo.pid")))
    if pid_file.exists():
        pid = pid_file.read_text(encoding="utf-8").strip()
        if pid:
            _run_shell(["kill", pid])
        pid_file.unlink(missing_ok=True)
    engine_path = Path(str(config.get("engine_path") or (_chatclash_home() / "bin" / "mihomo")))
    clash_dir = _clash_dir_from_local(config)
    log_file = Path(str(config.get("log_file") or (_chatclash_home() / "logs" / "mihomo.log")))
    if not engine_path.exists():
        raise click.ClickException(f"mihomo binary missing: {engine_path}. Run `chatclash mihomo install` first.")
    import subprocess
    with log_file.open("ab") as log:
        proc = subprocess.Popen([str(engine_path), "-d", str(clash_dir)], stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    pid_file.write_text(str(proc.pid), encoding="utf-8")
    render_success("mihomo restarted")


@main.command(name="logs")
@click.option("--tail", default=100, show_default=True, type=int)
@click.option("--dry-run", is_flag=True)
def service_logs(tail: int, dry_run: bool) -> None:
    """Show redacted Clash logs."""

    config = _read_local_config()
    log_file = Path(str(config.get("log_file") or (_chatclash_home() / "logs" / "mihomo.log")))
    click.echo(f"tail -n {tail} {log_file}")
    if dry_run:
        render_success("dry-run only; no files changed")
        return
    if not log_file.exists():
        return
    output = _run_shell(["tail", "-n", str(tail), str(log_file)])
    click.echo(_redact_text(output), nl=False)


@main.command(name="verify")
@click.option("--url", "urls", multiple=True)
@click.option("--min-success", default=2, show_default=True, type=int)
@click.option("--timeout", default=30, show_default=True, type=int)
@click.option("--dry-run", is_flag=True)
def verify_command(urls: tuple[str, ...], min_success: int, timeout: int, dry_run: bool) -> None:
    """Verify the local Clash HTTP proxy from inside this machine."""

    config = _read_local_config()
    proxy = _local_proxy_url(config)
    masked_proxy = _masked_proxy_url(config)
    targets = list(urls) or [
        "http://example.com",
        "https://example.com",
        "https://github.com",
        "https://www.gstatic.com/generate_204",
    ]
    click.echo(f"proxy: {masked_proxy}")
    if dry_run:
        for url in targets:
            click.echo(f"check: {url}")
        render_success("dry-run only; no files changed")
        return
    ok = 0
    for url in targets:
        click.echo(f"-- {url}")
        try:
            output = _curl_head(proxy, url, timeout)
            first = output.splitlines()[0] if output.splitlines() else "<empty>"
            click.echo(first)
            if " 200" in output or " 204" in output or " 301" in output or " 302" in output:
                ok += 1
        except click.ClickException as exc:
            click.echo(f"failed: {exc}")
    click.echo(f"success_count={ok}")
    if ok < min_success:
        raise click.ClickException(f"verification failed: success_count={ok} < {min_success}")


@main.command(name="ip-api")
@click.option("--lang", default="zh-CN", show_default=True)
@click.option("--timeout", default=20, show_default=True, type=int)
@click.option("--dry-run", is_flag=True)
def ip_api_command(lang: str, timeout: int, dry_run: bool) -> None:
    """Query ip-api.com through the local Clash HTTP proxy."""

    config = _read_local_config()
    proxy = _local_proxy_url(config)
    masked_proxy = _masked_proxy_url(config)
    url = f"http://ip-api.com/json/?lang={urllib.parse.quote(lang)}"
    click.echo(f"proxy: {masked_proxy}")
    click.echo(f"url: {url}")
    if dry_run:
        render_success("dry-run only; no files changed")
        return
    output = _curl_get(proxy, url, timeout)
    try:
        data = yaml.safe_load(output)
    except yaml.YAMLError:
        data = None
    if isinstance(data, dict):
        for key in ("status", "country", "countryCode", "regionName", "city", "isp", "org", "as", "query", "timezone"):
            if key in data:
                click.echo(f"{key}={data[key]}")
    else:
        click.echo(output)


@main.group(name="check")
def check_group() -> None:
    """Run local ChatClash proxy checks."""


@check_group.command(name="proxy")
@click.option("--url", "urls", multiple=True)
@click.option("--min-success", default=2, show_default=True, type=int)
@click.option("--timeout", default=30, show_default=True, type=int)
@click.option("--dry-run", is_flag=True)
def check_proxy_command(urls: tuple[str, ...], min_success: int, timeout: int, dry_run: bool) -> None:
    """Verify the local ChatClash HTTP proxy."""

    verify_command.callback(urls=urls, min_success=min_success, timeout=timeout, dry_run=dry_run)


@check_group.command(name="ip")
@click.option("--lang", default="zh-CN", show_default=True)
@click.option("--timeout", default=20, show_default=True, type=int)
@click.option("--dry-run", is_flag=True)
def check_ip_command(lang: str, timeout: int, dry_run: bool) -> None:
    """Query ip-api.com through the local ChatClash proxy."""

    ip_api_command.callback(lang=lang, timeout=timeout, dry_run=dry_run)


@main.group()
def setup() -> None:
    """Generate local service configuration."""


@setup.command(name="clash")
@click.argument(
    "clash_dir",
    required=False,
    type=click.Path(path_type=Path, file_okay=False, dir_okay=True),
)
@click.option("--http-port", default=DEFAULT_HTTP_PORT, show_default=True, type=int)
@click.option("--socks-port", default=DEFAULT_SOCKS_PORT, show_default=True, type=int)
@click.option(
    "--controller-port", default=DEFAULT_CONTROLLER_PORT, show_default=True, type=int
)
@click.option("--yacd-port", default=DEFAULT_YACD_PORT, show_default=True, type=int)
@click.option("--clash-image", default=DEFAULT_CLASH_IMAGE, show_default=True)
@click.option("--yacd-image", default=DEFAULT_YACD_IMAGE, show_default=True)
@click.option("--auth", default=None, help="Optional proxy authentication user:pass.")
@click.option("--dry-run", is_flag=True, help="Show the write plan without changes.")
@click.option("-y", "--yes", is_flag=True, help="Skip write confirmations.")
@add_interactive_option
def setup_clash(
    clash_dir: Path | None,
    http_port: int,
    socks_port: int,
    controller_port: int,
    yacd_port: int,
    clash_image: str,
    yacd_image: str,
    auth: str | None,
    dry_run: bool,
    yes: bool,
    interactive: bool | None,
) -> None:
    """Generate a Clash + Yacd Docker Compose directory."""

    _ = interactive
    target = clash_dir or DEFAULT_CLASH_DIR
    compose_path = target / "docker-compose.yaml"
    config_path = target / "config.yaml"
    plan = [
        f"target: {target}",
        f"compose: {compose_path}",
        f"config: {config_path}",
        f"ports: http={http_port}, socks={socks_port}, controller={controller_port}, yacd={yacd_port}",
        f"images: clash={clash_image}, yacd={yacd_image}",
        f"auth: {_mask(auth) if auth else '<none>'}",
    ]
    click.echo("\n".join(plan))
    if dry_run:
        render_success("dry-run only; no files changed")
        return

    if _sensitive_path(target):
        _confirm_write(target, yes=yes, reason=f"{target} is a real service directory")
    if compose_path.exists():
        _confirm_write(compose_path, yes=yes, reason=f"{compose_path} already exists")
    if config_path.exists():
        _confirm_write(config_path, yes=yes, reason=f"{config_path} already exists")

    target.mkdir(parents=True, exist_ok=True)
    (target / "ui").mkdir(exist_ok=True)
    (target / "backups").mkdir(exist_ok=True)
    compose_path.write_text(
        _compose_yaml(
            http_port=http_port,
            socks_port=socks_port,
            controller_port=controller_port,
            yacd_port=yacd_port,
            clash_image=clash_image,
            yacd_image=yacd_image,
        ),
        encoding="utf-8",
    )
    if not config_path.exists():
        config_path.write_text(
            _placeholder_config(http_port=http_port, socks_port=socks_port, auth=auth),
            encoding="utf-8",
        )
    render_success(f"generated Clash compose directory at {target}")


@main.command()
@click.argument(
    "clash_dir",
    required=False,
    type=click.Path(path_type=Path, file_okay=False, dir_okay=True),
)
def status(clash_dir: Path | None) -> None:
    """Show this machine's ChatClash status, or a legacy compose dir summary when DIR is passed."""

    if clash_dir is None:
        _show_single_machine_status()
        return
    target = clash_dir
    compose_path = target / "docker-compose.yaml"
    config_path = target / "config.yaml"
    click.echo(f"directory: {target}")
    for name in ("docker-compose.yaml", "config.yaml", "ui", "backups"):
        path = target / name
        click.echo(f"{name}: {'present' if path.exists() else 'missing'}")

    compose = _load_yaml_file(compose_path)
    services = compose.get("services") or {}
    for service_name in ("clash", "yacd"):
        service = services.get(service_name) or {}
        if service:
            click.echo(
                f"{service_name}: image={service.get('image', '<unknown>')}, "
                f"ports={','.join(str(item) for item in (service.get('ports') or [])) or '<none>'}"
            )

    config = _load_yaml_file(config_path)
    if config:
        proxies, groups, rules = _counts(config)
        click.echo(f"http-port: {config.get('port', '<unknown>')}")
        click.echo(f"socks-port: {config.get('socks-port', '<unknown>')}")
        click.echo(f"external-controller: {config.get('external-controller', '<unknown>')}")
        click.echo(f"proxies: {proxies}")
        click.echo(f"proxy-groups: {groups}")
        click.echo(f"rules: {rules}")


@main.group()
def proxy() -> None:
    """Proxy helper commands."""


@proxy.command(name="show")
def proxy_show() -> None:
    """Show proxy endpoints for this machine."""

    config = _read_local_config()
    click.echo(f"HTTP proxy: {_http_proxy_url(config)}")
    click.echo(f"SOCKS proxy: {_socks_proxy_url(config)}")


@proxy.command(name="env")
def proxy_env() -> None:
    """Print proxy environment variables for the current shell to eval."""

    config = _read_local_config()
    click.echo(f"export http_proxy={_http_proxy_url(config)}")
    click.echo(f"export https_proxy={_http_proxy_url(config)}")
    click.echo(f"export all_proxy={_socks_proxy_url(config)}")
    click.echo("export no_proxy=localhost,127.0.0.1,::1")


@main.group()
def sub() -> None:
    """Manage subscription conversion."""


@sub.command(name="status")
def sub_status() -> None:
    """Show whether subscription and subconverter URLs are configured."""

    subscription = _subscription_url()
    subconverter = _subconverter_url()
    click.echo(f"CHATCLASH_SUBSCRIPTION_URL: {_mask(subscription)}")
    click.echo(
        "CHATCLASH_SUBCONVERTER_URL: "
        f"{subconverter if _clean(subconverter) else '<not set>'}"
    )
    if not _clean(subconverter):
        render_warning("pass -s/--subconverter-url or configure CHATCLASH_SUBCONVERTER_URL")


@sub.command(name="url")
@click.argument("subscription_url", required=False)
@click.option("-s", "--subconverter-url", default=None)
@click.option("-l", "--config-url", default=DEFAULT_CONFIG_URL, show_default=True)
@click.option("--show", is_flag=True, help="Show the full generated URL.")
@add_interactive_option
def sub_url(
    subscription_url: str | None,
    subconverter_url: str | None,
    config_url: str,
    show: bool,
    interactive: bool | None,
) -> None:
    """Construct a subconverter /sub URL."""

    values = resolve_command_inputs(
        schema=SUB_INPUT_SCHEMA,
        provided={
            "subscription_url": subscription_url,
            "subconverter_url": subconverter_url,
        },
        interactive=interactive,
        usage="Usage: chatclash sub url [SUBSCRIPTION_URL] -s URL [-i|-I]",
    )
    final_url = _build_subconverter_url(
        values["subscription_url"], values["subconverter_url"], config_url
    )
    if show:
        render_warning("full URL includes the subscription URL")
        click.echo(final_url)
    else:
        click.echo(_redact_text(final_url, values["subscription_url"]))


@sub.command(name="generate")
@click.argument("subscription_url", required=False)
@click.option("-s", "--subconverter-url", default=None)
@click.option("-l", "--config-url", default=DEFAULT_CONFIG_URL, show_default=True)
@click.option(
    "-o",
    "--output",
    type=click.Path(path_type=Path, dir_okay=False),
    default=DEFAULT_CLASH_DIR / "config.yaml",
    show_default=True,
)
@click.option("--debug", is_flag=True, help="Print redacted debugging details.")
@click.option("--dry-run", is_flag=True, help="Show the plan without writing.")
@click.option("-y", "--yes", is_flag=True, help="Skip write confirmations.")
@add_interactive_option
def sub_generate(
    subscription_url: str | None,
    subconverter_url: str | None,
    config_url: str,
    output: Path,
    debug: bool,
    dry_run: bool,
    yes: bool,
    interactive: bool | None,
) -> None:
    """Generate config.yaml through subconverter."""

    values = resolve_command_inputs(
        schema=SUB_INPUT_SCHEMA,
        provided={
            "subscription_url": subscription_url,
            "subconverter_url": subconverter_url,
        },
        interactive=interactive,
        usage="Usage: chatclash sub generate [SUBSCRIPTION_URL] -s URL [-o PATH] [-i|-I]",
    )
    request_url = _build_subconverter_url(
        values["subscription_url"], values["subconverter_url"], config_url
    )
    backup_path = output.parent / "backups" / f"{output.name}.<timestamp>.bak"
    click.echo(f"request: {_redact_text(request_url, values['subscription_url'])}")
    click.echo(f"output: {output}")
    click.echo(f"backup: {backup_path if output.exists() else '<none needed>'}")
    if debug:
        click.echo(f"config-url: {config_url}")
        click.echo(f"subconverter-url: {values['subconverter_url']}")
        click.echo(f"subscription-url: {_mask(values['subscription_url'])}")
    if dry_run:
        render_success("dry-run only; no files changed")
        return

    if _sensitive_path(output):
        _confirm_write(output, yes=yes, reason=f"{output} is in /srv/clash")
    if output.exists():
        _confirm_write(output, yes=yes, reason=f"{output} already exists")

    converted = _fetch_url(request_url)
    content, parsed = _merge_header(converted)
    proxies, groups, rules = _counts(parsed)
    output.parent.mkdir(parents=True, exist_ok=True)
    backup = _backup_existing(output)
    output.write_text(content, encoding="utf-8")
    click.echo(f"proxies: {proxies}")
    click.echo(f"proxy-groups: {groups}")
    click.echo(f"rules: {rules}")
    if backup:
        click.echo(f"backup-written: {backup}")
    render_success(f"generated {output}")


@main.group()
def deploy() -> None:
    """Deployment placeholders."""


@deploy.group()
def ssr() -> None:
    """SSR deployment boundary reserved for later phases."""


@ssr.command(name="init")
def ssr_init() -> None:
    """Reserved SSR init command."""

    raise click.ClickException("SSR deployment is reserved for a later phase")


@ssr.command(name="status")
def ssr_status() -> None:
    """Reserved SSR status command."""

    raise click.ClickException("SSR deployment is reserved for a later phase")


@ssr.command(name="export")
def ssr_export() -> None:
    """Reserved SSR export command."""

    raise click.ClickException("SSR deployment is reserved for a later phase")


if __name__ == "__main__":
    main()
