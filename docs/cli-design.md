# ChatClash CLI Design

## 定位

`chatclash` 当前阶段先做任务导向的单机闭环：

```text
初始化 ~/.chatarch/chatclash
  -> 下载/安装轻量 Mihomo 二进制
  -> 配置订阅 URL、代理认证和端口
  -> 刷新 Clash config.yaml
  -> 启动本机代理服务
  -> verify / ip-api 验收代理可用
```

不做多机器编排，不做 instance inventory，不把 Docker 作为当前方案候选。当前事实来源是：

```text
~/.chatarch/chatclash/config.yaml
~/.chatarch/chatclash/bin/mihomo
~/.chatarch/chatclash/clash/config.yaml
```

## ChatArch 规范

后续实现必须遵循 ChatArch 项目规范：

- 项目结构沿用 `chattool pypi init -t chatarch` 生成模板。
- CLI 入口保持 `chatclash = "chatclash.cli:main"`。
- CLI 参数和交互使用 `chatstyle`：`CommandSchema`、`CommandField`、`add_interactive_option`、`resolve_command_inputs`。
- `-i/-I`、`--dry-run`、`-y/--yes` 行为与现有 ChatArch CLI 保持一致。
- `chatenv` 只保存需要跨设备复用的值。

当前 chatenv 字段只需要两个：

```text
CHATCLASH_SUBSCRIPTION_URL
CHATCLASH_SUBCONVERTER_URL
```

说明：

- `CHATCLASH_SUBSCRIPTION_URL`：订阅 URL，敏感，默认脱敏。
- `CHATCLASH_SUBCONVERTER_URL`：subconverter 服务地址。它可能是远端服务地址，需要跨机器复用。

不引入：

```text
CHATCLASH_HOME
CHATCLASH_RULE_CONFIG_URL
CHATCLASH_HTTP_PORT
CHATCLASH_SOCKS_PORT
CHATCLASH_CONTROLLER_PORT
CHATCLASH_YACD_PORT
CHATCLASH_AUTH
```

这些都是 CLI 参数、默认值或当次生成配置，不进入 chatenv。


## 单机维护命令（当前开发方向）

当前阶段 `ChatClash` 定位为单机 Clash 维护工具：在哪台机器上使用，就在那台机器本地运行 `chatclash`。SSH 只负责进入机器，`chatclash` 不做多机器编排或 instance inventory。默认 backend 是轻量二进制 Mihomo；当前方案不提供 Docker 候选。

正式默认目录采用 Arch 系列位置：

```text
~/.chatarch/chatclash/
```

测试和开发验证应放在 Playground/任务实验区或一次性临时目录；不要把测试安装、测试 Docker 服务或临时 Clash config 写入 `~/.chatarch` 或 `/srv/clash`。

新增顶层命令：

```text
chatclash init
chatclash engine install
chatclash config show
chatclash config set
chatclash update
chatclash up/down/restart/logs
chatclash verify
chatclash ip-api
```


### Engine backend

默认：

```text
engine: binary
engine_path: ~/.chatarch/chatclash/bin/mihomo
```

`chatclash engine install` 从 Mihomo release 下载当前平台单文件二进制到 `bin/mihomo`。这比 Docker 更适合 `~/.chatarch/chatclash/` 这种轻量正式目录。


### `chatclash init`

初始化当前机器的 ChatClash home、轻量二进制运行目录、placeholder Clash `config.yaml` 和本地配置文件。默认 home 为 `~/.chatarch/chatclash/`，测试可通过 `CHATCLASH_HOME` 或 `--home` 指向临时目录。

### `chatclash config show/set`

查看或设置订阅 URL、代理认证、subconverter URL 与端口。输出必须脱敏敏感值。

### `chatclash update`

从订阅 URL 刷新 Clash 配置：直接 Clash YAML 优先；如果返回内容不是 Clash YAML，则在配置了 subconverter URL 时通过 subconverter 生成。写入前备份旧 `config.yaml`，并保留本机 header（端口、认证、controller）。

