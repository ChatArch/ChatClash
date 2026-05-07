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
from chatenv import BaseEnvConfig, get_paths
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
    for value in (_subscription_url(), *extra_secrets):
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
    auth: str | None = None,
) -> dict[str, Any]:
    header: dict[str, Any] = {
        "port": http_port,
        "socks-port": socks_port,
        "allow-lan": True,
        "mode": "Rule",
        "log-level": "info",
        "external-controller": ":9090",
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


@click.group()
def main() -> None:
    """ChatArch CLI for Clash, subconverter, and proxy operations."""


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
    """Show a redacted summary of a Clash compose directory."""

    target = clash_dir or DEFAULT_CLASH_DIR
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


@proxy.command(name="env")
@click.argument("proxy_url", required=False)
def proxy_env(proxy_url: str | None) -> None:
    """Print proxy environment variables for the current shell to copy."""

    url = proxy_url or DEFAULT_PROXY_URL
    click.echo(f"export http_proxy={url}")
    click.echo(f"export https_proxy={url}")
    click.echo(f"export all_proxy={url}")
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
