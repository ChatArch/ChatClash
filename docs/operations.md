# 运行与维护

| 目标 | 操作顺序 |
| --- | --- |
| 更新 Python CLI | 同一解释器安装 → `pip check` → 版本/命令树检查 |
| 更新订阅 | `sub update` → `proxy validate` → `mihomo reload` |
| 更新引擎 | `mihomo update` → `proxy validate` → `mihomo restart` |
| 改监听参数 | `proxy set` → `proxy validate` → `mihomo restart` |
| 检查代理 | 脱敏状态 → 配置校验 → `chatenv test` 联网测试 |

## CLI 与已部署服务的关系 {#service}

ChatClash 是 Python 管理 CLI；Mihomo 是独立二进制。用户级 `chatclash-mihomo.service` 直接执行引擎，不是常驻 Python 服务。默认布局对应以下命令（unit 中保存展开后的绝对路径）：

```bash
~/.chatarch/chatclash/bin/mihomo -d ~/.chatarch/chatclash/clash
```

此处仅说明执行关系，不要在已有服务旁再运行一个引擎。升级 Python 包不会替换或重启它；`mihomo update` 替换磁盘二进制也不会自动重启。修改 ChatEnv、`init` 或 `sub set` 不会自动更新运行中的配置。

`install --daemon` 写入并启用用户级 unit，但不启动。存在该 unit 时，`start`、`stop`、`restart` 使用 `systemctl --user`；没有 unit 时，`start` 直接运行引擎，可能占用前台。当前服务生命周期面向 Linux，不是跨平台服务管理器。

## 刷新订阅 {#subscription}

```bash
chatclash sub status -I
chatclash sub update -I
chatclash proxy validate -I
chatclash mihomo reload -I
chatclash mihomo status -I
chatenv test -t chatclash
```

更新先生成候选配置并校验，再原子替换本机 YAML；`sub generate` 与 `proxy set` 的活动配置重渲染也会先写入私有临时文件再替换。校验或替换失败时，已有目标配置应保持不变。必须已安装 Mihomo。`--no-validate` 是显式跳过校验的例外选项，不是缺少引擎时的默认补救；使用后仍须安装引擎、校验成功才能启动或应用。

配置替换不等于运行中引擎已重载。`reload` 通过本地 controller 应用配置，不替换进程或二进制；首次部署用 `start`，引擎升级或监听变更用 `restart`。重载失败时保留错误信息，检查 controller 可达性/认证，不要反复更新订阅掩盖失败。

如果服务已经健康运行，但订阅源无法直连，可显式选择已有本机代理：

```bash
chatclash sub update --fetch-proxy local -I
```

这只是本次下载的临时路径，不会启动代理，也不能解决首次部署的循环依赖。无转换器地址时直接读取 Clash YAML；设置转换器后通过转换器生成。本机生成配置和备份可能含凭证，不跨机器复制、不贴进 issue。

## 升级与诊断 {#maintenance}

Python CLI 升级见[安装](installation.md#upgrade)。引擎升级需单独安排可能中断连接的重启窗口：

```bash
chatclash mihomo update -I
chatclash proxy validate -I
chatclash mihomo restart -I
chatclash mihomo status -I
chatenv test -t chatclash
```

只读状态和日志入口：

```bash
chatclash status -I
chatclash sub status -I
chatclash proxy show -I
chatclash mihomo logs --tail 100 -I
```

`logs` 在 systemd 模式展示服务状态附带的日志，不等价于完整历史日志查询。必要时在本机使用 `journalctl --user -u chatclash-mihomo.service -n 100 --no-pager`；原始日志必须先审查、脱敏再分享。`status` 显示运行不代表网络可达，`proxy validate` 检查配置，`chatenv test` 则真实请求外部测试站点。

## 安全使用代理环境变量 {#proxy-env}

```bash
chatclash proxy show -I
chatclash proxy env -I
```

默认脱敏输出只用于展示，不能当作已认证的可执行导出值。需要带认证访问时，仅在关闭跟踪、不回显秘密的子 shell 内消费 `--no-mask`：

```bash
(
  set +x
  eval "$(chatclash proxy env --no-mask -I)"
  curl --fail --silent --show-error --output /dev/null https://example.com
)
```

子 shell 结束后父 shell 的环境不变。不要单独打印未脱敏导出、运行 `env`/`printenv`、开启 `set -x` 或使用 verbose 请求日志；不要把输出重定向到文档/工单。此示例只连接占位测试站点，按需替换为可信测试目标。秘密仍存在于子进程环境中，不能把此模式当作多用户主机上的安全隔离边界。

## 可选订阅转换器 {#converter}

只有订阅格式需要转换时才部署。转换器会接收到完整订阅地址，使用本机或可信服务，避免不可信的公共转换器。

```bash
chatclash sub converter install -I
chatclash sub converter start -I
chatenv set CHATCLASH_SUBCONVERTER_URL=http://127.0.0.1:25500
chatclash sub converter status -I
chatclash sub update -I
chatclash proxy validate -I
chatclash mihomo reload -I
```

此序列面向已有运行中引擎；首次部署在校验后执行 `mihomo start`。转换器默认仅监听 `127.0.0.1:25500`；不要无意改成公网监听。`--host`/`--port` 是转换器运行参数，不是 ChatEnv 字段；修改后需同步基础 URL。`converter status --host/--port` 描述预期端点，不会重新配置正在运行的服务。

```bash
chatclash sub converter logs --tail 100 -I
chatclash sub converter stop -I
```

`sub generate --output` 可写指定配置文件，但不自动激活；`sub url` 默认脱敏。普通操作不需要展示完整转换 URL。

## 管理端口安全 {#controller}

新安装的 HTTP/SOCKS 配置仅绑定 loopback；没有 `CHATCLASH_PROXY_AUTH` 时，LAN/非 loopback 绑定会被拒绝。生成配置的 controller 默认仅绑定 `127.0.0.1:9090`，未设置 secret。**代理的 `CHATCLASH_PROXY_AUTH` 只保护 HTTP/SOCKS 入口，不保护 controller。** 旧配置可能仍是 `:9090` 或其他外部绑定；升级后用 `sub update`（或任何会重新生成配置的操作）写入新头部，再显式重载/重启。`proxy set --bind-host` 不是 controller 绑定开关。当前 CLI 没有独立管理端口认证配置接口；无论何种绑定，都不能直接暴露公网，也不能依靠临时手改 YAML 作为持久安全策略。

返回：[配置与 ChatEnv](configuration.md) · [CLI 树](cli-tree.md)。
