# ChatClash

ChatClash 是 ChatArch 的单机代理管理工具：用 Python CLI 管理独立的 Mihomo 引擎（Linux 与 Windows），通过 ChatEnv 保存配置，生成订阅 YAML 并校验代理。它不编排远程机器，也不把 Python CLI 当作常驻代理服务。

[文档站](https://arch.gh.wzhecnu.cn/ChatClash/) · [英文版](README.en.md) · [PyPI](https://pypi.org/project/chatclash/) · [问题反馈](https://github.com/ChatArch/ChatClash/issues)

## 按场景进入

| 我想做什么 | 从这里开始 |
| --- | --- |
| 安装、升级 CLI 或解决依赖冲突 | [安装与依赖](docs/installation.md) |
| 配置订阅、认证、根目录或切换配置 | [配置与 ChatEnv](docs/configuration.md) |
| 刷新订阅、重载配置、升级引擎 | [运行与维护](docs/operations.md) |
| 给单个命令使用带认证的代理 | [安全代理环境变量](docs/operations.md#proxy-env) |
| 查找命令、参数和功能边界 | [CLI 树](docs/cli-tree.md) · [设计边界](docs/cli-design.md) |

## 安装与首次运行

先完成标准 `chatuv setup`。使用同一虚拟环境的解释器，避免系统/用户安装混用：

```bash
~/.chatarch/venv/bin/python -m pip install -U chatclash
~/.chatarch/venv/bin/python -m pip check
~/.chatarch/venv/bin/chatclash --version
```

ChatClash 与 ChatEnv 必须装在同一解释器中。旧应用的 `chatstyle<0.2` 约束可能与必需的 ChatStyle 0.2 冲突；定向升级兼容包或隔离旧环境，不要降级 ChatStyle 或用 `--no-deps`。

下面假设该环境的 `bin`（Windows 为 `Scripts`）已加入 `PATH`。Linux 使用用户级 systemd；Windows 用当前用户下的受控 Mihomo 进程，不要求管理员权限。**新安装的 HTTP/SOCKS 代理只绑定 loopback；若改为 LAN/非 loopback 监听，ChatClash 会要求已配置代理认证。生成的 controller 仍只绑定 `127.0.0.1:9090`，但没有 secret；代理认证也不能保护它。旧配置可能仍使用 `:9090` 或其他外部绑定，升级后刷新生成配置并限制可信管理入口。**

```bash
chatclash init -i
chatclash mihomo install --daemon
chatclash sub update -I
chatclash proxy validate -I
chatclash mihomo start -I
chatclash status -I
chatenv test -t chatclash
```

`init` 不是已有部署的升级命令；`install --daemon` 不启动服务。`chatenv test` 会联网测试代理。需要转换器时先看[对应流程](docs/operations.md#converter)。

### Windows 首次运行

在 PowerShell 中使用同一 ChatArch 环境安装，`mihomo install` 会选择 Windows x64 或 arm64 ZIP 资产并校验发布元数据提供的 SHA-256（如有）。Windows 不需要也不会安装 systemd unit：

```powershell
chatclash init -i
chatclash mihomo install -I
chatclash sub update -I
chatclash proxy validate -I
chatclash mihomo start -I
chatclash proxy system show -I
chatclash proxy system enable -I
```

只有 `mihomo status` 显示运行且 `proxy system show` 的 `ready: yes` 时，`proxy system enable` 才会写当前用户的 Windows 手动代理，并先备份原值及 WinINet 的有效连接模式；完成后用 `chatclash proxy system disable -I` 恢复。临时 PowerShell 会话用 `chatclash proxy env --shell powershell -I`；长期用户环境变量须显式 `--persist --no-mask`，并用 `--restore` 恢复。详见[运行与维护](docs/operations.md#windows)。

## 哪一层发生变化？

| 操作 | 结果 | 仍需显式执行 |
| --- | --- | --- |
| pip 升级 `chatclash` | 更新 Python CLI | 不替换/重启引擎 |
| `mihomo update` | 替换引擎二进制 | 校验后 `mihomo restart` |
| `sub update` | 校验候选并替换 YAML | `proxy validate` 后 `mihomo reload` |
| `init` / `sub set` / ChatEnv 写入 | 修改持久配置 | 按需生成并显式应用，不自动重载 |

默认根目录为 `~/.chatarch/chatclash`；字段优先级是进程环境变量 > 活动 ChatEnv 配置 > 默认值。`proxy show`、`proxy env` 和 `chatenv cat` 默认脱敏；脱敏导出只供展示。带认证导出只在[不回显的子 shell](docs/operations.md#proxy-env)内消费。

## CLI 树

完整树由 `chatclash --tree` 从注册命令生成；`chatclash --tree-brief` 省略参数签名。下方原样保留生成输出，中文说明见[分组导航](docs/cli-tree.md#groups)。

```text
chatclash
├── --help  # Show this message and exit.
├── --version  # Show the version and exit.
├── --tree  # Print the registered CLI tree and exit.
├── --tree-brief  # Print the registered CLI tree without parameter signatures and exit.
├── --interactive  # Auto prompt on missing args, -i forces interactive, -I disables it.
├── init [--home HOME] [--dry-run] [--local-only] [--url-env URL-ENV] [--subscription-url SUBSCRIPTION-URL] [--proxy-auth-env PROXY-AUTH-ENV] [--proxy-auth PROXY-AUTH] [--subconverter-url SUBCONVERTER-URL] [--yes] [--interactive]  # Initialize this machine and collect required ChatEnv config.
├── mihomo [--interactive]  # Install and manage the local runtime.
│   ├── install [--repo REPO] [--version VERSION] [--dry-run] [--force] [--daemon] [--interactive]  # Install the local Mihomo binary.
│   ├── logs [--tail TAIL] [--dry-run] [--interactive]  # Show local Mihomo runtime logs.
│   ├── reload [--dry-run] [--interactive]  # Hot-reload the current active config through Mihomo's controller.
│   ├── restart [--dry-run] [--interactive]  # Restart the local Mihomo runtime.
│   ├── start [--dry-run] [--interactive]  # Start the local Mihomo runtime.
│   ├── status [--interactive]  # Show local Mihomo runtime status.
│   ├── stop [--dry-run] [--interactive]  # Stop the local Mihomo runtime.
│   ├── uninstall [--dry-run] [--daemon] [--interactive]  # Uninstall the local Mihomo binary.
│   └── update [--repo REPO] [--version VERSION] [--dry-run] [--interactive]  # Update the local Mihomo binary.
├── proxy [--interactive]  # Show and update local proxy endpoint settings.
│   ├── env [--no-mask] [--shell SHELL-NAME] [--persist] [--restore] [--dry-run] [--interactive]  # Print shell proxy environment exports.
│   ├── set [--http-port HTTP-PORT-VALUE] [--socks-port SOCKS-PORT-VALUE] [--controller-port CONTROLLER-PORT-VALUE] [--bind-host BIND-HOST] [--proxy-host PROXY-HOST-VALUE] [--dry-run] [--yes] [--interactive]  # Update local proxy listener settings and re-render active config.
│   ├── show [--no-mask] [--interactive]  # Show proxy endpoints for this machine.
│   ├── system [--interactive]  # Manage the Windows current-user system proxy with backup and restore.
│   │   ├── disable [--dry-run] [--interactive]  # Restore the Windows current-user proxy settings saved at enable time.
│   │   ├── enable [--dry-run] [--interactive]  # Enable Windows proxy for the ready local loopback HTTP listener.
│   │   └── show [--interactive]  # Show Windows current-user proxy status without changing it.
│   └── validate [--dry-run] [--interactive]  # Validate the current active Mihomo config.
├── status [--interactive]  # Show this machine's ChatClash status.
└── sub [--interactive]  # Manage subscription-backed runtime config.
    ├── converter [--interactive]  # Install and manage the local subscription converter service.
    │   ├── install [--source SOURCE] [--repo REPO] [--version VERSION] [--force] [--dry-run] [--interactive]  # Install the local subscription converter binary.
    │   ├── logs [--tail TAIL] [--dry-run] [--interactive]  # Show local subscription converter logs.
    │   ├── start [--host HOST] [--port PORT] [--dry-run] [--interactive]  # Start the local subscription converter service.
    │   ├── status [--host HOST] [--port PORT] [--interactive]  # Show the local subscription converter service status.
    │   └── stop [--dry-run] [--interactive]  # Stop the local subscription converter service.
    ├── generate [SUBSCRIPTION-URL] [--subconverter-url SUBCONVERTER-URL] [--output OUTPUT] [--dry-run] [--yes] [--interactive]  # Generate a Clash-compatible config through subscription conversion.
    ├── set [--url-env URL-ENV] [--subconverter-url-env SUBCONVERTER-URL-ENV] [--subscription-url SUBSCRIPTION-URL] [--subconverter-url SUBCONVERTER-URL] [--interactive]  # Store subscription operator config through ChatEnv.
    ├── status [--interactive]  # Show redacted subscription config state.
    ├── update [--dry-run] [--no-validate] [--fetch-proxy FETCH-PROXY] [--interactive]  # Refresh the runtime config from the configured subscription.
    └── url [SUBSCRIPTION-URL] [--subconverter-url SUBCONVERTER-URL] [--show] [--interactive]  # Build a subconverter URL for the configured subscription.
```
