# Operations

| Goal | Sequence |
| --- | --- |
| Upgrade Python CLI | Install with the same interpreter → `pip check` → version/tree checks |
| Refresh subscription | `sub update` → `proxy validate` → `mihomo reload` |
| Upgrade engine | `mihomo update` → `proxy validate` → `mihomo restart` |
| Change listeners | `proxy set` → `proxy validate` → `mihomo restart` |
| Check proxy | Masked status → configuration validation → online `chatenv test` |

## CLI versus deployed service {#service}

ChatClash is a Python management CLI; Mihomo is a separate binary. The user-level `chatclash-mihomo.service` executes the engine directly, not a persistent Python service. The default layout corresponds to this command (the unit stores expanded absolute paths):

```bash
~/.chatarch/chatclash/bin/mihomo -d ~/.chatarch/chatclash/clash
```

This illustrates the execution relationship; do not launch another engine alongside an existing service. Upgrading the Python package neither replaces nor restarts the engine. `mihomo update` replaces the on-disk binary without restarting. ChatEnv writes, `init`, and `sub set` do not update the running engine's configuration.

`install --daemon` writes/enables a user unit without starting it. With that unit present, `start`, `stop`, and `restart` use `systemctl --user`; without it, `start` directly runs the engine and can occupy the foreground. Service lifecycle support targets Linux, not cross-platform service management.

## Refresh a subscription {#subscription}

```bash
chatclash sub status -I
chatclash sub update -I
chatclash proxy validate -I
chatclash mihomo reload -I
chatclash mihomo status -I
chatenv test -t chatclash
```

The update generates and validates a candidate before atomically replacing local YAML; `sub generate` and the active-config re-render in `proxy set` also write a private temporary file before replacement. Validation or replacement failure should leave the existing target configuration intact. Mihomo must already be installed. `--no-validate` explicitly bypasses validation; it is an exception, not the normal fix for a missing engine. After using it, install the engine and validate successfully before starting or applying the configuration.

File replacement is not a running-engine reload. `reload` applies configuration through the local controller without replacing the process or binary. Use `start` for first deployment and `restart` for engine upgrades or listener changes. If reload fails, preserve the error and check controller reachability/authentication instead of repeatedly refreshing subscriptions.

If a healthy proxy already runs but the subscription cannot be fetched directly, explicitly use the existing local proxy:

```bash
chatclash sub update --fetch-proxy local -I
```

This is a transient route for that download; it does not start a proxy or solve the initial bootstrap dependency. Without a converter URL, ChatClash reads Clash YAML directly; with one configured, it generates through the converter. Local generated files and backups can contain credentials: do not copy them between hosts or paste them into issues.

## Upgrades and diagnostics {#maintenance}

See [Installation](installation.md#upgrade) for CLI upgrades. Schedule engine upgrades separately, with a restart window that may interrupt connections:

```bash
chatclash mihomo update -I
chatclash proxy validate -I
chatclash mihomo restart -I
chatclash mihomo status -I
chatenv test -t chatclash
```

Read-only status and log entry points:

```bash
chatclash status -I
chatclash sub status -I
chatclash proxy show -I
chatclash mihomo logs --tail 100 -I
```

In systemd mode, `logs` displays the service status with attached log lines, not a complete historical journal query. If needed, use `journalctl --user -u chatclash-mihomo.service -n 100 --no-pager` locally; inspect/redact raw logs before sharing. A running `status` is not proof of connectivity. `proxy validate` checks configuration; `chatenv test` makes real requests to external test sites.

## Use proxy exports safely {#proxy-env}

```bash
chatclash proxy show -I
chatclash proxy env -I
```

Default masked output is for display, not executable authenticated exports. Consume `--no-mask` only inside a non-echoing subshell with tracing disabled:

```bash
(
  set +x
  eval "$(chatclash proxy env --no-mask -I)"
  curl --fail --silent --show-error --output /dev/null https://example.com
)
```

The parent shell's environment remains unchanged when the subshell exits. Do not print unmasked exports separately, run `env`/`printenv`, enable `set -x`, or use verbose request logging. Do not redirect exports into documentation or tickets. Replace the example test site with a trusted target if needed. Secrets still exist in child-process environments; this is not a security isolation boundary on a multi-user host.

## Optional subscription converter {#converter}

Deploy a converter only when the subscription format needs it. It receives the full subscription URL: use a local or trusted service, not an untrusted public converter.

```bash
chatclash sub converter install -I
chatclash sub converter start -I
chatenv set CHATCLASH_SUBCONVERTER_URL=http://127.0.0.1:25500
chatclash sub converter status -I
chatclash sub update -I
chatclash proxy validate -I
chatclash mihomo reload -I
```

This sequence assumes an already running engine; use `mihomo start` after validation for first deployment. The converter defaults to `127.0.0.1:25500`; do not accidentally expose it publicly. Its `--host`/`--port` are runtime parameters, not ChatEnv fields; update the stored base URL after changing them. `converter status --host/--port` describes the expected endpoint, not a reconfiguration of the running service.

```bash
chatclash sub converter logs --tail 100 -I
chatclash sub converter stop -I
```

`sub generate --output` writes a selected file without activating it. `sub url` masks output by default; ordinary operations do not require displaying a complete conversion URL.

## Controller security {#controller}

New HTTP/SOCKS configuration binds only to loopback; a LAN/non-loopback bind without `CHATCLASH_PROXY_AUTH` is rejected. Generated configuration binds the no-secret controller only to `127.0.0.1:9090`. **`CHATCLASH_PROXY_AUTH` protects HTTP/SOCKS listeners, not the controller.** Older configuration can still use `:9090` or another external bind: after upgrading, use `sub update` (or another configuration-rendering operation), then explicitly reload/restart. `proxy set --bind-host` is not a controller bind switch. There is no dedicated controller-auth configuration interface in the CLI. Never expose any controller bind directly to the Internet; later generation can overwrite hand edits, so temporary YAML edits are not a durable security policy.

Back to [Configuration and ChatEnv](configuration.md) · [CLI Tree](cli-tree.md).
