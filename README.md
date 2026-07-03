<div align="center">
    <a href="https://pypi.python.org/pypi/chatclash">
        <img src="https://img.shields.io/pypi/v/chatclash.svg" alt="PyPI version" />
    </a>
</div>

# chatclash

ChatArch single-machine proxy toolkit for Mihomo runtime management, subscription-backed config generation, and local proxy checks.

## Quick start

```bash
pip install -e ".[dev]"
chatclash init
chatclash sub set -i
# If the subscription source blocks direct server fetches, use:
chatclash sub set --fetch-proxy local
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
chatclash sub status
chatclash proxy set --http-port 7890 --socks-port 7891 --controller-port 9090
chatclash sub update
chatclash mihomo update
chatclash mihomo restart
chatclash mihomo logs
chatclash proxy show
eval "$(chatclash proxy env)"
python -m pytest -q
```

## ChatArch conventions

- CLI interaction uses ChatStyle helpers and the shared `-i/-I` pattern where applicable.
- Operator config is stored through ChatEnv; local config stores only machine-local runtime facts.
- Major CLI capabilities have reusable Python APIs under `src/chatclash/` modules.
- Sensitive values must not be printed in CLI output, logs, docs, or tests.

## ChatEnv fields

| Field | Notes |
|---|---|
| `CHATCLASH_SUBSCRIPTION_URL` | Subscription URL, sensitive |
| `CHATCLASH_PROXY_AUTH` | Proxy authentication, sensitive |
| `CHATCLASH_SUBCONVERTER_URL` | Optional subconverter service base URL |
| `CHATCLASH_SUBSCRIPTION_FETCH_PROXY` | Subscription fetch proxy; `local` uses this machine's proxy |

Machine-local ports, hosts, runtime paths, PID files, and log files live in ChatClash local config rather than ChatEnv.
