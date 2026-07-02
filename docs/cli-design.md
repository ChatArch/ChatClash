# ChatClash 单机 CLI 路线

## 定位

`chatclash` 是单机 Clash/Mihomo 管理工具：在哪台机器上运行，就管理这台机器上的代理服务。

它不做多机器 `remote` / `instance` 编排，也不自己发明一套 env/config 系统：

- 用户可配置/可复用的运行配置走 ChatEnv，包括订阅、认证、端口和订阅拉取代理。
- 本机运行布局和状态留在 `~/.chatarch/chatclash/`，例如二进制路径、PID、日志和生成后的 Mihomo config。
- 运行的应用叫 `mihomo`，CLI 里不再叫抽象的 `engine`。
- 启动、停止、自启动都属于 Mihomo 这个本机服务，不再单独暴露 `daemon` 组。

## 最终 CLI 树

```text
chatclash
├── init
│
├── status
│
├── subscription
│   ├── set
│   ├── status
│   └── update
│
├── mihomo
│   ├── install
│   ├── uninstall
│   ├── update
│   ├── start
│   ├── stop
│   ├── restart
│   ├── status
│   └── logs
│
├── check
│   ├── proxy
│   └── ip
│
└── proxy
    ├── show
    └── env
```

### 为什么不要单独的 `daemon`

`daemon` 是实现方式，不是用户心智。用户实际关心的是：

```text
安装 Mihomo
卸载 Mihomo
更新 Mihomo 版本
启动 Mihomo
停止 Mihomo
重启 Mihomo
查看 Mihomo 状态/日志
可选：安装时顺手注册为后台服务/自启动
```

所以这些命令应该都收进 `chatclash mihomo ...`。底层可以用 systemd user service、pid file 或别的 supervisor，但 CLI 不把这个细节暴露成一层主概念。

`--daemon` 只作为安装/卸载时的选项：

```bash
chatclash mihomo install --daemon
chatclash mihomo uninstall --daemon
```

含义是“同时安装/移除后台服务和自启动”。它不是一个单独的顶层命令组。

## 一台机器上的完整路线

### 0. 进入目标机器

`chatclash` 不负责 SSH 编排。先用外部 SSH 进入那台机器，然后在本机执行：

```bash
ssh <host>
```

后续所有命令都只作用于当前机器。

### 1. 初始化本机目录

```bash
chatclash init
```

创建本机运行目录：

```text
~/.chatarch/chatclash/
├── config.yaml
├── bin/
├── run/
├── logs/
├── cache/
└── clash/
    ├── config.yaml
    ├── Country.mmdb
    └── backups/
```

`config.yaml` 只保存本机运行布局/状态，例如：

```text
home
clash_dir
mihomo_path
pid_file
log_file
```

订阅 URL、代理认证、subconverter 地址、HTTP/SOCKS/controller 端口、订阅拉取代理都走 ChatEnv，不写进本地 config。

### 2. 配置订阅

```bash
chatclash subscription set
```

这个命令不建立新的 env 系统。它只是 ChatClash 面向用户的薄封装，实际写入 ChatEnv。

推荐交互式配置：

```bash
chatclash subscription set -i
```

也可以用环境变量名传入，避免把敏感 URL 和密码写进 shell history：

```bash
export CLASH_SUB_URL='...'
export CLASH_PROXY_AUTH='***'
chatclash subscription set \
  --url-env CLASH_SUB_URL \
  --proxy-auth-env CLASH_PROXY_AUTH \
  --http-port 7890 \
  --socks-port 7891 \
  --controller-port 9090
```

ChatEnv 字段：

