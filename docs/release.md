# Release

## Preconditions

- `python -m pytest -q`
- `python -m build`
- Optional real smoke check:
  - `~/.codex/skills/chatclash-dev/scripts/smoke_service.sh /home/rexwzh/workspace/core/ChatClash`

## Local Release Flow

1. Update `src/chatclash/__init__.py` version.
2. Update `CHANGELOG.md`.
3. Run tests and build.
4. Commit with a release message.
5. Tag the release, for example `v0.1.1`.
6. Push branch and tag:

```bash
git push origin master
git push origin v0.1.1
```

If you are releasing the current stable line without bumping code version, tag the exact release commit as `v0.1.0` first and let the tag-triggered workflow publish from that ref.

## GitHub Actions

- `CI`: tests, build, and docs build.
- `Deploy Docs`: publishes `mkdocs gh-deploy` on push to `master` or `main`.
- `Preview Docs`: publishes preview docs for pull requests from the same repo.
- `Publish Package`: manual dispatch for packaging; enable trusted publishing or PyPI credentials before using it as a real release gate.

## Notes

- Keep release notes minimal and factual.
- Do not cut a tag until CI and smoke checks are green.
