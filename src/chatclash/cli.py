"""Thin CLI adapter for ChatClash."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

import click
from chatstyle import CommandField, CommandSchema, add_interactive_option, render_success, resolve_command_inputs, resolve_interactive_mode

from . import __version__
from .converter import (
    converter_status,
    install_converter,
    read_converter_logs,
    start_converter,
    stop_converter,
)
from .chatenv_store import read_operator_config
from .mihomo import (
    install_mihomo,
    read_mihomo_logs,
    reload_mihomo,
    restart_mihomo,
    start_mihomo,
    stop_mihomo,
    uninstall_mihomo,
    validate_mihomo_config,
    get_mihomo_status,
)
from .paths import initialize_home, read_local_config
from .proxy import get_proxy_endpoints, get_proxy_env, proxy_auth_status, set_proxy_auth, set_proxy_config
from .status import get_status
from .subscription import (
    build_subscription_url,
    generate_subscription_config,
    get_subscription_status,
    render_active_config_from_local,
    set_subscription_config,
    update_subscription_config,
)
from .utils import mask


def _configured_subscription_url() -> str | None:
    return read_operator_config().subscription_url


def _configured_proxy_auth() -> str | None:
    return read_operator_config().proxy_auth


def _configured_subconverter_url() -> str | None:
    return read_operator_config().subconverter_url


SUB_SET_SCHEMA = CommandSchema(
    name="chatclash-sub-set",
    fields=(
        CommandField("subscription_url", "Subscription URL", sensitive=True),
        CommandField("subconverter_url", "Subconverter base URL"),
    ),
)

INIT_SCHEMA = CommandSchema(
    name="chatclash-init",
    fields=(
        CommandField(
            "subscription_url",
            "Subscription URL",
            required=True,
            sensitive=True,
            default_factory=_configured_subscription_url,
            missing_message="Missing subscription URL. Pass --subscription-url/--url-env, or run interactively.",
        ),
        CommandField(
            "proxy_auth",
            "Proxy authentication user:password",
            sensitive=True,
            default_factory=_configured_proxy_auth,
            prompt_if_missing=True,
        ),
        CommandField("subconverter_url", "Subconverter base URL", default_factory=_configured_subconverter_url),
    ),
)


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




def _resolve_no_input_interactive(interactive: bool | None) -> None:
    """Route no-input commands through ChatStyle interactive resolution."""
    resolve_interactive_mode(interactive, auto_prompt_condition=False)


def _echo_lines(lines: Iterable[str]) -> None:
    for line in lines:
        click.echo(line)


def _fail(exc: Exception) -> None:
    raise click.ClickException(str(exc)) from exc


@click.group()
@click.version_option(__version__)
@add_interactive_option
def main(interactive: bool | None) -> None:
    _resolve_no_input_interactive(interactive)
    """Manage this machine's ChatClash runtime and subscription config."""


@main.command(name="init")
@click.option("--home", type=click.Path(path_type=Path, file_okay=False, dir_okay=True), default=None)
@click.option("--dry-run", is_flag=True, help="Show the init plan without writing.")
@click.option("--local-only", is_flag=True, help="Only initialize local runtime files; do not configure ChatEnv.")
@click.option("--url-env", default=None, help="Environment variable containing the subscription URL.")
@click.option("--subscription-url", default=None, help="Subscription URL. Prefer --url-env for secrets.")
@click.option("--proxy-auth-env", default=None, help="Environment variable containing proxy authentication.")
@click.option("--proxy-auth", default=None, help="Proxy authentication in user:password format. Prefer --proxy-auth-env.")
@click.option("--subconverter-url", default=None)
@click.option("-y", "--yes", is_flag=True, help="Accepted for write-confirmation consistency.")
@add_interactive_option
def init_command(
    home: Path | None,
    dry_run: bool,
    local_only: bool,
    url_env: str | None,
    subscription_url: str | None,
    proxy_auth_env: str | None,
    proxy_auth: str | None,
    subconverter_url: str | None,
    yes: bool,
    interactive: bool | None,
) -> None:
    """Initialize this machine and collect required ChatEnv config."""
    try:
        if url_env:
            subscription_url = os.getenv(url_env)
            if subscription_url is None:
                raise ValueError(f"environment variable not set: {url_env}")
        if proxy_auth_env:
            proxy_auth = os.getenv(proxy_auth_env)
            if proxy_auth is None:
                raise ValueError(f"environment variable not set: {proxy_auth_env}")
        values: dict[str, str | None] = {}
        if not dry_run and not local_only:
            values = resolve_command_inputs(
                schema=INIT_SCHEMA,
                provided={
                    "subscription_url": subscription_url,
                    "proxy_auth": proxy_auth,
                    "subconverter_url": subconverter_url,
                },
                interactive=interactive,
                usage="Usage: chatclash init [--url-env NAME|--subscription-url URL] [--proxy-auth-env NAME] [-i|-I]",
            )
        else:
            _resolve_no_input_interactive(interactive)
        result = initialize_home(home=home, dry_run=dry_run)
        changed: list[str] = []
        if not dry_run and not local_only:
            changed.extend(set_subscription_config(
                home=str(result.home),
                subscription_url=values.get("subscription_url"),
                subconverter_url=values.get("subconverter_url"),
            ))
            if values.get("proxy_auth"):
                changed.extend(set_proxy_auth(auth=values.get("proxy_auth")))
    except Exception as exc:  # pragma: no cover - Click translation
        _fail(exc)
    click.echo(f"home: {result.home}")
    click.echo(f"clash_dir: {result.clash_dir}")
    if local_only:
        click.echo("chat_env: skipped (--local-only)")
    elif not dry_run:
        click.echo("chat_env_updated: " + (", ".join(changed) if changed else "<none>"))
    if result.dry_run:
        render_success("dry-run only; no files changed")
    else:
        render_success("initialized ChatClash home")


