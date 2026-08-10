<div align="center">
    <a href="https://pypi.python.org/pypi/chatclash">
        <img src="https://img.shields.io/pypi/v/chatclash.svg" alt="PyPI version" />
    </a>
</div>

# chatclash

ChatArch single-machine proxy toolkit for Mihomo runtime management, subscription-backed config generation, and ChatEnv-backed proxy validation.

## Quick start

```bash
pip install -e ".[dev]"
chatclash init
chatclash sub set -i
# If the subscription source blocks direct server fetches, use:
chatclash mihomo install --daemon
chatclash sub update
chatclash mihomo start
chatclash status
chatclash --tree
chatenv test -t chatclash
```

## CLI tree

Runtime readback comes from `chatclash --tree`:

```text
chatclash  # Manage this machine's ChatClash runtime and subscription config.
├── --help  # Show this help message.
├── --version  # Show the installed package version.
├── --tree  # Print the registered command tree.
├── init [--home <HOME>] [--dry-run] [--local-only] [--url-env <URL-ENV>] [--subscription-url <SUBSCRIPTION-URL>] [--proxy-auth-env <PROXY-AUTH-ENV>] [--proxy-auth <PROXY-AUTH>] [--subconverter-url <SUBCONVERTER-URL>] [--yes] [--interactive]  # Initialize this machine and collect required ChatEnv config.
├── mihomo [--interactive]  # Install and manage the local runtime.
│   ├── install [--repo <REPO>] [--version <VERSION>] [--dry-run] [--force] [--daemon] [--interactive]  # Install the local Mihomo binary.
│   ├── logs [--tail <TAIL>] [--dry-run] [--interactive]  # Show local Mihomo runtime logs.
│   ├── reload [--dry-run] [--interactive]  # Hot-reload the current active config through Mihomo's controller.
│   ├── restart [--dry-run] [--interactive]  # Restart the local Mihomo runtime.
│   ├── start [--dry-run] [--interactive]  # Start the local Mihomo runtime.
│   ├── status [--interactive]  # Show local Mihomo runtime status.
│   ├── stop [--dry-run] [--interactive]  # Stop the local Mihomo runtime.
│   ├── uninstall [--dry-run] [--daemon] [--interactive]  # Uninstall the local Mihomo binary.
│   └── update [--repo <REPO>] [--version <VERSION>] [--dry-run] [--interactive]  # Update the local Mihomo binary.
├── proxy [--interactive]  # Show and update local proxy endpoint settings.
│   ├── env [--no-mask] [--interactive]  # Print shell proxy environment exports.
│   ├── set [--http-port <HTTP-PORT-VALUE>] [--socks-port <SOCKS-PORT-VALUE>] [--controller-port <CONTROLLER-PORT-VALUE>] [--bind-host <BIND-HOST>] [--proxy-host <PROXY-HOST-VALUE>] [--dry-run] [--yes] [--interactive]  # Update local proxy listener settings and re-render active config.
│   ├── show [--no-mask] [--interactive]  # Show proxy endpoints for this machine.
│   └── validate [--dry-run] [--interactive]  # Validate the current active Mihomo config.
├── status [--interactive]  # Show this machine's ChatClash status.
└── sub [--interactive]  # Manage subscription-backed runtime config.
    ├── converter [--interactive]  # Install and manage the local subscription converter service.
    │   ├── install [--source <SOURCE>] [--repo <REPO>] [--version <VERSION>] [--force] [--dry-run] [--interactive]  # Install the local subscription converter binary.
    │   ├── logs [--tail <TAIL>] [--dry-run] [--interactive]  # Show local subscription converter logs.
    │   ├── start [--host <HOST>] [--port <PORT>] [--dry-run] [--interactive]  # Start the local subscription converter service.
    │   ├── status [--host <HOST>] [--port <PORT>] [--interactive]  # Show the local subscription converter service status.
    │   └── stop [--dry-run] [--interactive]  # Stop the local subscription converter service.
    ├── generate [<SUBSCRIPTION-URL>] [--subconverter-url <SUBCONVERTER-URL>] [--output <OUTPUT>] [--dry-run] [--yes] [--interactive]  # Generate a Clash-compatible config through subscription conversion.
    ├── set [--url-env <URL-ENV>] [--subconverter-url-env <SUBCONVERTER-URL-ENV>] [--subscription-url <SUBSCRIPTION-URL>] [--subconverter-url <SUBCONVERTER-URL>] [--interactive]  # Store subscription operator config through ChatEnv.
    ├── status [--interactive]  # Show redacted subscription config state.
    ├── update [--dry-run] [--no-validate] [--fetch-proxy <FETCH-PROXY>] [--interactive]  # Refresh the runtime config from the configured subscription.
    └── url [<SUBSCRIPTION-URL>] [--subconverter-url <SUBCONVERTER-URL>] [--show] [--interactive]  # Build a subconverter URL for the configured subscription.
```

