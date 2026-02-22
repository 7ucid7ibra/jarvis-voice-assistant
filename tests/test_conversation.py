from pathlib import Path

from jarvis_assistant.conversation import Conversation


def test_conversation_accepts_bare_filename(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    conv = Conversation(history_file="conversation_history.json")
    conv.add_message("user", "hello")
    assert Path("conversation_history.json").exists()


def test_conversation_creates_parent_directory(tmp_path):
    history_path = tmp_path / "history" / "profile_a.json"
    conv = Conversation(history_file=str(history_path))
    conv.add_message("assistant", "ok")
    assert history_path.exists()
