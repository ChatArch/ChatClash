<div align="center">
    <a href="https://pypi.python.org/pypi/chatclash">
        <img src="https://img.shields.io/pypi/v/chatclash.svg" alt="PyPI version" />
    </a>
</div>

# chatclash

ChatArch single-machine proxy toolkit for Mihomo runtime management, subscription-backed config generation, and local proxy checks.

## Quick Start

```bash
pip install -e ".[dev]"
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
chatclash sub status
chatclash sub url "$SUBSCRIPTION_URL" -s http://127.0.0.1:25500
chatclash sub generate "$SUBSCRIPTION_URL" -s http://127.0.0.1:25500 -o <OUTPUT_CONFIG> -y
chatclash proxy show
eval "$(chatclash proxy env)"
python -m pytest -q
```

## ChatArch conventions

- CLI interaction uses ChatStyle helpers and the shared `-i/-I` pattern where applicable.
- Operator config is stored through ChatEnv; local config stores only machine-local runtime facts.
- Major CLI capabilities have reusable Python APIs under `src/chatclash/` modules.
- Sensitive values must not be printed in CLI output, logs, docs, or tests.
