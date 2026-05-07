# Changelog

## 0.1.0

### Added
- `setup clash`, `status`, `proxy env`, `sub status`, `sub url`, and `sub generate`.
- `.codex/skills/chatclash-usage` for quickstart, service startup, and Docker proxy setup.

### Changed
- Real Docker Compose generation and subconverter-backed config generation now match the PRD.
- Release workflow now checks build artifacts and publishes through trusted PyPI publishing.
- Docs deploy and preview workflows are aligned around the docs publishing flow.

### Fixed
- CLI and docs now use the actual ChatClash command set instead of the initial template `hello` example.
