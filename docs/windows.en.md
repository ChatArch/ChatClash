# Windows Guide

ChatClash 0.1.10 supports user-level Mihomo on Windows x64/arm64. Run these commands in a regular PowerShell window without elevation. This guide contains no real subscription URLs, node passwords, or tokens.

## Install the CLI

Assuming uv and the default ChatArch virtual environment are available (adjust paths for a custom home):

```powershell
$chatarchPython = "$env:USERPROFILE\.chatarch\venv\Scripts\python.exe"
uv pip install --python $chatarchPython --upgrade "chatclash==0.1.10"
uv pip check --python $chatarchPython
$env:Path = "$env:USERPROFILE\.chatarch\venv\Scripts;$env:Path"
chatclash --version
```

Expect `0.1.10`. If pip is installed in that environment, `& $chatarchPython -m pip install --upgrade "chatclash==0.1.10"` also works. ChatClash and ChatEnv must share an interpreter. Installing the Python package does not install the engine or enable Windows proxy settings.

## Import your subscription

```powershell
chatclash init -i
```

Paste your subscription into the hidden `Subscription URL` prompt. `Proxy authentication` protects your local proxy listener; it is not a subscription node password. Leave it empty for local loopback-only use. Leave `Subconverter base URL` empty when the subscription already supplies Clash YAML.

ChatEnv stores the subscription in the current user's active profile. Runtime configuration and node credentials default to `~/.chatarch/chatclash`, subject to custom `CHATARCH_HOME` / `CHATCLASH_HOME`. Do not upload those directories, backups, raw logs, or screenshots to Git, issues, or tickets. Windows file privacy relies on directory ACLs: use your private user directory. Use `init` for first deployment only; repeating it can reset machine-local settings.

Run commands individually. Resolve errors before proceeding, especially before enabling the system proxy:

```powershell
chatclash mihomo install -I
chatclash sub update -I
chatclash proxy validate -I
chatclash mihomo start -I
chatclash mihomo status -I
chatenv test -t chatclash -I
```

Installation selects a Windows ZIP. `start` waits for the HTTP listener and `status` should report `running: yes`. Verify connectivity before continuing. The DIRECT configuration from `init --local-only` does not demonstrate working subscription nodes. Skip installation if the engine is already present.

## Enable Windows proxy

```powershell
chatclash proxy system show -I
chatclash proxy system enable -I
chatclash proxy system show -I
```

Defaults are HTTP `127.0.0.1:7890` and SOCKS `127.0.0.1:7891`. Expect `enabled: yes` and `backup: present`. ChatClash saves the previous manual proxy and default-connection WinINet mode, temporarily suspends PAC/auto-detection mode, and restores it later. It does not manage WinHTTP, machine-wide proxy, named VPN connections, or TUN. Applications decide whether to honor system settings; some need restarting.

Restore settings before stopping the engine so applications do not point at a closed port:

```powershell
chatclash proxy system disable -I
chatclash mihomo stop -I
chatclash proxy system show -I
```

`disable` restores previous settings, which may themselves enable a proxy. It also works after a crash or reboot. With no backup, it leaves current settings unchanged. This Windows release has no login autostart or automatic crash restart: start the engine manually after reboot, or restore system settings.

## Session proxy for Git / Python / uv

These tools may not honor Windows system settings. With no local proxy authentication configured, use a new PowerShell window:

```powershell
$env:HTTP_PROXY = 'http://127.0.0.1:7890'
$env:HTTPS_PROXY = $env:HTTP_PROXY
$env:NO_PROXY = 'localhost,127.0.0.1,::1'
git ls-remote https://github.com/ChatArch/ChatClash.git HEAD
python -c "import urllib.request; print(urllib.request.urlopen('https://github.com', timeout=20).status)"
```

Start the engine first and adjust custom ports. Close this new window to discard its variables. ChatClash does not overwrite tool-specific settings such as Git proxy configuration. See [safe proxy exports](operations.en.md#proxy-env) for authentication; masked output is not executable authentication configuration.

Optional persistence affects future processes and must be explicitly requested. Suppress exported credentials:

```powershell
chatclash proxy env --persist --no-mask -I > $null
# Later, restore the previous user variables before stopping the proxy:
chatclash proxy env --restore -I
```

Restoring user variables does not modify already-open process environments; reopen those windows. Prefer temporary sessions unless persistence is needed.

## Bootstrap downloads and missing GeoIP data

First installation, subscription requests, and GeoIP downloads may need an **already working proxy**. Do not point downloads at an unstarted engine's `7890` port. If a trusted HTTP proxy actually listens at `127.0.0.1:1080`, set this in a new PowerShell window:

```powershell
$env:HTTP_PROXY = 'http://127.0.0.1:1080'
$env:HTTPS_PROXY = $env:HTTP_PROXY
$env:NO_PROXY = 'localhost,127.0.0.1,::1'
chatclash mihomo install -I
chatclash sub update -I
chatclash proxy validate -I
```

`1080` is only an example for an existing HTTP proxy; replace it with its actual endpoint and skip installation if already installed. The temporary environment covers subscription fetches and resource downloads during validation. Close this window afterward and start Mihomo in a fresh window. Do not hide resource failures using `--no-validate`. With a healthy local Mihomo already running, `chatclash sub update --fetch-proxy local -I` can also fetch subscriptions.

## Routine maintenance

```powershell
# Refresh the subscription and apply it to a running engine:
chatclash sub update -I
chatclash mihomo reload -I
chatclash mihomo status -I
chatenv test -t chatclash -I

# Inspect locally; redact before sharing:
chatclash mihomo logs --tail 30 -I
```

A running Windows `.exe` may be locked. Before upgrading the engine, restore system proxy settings and stop Mihomo, then update, validate, start, check connectivity, and enable the system proxy if needed. See [Operations](operations.en.md) for Linux systemd workflows.
