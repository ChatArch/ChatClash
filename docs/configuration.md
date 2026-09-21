# 配置与 ChatEnv

| 配置层 | 保存什么 | 何时生效 |
| --- | --- | --- |
| ChatEnv / 进程环境变量 | 根目录、订阅、代理认证、转换器地址 | 后续 CLI 读取；不会通知运行中的引擎 |
| 本地 `config.yaml` | 端口、主机地址、引擎及日志路径 | CLI 生成配置、管理服务时使用 |
| `clash/config.yaml` | Mihomo 实际读取的生成配置 | 启动或显式重载/重启后 |

## 字段与优先级 {#fields}

提供者别名和存储目录统一为小写 `chatclash`。

| 字段 | 默认值 / 用途 | 敏感 |
| --- | --- | --- |
| `CHATCLASH_HOME` | 未设置时为有效 `CHATARCH_HOME` 下的 `chatclash`，通常 `~/.chatarch/chatclash` | 否 |
| `CHATCLASH_SUBSCRIPTION_URL` | 无；订阅配置生成所需 URL | 是 |
| `CHATCLASH_PROXY_AUTH` | 无；`user:password`，改为 LAN/非 loopback 监听时必需 | 是 |
| `CHATCLASH_SUBCONVERTER_URL` | 无；可选转换器基础 URL | 否，但不要在地址中嵌入秘密 |

配置优先级为 **进程 `CHATCLASH_*` 环境变量 > 当前 ChatEnv 配置 > 默认值**；命令支持的显式参数用于该次操作。根目录支持 `~` 展开。若活动配置已存储 `CHATCLASH_HOME`，仅改变 `CHATARCH_HOME` 不会覆盖它。

默认活动文件为 `~/.chatarch/envs/chatclash/.env`，命名配置为同目录的 `NAME.env`。自定义 `CHATARCH_HOME` 后，ChatEnv 存储根目录随之变化。请通过 ChatEnv 管理，不要将秘密复制到源码仓库或公开文档。

## 初始化与自动化 {#initialize}

首次使用优先交互输入：

```bash
chatclash init -i
chatenv cat -t chatclash
chatclash sub status -I
```

`cat` 默认脱敏。自动化应由受控的秘密管理工具注入环境变量，再按**变量名**传入，而不是将值写进命令参数：

```bash
chatclash init --url-env CHATCLASH_SUBSCRIPTION_URL --proxy-auth-env CHATCLASH_PROXY_AUTH -I
chatclash sub set --url-env CHATCLASH_SUBSCRIPTION_URL -I
```

`-i` 强制交互，`-I` 禁止提示。`--yes` 不会补齐缺少的配置或绕过校验。`init`、`sub set`、ChatEnv 写入都不会自动重载 Mihomo。

## 切换与导入配置 {#profiles}

```bash
chatenv new office -t chatclash -I --yes
chatenv use office -t chatclash -I
chatenv set CHATCLASH_SUBCONVERTER_URL=http://127.0.0.1:25500
chatenv cat -t chatclash
```

`new` 建立命名配置，不代表秘密已填好；`use` 选择当前配置。`chatenv set KEY=VALUE` 不带 `-t`。ChatClash **没有 `--profile` 参数**，通过 ChatEnv 选择后再运行 ChatClash。现有 shell 中的同名环境变量仍优先，切换前应清除不再需要的覆盖值。

已有权限受控的 `KEY=VALUE` 输入可经标准输入导入；不要打印内容或开启 shell 跟踪：

```bash
(
  set +x
  chatenv paste --stdin --profile office -I --yes < "$HOME/.chatarch/imports/chatclash.env"
)
chatenv use office -t chatclash -I
chatenv cat -t chatclash
```

输入文件由操作者安全准备，至少包含所需 `CHATCLASH_*` 字段；不要提交该文件。省略 `--profile office` 会写入活动配置。`paste` 读取整个 `KEY=VALUE` 流，不是 `paste KEY --stdin`。提供者发现要求见[安装](installation.md#install)。

## 目录和初始化边界 {#paths}

| 默认路径 | 用途 |
| --- | --- |
| `~/.chatarch/chatclash/config.yaml` | 本机运行布局与监听参数 |
| `~/.chatarch/chatclash/clash/config.yaml` | 引擎配置，可能包含节点凭证与认证 |
| `~/.chatarch/chatclash/bin/mihomo` | 独立于 Python 环境的引擎 |
| `~/.chatarch/chatclash/clash/backups/` | 配置备份，同样按秘密保护 |
| `~/.chatarch/chatclash/logs/`、`run/`、`cache/` | 本机运行状态 |
| `~/.config/systemd/user/chatclash-mihomo.service` | 操作系统要求的薄入口；指向 ChatArch 目录 |

`chatclash init --home "$HOME/.chatarch/chatclash-lab" -i` 初始化指定目录，并通常将根目录保存到当前 ChatEnv 配置。`--local-only` 只初始化本地文件，**不保存根目录到 ChatEnv**：

```bash
CHATCLASH_HOME="$HOME/.chatarch/chatclash-lab" chatclash init --local-only -I
CHATCLASH_HOME="$HOME/.chatarch/chatclash-lab" chatclash status -I
```

后续每次命令必须使用相同根目录；不要误操作默认部署。切换配置或根目录不会迁移文件，也不会改写既有 systemd unit 指向。

## 监听默认值与安全 {#listeners}

| 项目 | 默认值 |
| --- | --- |
| HTTP / SOCKS 端口 | `7890` / `7891` |
| 代理绑定 / 本机连接地址 | `127.0.0.1` / `127.0.0.1` |
| 管理端口 | `127.0.0.1:9090`，默认未设置 controller secret |
| 可选转换器 | 本地启动默认为 `127.0.0.1:25500` |

端口与主机地址不属于 ChatEnv 字段。新安装的 HTTP/SOCKS 配置为 `allow-lan: false` 且仅绑定 `127.0.0.1`。若用 `proxy set --bind-host` 改为 LAN/非 loopback 而没有认证，生成操作会失败并保留原配置；先通过 ChatEnv 安全地配置 `CHATCLASH_PROXY_AUTH`，再改绑定。修改代理绑定不会自动限制 controller 绑定：

```bash
chatclash proxy set --bind-host 127.0.0.1 --proxy-host 127.0.0.1 -I -y
chatclash proxy validate -I
chatclash mihomo restart -I
```

先保证已有生成配置与引擎。新生成的 controller 固定为 loopback `127.0.0.1:9090`；旧 `:9090` 或其他外部绑定需刷新生成配置后才会迁移。**局域网代理认证不等于 controller 认证**。当前 CLI 没有 controller secret/绑定专用参数，不要假设存在，也不要以手工修改生成 YAML 作为长期配置方案。

下一步：[运维与安全代理环境变量](operations.md#proxy-env) · [CLI 树](cli-tree.md)。
