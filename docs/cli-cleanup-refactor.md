# ChatClash CLI Cleanup and Module/API Refactor

This PR tracks the ChatClash CLI cleanup and code-structure refactor.

## Target CLI tree

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

## Review requirements

This branch must satisfy the ChatArch CLI repository review points:

1. CLI tree is concise and matches this PRD.
2. Code is decoupled and layered; `cli.py` is a thin adapter.
3. CLI interaction follows ChatStyle conventions.
4. Major CLI capabilities have reusable Python APIs.
5. Secrets and private information are protected.
6. Tests and gates accurately cover the repository.

## Implementation direction

- Move command behavior out of `cli.py` into importable modules.
- Do not use Click command callback calls for behavior reuse.
- Keep package-specific CLI decisions in this repository's docs and tests.
- Keep ChatEnv/ChatStyle integration intact.
