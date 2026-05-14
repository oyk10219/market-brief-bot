from pathlib import Path

from src.summarizer import _codex_command, _codex_environment


def test_codex_environment_uses_default_codex_home_and_removes_blocked_proxy(monkeypatch, tmp_path):
    monkeypatch.delenv("CODEX_HOME", raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "localappdata"))
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:9")

    env = _codex_environment(tmp_path / "project")

    assert "CODEX_HOME" not in env
    assert "HTTPS_PROXY" not in env


def test_codex_environment_prepares_explicit_codex_home(monkeypatch, tmp_path):
    codex_home = tmp_path / "codex-home"
    monkeypatch.setenv("CODEX_HOME", str(codex_home))

    env = _codex_environment(tmp_path / "project")

    assert env["CODEX_HOME"] == str(codex_home)
    assert (codex_home / "sessions").exists()
    assert (codex_home / "tmp").exists()


def test_codex_command_overrides_reasoning_effort(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: "codex")

    command = _codex_command(Path("summary.md"), Path("."), model="gpt-5.2", reasoning_effort="low")

    assert "-c" in command
    assert 'model_reasoning_effort="low"' in command
    assert command[-3:] == ["-m", "gpt-5.2", "-"]
