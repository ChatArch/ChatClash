"""Windows user-scope proxy and environment management.

The module deliberately uses HKCU only.  It never changes WinHTTP, services, or
machine-wide settings, so every operation is usable without elevation.
"""

from __future__ import annotations

import json
import platform
import socket
import tempfile
from pathlib import Path
from typing import Any

from .paths import chatclash_home, http_port, proxy_host
from .utils import mask


INTERNET_SETTINGS = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
USER_ENVIRONMENT = r"Environment"
SYSTEM_PROXY_BACKUP = "windows-system-proxy-backup.json"
USER_ENV_BACKUP = "windows-proxy-env-backup.json"
PROXY_ENV_NAMES = ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY")
INTERNET_OPTION_PER_CONNECTION_OPTION = 75
INTERNET_PER_CONN_FLAGS = 1
INTERNET_PER_CONN_FLAGS_UI = 10
PROXY_TYPE_DIRECT = 1
PROXY_TYPE_PROXY = 2
PROXY_TYPE_AUTO_PROXY_URL = 4
PROXY_TYPE_AUTO_DETECT = 8


def is_windows() -> bool:
    return platform.system().lower() == "windows"


def _require_windows() -> None:
    if not is_windows():
        raise RuntimeError("Windows user proxy management is only available on Windows")


def _winreg():
    _require_windows()
    import winreg

    return winreg


def _backup_path(name: str) -> Path:
    return chatclash_home() / name


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise RuntimeError(f"invalid backup file: {path}")
    return loaded


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(json.dumps(value, indent=2, sort_keys=True))
        temporary = Path(handle.name)
    try:
        temporary.chmod(0o600)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _registry_value(key: Any, name: str) -> dict[str, Any]:
    registry = _winreg()
    try:
        value, kind = registry.QueryValueEx(key, name)
    except FileNotFoundError:
        return {"present": False}
    return {"present": True, "value": value, "kind": kind}


def _restore_registry_value(key: Any, name: str, snapshot: dict[str, Any]) -> None:
    registry = _winreg()
    if snapshot.get("present"):
        registry.SetValueEx(key, name, 0, int(snapshot["kind"]), snapshot["value"])
    else:
        try:
            registry.DeleteValue(key, name)
        except FileNotFoundError:
            pass


def _broadcast_settings_change() -> None:
    """Refresh WinINet and notify applications of user setting changes."""
    if not is_windows():
        return
    try:
        import ctypes

        wininet = ctypes.windll.wininet
        wininet.InternetSetOptionW(0, 39, None, 0)  # INTERNET_OPTION_SETTINGS_CHANGED
        wininet.InternetSetOptionW(0, 37, None, 0)  # INTERNET_OPTION_REFRESH
        ctypes.windll.user32.SendMessageTimeoutW(0xFFFF, 0x001A, 0, "Environment", 0x0002, 5000, None)
    except Exception:
        # Registry values remain correct even when no interactive shell is present.
        pass


def _wininet_connection_flags() -> int:
    """Read effective WinINet flags, including connection-level WPAD/PAC state."""
    _require_windows()
    import ctypes
    from ctypes import wintypes

    class OptionValue(ctypes.Union):
        _fields_ = [("dwValue", wintypes.DWORD), ("pszValue", wintypes.LPWSTR), ("ftValue", wintypes.FILETIME)]

    class Option(ctypes.Structure):
        _fields_ = [("dwOption", wintypes.DWORD), ("Value", OptionValue)]

    class OptionList(ctypes.Structure):
        _fields_ = [("dwSize", wintypes.DWORD), ("pszConnection", wintypes.LPWSTR), ("dwOptionCount", wintypes.DWORD), ("dwOptionError", wintypes.DWORD), ("pOptions", ctypes.POINTER(Option))]

    options = (Option * 1)()
    options[0].dwOption = INTERNET_PER_CONN_FLAGS_UI
    option_list = OptionList(ctypes.sizeof(OptionList), None, 1, 0, options)
    size = wintypes.DWORD(ctypes.sizeof(option_list))
    wininet = ctypes.windll.wininet
    wininet.InternetQueryOptionW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPVOID, ctypes.POINTER(wintypes.DWORD)]
    wininet.InternetQueryOptionW.restype = wintypes.BOOL
    if not wininet.InternetQueryOptionW(None, INTERNET_OPTION_PER_CONNECTION_OPTION, ctypes.byref(option_list), ctypes.byref(size)):
        raise ctypes.WinError(ctypes.get_last_error())
    return int(options[0].Value.dwValue)


