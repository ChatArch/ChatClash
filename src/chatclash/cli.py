"""Thin CLI adapter for ChatClash."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

import click
from chatstyle import CommandField, CommandSchema, add_interactive_option, render_success, resolve_command_inputs

from . import __version__
from .checks import check_ip, check_proxy
from .chatenv_store import read_operator_config
from .mihomo import (
    install_mihomo,
    read_mihomo_logs,
    restart_mihomo,
    start_mihomo,
    stop_mihomo,
    uninstall_mihomo,
    get_mihomo_status,
)
from .paths import initialize_home
from .proxy import get_proxy_endpoints, get_proxy_env, set_proxy_config
from .status import get_status
from .subscription import (
    build_subscription_url,
    generate_subscription_config,
    get_subscription_status,
    set_subscription_config,
    update_subscription_config,
)
from .utils import mask


SUB_SET_SCHEMA = CommandSchema(
    name="chatclash-sub-set",
    fields=(
        CommandField("subscription_url", "Subscription URL", sensitive=True),
        CommandField("proxy_auth", "Proxy authentication user:password", sensitive=True),
        CommandField("subconverter_url", "Subconverter base URL"),
        CommandField("subscription_fetch_proxy", "Proxy for fetching subscription; use local for this machine's proxy"),
    ),
)


def _configured_subscription_url() -> str | None:
    return read_operator_config().subscription_url


def _configured_subconverter_url() -> str | None:
    return read_operator_config().subconverter_url


SUB_URL_SCHEMA = CommandSchema(
    name="chatclash-sub-url",
    fields=(
        CommandField(
            "subscription_url",
            prompt="Subscription URL",
            required=True,
            sensitive=True,
            default_factory=_configured_subscription_url,
            missing_message="Missing subscription URL. Configure CHATCLASH_SUBSCRIPTION_URL or pass SUBSCRIPTION_URL.",
        ),
        CommandField(
            "subconverter_url",
            prompt="subconverter URL",
            required=True,
            default_factory=_configured_subconverter_url,
            missing_message="Missing subconverter URL. Configure CHATCLASH_SUBCONVERTER_URL or pass -s/--subconverter-url.",
        ),
    ),
)


def _echo_lines(lines: Iterable[str]) -> None:
    for line in lines:
        click.echo(line)


def _fail(exc: Exception) -> None:
    raise click.ClickException(str(exc)) from exc


@click.group()
@click.version_option(__version__)
def main() -> None:
    """Manage this machine's ChatClash runtime and subscription config."""


@main.command(name="init")
@click.option("--home", type=click.Path(path_type=Path, file_okay=False, dir_okay=True), default=None)
@click.option("--dry-run", is_flag=True, help="Show the init plan without writing.")
@click.option("-y", "--yes", is_flag=True, help="Accepted for write-confirmation consistency.")
def init_command(home: Path | None, dry_run: bool, yes: bool) -> None:
    """Initialize this machine's ChatClash home."""
    try:
        result = initialize_home(home=home, dry_run=dry_run)
    except Exception as exc:  # pragma: no cover - Click translation
        _fail(exc)
    click.echo(f"home: {result.home}")
    click.echo(f"clash_dir: {result.clash_dir}")
    if result.dry_run:
        render_success("dry-run only; no files changed")
    else:
        render_success("initialized ChatClash home")


@main.command(name="status")
def status_command() -> None:
    """Show this machine's ChatClash status."""
    try:
        status = get_status()
    except Exception as exc:
        _fail(exc)
    for key, value in status.items():
        click.echo(f"{key}: {value}")


@main.group(name="sub")
def sub_group() -> None:
    """Manage subscription-backed runtime config."""