@main.command(name="status")
@add_interactive_option
def status_command(interactive: bool | None) -> None:
    """Show this machine's ChatClash status."""
    try:
        _resolve_no_input_interactive(interactive)
        status = get_status()
    except Exception as exc:
        _fail(exc)
    for key, value in status.items():
        click.echo(f"{key}: {value}")


@main.group(name="sub")
@add_interactive_option
def sub_group(interactive: bool | None) -> None:
    """Manage subscription-backed runtime config."""
    _resolve_no_input_interactive(interactive)


@sub_group.command(name="set")
@click.option("--url-env", default=None, help="Environment variable containing the subscription URL.")
@click.option("--subconverter-url-env", default=None, help="Environment variable containing subconverter URL.")
@click.option("--subscription-url", default=None, help="Subscription URL. Prefer --url-env for secrets.")
@click.option("--subconverter-url", default=None)
@add_interactive_option
def sub_set(
    url_env: str | None,
    subconverter_url_env: str | None,
    subscription_url: str | None,
    subconverter_url: str | None,
    interactive: bool | None,
) -> None:
    """Store subscription operator config through ChatEnv."""
    try:
        if url_env:
            subscription_url = os.getenv(url_env)
            if subscription_url is None:
                raise ValueError(f"environment variable not set: {url_env}")
        if subconverter_url_env:
            subconverter_url = os.getenv(subconverter_url_env)
            if subconverter_url is None:
                raise ValueError(f"environment variable not set: {subconverter_url_env}")
        values = resolve_command_inputs(
            schema=SUB_SET_SCHEMA,
            provided={
                "subscription_url": subscription_url,
                "subconverter_url": subconverter_url,
            },
            interactive=interactive,
            usage="Usage: chatclash sub set [--url-env NAME] [-i|-I]",
        )
        changed = set_subscription_config(
            subscription_url=values.get("subscription_url"),
            subconverter_url=values.get("subconverter_url"),
        )
    except Exception as exc:
        _fail(exc)
    click.echo("updated: " + (", ".join(changed) if changed else "<none>"))


@sub_group.command(name="status")
@add_interactive_option
def sub_status(interactive: bool | None) -> None:
    """Show redacted subscription config state."""
    _resolve_no_input_interactive(interactive)
    for key, value in get_subscription_status().items():
        click.echo(f"{key}: {value}")


@sub_group.command(name="update")
@click.option("--dry-run", is_flag=True)
@click.option("--no-validate", is_flag=True)
@click.option("--fetch-proxy", default=None, help="Transient proxy for fetching this subscription update; use local for this machine proxy.")
@add_interactive_option
def sub_update(dry_run: bool, no_validate: bool, fetch_proxy: str | None, interactive: bool | None) -> None:
    """Refresh the runtime config from the configured subscription."""
    try:
        _resolve_no_input_interactive(interactive)
        result = update_subscription_config(dry_run=dry_run, no_validate=no_validate, fetch_proxy=fetch_proxy)
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