## Common commands

```bash
chatclash sub status
chatclash sub converter status
chatclash sub update
chatclash proxy set --http-port 7890 --socks-port 7891 --controller-port 9090 -I -y
chatclash proxy validate
chatclash mihomo update
chatclash mihomo restart
chatclash mihomo logs
chatclash proxy show
eval "$(chatclash proxy env)"
python -m pytest -q
```

## ChatArch conventions

- CLI interaction uses ChatStyle helpers and the shared `-i/-I` pattern where applicable.
- Operator config and `CHATCLASH_HOME` are stored through ChatEnv; local config stores only derived runtime facts.
- Major CLI capabilities have reusable Python APIs under `src/chatclash/` modules.
- Sensitive values must not be printed in CLI output, logs, docs, or tests.

## ChatEnv fields

| Field | Notes |
|---|---|
| `CHATCLASH_HOME` | Machine-local ChatClash runtime directory |
| `CHATCLASH_SUBSCRIPTION_URL` | Subscription URL, sensitive |
| `CHATCLASH_PROXY_AUTH` | Proxy authentication, sensitive |
| `CHATCLASH_SUBCONVERTER_URL` | Optional subconverter service base URL |

Machine-local ports, hosts, runtime paths, PID files, and log files live in ChatClash local config rather than ChatEnv. `CHATCLASH_HOME` is the ChatEnv-managed root used to locate that local config.



## Local subscription converter service

`chatclash sub converter` manages the local subscription converter service used by `CHATCLASH_SUBCONVERTER_URL`. Host and port are service runtime parameters, not ChatEnv fields.

```bash
chatclash sub converter install
chatclash sub converter start              # default http://127.0.0.1:25500
chatclash sub converter start --host 0.0.0.0 --port 26666
chatclash sub converter status
chatclash sub converter logs --tail 200
chatclash sub converter stop
```

After starting a local converter, store its base URL through ChatEnv when this machine should use it for subscription conversion:

```bash
chatenv set CHATCLASH_SUBCONVERTER_URL='http://127.0.0.1:25500'
chatclash sub url --show -I
chatclash sub update
```

When `CHATCLASH_SUBCONVERTER_URL` is configured, `chatclash sub generate` and `chatclash sub update` use the converter endpoint to regenerate the local Mihomo config. The generated `config.yaml` is a machine-local artifact: do not copy it between machines. To refresh another host, configure that host's subscription/converter settings and run generation there.

The converter request follows the original ACL4SSR/SubConverter contract (`target=clash`, `insert=false`, `new_name=true`, and related compatibility flags). Some providers return node-only YAML; ChatClash composes the local listener header, authentication, default groups, and rules around those generated nodes.


## Authentication and ChatEnv

All public commands expose the shared ChatStyle `-i/-I` interactive option. For first-time machine setup, run `chatclash init` interactively, or pass values explicitly for automation:

```bash
chatclash init --url-env CHATCLASH_SUBSCRIPTION_URL --proxy-auth-env CHATCLASH_PROXY_AUTH -I
chatclash proxy show              # masked
chatclash proxy show --no-mask    # shows authenticated proxy URLs
chatclash proxy env --no-mask     # usable authenticated http_proxy/https_proxy/all_proxy exports
```

ChatEnv remains the system of record:

```bash
chatenv cat -t chatclash
chatenv cat -t chatclash --no-mask
chatenv test -t chatclash
```