@sub_group.command(name="set")
@click.option("--url-env", default=None, help="Environment variable containing the subscription URL.")
@click.option("--proxy-auth-env", default=None, help="Environment variable containing proxy auth.")
@click.option("--subconverter-url-env", default=None, help="Environment variable containing subconverter URL.")
@click.option("--subscription-url", default=None, help="Subscription URL. Prefer --url-env for secrets.")
@click.option("--proxy-auth", default=None, help="Proxy auth. Prefer --proxy-auth-env for secrets.")
@click.option("--subconverter-url", default=None)
@click.option("--fetch-proxy", "subscription_fetch_proxy", default=None)
@add_interactive_option
def sub_set(
    url_env: str | None,
    proxy_auth_env: str | None,
    subconverter_url_env: str | None,
    subscription_url: str | None,
    proxy_auth: str | None,
    subconverter_url: str | None,
    subscription_fetch_proxy: str | None,
    interactive: bool | None,
) -> None:
    """Store subscription operator config through ChatEnv."""
    try:
        if url_env:
            subscription_url = os.getenv(url_env)
            if subscription_url is None:
                raise ValueError(f"environment variable not set: {url_env}")
        if proxy_auth_env:
            proxy_auth = os.getenv(proxy_auth_env)
            if proxy_auth is None:
                raise ValueError(f"environment variable not set: {proxy_auth_env}")
        if subconverter_url_env:
            subconverter_url = os.getenv(subconverter_url_env)
            if subconverter_url is None:
                raise ValueError(f"environment variable not set: {subconverter_url_env}")
        values = resolve_command_inputs(
            schema=SUB_SET_SCHEMA,
            provided={
                "subscription_url": subscription_url,
                "proxy_auth": proxy_auth,
                "subconverter_url": subconverter_url,
                "subscription_fetch_proxy": subscription_fetch_proxy,
            },
            interactive=interactive,
            usage="Usage: chatclash sub set [--url-env NAME] [--proxy-auth-env NAME] [-i|-I]",
        )
        changed = set_subscription_config(
            subscription_url=values.get("subscription_url"),
            proxy_auth=values.get("proxy_auth"),
            subconverter_url=values.get("subconverter_url"),
            fetch_proxy=values.get("subscription_fetch_proxy"),
        )
    except Exception as exc:
        _fail(exc)
    click.echo("updated: " + (", ".join(changed) if changed else "<none>"))


@sub_group.command(name="status")
def sub_status() -> None:
    """Show redacted subscription config state."""
    for key, value in get_subscription_status().items():
        click.echo(f"{key}: {value}")


@sub_group.command(name="update")
@click.option("--dry-run", is_flag=True)
@click.option("--no-validate", is_flag=True)
def sub_update(dry_run: bool, no_validate: bool) -> None:
    """Refresh the runtime config from the configured subscription."""
    try:
        result = update_subscription_config(dry_run=dry_run, no_validate=no_validate)
    except Exception as exc:
        _fail(exc)
    click.echo(f"target: {result['target']}")
    if dry_run:
        render_success("dry-run only; no files changed")
    else:
        render_success("subscription update complete")


@sub_group.command(name="url")
@click.argument("subscription_url", required=False)
@click.option("-s", "--subconverter-url", default=None)
@click.option("--show", is_flag=True, help="Show the full generated URL.")
@add_interactive_option
def sub_url(subscription_url: str | None, subconverter_url: str | None, show: bool, interactive: bool | None) -> None:
    """Build a subconverter URL for the configured subscription."""
    try:
        values = resolve_command_inputs(
            schema=SUB_URL_SCHEMA,
            provided={"subscription_url": subscription_url, "subconverter_url": subconverter_url},
            interactive=interactive,
            usage="Usage: chatclash sub url [SUBSCRIPTION_URL] -s SUBCONVERTER_URL [-i|-I]",
        )
        url = build_subscription_url(values.get("subscription_url"), subconverter_url=values.get("subconverter_url"))
    except Exception as exc:
        _fail(exc)
    click.echo(url if show else f"subconverter_url: {mask(url)}")


