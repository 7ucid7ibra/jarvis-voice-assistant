from types import SimpleNamespace

import pytest

import jarvis_assistant.ha_client as ha_client_module


class _Resp:
    def __init__(self, payload=None, status_code=200):
        self._payload = payload if payload is not None else []
        self.status_code = status_code

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_ha_token_updates_after_client_init(monkeypatch):
    fake_cfg = SimpleNamespace(ha_url="http://ha.local:8123", ha_token="")
    monkeypatch.setattr(ha_client_module, "cfg", fake_cfg)

    client = ha_client_module.HomeAssistantClient()

    with pytest.raises(RuntimeError, match="token is not set"):
        client._headers()

    # Simulate user saving token in Settings while app is already running.
    fake_cfg.ha_token = "new-runtime-token"
    headers = client._headers()
    assert headers["Authorization"] == "Bearer new-runtime-token"


def test_ha_url_updates_after_client_init(monkeypatch):
    fake_cfg = SimpleNamespace(ha_url="http://old.local:8123", ha_token="abc")
    monkeypatch.setattr(ha_client_module, "cfg", fake_cfg)

    captured = {}

    def _fake_get(url, headers, timeout):
        captured["url"] = url
        captured["headers"] = headers
        captured["timeout"] = timeout
        return _Resp(payload=[])

    monkeypatch.setattr(ha_client_module.requests, "get", _fake_get)

    client = ha_client_module.HomeAssistantClient()
    fake_cfg.ha_url = "http://new.local:8123/"
    client.get_states()

    assert captured["url"] == "http://new.local:8123/api/states"
    assert captured["headers"]["Authorization"] == "Bearer abc"
    assert captured["timeout"] == 5


def test_explicit_token_override_still_wins(monkeypatch):
    fake_cfg = SimpleNamespace(ha_url="http://ha.local:8123", ha_token="cfg-token")
    monkeypatch.setattr(ha_client_module, "cfg", fake_cfg)

    client = ha_client_module.HomeAssistantClient(token="explicit-token")
    fake_cfg.ha_token = "changed-after-init"

    headers = client._headers()
    assert headers["Authorization"] == "Bearer explicit-token"