| 字段 | 敏感 | 用途 |
|---|---:|---|
| `CHATCLASH_SUBSCRIPTION_URL` | 是 | Clash/Mihomo 订阅 URL |
| `CHATCLASH_PROXY_AUTH` | 是 | 本机代理认证，格式 `user:password` |
| `CHATCLASH_SUBCONVERTER_URL` | 否 | subconverter 服务地址 |
| `CHATCLASH_HTTP_PORT` | 否 | 本机 HTTP 代理端口 |
| `CHATCLASH_SOCKS_PORT` | 否 | 本机 SOCKS 代理端口 |
| `CHATCLASH_CONTROLLER_PORT` | 否 | 本机 Mihomo controller 端口 |
| `CHATCLASH_SUBSCRIPTION_FETCH_PROXY` | 否 | 拉取订阅时使用的代理；`local` 表示走当前 ChatClash 代理 |

查看订阅状态：

```bash
chatclash subscription status
```

输出只显示是否已配置、最后更新时间、备份数量等摘要，不打印订阅 URL 和密码明文。

### 3. 安装 Mihomo

```bash
chatclash mihomo install
```

职责：

- 下载或安装 Mihomo 二进制。
- 放到 `~/.chatarch/chatclash/bin/mihomo`。
- 记录当前机器使用的二进制路径。

如果希望安装时直接注册后台服务和自启动：

```bash
chatclash mihomo install --daemon
```

`--daemon` 的含义是：额外安装当前用户级别的 systemd service，并设置为开机或登录后自动启动。

卸载：

```bash
chatclash mihomo uninstall
```

如果要同时移除后台服务和自启动：

```bash
chatclash mihomo uninstall --daemon
```

更新 Mihomo 版本：

```bash
chatclash mihomo update
```

这里的 `update` 只表示更新 Mihomo 二进制版本，不表示更新订阅；订阅更新永远是 `chatclash subscription update`。

### 4. 拉取订阅并生成配置

```bash
chatclash subscription update
```

职责：

- 从 ChatEnv 读取订阅 URL / 认证 / subconverter 地址 / 端口 / 订阅拉取代理。
- 拉取订阅；如果 `CHATCLASH_SUBSCRIPTION_FETCH_PROXY=local`，则通过当前机器的 ChatClash 代理去拉取订阅，适合订阅源对服务器直连 IP 返回 403 的场景。
- 生成 `~/.chatarch/chatclash/clash/config.yaml`。
- 保留旧配置备份。
- 做基本 YAML / Mihomo 配置校验。

失败时不覆盖可用配置；成功后再启动或重启 Mihomo。

### 5. 启动 Mihomo

```bash
chatclash mihomo start
```

常用运行命令：

```bash
chatclash mihomo status
chatclash mihomo logs
chatclash mihomo restart
chatclash mihomo stop
```

如果订阅更新后要应用新配置：

```bash
chatclash subscription update
chatclash mihomo restart
```

### 6. 自启动怎么处理

不单独设计 `daemon install` / `daemon enable` 这层。自启动只是安装 Mihomo 时的一个选项：

```bash
chatclash mihomo install --daemon
```

如果一开始没有加，后面也可以重复执行同一个命令补装 service：

```bash
chatclash mihomo install --daemon
```

移除自启动：

```bash
chatclash mihomo uninstall --daemon
```

### 7. 查看总状态

```bash
chatclash status
```

这是总览命令，用来回答“这台机器现在配好了吗”：

```text
ChatClash home:        ~/.chatarch/chatclash
mihomo installed:      yes/no
mihomo version:        x.y.z
mihomo running:        yes/no
mihomo autostart:      enabled/disabled
subscription set:      yes/no
proxy auth set:        yes/no
config exists:         yes/no
http proxy:            127.0.0.1:7890
socks proxy:           127.0.0.1:7891
last update:           timestamp / unknown
backups:               count
```

所有敏感值只显示存在与否或脱敏摘要。

### 8. 检查代理

检查代理连通性：

```bash
chatclash check proxy
```

检查出口 IP：

```bash
chatclash check ip
```

`check` 是用户视角的检查命令，不叫 `verify`。

### 9. 使用代理

服务启动后，本机代理地址默认是：

