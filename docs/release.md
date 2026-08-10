# Release

## Preconditions

- `python -m pytest -q`
- `python -m build`
- Optional real smoke check:
  - `<LOCAL_SKILLS_DIR>/chatclash-dev/scripts/smoke_service.sh <CHATCLASH_REPO>`

## Local Release Flow

1. Update `src/chatclash/__init__.py` version.
2. Update `CHANGELOG.md`.
3. Run tests and build.
4. Commit with a release message.
5. Tag the merged default-branch commit, for example `v0.1.6`.
6. Push branch and tag:

```bash
git push origin master
git push origin v0.1.6
```

If you are releasing the current stable line without bumping code version, tag the exact release commit as `v0.1.0` first and let the tag-triggered workflow publish from that ref.

## GitHub Actions

- `CI`: tests, build, and docs build.
- `Deploy Docs`: publishes `mkdocs gh-deploy` on push to `master` or `main`.
- `Preview Docs`: publishes preview docs for pull requests from the same repo.
- `Publish Package`: tag-triggered build and PyPI publish through trusted publishing/OIDC (`id-token: write`).

## Notes

- Keep release notes minimal and factual.
- Do not cut a tag until CI and smoke checks are green.
