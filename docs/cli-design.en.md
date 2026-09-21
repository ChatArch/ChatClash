# CLI Design and Boundaries

ChatClash is a Mihomo management CLI for the **current machine**. It stores configuration, renders configuration files, and invokes local service controls; it does not orchestrate remote machines or run the proxy as a persistent Python process.

## Registered commands

```bash
chatclash --tree        # complete tree with parameter signatures
chatclash --tree-brief  # same nodes without signatures
```

Both views are generated from the live Click registry. [CLI Tree](cli-tree.md) is the authoritative full output; planned capabilities are never documented as executable commands.

## Responsibility map

| Command group | Owns | Does not own |
| --- | --- | --- |
| `init` | Creates machine-local runtime files and starter configuration; optionally writes active ChatEnv values | Starting the engine or upgrading an existing deployment |
| `sub` | Stores subscription settings and generates/updates candidate YAML | Automatically reloading a running engine after a file update |
| `proxy` | Changes local listener values, validates configuration, and provides proxy endpoint information | Controller authentication or bind-policy management |
| `mihomo` | Installs, updates, starts, stops, restarts, and inspects the local engine | Upgrading the Python CLI or remote services |
| `status` | Reads local runtime, configuration, and backup summaries | Proving external network connectivity |

## Configuration and state ownership

ChatEnv stores operator configuration: `CHATCLASH_HOME`, the subscription URL, proxy authentication, and an optional converter URL. Machine-local `config.yaml` stores ports, listener hosts, binary paths, and log paths; `clash/config.yaml` is the generated file read by Mihomo.

Process `CHATCLASH_*` variables override the active ChatEnv profile. Changing a ChatEnv profile does not migrate files or make a running Mihomo process read new values. See [Configuration and ChatEnv](configuration.md) for fields and paths.

## Python API boundary

The CLI is a thin adapter over importable behavior in:

- `chatclash.subscription`
- `chatclash.proxy`
- `chatclash.mihomo`
- `chatclash.checks`
- `chatclash.status`
- `chatclash.paths`

Other Python callers should use these modules rather than Click callbacks.

## Deployed service

The user-level `chatclash-mihomo.service` runs a separate Mihomo binary directly. Upgrading the CLI package does not replace or restart that engine. A subscription update also requires an explicit `mihomo reload` or `mihomo restart` after validation to affect the running service. See [Operations](operations.md#service) for the sequence.

## Safety and verification

- `proxy show`, `proxy env`, and `chatenv cat` mask output by default. Consume authenticated exports only in the [non-echoing subshell](operations.md#proxy-env).
- New generated configuration binds the no-secret controller to `127.0.0.1:<port>`; legacy `:<port>` or externally bound configuration migrates only after a configuration rendering operation.
- `proxy validate` checks local YAML; `chatenv test -t chatclash` makes real proxy requests; a running service does not itself prove connectivity.
- Subscription data, authentication, generated YAML, and backups can contain secrets. Do not copy them between hosts or paste them into issues.