def _set_wininet_connection_flags(flags: int) -> None:
    """Set the effective default-connection proxy mode through WinINet."""
    _require_windows()
    import ctypes
    from ctypes import wintypes

    class OptionValue(ctypes.Union):
        _fields_ = [("dwValue", wintypes.DWORD), ("pszValue", wintypes.LPWSTR), ("ftValue", wintypes.FILETIME)]

    class Option(ctypes.Structure):
        _fields_ = [("dwOption", wintypes.DWORD), ("Value", OptionValue)]

    class OptionList(ctypes.Structure):
        _fields_ = [("dwSize", wintypes.DWORD), ("pszConnection", wintypes.LPWSTR), ("dwOptionCount", wintypes.DWORD), ("dwOptionError", wintypes.DWORD), ("pOptions", ctypes.POINTER(Option))]

    options = (Option * 1)()
    options[0].dwOption = INTERNET_PER_CONN_FLAGS
    options[0].Value.dwValue = flags
    option_list = OptionList(ctypes.sizeof(OptionList), None, 1, 0, options)
    wininet = ctypes.windll.wininet
    wininet.InternetSetOptionW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPVOID, wintypes.DWORD]
    wininet.InternetSetOptionW.restype = wintypes.BOOL
    if not wininet.InternetSetOptionW(None, INTERNET_OPTION_PER_CONNECTION_OPTION, ctypes.byref(option_list), ctypes.sizeof(option_list)):
        raise ctypes.WinError(ctypes.get_last_error())


def local_proxy_ready() -> bool:
    """Require a listening loopback proxy before changing Windows proxy routing."""
    host = proxy_host()
    if host.lower() not in {"127.0.0.1", "localhost", "::1"}:
        return False
    try:
        with socket.create_connection((host, http_port()), timeout=1):
            return True
    except OSError:
        return False


def _require_snapshot(snapshot: dict[str, Any], names: tuple[str, ...], path: Path) -> None:
    missing = []
    for name in names:
        value = snapshot.get(name)
        if not isinstance(value, dict) or not isinstance(value.get("present"), bool):
            missing.append(name)
        elif value["present"] and ("kind" not in value or "value" not in value):
            missing.append(name)
    if missing:
        raise RuntimeError(f"backup is incomplete and will not be restored: {path}")


def get_system_proxy_status() -> dict[str, str]:
    _require_windows()
    registry = _winreg()
    with registry.OpenKey(registry.HKEY_CURRENT_USER, INTERNET_SETTINGS, 0, registry.KEY_READ) as key:
        enabled = _registry_value(key, "ProxyEnable").get("value", 0)
        server = _registry_value(key, "ProxyServer").get("value", "")
        override = _registry_value(key, "ProxyOverride").get("value", "")
    flags = _wininet_connection_flags()
    backup = _backup_path(SYSTEM_PROXY_BACKUP)
    return {
        "enabled": "yes" if int(enabled or 0) else "no",
        "server": mask(str(server)) if server else "<not set>",
        "bypass": str(override or "<not set>"),
        "pac": "configured" if flags & PROXY_TYPE_AUTO_PROXY_URL else "not configured",
        "auto_detect": "enabled" if flags & PROXY_TYPE_AUTO_DETECT else "disabled",
        "backup": "present" if backup.exists() else "absent",
        "ready": "yes" if local_proxy_ready() else "no",
    }


def enable_system_proxy(*, dry_run: bool = False) -> list[str]:
    _require_windows()
    if not local_proxy_ready():
        raise RuntimeError("local HTTP proxy is not listening; start Mihomo and wait for its loopback port before enabling Windows proxy")
    server = f"http={proxy_host()}:{http_port()};https={proxy_host()}:{http_port()}"
    backup_path = _backup_path(SYSTEM_PROXY_BACKUP)
    lines = ["scope: current user", f"server: {server}"]
    if dry_run:
        return lines + [f"backup: {backup_path}"]
    registry = _winreg()
    with registry.CreateKeyEx(registry.HKEY_CURRENT_USER, INTERNET_SETTINGS, 0, registry.KEY_READ | registry.KEY_WRITE) as key:
        flags = _wininet_connection_flags()
        if not backup_path.exists():
            snapshot = {name: _registry_value(key, name) for name in ("ProxyEnable", "ProxyServer", "ProxyOverride")}
            snapshot["wininet_flags"] = flags
            _write_json(backup_path, snapshot)
        registry.SetValueEx(key, "ProxyEnable", 0, registry.REG_DWORD, 1)
        registry.SetValueEx(key, "ProxyServer", 0, registry.REG_SZ, server)
        registry.SetValueEx(key, "ProxyOverride", 0, registry.REG_SZ, "localhost;127.0.0.1;<local>")
    _set_wininet_connection_flags(PROXY_TYPE_DIRECT | PROXY_TYPE_PROXY)
    _broadcast_settings_change()
    return lines + ["enabled: yes"]