## 接口

### 1. 配置 Clash

```bash
chatclash setup clash [CLASH_DIR]
```

用途：生成 Clash + Yacd 的 Docker Compose 目录。默认目录是 `/tmp/clash`，避免误改已有 `/srv/clash`。

参数：

| 参数 | 默认值 | 说明 |
|---|---:|---|
| `CLASH_DIR` | `/tmp/clash` | 目标目录 |
| `--http-port` | `7890` | HTTP 代理端口 |
| `--socks-port` | `7891` | SOCKS 代理端口 |
| `--controller-port` | `7900` | 宿主机 controller 端口，映射容器 `9090` |
| `--yacd-port` | `9135` | Yacd 端口 |
| `--clash-image` | `dreamacro/clash` | Clash 镜像 |
| `--yacd-image` | `haishanh/yacd:master` | Yacd 镜像 |
| `--auth` | 空 | 可选代理认证，写入 config header 时脱敏展示 |
| `--dry-run` | false | 展示计划，不写文件 |
| `-y/--yes` | false | 写操作跳过确认 |
| `-i/-I` | auto | chatstyle 交互开关 |

行为：

- 创建 `CLASH_DIR/`、`CLASH_DIR/ui/`、`CLASH_DIR/backups/`。
- 生成 `docker-compose.yaml`。
- 如果没有 `config.yaml`，生成最小占位配置。
- 不记录额外 `chatclash.toml`。
- 对 `/srv/clash` 或覆盖已有文件必须确认。

生成结构：

```text
CLASH_DIR/
  docker-compose.yaml
  config.yaml
  ui/
  backups/
```

### 2. 查看状态

```bash
chatclash status [CLASH_DIR]
```

用途：读取现有文件做摘要，不依赖额外配置文件。

行为：

- 查看 `docker-compose.yaml`、`config.yaml`、`ui/`、`backups/` 是否存在。
- 从 `docker-compose.yaml` 读取端口/镜像摘要。
- 从 `config.yaml` 读取端口、controller、proxies/groups/rules 数量摘要。
- 不输出节点密钥、server、UUID、订阅 URL、认证明文。

### 3. 输出代理环境变量

```bash
chatclash proxy env [PROXY_URL]
```

用途：输出 shell 片段，不修改当前 shell。

默认：

```text
PROXY_URL=http://127.0.0.1:7890
```

输出：

```bash
export http_proxy=http://127.0.0.1:7890
export https_proxy=http://127.0.0.1:7890
export all_proxy=http://127.0.0.1:7890
export no_proxy=localhost,127.0.0.1,::1
```

复杂容器代理配置不放入主 CLI，后续写 skill/文档。

### 4. 订阅状态

```bash
chatclash sub status
```

用途：查看 chatenv/env 中的订阅和 subconverter 配置状态。

行为：

- 读取 `CHATCLASH_SUBSCRIPTION_URL`，默认脱敏。
- 读取 `CHATCLASH_SUBCONVERTER_URL`，如果未配置，提示可用 `-s/--subconverter-url` 临时传入。
- 不请求网络，不写文件。

### 5. 构造 subconverter URL

```bash
chatclash sub url [SUBSCRIPTION_URL]
chatclash sub url [SUBSCRIPTION_URL] -s http://127.0.0.1:25500
chatclash sub url [SUBSCRIPTION_URL] -l <CONFIG_URL>
chatclash sub url [SUBSCRIPTION_URL] --show
```

参数与 `reference/subconverter.md` 对齐：

| 参数 | 默认值 | 说明 |
|---|---|---|
| `SUBSCRIPTION_URL` | chatenv/env | 订阅 URL |
| `-s/--subconverter-url` | chatenv/env | subconverter 服务地址 |
| `-l/--config-url` | ACL4SSR Online | 规则配置 URL |
| `--show` | false | 显示完整 URL |
| `-i/-I` | auto | chatstyle 交互开关 |

