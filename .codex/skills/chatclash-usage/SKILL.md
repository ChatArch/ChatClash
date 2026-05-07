---
name: chatclash-usage
description: Show ChatClash quickstart, runtime commands, service startup, status checks, subscription conversion basics, and Docker proxy setup. Use when the user wants to use ChatClash, bring up the generated Clash/Yacd service, verify the runtime, or configure Docker/system proxy behavior around ChatClash.
---

# ChatClash Usage

## Quick Start

Use these commands from the repo checkout:

```bash
cd /home/rexwzh/workspace/core/ChatClash
pip install -e ".[dev]"
chatclash setup clash /tmp/clash -y
chatclash status /tmp/clash
chatclash proxy env
```

If you have a subconverter service and subscription URL:

```bash
chatclash sub status
chatclash sub url "$SUBSCRIPTION_URL" -s http://127.0.0.1:25500
chatclash sub generate "$SUBSCRIPTION_URL" -s http://127.0.0.1:25500 -o /tmp/clash/config.yaml -y
```

## Start the Service

Bring the generated stack up with Docker Compose:

```bash
sudo docker-compose -f /tmp/clash/docker-compose.yaml up -d
```

Useful checks:

```bash
sudo docker-compose -f /tmp/clash/docker-compose.yaml ps
curl --noproxy '*' http://127.0.0.1:7900/configs
curl --noproxy '*' http://127.0.0.1:9135/
```

If ports were changed during setup, use the values from `chatclash status`.

## Docker Proxy

If Docker itself needs proxy access, configure the daemon instead of shell aliases:

```ini
[Service]
Environment="HTTP_PROXY=http://proxy.example.com:8080"
Environment="HTTPS_PROXY=http://proxy.example.com:8080"
Environment="NO_PROXY=localhost,127.0.0.1,docker-registry.somecorporation.com"
```

Then reload and restart Docker:

```bash
sudo systemctl daemon-reload
sudo systemctl restart docker
```

## Notes

- Do not print or paste full subscription URLs, credentials, UUIDs, passwords, or server values.
- Use `-y/--yes` only when you intend to overwrite files.
- Avoid `/srv/clash` unless you explicitly want to touch the live service directory.
