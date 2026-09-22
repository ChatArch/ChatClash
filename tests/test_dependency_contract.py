from importlib.metadata import metadata, requires


def test_runtime_dependencies_keep_the_shared_cli_baseline():
    dependencies = requires("chatclash") or []
    assert any(line.startswith("chatstyle") and ">=0.2.0" in line and "<0.3.0" in line for line in dependencies)
    assert any(line.startswith("chatenv") and ">=0.2.11" in line and "<0.3.0" in line for line in dependencies)
    assert any(line.startswith("click") and "<9.0" in line for line in dependencies)
    assert any(line.lower().startswith("pyyaml") and "<7.0" in line for line in dependencies)
    assert metadata("chatclash")["Requires-Python"] == ">=3.10"
