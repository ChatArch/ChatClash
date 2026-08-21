# CLI Tree

ChatStyle renders `chatclash --tree` from the registered Click command object; `chatclash --tree-brief` preserves the same nodes without parameter signatures. This page lists implemented, reachable commands only; planned capabilities must not appear as successful CLI leaves.

```text
chatclash
├── --help  # Show this message and exit.
├── --version  # Show the version and exit.
├── --tree  # Print the registered CLI tree and exit.
├── --tree-brief  # Print the registered CLI tree without parameter signatures and exit.
├── --interactive  # Auto prompt on missing args, -i forces interactive, -I disables it.
├── init [--home HOME] [--dry-run] [--local-only] [--url-env URL-ENV] [--subscription-url SUBSCRIPTION-URL] [--proxy-auth-env PROXY-AUTH-ENV] [--proxy-auth PROXY-AUTH] [--subconverter-url SUBCONVERTER-URL] [--yes] [--interactive]  # Initialize this machine and collect required ChatEnv config.
├── mihomo [--interactive]  # Install and manage the local runtime.
│   ├── install [--repo REPO] [--version VERSION] [--dry-run] [--force] [--daemon] [--interactive]  # Install the local Mihomo binary.
│   ├── logs [--tail TAIL] [--dry-run] [--interactive]  # Show local Mihomo runtime logs.
│   ├── reload [--dry-run] [--interactive]  # Hot-reload the current active config through Mihomo's controller.
│   ├── restart [--dry-run] [--interactive]  # Restart the local Mihomo runtime.
│   ├── start [--dry-run] [--interactive]  # Start the local Mihomo runtime.
│   ├── status [--interactive]  # Show local Mihomo runtime status.
│   ├── stop [--dry-run] [--interactive]  # Stop the local Mihomo runtime.
│   ├── uninstall [--dry-run] [--daemon] [--interactive]  # Uninstall the local Mihomo binary.
│   └── update [--repo REPO] [--version VERSION] [--dry-run] [--interactive]  # Update the local Mihomo binary.
├── proxy [--interactive]  # Show and update local proxy endpoint settings.
│   ├── env [--no-mask] [--interactive]  # Print shell proxy environment exports.
│   ├── set [--http-port HTTP-PORT-VALUE] [--socks-port SOCKS-PORT-VALUE] [--controller-port CONTROLLER-PORT-VALUE] [--bind-host BIND-HOST] [--proxy-host PROXY-HOST-VALUE] [--dry-run] [--yes] [--interactive]  # Update local proxy listener settings and re-render active config.
│   ├── show [--no-mask] [--interactive]  # Show proxy endpoints for this machine.
│   └── validate [--dry-run] [--interactive]  # Validate the current active Mihomo config.
├── status [--interactive]  # Show this machine's ChatClash status.
└── sub [--interactive]  # Manage subscription-backed runtime config.
    ├── converter [--interactive]  # Install and manage the local subscription converter service.
    │   ├── install [--source SOURCE] [--repo REPO] [--version VERSION] [--force] [--dry-run] [--interactive]  # Install the local subscription converter binary.
    │   ├── logs [--tail TAIL] [--dry-run] [--interactive]  # Show local subscription converter logs.
    │   ├── start [--host HOST] [--port PORT] [--dry-run] [--interactive]  # Start the local subscription converter service.
    │   ├── status [--host HOST] [--port PORT] [--interactive]  # Show the local subscription converter service status.
    │   └── stop [--dry-run] [--interactive]  # Stop the local subscription converter service.
    ├── generate [SUBSCRIPTION-URL] [--subconverter-url SUBCONVERTER-URL] [--output OUTPUT] [--dry-run] [--yes] [--interactive]  # Generate a Clash-compatible config through subscription conversion.
    ├── set [--url-env URL-ENV] [--subconverter-url-env SUBCONVERTER-URL-ENV] [--subscription-url SUBSCRIPTION-URL] [--subconverter-url SUBCONVERTER-URL] [--interactive]  # Store subscription operator config through ChatEnv.
    ├── status [--interactive]  # Show redacted subscription config state.
    ├── update [--dry-run] [--no-validate] [--fetch-proxy FETCH-PROXY] [--interactive]  # Refresh the runtime config from the configured subscription.
    └── url [SUBSCRIPTION-URL] [--subconverter-url SUBCONVERTER-URL] [--show] [--interactive]  # Build a subconverter URL for the configured subscription.
```

## Update contract

- Keep tests, README, this CLI tree page, and the changelog aligned whenever commands change.
- Sensitive options are shown by name only; never document subscription URLs, proxy auth values, or tokens.
- This package manages the current machine's ChatClash/Mihomo runtime and does not orchestrate remote hosts.
