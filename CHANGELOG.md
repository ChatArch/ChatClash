# Changelog

## Unreleased

- Refine the command tree to `init`, `status`, `sub`, `proxy`, `mihomo`, and `check`.
- Split CLI behavior into reusable Python API modules for subscription, proxy, Mihomo runtime, checks, status, and local paths.
- Keep sensitive subscription URLs and proxy authentication masked in command output.
- Default to a lightweight Mihomo binary backend for the single-machine flow.
- Support direct Clash YAML subscription refresh with local header/auth preservation and private backups.


## 0.1.0

### Added
- Initial CLI scaffolding and subscription conversion helpers.
- `.codex/skills/chatclash-usage` for quickstart and proxy setup notes.

### Changed
- Real Docker Compose generation and subconverter-backed config generation now match the PRD.
- Release workflow now checks build artifacts and publishes through trusted PyPI publishing.
- Docs deploy and preview workflows are aligned around the docs publishing flow.

### Fixed
- CLI and docs now use the actual ChatClash command set instead of the initial template `hello` example.
