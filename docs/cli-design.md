# ChatClash CLI design

ChatClash is a single-machine Mihomo management CLI. It does not orchestrate remote machines and does not expose historical implementation paths as normal user commands.

## Target command tree

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

## Responsibilities

- `init`: create the machine-local ChatClash home and starter runtime config.
- `status`: summarize local runtime, config, subscription, ports, and backup state without printing secrets.
- `sub`: manage subscription-backed config through ChatEnv and config-generation APIs.
- `proxy`: manage machine-local listener/endpoint settings and shell proxy exports.
- `mihomo`: install, update, start, stop, restart, inspect, and read logs for the local Mihomo runtime.
- `check`: run proxy and external-IP checks from this machine.

## Config ownership

ChatEnv stores operator-owned values:

- `CHATCLASH_SUBSCRIPTION_URL`
- `CHATCLASH_PROXY_AUTH`
- `CHATCLASH_SUBCONVERTER_URL`
- `CHATCLASH_SUBSCRIPTION_FETCH_PROXY`

Machine-local config stores runtime layout and local listener facts:

- home and runtime config directory
- Mihomo binary path
- PID/log/cache paths
- HTTP/SOCKS/controller ports
- bind host and advertised proxy host

## Python API boundary

The CLI is a thin adapter over importable Python APIs:

- `chatclash.subscription`
- `chatclash.proxy`
- `chatclash.mihomo`
- `chatclash.checks`
- `chatclash.status`
- `chatclash.paths`

Command behavior should be shared through these modules, not by calling Click command callbacks.

## Security

Do not print raw subscription URLs, proxy credentials, tokens, cookies, private keys, or private workspace paths. Tests may use obvious dummy values only when they assert redaction behavior.
