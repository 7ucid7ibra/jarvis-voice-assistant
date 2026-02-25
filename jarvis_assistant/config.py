import json
import os
from urllib.parse import urlparse

from . import app_paths
from . import secret_store
from .utils import logger

# Default Settings
DEFAULT_WHISPER_MODEL = "base"
DEFAULT_OLLAMA_MODEL = "qwen2.5:0.5b"
DEFAULT_OLLAMA_API_URL = "http://127.0.0.1:11434"
DEFAULT_OLLAMA_URL_HISTORY = [DEFAULT_OLLAMA_API_URL]
DEFAULT_TTS_RATE = 190
DEFAULT_TTS_VOLUME = 1.0
DEFAULT_TTS_VOICE_ID = None
DEFAULT_WAKE_WORD_ENABLED = False
DEFAULT_WAKE_WORD = "jarvis"
DEFAULT_WAKE_RECORD_SILENCE_SEC = 1.2
DEFAULT_WAKE_RECORD_MAX_SEC = 8.0
DEFAULT_WAKE_VAD_ENERGY_THRESHOLD = 0.01
DEFAULT_HA_URL = os.environ.get("HA_URL", "")
DEFAULT_HA_TOKEN = ""
DEFAULT_ASSISTANT_NAME = "JARVIS"
DEFAULT_LANGUAGE = None  # None = auto, "en" = English, "de" = German
DEFAULT_API_PROVIDER = "ollama"
DEFAULT_API_KEY = ""
DEFAULT_TODO_ENTITY = "todo.shopping_list"
DEFAULT_PROFILE = "default"
DEFAULT_PROFILES = ["default"]
DEFAULT_TELEGRAM_BOT_TOKEN = ""
DEFAULT_TELEGRAM_CHAT_ID = ""
DEFAULT_WEB_SEARCH_ENABLED = False

# UI Colors
COLOR_BACKGROUND = "#05070b"
COLOR_ACCENT_CYAN = "#37e6ff"
COLOR_ACCENT_TEAL = "#4fffff"
COLOR_BUBBLE_USER = "#0b1018"
COLOR_BUBBLE_ASSISTANT = "#0f1520"
COLOR_TEXT_PRIMARY = "#ffffff"
COLOR_TEXT_SECONDARY = "#888888"

# Resolve settings file from writable app data path by default.
SETTINGS_FILE = os.environ.get("JARVIS_SETTINGS_FILE", app_paths.settings_file())
SECRET_KEYS = {
    "ha_token",
    "api_key",
    "telegram_bot_token",
    "telegram_chat_id",
}
SECRET_ENV_MAP = {
    "ha_token": "HA_TOKEN",
    "api_key": "API_KEY",
    "telegram_bot_token": "TELEGRAM_BOT_TOKEN",
    "telegram_chat_id": "TELEGRAM_CHAT_ID",
}


