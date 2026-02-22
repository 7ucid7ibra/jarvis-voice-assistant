from jarvis_assistant import secret_store


class _FakeKeyring:
    def __init__(self):
        self._data = {}

    def get_password(self, service, key):
        return self._data.get((service, key))

    def set_password(self, service, key, value):
        self._data[(service, key)] = value

    def delete_password(self, service, key):
        self._data.pop((service, key), None)


def test_secret_store_roundtrip(monkeypatch):
    fake = _FakeKeyring()
    monkeypatch.setattr(secret_store, "keyring", fake)

    assert secret_store.is_available() is True
    secret_store.set_secret("ha_token", "abc123")
    assert secret_store.get_secret("ha_token") == "abc123"
    secret_store.delete_secret("ha_token")
    assert secret_store.get_secret("ha_token") == ""


def test_secret_store_handles_missing_backend(monkeypatch):
    monkeypatch.setattr(secret_store, "keyring", None)

    assert secret_store.is_available() is False
    secret_store.set_secret("ha_token", "abc123")
    assert secret_store.get_secret("ha_token") == ""
