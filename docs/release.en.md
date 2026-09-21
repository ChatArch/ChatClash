# Release

## Local acceptance

Run the following in an isolated environment at the supported Python version:

```bash
python -m pytest -q
python -m pip check
chatclash --version
chatclash --tree
chatclash --tree-brief
python -m build
python -m twine check dist/*
mkdocs build --strict
git diff --check
```

Install the built wheel into a fresh environment and read back `--version`, `--tree`, `--tree-brief`, and ChatEnv provider discovery. An editable source environment is not public-install verification.

## Release order

1. Select the next forward version from PyPI, remote tags, and default-branch source.
2. Update version, changelog, tests, and user docs; complete local acceptance and independent review first.
3. Push a branch and create a PR; merge only after checks are green for its exact head.
4. Synchronize the default branch and prove the release tag targets the merged default-branch commit, not a feature-branch commit.
5. Create and push the `v<version>` tag in the repository's established style, then wait for the tag-triggered publish workflow.
6. Read back exact-version PyPI metadata, wheel, and sdist; install the exact version from public PyPI in a cache-free isolated environment.
7. Synchronize the canonical checkout, confirm a clean status, and install the exact public release into the standard ChatArch venv when appropriate.

## Service boundary

Publishing a Python package does not automatically replace the engine, refresh a subscription, or restart `chatclash-mihomo.service`. Plan production migration separately: install the published version, render and validate configuration, then explicitly reload/restart in an authorized maintenance window and verify proxy behavior. Never commit or publish subscription data, authentication, or generated YAML.
