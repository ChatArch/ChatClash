---
name: chatclash-usage
description: Show ChatClash quickstart, runtime commands, status checks, subscription conversion basics, and proxy environment helpers.
---

# ChatClash Usage

## Quick Start

Use these commands from the repo checkout:

```bash
cd <CHATCLASH_REPO>
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

## Subscription helpers

```bash
chatclash sub status
chatclash sub url "$SUBSCRIPTION_URL" -s http://127.0.0.1:25500
chatclash sub generate "$SUBSCRIPTION_URL" -s http://127.0.0.1:25500 -o <OUTPUT_CONFIG> -y
```

## Proxy helpers

```bash
chatclash proxy show
eval "$(chatclash proxy env)"
```

## Notes

- Do not print or paste full subscription URLs, credentials, UUIDs, passwords, or server values.
- Use `-y/--yes` only when you intend to write files.
- Use task-local directories for tests and smoke checks.
