# Release

## Preconditions

- `python -m pytest -q`
- `mkdocs build --strict`
- `python -m build`
- `python -m twine check dist/*`
- `chatclash --version`
- `chatclash --tree`
- `chatclash --tree-brief`
- `git diff --check`
- Optional real smoke check:
  - `<LOCAL_SKILLS_DIR>/chatclash-dev/scripts/smoke_service.sh <CHATCLASH_REPO>`

## Local Release Flow

1. Update `src/chatclash/__init__.py` version.
2. Update `CHANGELOG.md`.
3. Run all preconditions above.
4. Commit and push a release branch, then open a PR against `master`.
5. Merge only after the exact PR head has green checks.
6. Fast-forward the local `master` checkout to the merged remote commit.
7. Tag that exact merged default-branch commit, then push only the tag:

```bash
git tag -a v0.1.8 -m "Release ChatClash 0.1.8"
git push origin v0.1.8
```

8. Require the tag-driven publish workflow to succeed, verify wheel and sdist on the exact PyPI version page, and clean-install that exact version before running published `--version`, `--tree`, and `--tree-brief` readbacks.

## GitHub Actions

- `CI`: tests, build, and docs build.
- `Deploy Docs`: publishes `mkdocs gh-deploy` on push to `master` or `main`.
- `Preview Docs`: publishes preview docs for pull requests from the same repo.
- `Publish Package`: tag-triggered build and PyPI publish through trusted publishing/OIDC (`id-token: write`).

## Notes

- Keep release notes minimal and factual.
- Do not cut a tag until CI and smoke checks are green.
