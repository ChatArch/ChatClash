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
chatclash --tree
chatclash --tree-brief
chatenv test -t chatclash
```

## CLI tree

ChatStyle 从真实 Click 注册表生成两种视图：`chatclash --tree` 保留参数签名，`chatclash --tree-brief` 保留相同节点但省略签名。完整视图见 [CLI 树](cli-tree.md)；简版如下：

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

ChatClash registers `CHATCLASH_HOME`, `CHATCLASH_SUBSCRIPTION_URL`, `CHATCLASH_PROXY_AUTH`, and `CHATCLASH_SUBCONVERTER_URL` with ChatEnv. Subscription URL and proxy auth are sensitive fields.