class Config:
    def __init__(self, settings_file: str = SETTINGS_FILE):
        app_paths.migrate_legacy_data_once()
        self._settings_file = settings_file
        self._settings = self._load_settings()
        self._migrate_legacy_secrets()

    def _normalize_ollama_base_url(self, value: str | None) -> str:
        raw = (value or "").strip()
        if not raw:
            return DEFAULT_OLLAMA_API_URL

        lower = raw.lower()
        if lower.startswith("http://http://"):
            raw = "http://" + raw[len("http://http://"):]
        elif lower.startswith("https://https://"):
            raw = "https://" + raw[len("https://https://"):]

        parsed = urlparse(raw if "://" in raw else f"http://{raw}")
        scheme = parsed.scheme or "http"
        netloc = parsed.netloc or parsed.path
        path = parsed.path if parsed.netloc else ""

        if not netloc:
            return DEFAULT_OLLAMA_API_URL

        if path.lower().startswith("/api/"):
            path = ""

        normalized = f"{scheme}://{netloc}{path}".rstrip("/")
        return normalized or DEFAULT_OLLAMA_API_URL

    def _load_settings(self):
        if os.path.exists(self._settings_file):
            try:
                with open(self._settings_file, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _scrub_secret_keys(self) -> None:
        for key in SECRET_KEYS:
            self._settings.pop(key, None)

    def _read_secret(self, key: str, default: str = "") -> str:
        env_key = SECRET_ENV_MAP.get(key)
        if env_key:
            env_val = os.environ.get(env_key, "").strip()
            if env_val:
                return env_val

        stored = secret_store.get_secret(key)
        if stored:
            return stored

        legacy = self._settings.get(key, "")
        if isinstance(legacy, str) and legacy.strip():
            return legacy
        return default

    def _write_secret(self, key: str, value: str) -> None:
        clean_value = (value or "").strip()
        if clean_value:
            secret_store.set_secret(key, clean_value)
        else:
            secret_store.delete_secret(key)
        self._settings.pop(key, None)

    def _migrate_legacy_secrets(self) -> None:
        changed = False
        for key in SECRET_KEYS:
            legacy_value = self._settings.get(key)
            if not isinstance(legacy_value, str) or not legacy_value.strip():
                if key in self._settings:
                    self._settings.pop(key, None)
                    changed = True
                continue

            env_key = SECRET_ENV_MAP.get(key)
            if env_key and os.environ.get(env_key, "").strip():
                self._settings.pop(key, None)
                changed = True
                continue

            if secret_store.is_available():
                secret_store.set_secret(key, legacy_value.strip())
            else:
                logger.warning(
                    f"Keychain unavailable during migration for '{key}'. "
                    "Plaintext value will be removed from settings.json."
                )
            self._settings.pop(key, None)
            changed = True

        if changed:
            self.save()

    @property
    def whisper_model(self):
        return self._settings.get("whisper_model", DEFAULT_WHISPER_MODEL)

    @whisper_model.setter
    def whisper_model(self, value):
        self._settings["whisper_model"] = value

    @property
    def ollama_model(self):
        return self._settings.get("ollama_model", DEFAULT_OLLAMA_MODEL)

    @ollama_model.setter
    def ollama_model(self, value):
        self._settings["ollama_model"] = value

    @property
    def ollama_api_url(self):
        return self._normalize_ollama_base_url(
            self._settings.get("ollama_api_url", DEFAULT_OLLAMA_API_URL)
        )

    @ollama_api_url.setter
    def ollama_api_url(self, value: str) -> None:
        self._settings["ollama_api_url"] = self._normalize_ollama_base_url(value)

    @property
    def ollama_url_history(self) -> list[str]:
        history = self._settings.get("ollama_url_history", DEFAULT_OLLAMA_URL_HISTORY)
        if not isinstance(history, list):
            history = []
        cleaned: list[str] = []
        seen: set[str] = set()
        for item in history:
            if not isinstance(item, str):
                continue
            norm = self._normalize_ollama_base_url(item)
            if norm and norm not in seen:
                cleaned.append(norm)
                seen.add(norm)
        if DEFAULT_OLLAMA_API_URL not in seen:
            cleaned.insert(0, DEFAULT_OLLAMA_API_URL)
        return cleaned[:5]

    @ollama_url_history.setter
    def ollama_url_history(self, value: list[str]) -> None:
        if not isinstance(value, list):
            value = []
        cleaned: list[str] = []
        seen: set[str] = set()
        for item in value:
            if not isinstance(item, str):
                continue
            norm = self._normalize_ollama_base_url(item)
            if norm and norm not in seen:
                cleaned.append(norm)
                seen.add(norm)
        if DEFAULT_OLLAMA_API_URL not in seen:
            cleaned.insert(0, DEFAULT_OLLAMA_API_URL)
        self._settings["ollama_url_history"] = cleaned[:5]

    @property
    def tts_rate(self):
        return self._settings.get("tts_rate", DEFAULT_TTS_RATE)

    @tts_rate.setter
    def tts_rate(self, value):
        self._settings["tts_rate"] = value

    @property
    def tts_volume(self):
        return self._settings.get("tts_volume", DEFAULT_TTS_VOLUME)

    @tts_volume.setter
    def tts_volume(self, value):
        self._settings["tts_volume"] = value

    @property
    def tts_voice_id(self):
        return self._settings.get("tts_voice_id", DEFAULT_TTS_VOICE_ID)

    @tts_voice_id.setter
    def tts_voice_id(self, value):
        self._settings["tts_voice_id"] = value

    @property
    def wake_word_enabled(self):
        return self._settings.get("wake_word_enabled", DEFAULT_WAKE_WORD_ENABLED)

    @wake_word_enabled.setter
    def wake_word_enabled(self, value):
        self._settings["wake_word_enabled"] = value

    @property
    def wake_word(self):
        return self._settings.get("wake_word", DEFAULT_WAKE_WORD)

    @wake_word.setter
    def wake_word(self, value):
        self._settings["wake_word"] = value.lower().strip()

    @property
    def wake_record_silence_sec(self) -> float:
        try:
            return float(self._settings.get("wake_record_silence_sec", DEFAULT_WAKE_RECORD_SILENCE_SEC))
        except Exception:
            return DEFAULT_WAKE_RECORD_SILENCE_SEC

    @wake_record_silence_sec.setter
    def wake_record_silence_sec(self, value: float) -> None:
        self._settings["wake_record_silence_sec"] = float(value)

    @property
    def wake_record_max_sec(self) -> float:
        try:
            return float(self._settings.get("wake_record_max_sec", DEFAULT_WAKE_RECORD_MAX_SEC))
        except Exception:
            return DEFAULT_WAKE_RECORD_MAX_SEC

    @wake_record_max_sec.setter
    def wake_record_max_sec(self, value: float) -> None:
        self._settings["wake_record_max_sec"] = float(value)

    @property
    def wake_vad_energy_threshold(self) -> float:
        try:
            return float(self._settings.get("wake_vad_energy_threshold", DEFAULT_WAKE_VAD_ENERGY_THRESHOLD))
        except Exception:
            return DEFAULT_WAKE_VAD_ENERGY_THRESHOLD

    @wake_vad_energy_threshold.setter
    def wake_vad_energy_threshold(self, value: float) -> None:
        self._settings["wake_vad_energy_threshold"] = float(value)
    @property
    def ha_url(self) -> str:
        return self._settings.get("ha_url", os.environ.get("HA_URL", DEFAULT_HA_URL))

    @ha_url.setter
    def ha_url(self, value: str) -> None:
        self._settings["ha_url"] = value

    @property
    def ha_token(self) -> str:
        return self._read_secret("ha_token", DEFAULT_HA_TOKEN)

    @ha_token.setter
    def ha_token(self, value: str) -> None:
        self._write_secret("ha_token", value)

    @property
    def language(self) -> str | None:
        return self._settings.get("language", DEFAULT_LANGUAGE)

    @language.setter
    def language(self, value: str | None) -> None:
        self._settings["language"] = value

    @property
    def api_provider(self) -> str:
        return self._settings.get("api_provider", DEFAULT_API_PROVIDER)

    @api_provider.setter
    def api_provider(self, value: str) -> None:
        self._settings["api_provider"] = value

    @property
    def api_key(self) -> str:
        return self._read_secret("api_key", DEFAULT_API_KEY)

    @api_key.setter
    def api_key(self, value: str) -> None:
        self._write_secret("api_key", value)

    @property
    def todo_entity(self) -> str:
        return self._settings.get("todo_entity", DEFAULT_TODO_ENTITY)

    @todo_entity.setter
    def todo_entity(self, value: str) -> None:
        self._settings["todo_entity"] = value

    @property
    def assistant_name(self) -> str:
        return self._settings.get("assistant_name", DEFAULT_ASSISTANT_NAME)

    @assistant_name.setter
    def assistant_name(self, value: str) -> None:
        self._settings["assistant_name"] = value.upper()

    @property
    def current_profile(self) -> str:
        return self._settings.get("current_profile", DEFAULT_PROFILE)

    @current_profile.setter
    def current_profile(self, value: str) -> None:
        self._settings["current_profile"] = value

    @property
    def profiles(self) -> list:
        return self._settings.get("profiles", DEFAULT_PROFILES)

    @profiles.setter
    def profiles(self, value: list) -> None:
        self._settings["profiles"] = value

    @property
    def telegram_bot_token(self) -> str:
        return self._read_secret("telegram_bot_token", DEFAULT_TELEGRAM_BOT_TOKEN)

    @telegram_bot_token.setter
    def telegram_bot_token(self, value: str) -> None:
        self._write_secret("telegram_bot_token", value)

    @property
    def telegram_chat_id(self) -> str:
        return self._read_secret("telegram_chat_id", DEFAULT_TELEGRAM_CHAT_ID)

    @telegram_chat_id.setter
    def telegram_chat_id(self, value: str) -> None:
        self._write_secret("telegram_chat_id", value)

    @property
    def web_search_enabled(self) -> bool:
        return self._settings.get("web_search_enabled", DEFAULT_WEB_SEARCH_ENABLED)

    @web_search_enabled.setter
    def web_search_enabled(self, value: bool) -> None:
        self._settings["web_search_enabled"] = bool(value)

    @property
    def keychain_available(self) -> bool:
        return secret_store.is_available()

    def save(self):
        try:
            self._scrub_secret_keys()
            parent_dir = os.path.dirname(self._settings_file)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)
            with open(self._settings_file, "w") as f:
                json.dump(self._settings, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")


# Global instance
cfg = Config()