@sub_group.group(name="converter")
@add_interactive_option
def sub_converter_group(interactive: bool | None) -> None:
    """Install and manage the local subscription converter service."""
    _resolve_no_input_interactive(interactive)


@sub_converter_group.command(name="install")
@click.option("--source", default=None, help="Local file or URL to install as the converter binary.")
@click.option("--repo", default="tindy2013/subconverter", help="GitHub repo used when --source is omitted.")
@click.option("--version", default="latest", help="Release tag or latest.")
@click.option("--force", is_flag=True, help="Replace an existing converter binary.")
@click.option("--dry-run", is_flag=True)
@add_interactive_option
def sub_converter_install(source: str | None, repo: str, version: str, force: bool, dry_run: bool, interactive: bool | None) -> None:
    """Install the local subscription converter binary."""
    try:
        _resolve_no_input_interactive(interactive)
        result = install_converter(source=source, repo=repo, version=version, force=force, dry_run=dry_run)
    except Exception as exc:
        _fail(exc)
    _echo_lines(result.lines)
    if result.dry_run:
        render_success("dry-run only; no files changed")
    else:
        render_success("converter installed")


@sub_converter_group.command(name="start")
@click.option("--host", default="127.0.0.1", show_default=True, help="Converter listen host.")
@click.option("--port", type=int, default=25500, show_default=True, help="Converter listen port.")
@click.option("--dry-run", is_flag=True)
@add_interactive_option
def sub_converter_start(host: str, port: int, dry_run: bool, interactive: bool | None) -> None:
    """Start the local subscription converter service."""
    try:
        _resolve_no_input_interactive(interactive)
        result = start_converter(host=host, port=port, dry_run=dry_run)
    except Exception as exc:
        _fail(exc)
    _echo_lines(result.lines)
    if result.dry_run:
        render_success("dry-run only; no files changed")
    else:
        render_success("converter started")


@sub_converter_group.command(name="stop")
@click.option("--dry-run", is_flag=True)
@add_interactive_option
def sub_converter_stop(dry_run: bool, interactive: bool | None) -> None:
    """Stop the local subscription converter service."""
    try:
        _resolve_no_input_interactive(interactive)
        result = stop_converter(dry_run=dry_run)
    except Exception as exc:
        _fail(exc)
    _echo_lines(result.lines)
    if result.dry_run:
        render_success("dry-run only; no files changed")
    else:
        render_success("converter stopped")


@sub_converter_group.command(name="status")
@click.option("--host", default="127.0.0.1", show_default=True, help="Expected converter host for display.")
@click.option("--port", type=int, default=25500, show_default=True, help="Expected converter port for display.")
@add_interactive_option
def sub_converter_status(host: str, port: int, interactive: bool | None) -> None:
    """Show the local subscription converter service status."""
    try:
        _resolve_no_input_interactive(interactive)
        status = converter_status(host=host, port=port)
    except Exception as exc:
        _fail(exc)
    for key, value in status.items():
        click.echo(f"{key}: {value}")


@sub_converter_group.command(name="logs")
@click.option("--tail", type=int, default=100, show_default=True)
@click.option("--dry-run", is_flag=True)
@add_interactive_option
def sub_converter_logs(tail: int, dry_run: bool, interactive: bool | None) -> None:
    """Show local subscription converter logs."""
    try:
        _resolve_no_input_interactive(interactive)
        result = read_converter_logs(tail=tail, dry_run=dry_run)
    except Exception as exc:
        _fail(exc)
    _echo_lines(result.lines)
    if result.dry_run:
        render_success("dry-run only; no files changed")


@main.group(name="proxy")
@add_interactive_option
def proxy_group(interactive: bool | None) -> None:
    """Show and update local proxy endpoint settings."""
    _resolve_no_input_interactive(interactive)


@proxy_group.command(name="show")
@click.option("--no-mask", is_flag=True, help="Show configured proxy authentication in plain text.")
@add_interactive_option
def proxy_show(no_mask: bool, interactive: bool | None) -> None:
    """Show proxy endpoints for this machine."""
    _resolve_no_input_interactive(interactive)
    endpoints = get_proxy_endpoints(include_auth=True, no_mask=no_mask)
    auth = proxy_auth_status(no_mask=no_mask)
    click.echo(f"HTTP proxy: {endpoints.http}")
    click.echo(f"HTTPS proxy: {endpoints.https}")
    click.echo(f"SOCKS proxy: {endpoints.socks}")
    click.echo(f"auth_present: {'yes' if auth.present else 'no'}")
    if auth.user:
        click.echo(f"auth_user: {auth.user}")
    click.echo(f"proxy_auth: {auth.auth or '<not set>'}")


