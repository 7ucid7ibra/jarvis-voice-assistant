import importlib
import json
import sys

import pytest

from jarvis_assistant import secret_store


@pytest.fixture
def fake_store():
    return {}


def _load_config_module(monkeypatch, tmp_path, fake_store, *, keychain_available=True):
    settings_path = tmp_path / "settings.json"
    monkeypatch.setenv("JARVIS_SETTINGS_FILE", str(settings_path))

    def _get_secret(key):
        return fake_store.get(key, "")

    def _set_secret(key, value):
        fake_store[key] = value

    def _delete_secret(key):
        fake_store.pop(key, None)

    monkeypatch.setattr(secret_store, "is_available", lambda: keychain_available)
    monkeypatch.setattr(secret_store, "get_secret", _get_secret)
    monkeypatch.setattr(secret_store, "set_secret", _set_secret)
    monkeypatch.setattr(secret_store, "delete_secret", _delete_secret)

    sys.modules.pop("jarvis_assistant.config", None)
    return importlib.import_module("jarvis_assistant.config"), settings_path


def test_migrate_plaintext_secrets_and_scrub_file(monkeypatch, tmp_path, fake_store):
    config_module, settings_path = _load_config_module(monkeypatch, tmp_path, fake_store, keychain_available=True)
    settings_path.write_text(
        json.dumps(
            {
                "assistant_name": "JARVIS",
                "ha_token": "legacy-ha",
                "api_key": "legacy-api",
                "telegram_bot_token": "legacy-bot",
                "telegram_chat_id": "legacy-chat",
            }
        )
    )

    cfg = config_module.Config(settings_file=str(settings_path))

    assert cfg.ha_token == "legacy-ha"
    assert cfg.api_key == "legacy-api"
    assert cfg.telegram_bot_token == "legacy-bot"
    assert cfg.telegram_chat_id == "legacy-chat"

    saved = json.loads(settings_path.read_text())
    assert "ha_token" not in saved
    assert "api_key" not in saved
    assert "telegram_bot_token" not in saved
    assert "telegram_chat_id" not in saved


def test_secure_save_roundtrip_and_scrub(monkeypatch, tmp_path, fake_store):
    config_module, settings_path = _load_config_module(monkeypatch, tmp_path, fake_store, keychain_available=True)
    cfg = config_module.Config(settings_file=str(settings_path))

    cfg.ha_token = "ha-new"
    cfg.api_key = "api-new"
    cfg.save()

    cfg2 = config_module.Config(settings_file=str(settings_path))
    assert cfg2.ha_token == "ha-new"
    assert cfg2.api_key == "api-new"

    saved = json.loads(settings_path.read_text())
    assert "ha_token" not in saved
    assert "api_key" not in saved


def test_env_var_override(monkeypatch, tmp_path, fake_store):
    config_module, settings_path = _load_config_module(monkeypatch, tmp_path, fake_store, keychain_available=True)
    fake_store["ha_token"] = "stored-ha"
    monkeypatch.setenv("HA_TOKEN", "env-ha")
    cfg = config_module.Config(settings_file=str(settings_path))
    assert cfg.ha_token == "env-ha"


def test_clear_secret_removes_from_store_and_json(monkeypatch, tmp_path, fake_store):
    config_module, settings_path = _load_config_module(monkeypatch, tmp_path, fake_store, keychain_available=True)
    cfg = config_module.Config(settings_file=str(settings_path))
    cfg.ha_token = "set-me"
    cfg.save()
    assert fake_store.get("ha_token") == "set-me"

    cfg.ha_token = ""
    cfg.save()
    assert "ha_token" not in fake_store

    saved = json.loads(settings_path.read_text())
    assert "ha_token" not in saved


def test_keychain_unavailable_scrubs_plaintext_without_crash(monkeypatch, tmp_path, fake_store):
    config_module, settings_path = _load_config_module(monkeypatch, tmp_path, fake_store, keychain_available=False)
    settings_path.write_text(json.dumps({"ha_token": "legacy-ha"}))

    cfg = config_module.Config(settings_file=str(settings_path))

    assert cfg.ha_token == ""
    saved = json.loads(settings_path.read_text())
    assert "ha_token" not in saved
