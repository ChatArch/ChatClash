from pathlib import Path


def test_publish_workflow_uses_oidc_with_release_guards():
    workflow = Path(".github/workflows/publish.yml").read_text(encoding="utf-8")

    assert "id-token: write" in workflow
    assert "pypa/gh-action-pypi-publish@release/v1" in workflow
    assert "TWINE_PASSWORD" not in workflow
    assert "PYPI_API_TOKEN" not in workflow
    assert "secrets.PYPI" not in workflow
    assert "environment: pypi" not in workflow

    assert "Check tag matches package version" in workflow
    assert "Check release commit is on default branch" in workflow
    assert "git fetch --no-tags origin master:refs/remotes/origin/master" in workflow
    assert "git merge-base --is-ancestor" in workflow
    assert "origin/master" in workflow
    assert "git fetch origin master --tags" not in workflow
    assert "git fetch origin main --tags" not in workflow

    assert "Check PyPI version" in workflow
    assert "https://pypi.org/pypi/chatclash/" in workflow


def test_ci_workflow_runs_docs_build_and_installed_cli_smoke():
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "python -m pytest -q" in workflow
    assert "mkdocs build --strict" in workflow
    assert "python -m build" in workflow
    assert "chatclash --version" in workflow
    assert "chatclash --tree" in workflow
    assert "chatclash --tree-brief" in workflow


def test_docs_workflows_use_chatarch_public_domain_and_root_deploy():
    preview = Path(".github/workflows/preview.yaml").read_text(encoding="utf-8")
    deploy = Path(".github/workflows/deploy.yaml").read_text(encoding="utf-8")

    assert "CHATARCH_PREVIEW_URL" in preview
    assert "${site_url}/dev/" in preview
    assert "github.io" not in preview
    assert "mkdocs gh-deploy --force" in deploy