```text
HTTP proxy:  http://127.0.0.1:7890
SOCKS proxy: socks5://127.0.0.1:7891
```

查看可用代理地址：

```bash
chatclash proxy show
```

给当前 shell 输出代理环境变量：

```bash
chatclash proxy env
```

典型输出：

```bash
export http_proxy=http://127.0.0.1:7890
export https_proxy=http://127.0.0.1:7890
export all_proxy=socks5://127.0.0.1:7891
export no_proxy=localhost,127.0.0.1,::1
```

临时让当前 shell 走代理：

```bash
eval "$(chatclash proxy env)"
```

浏览器或其他应用则直接配置：

```text
HTTP:  127.0.0.1:7890
SOCKS: 127.0.0.1:7891
```

## 串起来的一条主流程

首次部署：

```bash
chatclash init
chatclash subscription set -i
chatclash mihomo install
chatclash subscription update
chatclash mihomo start
chatclash status
chatclash check proxy
chatclash check ip
```

以后更新订阅：

```bash
chatclash subscription update
chatclash mihomo restart
chatclash status
chatclash check proxy
```

临时使用代理：

```bash
eval "$(chatclash proxy env)"
curl https://example.com
```

排障：

```bash
chatclash status
chatclash mihomo status
chatclash mihomo logs
chatclash subscription status
chatclash check proxy
chatclash check ip
```

## 兼容别名策略

旧命令可以保留为兼容别名，但文档主路径不推荐：

```text
chatclash update   -> chatclash subscription update
chatclash up       -> chatclash mihomo start
chatclash down     -> chatclash mihomo stop
chatclash restart  -> chatclash mihomo restart
chatclash logs     -> chatclash mihomo logs
chatclash verify   -> chatclash check proxy
chatclash ip-api   -> chatclash check ip
```

兼容别名可以存在一段时间，但新文档、新测试、新示例都应该使用主树命令。


## 正式替换一台机器上的旧 Clash

适用于“这台机器原来已经有 Clash/Mihomo，占用原端口和认证，现在要用 ChatClash 管起来”的场景。

### 1. 先做只读巡检

```bash
chatclash status
chatclash mihomo status
ss -ltnp '( sport = :7890 or sport = :7891 or sport = :9090 )'
docker ps --format '{{.Names}} {{.Status}} {{.Ports}}' | grep -Ei 'clash|yacd|mihomo' || true
```

确认：

- 原 HTTP 端口，例如 `7890`。
- 原 SOCKS 端口，例如 `7891`。
- 原 controller 端口，例如 `9090`。
- 原代理认证是否存在；只看 `present`，不要打印密码。
- 是否还有旧 Docker Clash/Yacd 容器。

### 2. 备份当前正式配置

```bash
cp ~/.chatarch/chatclash/config.yaml \
  ~/.chatarch/chatclash/config.yaml.pre-migration.$(date +%Y%m%d-%H%M%S).bak
cp ~/.chatarch/chatclash/clash/config.yaml \
  ~/.chatarch/chatclash/clash/config.yaml.pre-migration.$(date +%Y%m%d-%H%M%S).bak
```

备份文件可能包含节点和认证信息，不要贴到聊天或 PR 里。

### 3. 确保本机配置保留原端口

ChatClash 本地 config 负责保存本机端口。正式替换时保持原端口不变，例如：

```text
http_port: 7890
socks_port: 7891
controller_port: 9090
```

订阅 URL、代理认证、端口和订阅拉取代理都只放 ChatEnv。

### 4. 安装 Mihomo 并接入自启动

如果二进制已经存在，下面命令不会强制重新下载；它会补装 systemd user service 并 enable：

```bash
chatclash mihomo install --daemon
```

如果明确要更新 Mihomo 版本，再单独执行：

```bash
chatclash mihomo update
```

`update` 只更新 Mihomo 二进制版本，不更新订阅。

### 5. 停旧服务，只保留 systemd 管理的一份 Mihomo

先停旧 Docker Clash/Yacd，如果存在：

