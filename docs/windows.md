# Windows 使用指南

ChatClash 0.1.10 支持 Windows x64/arm64 的用户级 Mihomo。以下命令在普通 PowerShell 中执行，不需要管理员权限。本文没有真实订阅地址、节点密码或令牌。

## 安装 CLI

假设已准备好默认 ChatArch 虚拟环境和 uv；若使用自定义目录，相应替换路径：

```powershell
$chatarchPython = "$env:USERPROFILE\.chatarch\venv\Scripts\python.exe"
uv pip install --python $chatarchPython --upgrade "chatclash==0.1.10"
uv pip check --python $chatarchPython
$env:Path = "$env:USERPROFILE\.chatarch\venv\Scripts;$env:Path"
chatclash --version
```

预期版本为 `0.1.10`。如果环境已安装 pip，也可用 `& $chatarchPython -m pip install --upgrade "chatclash==0.1.10"`。CLI 和 ChatEnv 必须安装到同一个解释器。安装 Python 包不会自动安装 Mihomo，也不会开启系统代理。

## 首次导入订阅

```powershell
chatclash init -i
```

在隐藏的 `Subscription URL` 提示中粘贴自己的订阅。`Proxy authentication` 是本机代理入口认证，不是订阅的节点密码；仅本机 loopback 使用时可以留空。订阅已提供 Clash YAML 时，`Subconverter base URL` 留空。

订阅由 ChatEnv 保存在当前用户的活动配置中；Mihomo 配置和节点凭据默认保存在 `~/.chatarch/chatclash`，也可能随自定义 `CHATARCH_HOME` / `CHATCLASH_HOME` 改变。不要把这些目录、备份、原始日志或截图上传到 Git、issue 或工单；Windows 文件保护依赖所在目录的 ACL，应放在自己的私有用户目录中。`init` 仅用于首次初始化，已有部署不要重复运行以免重置本机参数。

逐条运行；某条命令失败时先解决错误，不要继续启用系统代理：

```powershell
chatclash mihomo install -I
chatclash sub update -I
chatclash proxy validate -I
chatclash mihomo start -I
chatclash mihomo status -I
chatenv test -t chatclash -I
```

安装器自动选择 Windows ZIP。`start` 等待 HTTP 端口就绪，`status` 应显示 `running: yes`。联网检查成功后才继续下一节；`init --local-only` 生成的 DIRECT 配置不等于已经有可用订阅节点。若引擎已安装，无需重复 `install`。

## 启用 Windows 系统代理

```powershell
chatclash proxy system show -I
chatclash proxy system enable -I
chatclash proxy system show -I
```

默认 HTTP 为 `127.0.0.1:7890`，SOCKS 为 `127.0.0.1:7891`。启用后显示 `enabled: yes`、`backup: present`。ChatClash 保存原手动代理及默认连接的 WinINet 模式，暂时关闭 PAC/自动检测模式，恢复时还原；不管理 WinHTTP、机器级代理、VPN 命名连接或 TUN。应用是否使用系统代理取决于应用自身，一些应用需要重启。

关闭时先恢复设置，再停止引擎，避免把应用指向空端口：

```powershell
chatclash proxy system disable -I
chatclash mihomo stop -I
chatclash proxy system show -I
```

`disable` 是恢复原设置，不保证原设置本身就是关闭。引擎崩溃或系统重启后也可执行它；备份缺失时不会覆盖现有设置。Windows 首版没有开机自启或崩溃自动重启；重启电脑后先手动启动引擎，或恢复系统代理。

## Git / Python / uv 的会话代理

这些工具不一定使用 Windows 系统代理。仅在没有本机代理认证时，可在新的 PowerShell 窗口中使用：

```powershell
$env:HTTP_PROXY = 'http://127.0.0.1:7890'
$env:HTTPS_PROXY = $env:HTTP_PROXY
$env:NO_PROXY = 'localhost,127.0.0.1,::1'
git ls-remote https://github.com/ChatArch/ChatClash.git HEAD
python -c "import urllib.request; print(urllib.request.urlopen('https://github.com', timeout=20).status)"
```

先确认引擎已启动；自定义端口时替换示例中的端口。关闭这个新窗口即可移除会话变量。ChatClash 不会覆盖 Git 等工具已有的独立代理设置。需要带认证的会话输出时参考[安全使用代理环境变量](operations.md#proxy-env)；默认脱敏输出不能当作认证配置执行。

可选的持久化会影响以后启动的进程，必须显式执行，并避免回显认证值：

```powershell
chatclash proxy env --persist --no-mask -I > $null
# Later, restore the previous user variables before stopping the proxy:
chatclash proxy env --restore -I
```

恢复持久变量不会修改已打开窗口的进程环境，应重新打开窗口。除非确实需要，优先使用临时会话方式。

## 首次下载失败或 GeoIP 缺失

首次安装、订阅下载和 GeoIP 数据下载可能需要一个**已经可用的代理**。不能把引擎尚未启动的 `7890` 端口当作下载代理。若已有可信本机 HTTP 代理，例如它实际监听 `127.0.0.1:1080`，在新的 PowerShell 窗口设置：

```powershell
$env:HTTP_PROXY = 'http://127.0.0.1:1080'
$env:HTTPS_PROXY = $env:HTTP_PROXY
$env:NO_PROXY = 'localhost,127.0.0.1,::1'
chatclash mihomo install -I
chatclash sub update -I
chatclash proxy validate -I
```

`1080` 只是已有 HTTP 代理的示例端口，按实际配置替换；引擎已安装则跳过安装。此临时环境能同时供订阅请求与校验期间的资源下载使用。完成后关闭此窗口，在新窗口启动 Mihomo。不要用 `--no-validate` 隐藏资源下载错误。已有健康运行的本机 Mihomo 时，也可用 `chatclash sub update --fetch-proxy local -I` 下载订阅。

## 日常维护

```powershell
# Refresh the subscription and apply it to a running engine:
chatclash sub update -I
chatclash mihomo reload -I
chatclash mihomo status -I
chatenv test -t chatclash -I

# Inspect locally; redact before sharing:
chatclash mihomo logs --tail 30 -I
```

Windows 运行中的 `.exe` 可能无法覆盖。升级引擎前先恢复系统代理并停止 Mihomo，再 `mihomo update`、校验、启动、联网检查，最后按需重新启用系统代理。Linux 的 systemd 工作流见[运行与维护](operations.md)。
