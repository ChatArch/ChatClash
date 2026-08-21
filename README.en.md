<div align="center">
    <a href="https://pypi.python.org/pypi/chatclash">
        <img src="https://img.shields.io/pypi/v/chatclash.svg" alt="PyPI version" />
    </a>
</div>

# chatclash

ChatArch single-machine proxy toolkit for Mihomo runtime management, subscription-backed config generation, and ChatEnv-backed proxy validation.

## Quick Start

```bash
pip install -e ".[dev]"
chatclash init
chatclash sub set -i
chatclash mihomo install --daemon
chatclash sub update
chatclash mihomo start
chatclash status
chatclash --tree
chatclash --tree-brief
chatenv test -t chatclash
```

## CLI tree

`chatclash --tree` renders signatures from the registered Click commands. The compact `chatclash --tree-brief` view keeps the same nodes:

```text
chatclash
├── --help  # Show this message and exit.
├── --version  # Show the version and exit.
├── --tree  # Print the registered CLI tree and exit.
├── --tree-brief  # Print the registered CLI tree without parameter signatures and exit.
├── --interactive  # Auto prompt on missing args, -i forces interactive, -I disables it.
├── init  # Initialize this machine and collect required ChatEnv config.
├── mihomo  # Install and manage the local runtime.
│   ├── install  # Install the local Mihomo binary.
│   ├── logs  # Show local Mihomo runtime logs.
│   ├── reload  # Hot-reload the current active config through Mihomo's controller.
│   ├── restart  # Restart the local Mihomo runtime.
│   ├── start  # Start the local Mihomo runtime.
│   ├── status  # Show local Mihomo runtime status.
│   ├── stop  # Stop the local Mihomo runtime.
│   ├── uninstall  # Uninstall the local Mihomo binary.
│   └── update  # Update the local Mihomo binary.
├── proxy  # Show and update local proxy endpoint settings.
│   ├── env  # Print shell proxy environment exports.
│   ├── set  # Update local proxy listener settings and re-render active config.
│   ├── show  # Show proxy endpoints for this machine.
│   └── validate  # Validate the current active Mihomo config.
├── status  # Show this machine's ChatClash status.
└── sub  # Manage subscription-backed runtime config.
    ├── converter  # Install and manage the local subscription converter service.
    │   ├── install  # Install the local subscription converter binary.
    │   ├── logs  # Show local subscription converter logs.
    │   ├── start  # Start the local subscription converter service.
    │   ├── status  # Show the local subscription converter service status.
    │   └── stop  # Stop the local subscription converter service.
    ├── generate  # Generate a Clash-compatible config through subscription conversion.
    ├── set  # Store subscription operator config through ChatEnv.
    ├── status  # Show redacted subscription config state.
    ├── update  # Refresh the runtime config from the configured subscription.
    └── url  # Build a subconverter URL for the configured subscription.
```

## Common commands

```bash
chatclash sub status
chatclash sub url "$SUBSCRIPTION_URL" -s http://127.0.0.1:25500
chatclash sub generate "$SUBSCRIPTION_URL" -s http://127.0.0.1:25500 -o <OUTPUT_CONFIG> -y
chatclash proxy show
eval "$(chatclash proxy env)"
python -m pytest -q
```

## ChatArch conventions

- CLI interaction and registered full/brief tree rendering use ChatStyle, including the shared `-i/-I` pattern where applicable.
- Operator config and `CHATCLASH_HOME` are stored through ChatEnv; local config stores only derived runtime facts.
- Major CLI capabilities have reusable Python APIs under `src/chatclash/` modules.
- Sensitive values must not be printed in CLI output, logs, docs, or tests.



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
