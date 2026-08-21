# ChatClash CLI design

ChatClash is a single-machine Mihomo management CLI. It does not orchestrate remote machines and does not expose historical implementation paths as normal user commands.

## Registered command tree

The explicit `chatclash` root uses ChatStyle's shared registered-tree renderer:

```bash
chatclash --tree        # full command and option signatures
chatclash --tree-brief  # the same groups and leaves without signatures
```

Both views traverse the live Click registry rather than a package-local renderer. The current full output is maintained in [CLI Tree](cli-tree.md).

## Responsibilities

- `init`: create the machine-local ChatClash home and starter runtime config.
- `status`: summarize local runtime, config, subscription, ports, and backup state without printing secrets.
- `sub`: manage subscription-backed config through ChatEnv and config-generation APIs.
- `proxy`: manage machine-local listener/endpoint settings and shell proxy exports.
- `mihomo`: install, update, start, stop, restart, inspect, and read logs for the local Mihomo runtime.

## Config ownership

ChatEnv stores operator-owned values:

- `CHATCLASH_HOME`
- `CHATCLASH_SUBSCRIPTION_URL`
- `CHATCLASH_PROXY_AUTH`
- `CHATCLASH_SUBCONVERTER_URL`

Machine-local config stores runtime layout and local listener facts:

- runtime config directory under `CHATCLASH_HOME`
- Mihomo binary path
- PID/log/cache paths
- HTTP/SOCKS/controller ports
- bind host and advertised proxy host

## Python API boundary

The CLI is a thin adapter over importable Python APIs:

- `chatclash.subscription`
- `chatclash.proxy`
- `chatclash.mihomo`
- `chatclash.checks`
- `chatclash.status`
- `chatclash.paths`

Command behavior should be shared through these modules, not by calling Click command callbacks.

## Security

Do not print raw subscription URLs, proxy credentials, tokens, cookies, private keys, or private workspace paths. Tests may use obvious dummy values only when they assert redaction behavior.


## ChatEnv integration checks

ChatClash registers its operator config as a ChatEnv provider. A clean install should support:

```bash
chatenv cat -t chatclash
chatenv test -t chatclash
```

`cat` must show ChatClash operator fields with sensitive values masked. `test` must validate the current local proxy path through ChatClash's proxy check API rather than only checking schema presence.

`chatclash init` follows the shared ChatStyle interactive option pattern: `-i` forces interactive confirmation, `-I` disables prompting for automation, and `-y/--yes` skips the write confirmation.



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
