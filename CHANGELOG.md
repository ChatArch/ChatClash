# Changelog

## 0.1.5

- Make `chatclash proxy validate` fail when a LAN-exposed active Mihomo config is missing proxy authentication or no longer matches the ChatClash/ChatEnv proxy auth source.
- Add regression tests for refreshing active Mihomo configs so `authentication` is restored before restart.
- Keep the intended LAN sharing mode while preventing unauthenticated proxy exposure.

## 0.1.4

- Add `chatclash proxy set` to update local HTTP/SOCKS/controller port and host settings, then re-render the active config header without restarting Mihomo.
- Add `chatclash proxy validate` for explicit active config validation via `mihomo -t`.
- Add `chatclash mihomo reload` as a system-level hot reload for the current active config through the Mihomo controller.

## 0.1.3

- Make SubConverter-backed generation use the documented ACL4SSR parameters (`insert=false`, `new_name=true`, and related flags) instead of the minimal `/sub` query.
- Prefer the configured SubConverter path for `sub update` when `CHATCLASH_SUBCONVERTER_URL` is set, so updates do not silently bypass the converter.
- Normalize legacy SubConverter output keys (`Proxy`, `Proxy Group`, `Rule`) and compose local proxy groups/rules when the converter returns node-only `proxies`.
- Reject generated configs that contain no usable proxies instead of writing a misleading direct-only config.
- Register `CHATCLASH_HOME` with ChatEnv and persist it during `chatclash init`, keeping runtime root selection in the same config system as subscription settings.

## 0.1.2

- Require the latest ChatEnv 0.2 line and tighten runtime dependency windows.
- Make ChatClash visible through ChatEnv provider commands such as `chatenv cat -t chatclash`.
- Make `chatenv test -t chatclash` validate the current proxy via ChatClash proxy checks, without keeping a separate public `chatclash check` CLI surface.
- Keep `proxy` read-only: print masked endpoints and shell env; configuration stays in `init`/ChatEnv.
- Add `sub converter install/start/stop/status/logs` for the local subscription converter service with default `127.0.0.1:25500` and `--host/--port` overrides.
- Route all public commands through the shared ChatStyle `-i/-I` interactive option.
- Wire `chatclash init` into the shared `-i/-I` interactive mode pattern.

## 0.1.1

- Refine the command tree to `init`, `status`, `sub`, `proxy`, and `mihomo`.
- Split CLI behavior into reusable Python API modules for subscription, proxy, Mihomo runtime, checks, status, and local paths.
- Keep sensitive subscription URLs and proxy authentication masked in command output.
- Default to a lightweight Mihomo binary backend for the single-machine flow.
- Support direct Clash YAML subscription refresh with local header/auth preservation and private backups.


## 0.1.0

### Added
- Initial CLI scaffolding and subscription conversion helpers.
- `.codex/skills/chatclash-usage` for quickstart and proxy setup notes.

### Changed
- Real Docker Compose generation and subconverter-backed config generation now match the PRD.
- Release workflow now checks build artifacts and publishes through trusted PyPI publishing.
- Docs deploy and preview workflows are aligned around the docs publishing flow.

### Fixed
- CLI and docs now use the actual ChatClash command set instead of the initial template `hello` example.
