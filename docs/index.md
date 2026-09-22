# ChatClash 文档

用 Python CLI 管理当前机器上的独立 Mihomo 引擎。安装 CLI、保存配置、生成 YAML 和重载服务是不同操作；没有远程编排或自动重启的隐含步骤。

<div class="grid cards" markdown>

- **安装与依赖**

    选择同一 Python 环境，处理 ChatStyle 版本冲突，首次部署 Linux 服务。

    [开始安装](installation.md)

- **配置与 ChatEnv**

    查字段、优先级、活动配置、命名配置及本地路径。

    [管理配置](configuration.md)

- **运行与维护**

    更新订阅、重载配置、更新引擎，以及不回显秘密的代理用法。

    [进入运维](operations.md)

- **命令与边界**

    查看真实注册树，以及 CLI、Python API、引擎服务各自职责。

    [CLI 树](cli-tree.md) · [设计边界](cli-design.md)

</div>

## 按问题查找

| 问题 | 入口 |
| --- | --- |
| pip 安装成功，但环境仍冲突 | [依赖检查](installation.md#dependencies) |
| ChatEnv 找不到 ChatClash | [同一解释器安装](installation.md#install) |
| 切换配置后仍读到旧值 | [字段优先级](configuration.md#fields) |
| 自定义根目录与 `--local-only` | [目录边界](configuration.md#paths) |
| 升级 CLI 后代理为何没变 | [CLI 与服务](operations.md#service) |
| 订阅更新后如何生效 | [校验与重载](operations.md#subscription) |
| shell 导出为何不能直接使用 | [安全代理环境变量](operations.md#proxy-env) |

## 安全默认值须知

- 新安装的 HTTP/SOCKS 只监听 loopback；改为 LAN/非 loopback 会在未配置认证时被拒绝。新生成配置将无 secret 的 controller 绑定到 `127.0.0.1:9090`。代理认证不保护管理端口；旧 `:9090` 配置升级后要刷新生成配置，并限制可信网络/防火墙入口。
- 订阅地址、认证、生成配置与备份都可能包含秘密。默认脱敏输出仅供查看，不要打印未脱敏导出或完整转换 URL。
- `sub update` 不自动重载；引擎升级不自动重启；Python 包升级不替换引擎。
- 当前引擎安装和服务生命周期面向 Linux，不承诺 macOS/Windows 引擎支持。

## CLI 树

`chatclash --tree` 带参数签名，`chatclash --tree-brief` 保留相同节点但省略签名。完整视图见 [CLI 树](cli-tree.md)，简版原样如下：

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

## 相关链接

[PyPI](https://pypi.org/project/chatclash/) · [源码](https://github.com/ChatArch/ChatClash) · [问题反馈](https://github.com/ChatArch/ChatClash/issues) · [维护者发版指南](release.md)
