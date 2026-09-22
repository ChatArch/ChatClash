# Configuration and ChatEnv

| Layer | Contents | When it takes effect |
| --- | --- | --- |
| ChatEnv / process environment | Home, subscription, proxy authentication, converter URL | Subsequent CLI reads; no notification to the running engine |
| Local `config.yaml` | Ports, hosts, engine and log paths | CLI configuration generation and service management |
| `clash/config.yaml` | Generated configuration read by Mihomo | Startup or explicit reload/restart |

## Fields and precedence {#fields}

The canonical provider alias and storage directory are lowercase `chatclash`.

| Field | Default / purpose | Sensitive |
| --- | --- | --- |
| `CHATCLASH_HOME` | When absent, `chatclash` under the effective `CHATARCH_HOME`, normally `~/.chatarch/chatclash` | No |
| `CHATCLASH_SUBSCRIPTION_URL` | None; URL for subscription-backed generation | Yes |
| `CHATCLASH_PROXY_AUTH` | None; `user:password`, required for a LAN/non-loopback listener | Yes |
| `CHATCLASH_SUBCONVERTER_URL` | None; optional converter base URL | No, but do not embed secrets |

Precedence is **process `CHATCLASH_*` environment > active ChatEnv profile > defaults**; explicit options supported by a command apply to that operation. Home paths expand `~`. Changing `CHATARCH_HOME` does not override an explicitly stored `CHATCLASH_HOME` in the active profile.

The default active file is `~/.chatarch/envs/chatclash/.env`; named profiles are `NAME.env` in the same directory. A custom `CHATARCH_HOME` also relocates ChatEnv's storage root. Manage these through ChatEnv, and never copy secrets into a source repository or public documentation.

## Initialization and automation {#initialize}

Prefer interactive input on first setup:

```bash
chatclash init -i
chatenv cat -t chatclash
chatclash sub status -I
```

`cat` masks sensitive fields by default. For automation, inject environment variables through a trusted secret manager and pass their **names**, not secret values in command arguments:

```bash
chatclash init --url-env CHATCLASH_SUBSCRIPTION_URL --proxy-auth-env CHATCLASH_PROXY_AUTH -I
chatclash sub set --url-env CHATCLASH_SUBSCRIPTION_URL -I
```

`-i` forces interactive input; `-I` disables prompts. `--yes` does not supply missing configuration or bypass validation. `init`, `sub set`, and ChatEnv writes do not automatically reload Mihomo.

## Select and import profiles {#profiles}

```bash
chatenv new office -t chatclash -I --yes
chatenv use office -t chatclash -I
chatenv set CHATCLASH_SUBCONVERTER_URL=http://127.0.0.1:25500
chatenv cat -t chatclash
```

`new` creates a named profile, not populated credentials; `use` selects it. `chatenv set KEY=VALUE` takes no `-t`. ChatClash **has no `--profile` option**: select through ChatEnv before running ChatClash. Existing shell environment variables still take precedence; remove stale overrides before switching.

Import existing, access-controlled `KEY=VALUE` input through stdin. Do not print its contents or enable shell tracing:

```bash
(
  set +x
  chatenv paste --stdin --profile office -I --yes < "$HOME/.chatarch/imports/chatclash.env"
)
chatenv use office -t chatclash -I
chatenv cat -t chatclash
```

Prepare the input file securely with the required `CHATCLASH_*` fields; never commit it. Omit `--profile office` to write the active profile. `paste` consumes a complete `KEY=VALUE` stream, not `paste KEY --stdin`. See [Installation](installation.md#install) for provider discovery requirements.

## Paths and initialization boundaries {#paths}

| Default path | Purpose |
| --- | --- |
| `~/.chatarch/chatclash/config.yaml` | Machine-local layout and listeners |
| `~/.chatarch/chatclash/clash/config.yaml` | Engine configuration; may contain node and proxy credentials |
| `~/.chatarch/chatclash/bin/mihomo` | Engine independent of the Python environment |
| `~/.chatarch/chatclash/clash/backups/` | Configuration backups; protect as secrets too |
| `~/.chatarch/chatclash/logs/`, `run/`, `cache/` | Local runtime state |
| `~/.config/systemd/user/chatclash-mihomo.service` | OS-required thin entry pointing into ChatArch home |

`chatclash init --home "$HOME/.chatarch/chatclash-lab" -i` initializes that root and normally persists it in the active ChatEnv profile. `--local-only` initializes local files but **does not persist the root to ChatEnv**:

```bash
CHATCLASH_HOME="$HOME/.chatarch/chatclash-lab" chatclash init --local-only -I
CHATCLASH_HOME="$HOME/.chatarch/chatclash-lab" chatclash status -I
```

Use the same root on every subsequent command to avoid operating on the default deployment. Switching profiles or roots does not migrate files or rewrite an existing systemd unit's targets.

## Listener defaults and security {#listeners}

| Setting | Default |
| --- | --- |
| HTTP / SOCKS ports | `7890` / `7891` |
| Proxy bind / local connection host | `127.0.0.1` / `127.0.0.1` |
| Controller | `127.0.0.1:9090`, with no controller secret by default |
| Optional local converter | Starts on `127.0.0.1:25500` by default |

Ports and hosts are not ChatEnv fields. New HTTP/SOCKS configuration uses `allow-lan: false` and binds only to `127.0.0.1`. If `proxy set --bind-host` changes the listener to LAN/non-loopback without authentication, generation fails and preserves the current config; configure `CHATCLASH_PROXY_AUTH` safely through ChatEnv before changing the bind. Changing the proxy bind address does not automatically restrict the controller bind:

```bash
chatclash proxy set --bind-host 127.0.0.1 --proxy-host 127.0.0.1 -I -y
chatclash proxy validate -I
chatclash mihomo restart -I
```

An installed engine and generated configuration are prerequisites. New generated configuration uses loopback `127.0.0.1:9090`; legacy `:9090` or other external binds migrate only after configuration is rendered again. **LAN proxy authentication is not controller authentication**. The CLI has no dedicated controller secret/bind options; do not invent them or rely on hand edits to generated YAML as durable configuration.

Next: [Operations and safe proxy exports](operations.md#proxy-env) · [CLI Tree](cli-tree.md).
