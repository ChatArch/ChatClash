from pathlib import Path

from click.testing import CliRunner

from chatclash.cli import main


def _text_block(path: str) -> str:
    text = Path(path).read_text(encoding="utf-8")
    marker = "```text\n"
    assert marker in text, path
    return text.split(marker, 1)[1].split("\n```", 1)[0].strip()


def test_mkdocs_material_renderer_and_public_docs_contract():
    mkdocs = Path("mkdocs.yml").read_text(encoding="utf-8")
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")

    assert "site_url: https://arch.gh.wzhecnu.cn/ChatClash/" in mkdocs
    assert "repo_url: https://github.com/ChatArch/ChatClash" in mkdocs
    assert "mkdocs-static-i18n" in pyproject
    assert "mkdocs-material>=9.5,<9.7" in pyproject
    assert "chatstyle>=0.2.0,<0.3.0" in pyproject
    assert "chatenv>=0.2.10,<0.3.0" in pyproject

    assert "pymdownx.emoji" in mkdocs
    assert "emoji_index: !!python/name:material.extensions.emoji.twemoji" in mkdocs
    assert "emoji_generator: !!python/name:material.extensions.emoji.to_svg" in mkdocs

    assert "index.md" in mkdocs
    assert Path("docs/index.md").exists()
    assert Path("docs/index.en.md").exists()
    assert Path("docs/cli-tree.md").exists()
    assert Path("docs/cli-tree.en.md").exists()

    for path in ["docs/index.md", "docs/index.en.md", "docs/cli-tree.md", "docs/cli-tree.en.md"]:
        text = Path(path).read_text(encoding="utf-8")
        assert "ChatClash" in text
        assert "--tree" in text
        assert "--tree-brief" in text


def test_documented_trees_match_registered_full_and_brief_output():
    full = CliRunner().invoke(main, ["--tree"])
    brief = CliRunner().invoke(main, ["--tree-brief"])

    assert full.exit_code == 0, full.output
    assert brief.exit_code == 0, brief.output
    for path in ["README.md", "docs/cli-tree.md", "docs/cli-tree.en.md"]:
        assert _text_block(path) == full.output.strip(), path
    for path in ["README.en.md", "docs/index.md"]:
        assert _text_block(path) == brief.output.strip(), path


def test_no_literal_material_icon_tokens_in_source_docs():
    for path in Path("docs").glob("*.md"):
        text = path.read_text(encoding="utf-8")
        assert ":material-" not in text, path