@proxy_group.command(name="env")
@click.option("--no-mask", is_flag=True, help="Output usable proxy URLs with configured auth in plain text.")
@add_interactive_option
def proxy_env(no_mask: bool, interactive: bool | None) -> None:
    """Print shell proxy environment exports."""
    _resolve_no_input_interactive(interactive)
    auth = proxy_auth_status(no_mask=no_mask)
    if auth.present and not no_mask:
        click.echo("# auth is configured; run `chatclash proxy env --no-mask` to output usable authenticated proxy URLs")
    for key, value in get_proxy_env(include_auth=True, no_mask=no_mask).items():
        click.echo(f"export {key}={value}")


@proxy_group.command(name="set")
@click.option("--http-port", "http_port_value", type=int, default=None)
@click.option("--socks-port", "socks_port_value", type=int, default=None)
@click.option("--controller-port", "controller_port_value", type=int, default=None)
@click.option("--bind-host", default=None)
@click.option("--proxy-host", "proxy_host_value", default=None)
@click.option("--dry-run", is_flag=True)
@click.option("-y", "--yes", is_flag=True, help="Accepted for write-confirmation consistency.")
@add_interactive_option
def proxy_set(
    http_port_value: int | None,
    socks_port_value: int | None,
    controller_port_value: int | None,
    bind_host: str | None,
    proxy_host_value: str | None,
    dry_run: bool,
    yes: bool,
    interactive: bool | None,
) -> None:
    """Update local proxy listener settings and re-render active config."""
    changed: list[str] = []
    render_result: dict[str, object] = {}
    _ = yes
    try:
        config = read_local_config()
        if interactive is True:
            http_port_value = click.prompt("HTTP port", type=int, default=http_port_value or int(config.get("http_port") or 7890))
            socks_port_value = click.prompt("SOCKS port", type=int, default=socks_port_value or int(config.get("socks_port") or 7891))
            controller_port_value = click.prompt("Controller port", type=int, default=controller_port_value or int(config.get("controller_port") or 9090))
            bind_host = click.prompt("Bind host", default=bind_host or str(config.get("bind_host") or "0.0.0.0"))
            proxy_host_value = click.prompt("Proxy host", default=proxy_host_value or str(config.get("proxy_host") or "127.0.0.1"))
        else:
            _resolve_no_input_interactive(interactive)
        provided = {
            "http_port": http_port_value,
            "socks_port": socks_port_value,
            "controller_port": controller_port_value,
            "bind_host": bind_host,
            "proxy_host": proxy_host_value,
        }
        changed = [key for key, value in provided.items() if value is not None and config.get(key) != value]
        if dry_run:
            render_result = render_active_config_from_local(dry_run=True)
        else:
            changed = set_proxy_config(
                http_port_value=http_port_value,
                socks_port_value=socks_port_value,
                controller_port_value=controller_port_value,
                bind_host=bind_host,
                proxy_host_value=proxy_host_value,
            )
            render_result = render_active_config_from_local(dry_run=False) if changed else {"target": str(read_local_config().get("clash_dir")), "dry_run": False}
    except Exception as exc:
        _fail(exc)
    click.echo("updated: " + (", ".join(changed) if changed else "<none>"))
    if changed or dry_run:
        click.echo(f"active_config: {render_result['target']}")
    if dry_run:
        render_success("dry-run only; no files changed")
    elif changed:
        render_success("proxy config updated; run `chatclash proxy validate` then `chatclash mihomo restart` to apply to the running service")


@proxy_group.command(name="validate")
@click.option("--dry-run", is_flag=True)
def proxy_validate(dry_run: bool) -> None:
    """Validate the current active Mihomo config."""
    result = None
    try:
        result = validate_mihomo_config(dry_run=dry_run)
    except Exception as exc:
        _fail(exc)
    if result is None:  # pragma: no cover - defensive for type checkers
        return
    _echo_lines(result.lines)
    if dry_run:
        render_success("dry-run only; no validation command ran")
    else:
        render_success("proxy config validation complete")




