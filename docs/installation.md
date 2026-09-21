# 安装与依赖

| 你的场景 | 推荐路径 |
| --- | --- |
| 已使用 ChatArch | 在 ChatUV 建立的共享环境中安装 |
| 老应用约束冲突 | 定向升级兼容版本，或隔离旧应用 |
| 首次部署代理 | 安装 Python CLI 后，另行安装 Linux Mihomo 引擎 |

## 安装 Python CLI {#install}

需要 Python 3.10 或更高版本。先按 ChatArch 的标准流程完成 `chatuv setup`，再使用同一个解释器安装和检查：

```bash
~/.chatarch/venv/bin/python -m pip install -U chatclash
~/.chatarch/venv/bin/python -m pip check
~/.chatarch/venv/bin/chatclash --version
~/.chatarch/venv/bin/chatclash --tree
~/.chatarch/venv/bin/chatenv cat -t chatclash
```

上面使用默认 `CHATARCH_HOME=~/.chatarch`。如果自定义了 ChatArch 根目录，请对应替换路径。后续示例假设该环境的 `bin` 已在 `PATH` 中；不确定时使用完整路径，不要混用系统 Python、用户 site-packages 和其他虚拟环境。普通用户不需要源码 checkout 或 editable 安装。

ChatClash 通过 `chatenv.configs` 入口点 `chatclash = chatclash.config` 注册配置提供者。**ChatClash 与 ChatEnv 必须装在同一个解释器/虚拟环境中**；仅把两个可执行文件都加入 `PATH` 不足以保证发现。

## 依赖冲突 {#dependencies}

当前兼容范围包括 `chatstyle>=0.2.0,<0.3.0` 和 `chatenv>=0.2.11,<0.3.0`。ChatStyle 0.2 的共享命令树接口是必需依赖，不应降回旧版。

部分旧版 `chatgh`、`chatup`、`chatvideo`、`chatzulip` 约束 `chatstyle<0.2`，不能与此范围共存。以同一解释器的检查结果为准：

```bash
~/.chatarch/venv/bin/python -m pip check
~/.chatarch/venv/bin/python -m pip show chatclash chatenv chatstyle
```

| 检查结果 | 处理方法 |
| --- | --- |
| 旧应用限制 `chatstyle<0.2` | 仅升级报告中的冲突包到已兼容的版本，再执行 `pip check` |
| 旧应用没有兼容版本 | 将旧应用放进独立环境；或为 ChatClash 与 ChatEnv 建立专用环境 |
| 安装成功但仍报告冲突 | 环境尚未修复，不要把安装退出码当作兼容证明 |
| ChatEnv 找不到 `chatclash` | 核对两者所属解释器，确保提供者装在 ChatEnv 所在环境 |

不要用 `--no-deps` 绕过解析，也不要强行降级 ChatStyle。共享环境中避免无差别升级全部应用。专用环境可放在 `~/.chatarch/venvs/chatclash/`，其中同时安装 `chatclash` 和 `chatenv`，并始终使用该环境的命令。

## 首次部署 Linux 服务 {#first-deployment}

Python 包安装不等于引擎安装。当前引擎安装器选择 Linux amd64/arm64 资产，守护服务使用 Linux 用户级 systemd；不要把 Python 包的可安装性理解为 macOS/Windows 引擎与服务支持。

**启动前先限制网络入口。** 新安装的代理默认仅监听 loopback；若通过 `proxy set --bind-host` 改为 LAN/非 loopback，未配置的 `CHATCLASH_PROXY_AUTH` 会让生成操作失败而不写入配置。新生成配置将无 secret 的管理端口绑定为 `127.0.0.1:9090`。旧 `:9090` 配置需在升级后刷新生成配置；无论何种绑定，都不能直接暴露公网。代理认证不保护管理端口。

```bash
chatclash init -i
chatclash mihomo install --daemon
chatclash sub update -I
chatclash proxy validate -I
chatclash mihomo start -I
chatclash status -I
chatenv test -t chatclash
```

- `init -i` 通过交互输入订阅和 `user:password` 形式的代理认证，避免把秘密放进命令历史。
- `install --daemon` 安装引擎并写入、启用用户级 unit，**不会启动服务**。需要可用的用户 systemd 会话。
- 必须先安装引擎再 `sub update`，以便在替换配置前完成校验；不要以跳过校验作为日常安装路径。
- `chatenv test` 会请求外部站点验证代理连通性，不是纯离线配置检查。
- `init` 会重写本地布局/端口配置，不是日常升级命令；已有部署不要重复初始化来“升级”。

如果订阅需要转换器，先按[运维：订阅转换器](operations.md#converter)配置；下载失败不表示应该先启动尚未校验的代理。

## 升级哪个组件？ {#upgrade}

| 操作 | 更新对象 | 是否自动重启 Mihomo |
| --- | --- | --- |
| `python -m pip install -U chatclash` | 当前 Python 环境中的 CLI 和依赖 | 否；也不替换引擎 |
| `chatclash mihomo update` | 磁盘上的 Mihomo 二进制 | 否；需显式重启 |
| `chatclash sub update` | 本机生成的 YAML | 否；需显式校验、重载 |

详见[运行与维护](operations.md)。

## 相关链接

- [配置与 ChatEnv](configuration.md) · [CLI 树](cli-tree.md)
- [PyPI 安装包](https://pypi.org/project/chatclash/) · [源代码与问题反馈](https://github.com/ChatArch/ChatClash)
- [ChatArch 文档入口](https://arch.gh.wzhecnu.cn/)
