# Changelog

## 0.1.9

- 新安装的 HTTP/SOCKS 代理默认只绑定 loopback；任何 LAN/非 loopback 生成在缺少 `CHATCLASH_PROXY_AUTH` 时会失败并保留原配置。
- 新生成的 Mihomo 配置将无 secret 的 controller 固定绑定至 `127.0.0.1:<port>`，避免默认 `:<port>` 的网络暴露；旧配置须通过订阅更新或其他生成操作后显式重载/重启才迁移。
- `proxy env` 现在对每个导出值使用 POSIX shell quoting；配合文档中的非回显子 shell，避免本地端点文本被当作额外 shell 语法。
- `chatclash status` 现在读取活动 YAML 的实际 controller 绑定，不再把 loopback 管理端口误报为裸 `:port`。

- 修复默认运行目录未继承 `CHATARCH_HOME`、profile 中 `~` 路径未展开的问题；只读取 ChatClash active profile，避免反复加载其他服务的配置。
- 订阅更新改为在同目录私有临时文件中生成和校验，校验通过后备份并原子替换；`sub generate` 和活动配置重渲染也采用原子替换。校验或替换失败保留当前配置，缺失 Mihomo 时不再静默跳过校验。
- ChatEnv 依赖基线更新为 `>=0.2.11,<0.3.0`，保留 ChatStyle `>=0.2.0,<0.3.0` 的真实 CLI 树要求；新增依赖一致性、wheel 安装和 provider 发现验证。
- 完善中英文安装、依赖冲突排查、ChatEnv 配置和服务运维文档，区分 Python CLI、Mihomo 引擎、systemd、订阅生成与热加载。
- 扩充配置优先级、隔离 HOME、profile 切换、订阅失败保护等回归测试。

## 0.1.8 - 2026-08-21

- Replace the package-local CLI tree renderer with ChatStyle's registered Click tree runtime.
- Add top-level `chatclash --tree-brief` while preserving the full command signatures in `--tree`.
- Align the runtime bounds with `chatstyle>=0.2.0,<0.3.0` and `chatenv>=0.2.10,<0.3.0`.
- Add source, CI, docs, and release-contract coverage for the shared full and brief tree views.

## 0.1.7 - 2026-08-12

- Add the MkDocs Material emoji renderer baseline so Material icon shorthand cannot leak into generated/live pages.
- Broaden the docs extra to the current ChatArch Material compatibility window.
- Harden tag-driven PyPI publishing with tag/package-version, default-branch ancestry, and exact PyPI version guards.
- Add installed `chatclash --version` / `chatclash --tree` smoke checks to CI.

## 0.1.6

- Add top-level `chatclash --tree` generated from the registered Click command tree.
- Add tests for help/tree/version output and keep template `hello` absent from the visible CLI.
- Align MkDocs site metadata, public-domain Preview Docs links, docs dependency bounds, package documentation URL, and PyPI trusted-publishing workflow.

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
