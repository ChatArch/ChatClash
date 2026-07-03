# chatclash documentation

`chatclash` is a single-machine Mihomo management tool. It manages the local runtime, subscription-backed config generation, and local proxy checks on the machine where it runs.

## Recommended flow

```bash
chatclash init
chatclash sub set -i
chatclash mihomo install --daemon
chatclash sub update
chatclash mihomo start
chatclash status
chatclash check proxy
chatclash check ip
```

## CLI tree

```text
chatclash
├── init
├── status
├── sub
│   ├── set
│   ├── status
│   ├── update
│   ├── url
│   └── generate
├── proxy
│   ├── set
│   ├── show
│   └── env
├── mihomo
│   ├── install
│   ├── uninstall
│   ├── update
│   ├── start
│   ├── stop
│   ├── restart
│   ├── status
│   └── logs
└── check
    ├── proxy
    └── ip
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
