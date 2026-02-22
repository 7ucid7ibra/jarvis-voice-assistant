from __future__ import annotations

from .utils import logger

SERVICE_NAME = "jarvis_assistant"
SUPPORTED_KEYS = {"ha_token", "api_key", "telegram_bot_token", "telegram_chat_id"}

try:
    import keyring  # type: ignore
except Exception:
    keyring = None


def _is_supported_key(key: str) -> bool:
    return key in SUPPORTED_KEYS


def is_available() -> bool:
    if keyring is None:
        return False
    try:
        keyring.get_password(SERVICE_NAME, "__jarvis_healthcheck__")
        return True
    except Exception:
        return False


def get_secret(key: str) -> str:
    if not _is_supported_key(key):
        logger.warning("Secret store requested unknown key.")
        return ""
    if keyring is None:
        logger.warning("Keyring is not installed; secure secret retrieval unavailable.")
        return ""
    try:
        value = keyring.get_password(SERVICE_NAME, key)
        return value or ""
    except Exception as e:
        logger.warning(f"Keychain read failed for '{key}': {e}")
        return ""


def set_secret(key: str, value: str) -> None:
    if not _is_supported_key(key):
        logger.warning("Secret store requested unknown key.")
        return
    if keyring is None:
        logger.warning("Keyring is not installed; cannot save secret securely.")
        return
    clean_value = (value or "").strip()
    if not clean_value:
        delete_secret(key)
        return
    try:
        keyring.set_password(SERVICE_NAME, key, clean_value)
    except Exception as e:
        logger.warning(f"Keychain write failed for '{key}': {e}")


def delete_secret(key: str) -> None:
    if not _is_supported_key(key):
        logger.warning("Secret store requested unknown key.")
        return
    if keyring is None:
        return
    try:
        keyring.delete_password(SERVICE_NAME, key)
    except Exception:
        # Key may not exist; keep silent to avoid noisy logs during normal clears.
        pass