默认脱敏输出。`--show` 会暴露订阅 URL，必须提示风险。

### 6. 生成 config.yaml

```bash
chatclash sub generate [SUBSCRIPTION_URL]
chatclash sub generate [SUBSCRIPTION_URL] -s http://127.0.0.1:25500
chatclash sub generate [SUBSCRIPTION_URL] -l <CONFIG_URL>
chatclash sub generate [SUBSCRIPTION_URL] -o /tmp/clash/config.yaml
chatclash sub generate [SUBSCRIPTION_URL] --dry-run
chatclash sub generate [SUBSCRIPTION_URL] -y
chatclash sub generate [SUBSCRIPTION_URL] --debug
```

参数与 `reference/subconverter.md` 对齐：

| 参数 | 默认值 | 说明 |
|---|---|---|
| `SUBSCRIPTION_URL` | chatenv/env | 订阅 URL |
| `-s/--subconverter-url` | chatenv/env | subconverter 服务地址 |
| `-l/--config-url` | ACL4SSR Online | 规则配置 URL |
| `-o/--output` | `/tmp/clash/config.yaml` | 输出文件 |
| `--debug` | false | 调试输出，仍需脱敏 |
| `--dry-run` | false | 展示计划，不写文件 |
| `-y/--yes` | false | 写入跳过确认 |
| `-i/-I` | auto | chatstyle 交互开关 |

实现流程：

1. 解析订阅 URL：CLI 参数优先，其次 env/chatenv。
2. 解析 subconverter URL：CLI `-s` 优先，其次 env/chatenv。
3. 如果 subconverter URL 缺失，提示用户配置 `CHATCLASH_SUBCONVERTER_URL` 或传入 `-s`。第一阶段不自动安装/启动 subconverter。
4. 按 blog 参数构造 `/sub?...` 请求。
5. `--dry-run` 展示请求目标、输出路径、备份计划，不写文件。
6. 非 dry-run 时请求 subconverter，得到 Clash YAML。
7. 在返回 YAML 前追加本机 header。
8. 校验 YAML。
9. 展示 proxies/groups/rules 摘要。
10. 写入前备份旧文件到 `output.parent/backups/`。
11. 写入 `config.yaml`。

默认 header：

```yaml
port: 7890
socks-port: 7891
allow-lan: true
mode: Rule
log-level: info
external-controller: :9090
```

如果要改变 header 端口，后续可以给 `sub generate` 增加同名端口参数；第一版可以先使用默认 header，避免过度设计。

### 7. SSR 预留

```bash
chatclash deploy ssr init
chatclash deploy ssr status
chatclash deploy ssr export
```

第一阶段只保留边界，不实现实际 SSR 部署。

## 推荐流程

### 本地测试

```bash
chatclash setup clash /tmp/clash --dry-run
chatclash setup clash /tmp/clash -y

chatenv use -t chatclash sub-main
chatclash sub status
chatclash sub url
chatclash sub generate -o /tmp/clash/config.yaml --dry-run
chatclash sub generate -o /tmp/clash/config.yaml -y

chatclash status /tmp/clash
chatclash proxy env
```

### 临时传入 URL

```bash
chatclash sub generate "$SUB_URL" -s http://127.0.0.1:25500 -o /tmp/clash/config.yaml --dry-run
chatclash sub generate "$SUB_URL" -s http://127.0.0.1:25500 -o /tmp/clash/config.yaml -y
```

### 真实目录

```bash
chatclash setup clash /srv/clash --dry-run
chatclash sub generate -o /srv/clash/config.yaml --dry-run
```

真实目录写入必须确认，不能默认覆盖。

## 第一阶段实现要求

只实现：

- `setup clash`
- `status`
- `proxy env`
- `sub status`
- `sub url`
- `sub generate`

不实现：

- `chatclash.toml`
- controller/group/proxy/rules 管理
- SSR 实际部署
- 自动安装/启动 subconverter
- 额外 `CHATCLASH_*` env 字段

