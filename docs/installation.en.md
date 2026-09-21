# Installation and Dependencies

| Your situation | Recommended route |
| --- | --- |
| Existing ChatArch installation | Install into the shared environment created by ChatUV |
| Conflicting legacy applications | Upgrade compatible packages selectively, or isolate legacy applications |
| First proxy deployment | Install the Python CLI, then install the Linux Mihomo engine separately |

## Install the Python CLI {#install}

Python 3.10 or later is required. Complete the standard ChatArch `chatuv setup` procedure, then use the same interpreter for installation and checks:

```bash
~/.chatarch/venv/bin/python -m pip install -U chatclash
~/.chatarch/venv/bin/python -m pip check
~/.chatarch/venv/bin/chatclash --version
~/.chatarch/venv/bin/chatclash --tree
~/.chatarch/venv/bin/chatenv cat -t chatclash
```

These paths assume the default `CHATARCH_HOME=~/.chatarch`; adjust them for a custom ChatArch root. Later examples assume this environment's `bin` is on `PATH`. Use absolute paths when unsure, and do not mix system Python, user site-packages, and unrelated virtual environments. End users do not need a source checkout or an editable install.

ChatClash registers the `chatclash = chatclash.config` provider in the `chatenv.configs` entry-point group. **ChatClash and ChatEnv must be installed in the same interpreter/virtual environment.** Having both executables on `PATH` is not enough for discovery.

## Dependency conflicts {#dependencies}

The compatibility ranges include `chatstyle>=0.2.0,<0.3.0` and `chatenv>=0.2.11,<0.3.0`. ChatStyle 0.2 provides the required shared command-tree interface; do not downgrade it to an older series.

Some older releases of `chatgh`, `chatup`, `chatvideo`, and `chatzulip` require `chatstyle<0.2`, which cannot coexist with that range. Check the actual environment:

```bash
~/.chatarch/venv/bin/python -m pip check
~/.chatarch/venv/bin/python -m pip show chatclash chatenv chatstyle
```

| Result | Action |
| --- | --- |
| A legacy application requires `chatstyle<0.2` | Upgrade only the reported packages to compatible releases, then rerun `pip check` |
| No compatible legacy release exists | Isolate that application, or create a dedicated environment for ChatClash and ChatEnv |
| Installation succeeds but conflicts remain | The environment is not repaired; installer success is not compatibility evidence |
| ChatEnv cannot find `chatclash` | Check interpreter ownership and install the provider in ChatEnv's environment |

Do not bypass resolution with `--no-deps` or force a ChatStyle downgrade. Avoid blanket upgrades of every shared application. A dedicated environment can live at `~/.chatarch/venvs/chatclash/`; install both `chatclash` and `chatenv` there and consistently use its executables.

## First Linux service deployment {#first-deployment}

Installing the Python package does not install the engine. The engine installer selects Linux amd64/arm64 assets; daemon management uses Linux user-level systemd. Python package installability does not imply macOS/Windows engine or service support.

**Restrict network access before starting.** New proxy installations listen only on loopback. If `proxy set --bind-host` changes the listener to LAN/non-loopback, a missing `CHATCLASH_PROXY_AUTH` makes generation fail without writing configuration. New generated configuration binds the no-secret management endpoint to `127.0.0.1:9090`; refresh legacy `:9090` configuration after upgrading. Never expose any controller bind directly to the Internet. Proxy authentication does not protect the controller.

```bash
chatclash init -i
chatclash mihomo install --daemon
chatclash sub update -I
chatclash proxy validate -I
chatclash mihomo start -I
chatclash status -I
chatenv test -t chatclash
```

- `init -i` collects the subscription and `user:password` proxy credentials interactively, keeping secrets out of command history.
- `install --daemon` installs the engine and writes/enables a user unit; it **does not start the service**. A working user systemd session is required.
- Install the engine before `sub update` so validation can run before configuration replacement. Do not make validation bypass the normal setup path.
- `chatenv test` requests external sites to check proxy connectivity; it is not an offline schema check.
- `init` rewrites local layout/port settings. It is not an upgrade command; do not reinitialize an existing deployment to upgrade it.

If the subscription needs a converter, follow [Operations: subscription converter](operations.md#converter) first. Download failure is not a reason to start an unvalidated proxy.

## Which component is upgraded? {#upgrade}

| Operation | Updated component | Automatic Mihomo restart? |
| --- | --- | --- |
| `python -m pip install -U chatclash` | CLI and dependencies in that Python environment | No; it does not replace the engine either |
| `chatclash mihomo update` | Mihomo binary on disk | No; explicitly restart |
| `chatclash sub update` | Generated machine-local YAML | No; explicitly validate and reload |

See [Operations](operations.md).

## Useful links

- [Configuration and ChatEnv](configuration.md) · [CLI Tree](cli-tree.md)
- [PyPI package](https://pypi.org/project/chatclash/) · [Source and issues](https://github.com/ChatArch/ChatClash)
- [ChatArch documentation hub](https://arch.gh.wzhecnu.cn/)