@sub_group.command(name="generate")
@click.argument("subscription_url", required=False)
@click.option("-s", "--subconverter-url", default=None)
@click.option("-o", "--output", type=click.Path(path_type=Path, dir_okay=False), required=True)
@click.option("--dry-run", is_flag=True)
@click.option("-y", "--yes", is_flag=True, help="Accepted for write-confirmation consistency.")
@add_interactive_option
def sub_generate(subscription_url: str | None, subconverter_url: str | None, output: Path, dry_run: bool, yes: bool, interactive: bool | None) -> None:
    """Generate a Clash-compatible config through subscription conversion."""
    try:
        values = resolve_command_inputs(
            schema=SUB_URL_SCHEMA,
            provided={"subscription_url": subscription_url, "subconverter_url": subconverter_url},
            interactive=interactive,
            usage="Usage: chatclash sub generate [SUBSCRIPTION_URL] -s SUBCONVERTER_URL -o OUTPUT [-i|-I]",
        )
        result = generate_subscription_config(
            subscription_url=values.get("subscription_url"),
            subconverter_url=values.get("subconverter_url"),
            output=output,
            dry_run=dry_run,
            yes=yes,
        )
    except Exception as exc:
        _fail(exc)
    click.echo(f"output: {result['output']}")
    click.echo(f"proxies: {result['proxies']}")
    if dry_run:
        render_success("dry-run only; no files changed")


@main.group(name="proxy")
def proxy_group() -> None:
    """Show and update local proxy endpoint settings."""


@proxy_group.command(name="set")
@click.option("--http-port", type=int, default=None)
@click.option("--socks-port", type=int, default=None)
@click.option("--controller-port", type=int, default=None)
@click.option("--bind-host", default=None)
@click.option("--proxy-host", default=None)
def proxy_set(http_port: int | None, socks_port: int | None, controller_port: int | None, bind_host: str | None, proxy_host: str | None) -> None:
    """Set machine-local proxy listener and advertised host settings."""
    try:
        changed = set_proxy_config(
            http_port_value=http_port,
            socks_port_value=socks_port,
            controller_port_value=controller_port,
            bind_host=bind_host,
            proxy_host_value=proxy_host,
        )
    except Exception as exc:
        _fail(exc)
    click.echo("updated: " + (", ".join(changed) if changed else "<none>"))


@proxy_group.command(name="show")
def proxy_show() -> None:
    """Show proxy endpoints for this machine."""
    endpoints = get_proxy_endpoints()
    click.echo(f"HTTP proxy: {endpoints.http}")
    click.echo(f"HTTPS proxy: {endpoints.https}")
    click.echo(f"SOCKS proxy: {endpoints.socks}")


@proxy_group.command(name="env")
def proxy_env() -> None:
    """Print shell proxy environment exports."""
    for key, value in get_proxy_env().items():
        click.echo(f"export {key}={value}")


@main.group(name="mihomo")
def mihomo_group() -> None:
    """Install and manage the local runtime."""


@mihomo_group.command(name="install")
@click.option("--repo", default="MetaCubeX/mihomo", show_default=True)
@click.option("--version", default="latest", show_default=True)
@click.option("--dry-run", is_flag=True)
@click.option("--force", is_flag=True)
@click.option("--daemon", is_flag=True)
def mihomo_install(repo: str, version: str, dry_run: bool, force: bool, daemon: bool) -> None:
    try:
        result = install_mihomo(repo=repo, version=version, dry_run=dry_run, force=force, daemon=daemon)
    except Exception as exc:
        _fail(exc)
    _echo_lines(result.lines)
    if result.dry_run:
        render_success("dry-run only; no files changed")


@mihomo_group.command(name="uninstall")
@click.option("--dry-run", is_flag=True)
@click.option("--daemon", is_flag=True)
def mihomo_uninstall(dry_run: bool, daemon: bool) -> None:
    try:
        result = uninstall_mihomo(dry_run=dry_run, daemon=daemon)
    except Exception as exc:
        _fail(exc)
    _echo_lines(result.lines)
    if result.dry_run:
        render_success("dry-run only; no files changed")


