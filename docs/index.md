# chatclash documentation

`chatclash` is a single-machine Mihomo management tool. It manages the local runtime, subscription-backed config generation, and ChatEnv-backed proxy validation on the machine where it runs.

## Recommended flow

```bash
chatclash init
chatclash sub set -i
chatclash mihomo install --daemon
chatclash sub update
chatclash mihomo start
chatclash status
chatenv test -t chatclash
```

## CLI tree

```text
chatclash                         # 管理本机 Mihomo 代理服务
├── init                          # 初始化本机运行目录，并交互式收集 ChatEnv 配置
├── status                        # 查看整体状态
├── sub                           # 管理订阅和生成代理配置
│   ├── set                       # 保存订阅配置到 ChatEnv
│   ├── status                    # 查看订阅配置状态
│   ├── update                    # 用订阅刷新本机配置
│   ├── url                       # 生成订阅转换 URL
│   └── generate                  # 生成 Clash 配置文件
├── proxy                         # 打印本机代理端点和环境变量
│   ├── show                      # 显示代理端点，默认脱敏显示认证
│   └── env                       # 输出 shell 代理环境变量；--no-mask 输出可用认证 URL
└── mihomo                        # 管理 Mihomo 程序
    ├── install                   # 安装 Mihomo
    ├── uninstall                 # 卸载 Mihomo
    ├── update                    # 更新 Mihomo
    ├── start                     # 启动 Mihomo
    ├── stop                      # 停止 Mihomo
    ├── restart                   # 重启 Mihomo
    ├── status                    # 查看 Mihomo 状态
    └── logs                      # 查看 Mihomo 日志
```

## Common commands

```bash
chatclash status
chatclash sub status
chatclash sub update
chatclash mihomo status
chatclash mihomo logs
chatclash proxy show
eval "$(chatclash proxy env)"
```

Detailed design: [cli-design.md](cli-design.md).



## Local subscription converter service

`chatclash sub converter` manages the local subscription converter service used by `CHATCLASH_SUBCONVERTER_URL`. Host and port are service runtime parameters, not ChatEnv fields.

```bash
chatclash sub converter install
chatclash sub converter start              # default http://127.0.0.1:25500
chatclash sub converter start --host 0.0.0.0 --port 26666
chatclash sub converter status
chatclash sub converter logs --tail 200
chatclash sub converter stop
```

After starting a local converter, store its base URL through ChatEnv when this machine should use it for subscription conversion:

```bash
chatenv set CHATCLASH_SUBCONVERTER_URL='http://127.0.0.1:25500'
chatclash sub url --show -I
chatclash sub update
```

When `CHATCLASH_SUBCONVERTER_URL` is configured, `chatclash sub generate` and `chatclash sub update` use the converter endpoint to regenerate the local Mihomo config. The generated `config.yaml` is a machine-local artifact: do not copy it between machines. To refresh another host, configure that host's subscription/converter settings and run generation there.

The converter request follows the original ACL4SSR/SubConverter contract (`target=clash`, `insert=false`, `new_name=true`, and related compatibility flags). Some providers return node-only YAML; ChatClash composes the local listener header, authentication, default groups, and rules around those generated nodes.


## Authentication and ChatEnv

All public commands expose the shared ChatStyle `-i/-I` interactive option. For first-time machine setup, run `chatclash init` interactively, or pass values explicitly for automation:

```bash
chatclash init --url-env CHATCLASH_SUBSCRIPTION_URL --proxy-auth-env CHATCLASH_PROXY_AUTH -I
chatclash proxy show              # masked
chatclash proxy show --no-mask    # shows authenticated proxy URLs
chatclash proxy env --no-mask     # usable authenticated http_proxy/https_proxy/all_proxy exports
```

ChatEnv remains the system of record:

```bash
chatenv cat -t chatclash
chatenv cat -t chatclash --no-mask
chatenv test -t chatclash
```