```bash
docker stop clash yacd
```

再停掉手动启动的 Mihomo，并清理残留 pid：

```bash
systemctl --user stop chatclash-mihomo.service || true
pkill -f '^/home/.*/.chatarch/chatclash/bin/mihomo' || true
rm -f ~/.chatarch/chatclash/run/mihomo.pid
```

确认端口已经释放：

```bash
ss -ltnp '( sport = :7890 or sport = :7891 or sport = :9090 )'
```

### 6. 启动新服务

```bash
chatclash mihomo start
```

如果已经安装了 `--daemon`，这个命令会走：

```bash
systemctl --user start chatclash-mihomo.service
```

### 7. 验证端口、认证和出口

确认 systemd 接管成功：

```bash
systemctl --user is-enabled chatclash-mihomo.service
systemctl --user is-active chatclash-mihomo.service
systemctl --user show chatclash-mihomo.service -p MainPID -p ActiveState -p SubState
```

确认只剩一份 Mihomo：

```bash
pgrep -af '^/home/.*/.chatarch/chatclash/bin/mihomo'
```

确认端口：

```bash
ss -ltnp '( sport = :7890 or sport = :7891 or sport = :9090 )'
```

确认未带认证会被拒绝：

```bash
curl -sS -m 10 --proxy http://127.0.0.1:7890 -I http://example.com
# 期望看到：HTTP/1.1 407 Proxy Authentication Required
```

确认带 ChatEnv 里的账号密码可以通过：

```bash
chatclash check proxy --min-success 4 --timeout 30
chatclash check ip --timeout 30
```

`check proxy` 输出里的代理地址必须脱敏，例如：

```text
proxy: http://***@127.0.0.1:7890
success_count=4
```

### 8. 订阅刷新注意事项

刷新订阅使用：

```bash
chatclash subscription update
```

如果订阅源直连返回 403，但通过当前代理可访问，可配置：

```bash
chatclash subscription set --fetch-proxy local
chatclash subscription update
```

`local` 会使用当前 ChatClash 的本机代理地址和 ChatEnv 中的代理认证来拉取订阅。若订阅源确实返回 token 过期，ChatClash 不应该覆盖现有可用配置；应保留当前 `clash/config.yaml`，等订阅 URL 更新后再执行 `subscription update`。

远程 subconverter 应写入 ChatEnv：

```bash
chatclash subscription set --subconverter-url <SUBCONVERTER_BASE_URL>
```

如果 subconverter 只绑定在远程机器 `127.0.0.1:25500`，当前机器不能直接访问，需要先把服务改成可访问地址，或通过 SSH tunnel 暴露成本机 URL，再写入 `CHATCLASH_SUBCONVERTER_URL`。


## ChatEnv / ChatStyle 接入校对

当前实现要求：

- ChatEnv 是用户可配置项的系统来源：订阅 URL、代理认证、subconverter 地址、HTTP/SOCKS/controller 端口、订阅拉取代理。
- 本地 `~/.chatarch/chatclash/config.yaml` 只保存机器布局/状态：home、clash_dir、engine_path、pid_file、log_file 等。
- `chatclash subscription set` 是 ChatEnv 的薄封装，支持 `-i/-I`，并支持 `--url-env` / `--proxy-auth-env`，避免敏感值进入 shell history。
- 写入 ChatEnv 必须走 `EnvStore.load_active()` / `save_active()`，不手写 `.env`。
- 交互确认走 ChatStyle `ask_confirm()`；新命令输入走 `CommandSchema` / `CommandField` / `resolve_command_inputs()`。
- 对外输出只显示 present/端口/路径/计数，订阅 URL、代理认证和代理 URL 中的认证必须脱敏。

仍保留但不作为主路径的兼容入口：`config`、`engine`、`up/down/restart/logs`、`verify`、`ip-api`、旧 `sub`/`setup`。后续清理时可以分批 deprecate，但当前文档主路径只写新树。
