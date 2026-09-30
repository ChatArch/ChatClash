# ChatClash

ChatClash is a single-machine ChatArch proxy toolkit: a Python CLI manages the separate Mihomo engine on Linux and Windows, stores operator configuration through ChatEnv, generates subscription YAML, and validates the proxy. It neither orchestrates remote hosts nor runs the proxy as a persistent Python service.

[Documentation](https://arch.gh.wzhecnu.cn/ChatClash/en/) · [Chinese edition](README.md) · [PyPI](https://pypi.org/project/chatclash/) · [Issues](https://github.com/ChatArch/ChatClash/issues)

## Choose a scenario

| Goal | Start here |
| --- | --- |
| Install/upgrade the CLI or resolve dependency conflicts | [Installation and Dependencies](docs/installation.en.md) |
| Install, import a subscription, enable or restore Windows proxy | [Windows Guide](docs/windows.en.md) |
| Set subscription, authentication, home, or profiles | [Configuration and ChatEnv](docs/configuration.en.md) |
| Refresh subscriptions, reload configuration, upgrade the engine | [Operations](docs/operations.en.md) |
| Use an authenticated proxy for one command | [Safe proxy exports](docs/operations.en.md#proxy-env) |
| Find commands, options, and boundaries | [CLI Tree](docs/cli-tree.en.md) · [Design](docs/cli-design.en.md) |

## Install and deploy

Complete standard `chatuv setup` first. Use the same virtual environment's interpreter rather than mixing system and user installations:

```bash
~/.chatarch/venv/bin/python -m pip install -U chatclash
~/.chatarch/venv/bin/python -m pip check
~/.chatarch/venv/bin/chatclash --version
```

ChatClash and ChatEnv must share an interpreter. Legacy applications requiring `chatstyle<0.2` can conflict with the required ChatStyle 0.2 series. Upgrade compatible packages selectively or isolate legacy environments; do not downgrade ChatStyle or use `--no-deps`.

The following assumes that environment's `bin` (or `Scripts` on Windows) is on `PATH`. Linux uses user-level systemd; Windows uses a managed process for the current user and needs no elevation. **New HTTP/SOCKS installations bind only to loopback; changing to a LAN/non-loopback listener requires configured proxy authentication. Generated configuration still binds the controller only to `127.0.0.1:9090`, but it has no secret and proxy authentication does not protect it. Older configuration can still use `:9090` or another external bind: refresh generated configuration after upgrading and restrict management access.**

```bash
chatclash init -i
chatclash mihomo install --daemon
chatclash sub update -I
chatclash proxy validate -I
chatclash mihomo start -I
chatclash status -I
chatenv test -t chatclash
```

`init` is not an existing deployment's upgrade command. `install --daemon` does not start the service. `chatenv test` performs online proxy checks. See the [converter procedure](docs/operations.en.md#converter) when needed.

### First run on Windows

See the [Windows Guide](docs/windows.en.md) for PowerShell installation, hidden subscription input, online checks, and recovery. Enter subscriptions only at the interactive prompt, not in command history, scripts, or issues.

In PowerShell, install into the same ChatArch environment. `mihomo install` selects the Windows x64/arm64 ZIP asset and verifies a release-provided SHA-256 digest when one is available. Windows neither needs nor installs a systemd unit:

```powershell
chatclash init -i
chatclash mihomo install -I
chatclash sub update -I
chatclash proxy validate -I
chatclash mihomo start -I
chatclash proxy system show -I
chatclash proxy system enable -I
```

`proxy system enable` writes the current-user Windows manual proxy only after `mihomo status` is running and `proxy system show` reports `ready: yes`, and backs up its prior values plus the effective WinINet connection mode for `chatclash proxy system disable -I`. For a temporary session use `chatclash proxy env --shell powershell -I`; persistent user variables require explicit `--persist --no-mask` and can be restored with `--restore`. See [Operations](docs/operations.en.md#windows).

## Which layer changes?

| Operation | Result | Explicit follow-up |
| --- | --- | --- |
| pip upgrade of `chatclash` | Updates Python CLI | Does not replace/restart the engine |
| `mihomo update` | Replaces engine binary | Validate, then `mihomo restart` |
| `sub update` | Validates candidate and replaces YAML | `proxy validate`, then `mihomo reload` |
| `init` / `sub set` / ChatEnv writes | Changes persistent configuration | Generate/apply as needed; no automatic reload |

The default root is `~/.chatarch/chatclash`; precedence is process environment > active ChatEnv profile > defaults. `proxy show`, `proxy env`, and `chatenv cat` mask secrets by default. Masked exports are display-only; consume authenticated exports only in a [non-echoing subshell](docs/operations.en.md#proxy-env).

## CLI tree

`chatclash --tree` renders full registered signatures; `chatclash --tree-brief` omits signatures. The brief output is preserved below; see the [full tree and command groups](docs/cli-tree.en.md#groups).

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
│   ├── system  # Manage the Windows current-user system proxy with backup and restore.
│   │   ├── disable  # Restore the Windows current-user proxy settings saved at enable time.
│   │   ├── enable  # Enable Windows proxy for the ready local loopback HTTP listener.
│   │   └── show  # Show Windows current-user proxy status without changing it.
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
