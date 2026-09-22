# CLI 设计与边界

ChatClash 是**当前机器**的 Mihomo 管理 CLI。它保存配置、生成配置文件并调用本机服务控制；不编排远程机器，也不把 Python CLI 作为常驻代理进程。

## 注册命令

```bash
chatclash --tree        # 带参数签名的完整树
chatclash --tree-brief  # 相同节点的简版树
```

两个视图都从实际 Click 注册表生成。完整输出以 [CLI 树](cli-tree.md) 为准；文档不把规划能力伪装成可执行命令。

## 职责地图

| 命令组 | 负责什么 | 不做什么 |
| --- | --- | --- |
| `init` | 建立本机运行目录和起始配置，必要时写入当前 ChatEnv 配置 | 不启动引擎、不替代已有部署的升级流程 |
| `sub` | 保存订阅设置、生成或更新候选 YAML | 更新文件后不自动重载运行中的引擎 |
| `proxy` | 修改本机监听参数、校验配置、提供代理端点信息 | 不管理 controller 的认证或绑定策略 |
| `mihomo` | 安装、更新、启动、停止、重启和检查本机引擎 | 不升级 Python CLI 或远程服务 |
| `status` | 读取本机运行、配置和备份摘要 | 不证明外部网络连通性 |

## 配置与状态归属

ChatEnv 保存操作者配置：`CHATCLASH_HOME`、订阅地址、代理认证和可选转换器地址。机器本地 `config.yaml` 保存端口、监听主机、二进制和日志路径；`clash/config.yaml` 是 Mihomo 实际读取的生成文件。

进程 `CHATCLASH_*` 环境变量优先于活动 ChatEnv 配置。切换 ChatEnv profile 不迁移文件，也不会让正在运行的 Mihomo 自动读取新值。详细字段和路径见[配置与 ChatEnv](configuration.md)。

## Python API 边界

CLI 只是薄适配层。可复用的行为位于：

- `chatclash.subscription`
- `chatclash.proxy`
- `chatclash.mihomo`
- `chatclash.checks`
- `chatclash.status`
- `chatclash.paths`

其他 Python 调用方应调用这些模块，而不是调用 Click 回调函数。

## 已部署服务

用户级 `chatclash-mihomo.service` 直接执行独立 Mihomo 二进制。CLI 包升级不会替换或重启该引擎；订阅更新也必须在校验后显式 `mihomo reload` 或 `mihomo restart` 才会作用于运行中的服务。具体操作顺序见[运行与维护](operations.md#service)。

## 安全与验证

- `proxy show`、`proxy env` 和 `chatenv cat` 默认脱敏。带认证的导出只可在[非回显子 shell](operations.md#proxy-env)中消费。
- 新生成配置将无 secret 的 controller 绑定至 `127.0.0.1:<port>`；旧 `:<port>` 或外部绑定配置需要刷新生成文件后才会迁移。
- `proxy validate` 检查本机 YAML；`chatenv test -t chatclash` 发起真实代理请求；服务运行状态本身不等于连通性。
- 订阅、认证、生成 YAML 和备份都可能含秘密，不应跨机器复制或贴入 issue。
