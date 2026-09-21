# ChatClash Documentation

Use the Python CLI to manage the separate Mihomo engine on the current machine. Installing the CLI, storing configuration, rendering YAML, and applying a service change are distinct operations; no remote orchestration or automatic restart is implied.

<div class="grid cards" markdown>

- **Installation and dependencies**

    Choose one Python environment, resolve ChatStyle conflicts, and make a first Linux service deployment.

    [Start installation](installation.md)

- **Configuration and ChatEnv**

    Find fields, precedence, active/named profiles, and machine-local paths.

    [Manage configuration](configuration.md)

- **Operations**

    Refresh subscriptions, reload configuration, upgrade the engine, and use proxy exports without echoing secrets.

    [Open operations](operations.md)

- **Commands and boundaries**

    Inspect the registered CLI tree and the separate responsibilities of the CLI, Python API, and engine service.

    [CLI Tree](cli-tree.md) · [Design](cli-design.md)

</div>

## Find an answer by problem

| Problem | Start here |
| --- | --- |
| pip installation succeeds but the environment still conflicts | [Dependency checks](installation.md#dependencies) |
| ChatEnv cannot find ChatClash | [One-interpreter installation](installation.md#install) |
| a profile switch still reads an old value | [Field precedence](configuration.md#fields) |
| custom home and `--local-only` | [Path boundaries](configuration.md#paths) |
| why a CLI upgrade did not change the proxy | [CLI and service](operations.md#service) |
| how a subscription update takes effect | [Validation and reload](operations.md#subscription) |
| why shell exports must not be pasted blindly | [Safe proxy exports](operations.md#proxy-env) |

## Safety defaults

- New HTTP/SOCKS installations listen only on loopback; a LAN/non-loopback bind is rejected until authentication is configured. New generated configuration binds the no-secret controller to `127.0.0.1:9090`. Proxy authentication does not protect management access: refresh old `:9090` configuration after upgrading and use a trusted network/firewall boundary.
- Subscription URLs, authentication, generated configuration, and backups can contain secrets. Masked output is for inspection only; do not print unmasked exports or full conversion URLs.
- `sub update` does not reload the engine; an engine upgrade does not restart it; a Python package upgrade does not replace the engine.
- Engine installation and service lifecycle currently target Linux. No macOS/Windows engine-service support is promised.

## Command output

Use `chatclash --tree` for registered commands and signatures; `chatclash --tree-brief` omits signatures. The [CLI Tree](cli-tree.md) is the authoritative rendered command map.

## Useful links

[PyPI](https://pypi.org/project/chatclash/) · [Source](https://github.com/ChatArch/ChatClash) · [Issues](https://github.com/ChatArch/ChatClash/issues) · [Release guide](release.md)
