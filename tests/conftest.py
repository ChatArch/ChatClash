from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture(autouse=True)
def isolated_runtime_home(tmp_path, monkeypatch):
    home = tmp_path / "user-home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setenv("CHATARCH_HOME", str(tmp_path / "chatarch-home"))
    for key in ("CHATCLASH_HOME", "CHATCLASH_SUBSCRIPTION_URL", "CHATCLASH_PROXY_AUTH", "CHATCLASH_SUBCONVERTER_URL"):
        monkeypatch.delenv(key, raising=False)