def restore_system_proxy(*, dry_run: bool = False) -> list[str]:
    _require_windows()
    backup_path = _backup_path(SYSTEM_PROXY_BACKUP)
    snapshot = _read_json(backup_path)
    if snapshot is None:
        return ["restored: no backup was present"]
    names = ("ProxyEnable", "ProxyServer", "ProxyOverride")
    _require_snapshot(snapshot, names, backup_path)
    if not isinstance(snapshot.get("wininet_flags"), int):
        raise RuntimeError(f"backup is incomplete and will not be restored: {backup_path}")
    if dry_run:
        return [f"restore: {backup_path}"]
    registry = _winreg()
    with registry.CreateKeyEx(registry.HKEY_CURRENT_USER, INTERNET_SETTINGS, 0, registry.KEY_READ | registry.KEY_WRITE) as key:
        for name in names:
            _restore_registry_value(key, name, snapshot[name])
    _set_wininet_connection_flags(snapshot["wininet_flags"])
    backup_path.unlink(missing_ok=True)
    _broadcast_settings_change()
    return ["restored: previous current-user proxy settings"]


def get_powershell_proxy_env(*, include_auth: bool = True, no_mask: bool = False) -> dict[str, str]:
    from .proxy import get_proxy_env

    values = get_proxy_env(include_auth=include_auth, no_mask=no_mask)
    return {
        "HTTP_PROXY": values["http_proxy"],
        "HTTPS_PROXY": values["https_proxy"],
        "ALL_PROXY": values["all_proxy"],
        "NO_PROXY": values["no_proxy"],
    }


def powershell_proxy_commands(*, include_auth: bool = True, no_mask: bool = False) -> list[str]:
    values = get_powershell_proxy_env(include_auth=include_auth, no_mask=no_mask)
    return [f"$env:{name} = '{value.replace(chr(39), chr(39) * 2)}'" for name, value in values.items()]


def persist_proxy_environment(*, include_auth: bool = True, no_mask: bool = False, dry_run: bool = False) -> list[str]:
    _require_windows()
    from .proxy import proxy_auth_status

    if proxy_auth_status().present and not no_mask:
        raise RuntimeError("refusing to persist masked proxy authentication; pass --no-mask only when you accept storing it in current-user environment variables")
    if not local_proxy_ready():
        raise RuntimeError("local HTTP proxy is not listening; start Mihomo and wait for its loopback port before persisting proxy environment")
    values = get_powershell_proxy_env(include_auth=include_auth, no_mask=no_mask)
    backup_path = _backup_path(USER_ENV_BACKUP)
    if dry_run:
        return ["scope: current user", *[f"set: {name}" for name in values], f"backup: {backup_path}"]
    registry = _winreg()
    with registry.CreateKeyEx(registry.HKEY_CURRENT_USER, USER_ENVIRONMENT, 0, registry.KEY_READ | registry.KEY_WRITE) as key:
        if not backup_path.exists():
            _write_json(backup_path, {name: _registry_value(key, name) for name in PROXY_ENV_NAMES})
        for name, value in values.items():
            registry.SetValueEx(key, name, 0, registry.REG_SZ, value)
    _broadcast_settings_change()
    return ["persisted: HTTP_PROXY, HTTPS_PROXY, ALL_PROXY, NO_PROXY"]


def restore_proxy_environment(*, dry_run: bool = False) -> list[str]:
    _require_windows()
    backup_path = _backup_path(USER_ENV_BACKUP)
    snapshot = _read_json(backup_path)
    if snapshot is None:
        return ["restored: no environment backup was present"]
    _require_snapshot(snapshot, PROXY_ENV_NAMES, backup_path)
    if dry_run:
        return [f"restore: {backup_path}"]
    registry = _winreg()
    with registry.CreateKeyEx(registry.HKEY_CURRENT_USER, USER_ENVIRONMENT, 0, registry.KEY_READ | registry.KEY_WRITE) as key:
        for name in PROXY_ENV_NAMES:
            _restore_registry_value(key, name, snapshot[name])
    backup_path.unlink(missing_ok=True)
    _broadcast_settings_change()
    return ["restored: previous current-user proxy environment"]