@mihomo_group.command(name="update")
@click.option("--repo", default="MetaCubeX/mihomo", show_default=True)
@click.option("--version", default="latest", show_default=True)
@click.option("--dry-run", is_flag=True)
def mihomo_update(repo: str, version: str, dry_run: bool) -> None:
    try:
        result = install_mihomo(repo=repo, version=version, dry_run=dry_run, force=True)
    except Exception as exc:
        _fail(exc)
    _echo_lines(result.lines)
    if result.dry_run:
        render_success("dry-run only; no files changed")


@mihomo_group.command(name="start")
@click.option("--dry-run", is_flag=True)
def mihomo_start(dry_run: bool) -> None:
    try:
        result = start_mihomo(dry_run=dry_run)
    except Exception as exc:
        _fail(exc)
    _echo_lines(result.lines)
    if result.dry_run:
        render_success("dry-run only; no files changed")


@mihomo_group.command(name="stop")
@click.option("--dry-run", is_flag=True)
def mihomo_stop(dry_run: bool) -> None:
    try:
        result = stop_mihomo(dry_run=dry_run)
    except Exception as exc:
        _fail(exc)
    _echo_lines(result.lines)
    if result.dry_run:
        render_success("dry-run only; no files changed")


@mihomo_group.command(name="restart")
@click.option("--dry-run", is_flag=True)
def mihomo_restart(dry_run: bool) -> None:
    try:
        result = restart_mihomo(dry_run=dry_run)
    except Exception as exc:
        _fail(exc)
    _echo_lines(result.lines)
    if result.dry_run:
        render_success("dry-run only; no files changed")


@mihomo_group.command(name="status")
def mihomo_status() -> None:
    for key, value in get_mihomo_status().items():
        click.echo(f"{key}: {value}")


@mihomo_group.command(name="logs")
@click.option("--tail", default=100, show_default=True, type=int)
@click.option("--dry-run", is_flag=True)
def mihomo_logs(tail: int, dry_run: bool) -> None:
    try:
        result = read_mihomo_logs(tail=tail, dry_run=dry_run)
    except Exception as exc:
        _fail(exc)
    _echo_lines(result.lines)
    if result.dry_run:
        render_success("dry-run only; no files changed")


@main.group(name="check")
def check_group() -> None:
    """Run local proxy checks."""


@check_group.command(name="proxy")
@click.option("--url", "urls", multiple=True)
@click.option("--min-success", default=2, show_default=True, type=int)
@click.option("--timeout", default=30, show_default=True, type=int)
@click.option("--dry-run", is_flag=True)
def check_proxy_command(urls: tuple[str, ...], min_success: int, timeout: int, dry_run: bool) -> None:
    try:
        result = check_proxy(urls=urls if urls else None, min_success=min_success, timeout=timeout, dry_run=dry_run)
    except Exception as exc:
        _fail(exc)
    click.echo(f"proxy: {result.proxy}")
    click.echo(f"auth_present: {result.auth_present}")
    for item in result.results:
        click.echo(f"{item.url}: {'OK' if item.ok else 'FAIL'} {item.detail}")
    click.echo(f"success_count: {result.success_count}")
    if dry_run:
        render_success("dry-run only; no network checks ran")


@check_group.command(name="ip")
@click.option("--lang", default="zh-CN", show_default=True)
@click.option("--timeout", default=20, show_default=True, type=int)
@click.option("--dry-run", is_flag=True)
def check_ip_command(lang: str, timeout: int, dry_run: bool) -> None:
    try:
        click.echo(check_ip(lang=lang, timeout=timeout, dry_run=dry_run))
    except Exception as exc:
        _fail(exc)
