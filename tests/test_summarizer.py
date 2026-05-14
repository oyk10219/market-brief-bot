from src.summarizer import _codex_environment


def test_codex_environment_uses_localappdata_and_removes_blocked_proxy(monkeypatch, tmp_path):
    monkeypatch.delenv("CODEX_HOME", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "localappdata"))
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:9")

    env = _codex_environment(tmp_path / "project")

    assert env["CODEX_HOME"] == str(tmp_path / "localappdata" / "MarketBriefBot" / "codex")
    assert "HTTPS_PROXY" not in env
    assert (tmp_path / "localappdata" / "MarketBriefBot" / "codex" / "sessions").exists()
    assert (tmp_path / "localappdata" / "MarketBriefBot" / "codex" / "tmp").exists()