@main.group(name="mihomo")
@add_interactive_option
def mihomo_group(interactive: bool | None) -> None:
    """Install and manage the local runtime."""
    _resolve_no_input_interactive(interactive)


@mihomo_group.command(name="install")
@click.option("--repo", default="MetaCubeX/mihomo", show_default=True)
@click.option("--version", default="latest", show_default=True)
@click.option("--dry-run", is_flag=True)
@click.option("--force", is_flag=True)
@click.option("--daemon", is_flag=True)
@add_interactive_option
def mihomo_install(repo: str, version: str, dry_run: bool, force: bool, daemon: bool, interactive: bool | None) -> None:
    try:
        _resolve_no_input_interactive(interactive)
        result = install_mihomo(repo=repo, version=version, dry_run=dry_run, force=force, daemon=daemon)
    except Exception as exc:
        _fail(exc)
    _echo_lines(result.lines)
    if result.dry_run:
        render_success("dry-run only; no files changed")


@mihomo_group.command(name="uninstall")
@click.option("--dry-run", is_flag=True)
@click.option("--daemon", is_flag=True)
@add_interactive_option
def mihomo_uninstall(dry_run: bool, daemon: bool, interactive: bool | None) -> None:
    try:
        _resolve_no_input_interactive(interactive)
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
@add_interactive_option
def mihomo_update(repo: str, version: str, dry_run: bool, interactive: bool | None) -> None:
    try:
        _resolve_no_input_interactive(interactive)
        result = install_mihomo(repo=repo, version=version, dry_run=dry_run, force=True)
    except Exception as exc:
        _fail(exc)
    _echo_lines(result.lines)
    if result.dry_run:
        render_success("dry-run only; no files changed")


@mihomo_group.command(name="start")
@click.option("--dry-run", is_flag=True)
@add_interactive_option
def mihomo_start(dry_run: bool, interactive: bool | None) -> None:
    try:
        _resolve_no_input_interactive(interactive)
        result = start_mihomo(dry_run=dry_run)
    except Exception as exc:
        _fail(exc)
    _echo_lines(result.lines)
    if result.dry_run:
        render_success("dry-run only; no files changed")


@mihomo_group.command(name="stop")
@click.option("--dry-run", is_flag=True)
@add_interactive_option
def mihomo_stop(dry_run: bool, interactive: bool | None) -> None:
    try:
        _resolve_no_input_interactive(interactive)
        result = stop_mihomo(dry_run=dry_run)
    except Exception as exc:
        _fail(exc)
    _echo_lines(result.lines)
    if result.dry_run:
        render_success("dry-run only; no files changed")


@mihomo_group.command(name="restart")
@click.option("--dry-run", is_flag=True)
@add_interactive_option
def mihomo_restart(dry_run: bool, interactive: bool | None) -> None:
    try:
        _resolve_no_input_interactive(interactive)
        result = restart_mihomo(dry_run=dry_run)
    except Exception as exc:
        _fail(exc)
    _echo_lines(result.lines)
    if result.dry_run:
        render_success("dry-run only; no files changed")


@mihomo_group.command(name="reload")
@click.option("--dry-run", is_flag=True)
def mihomo_reload(dry_run: bool) -> None:
    """Hot-reload the current active config through Mihomo's controller."""
    result = None
    try:
        result = reload_mihomo(dry_run=dry_run)
    except Exception as exc:
        _fail(exc)
    if result is None:  # pragma: no cover - defensive for type checkers
        return
    _echo_lines(result.lines)
    if dry_run:
        render_success("dry-run only; no reload request sent")
    else:
        render_success("mihomo reload complete")


@mihomo_group.command(name="status")
@add_interactive_option
def mihomo_status(interactive: bool | None) -> None:
    _resolve_no_input_interactive(interactive)
    for key, value in get_mihomo_status().items():
        click.echo(f"{key}: {value}")


@mihomo_group.command(name="logs")
@click.option("--tail", default=100, show_default=True, type=int)
@click.option("--dry-run", is_flag=True)
@add_interactive_option
def mihomo_logs(tail: int, dry_run: bool, interactive: bool | None) -> None:
    try:
        _resolve_no_input_interactive(interactive)
        result = read_mihomo_logs(tail=tail, dry_run=dry_run)
    except Exception as exc:
        _fail(exc)
    _echo_lines(result.lines)
    if result.dry_run:
        render_success("dry-run only; no files changed")
