import os
import json

# Default Settings
DEFAULT_WHISPER_MODEL = "base"
DEFAULT_OLLAMA_MODEL = "qwen2.5:0.5b"
DEFAULT_OLLAMA_API_URL = "http://localhost:11434/api/chat"
DEFAULT_TTS_RATE = 190
DEFAULT_TTS_VOLUME = 1.0
DEFAULT_TTS_VOICE_ID = None
DEFAULT_WAKE_WORD_ENABLED = False
DEFAULT_WAKE_WORD = "jarvis"
DEFAULT_HA_URL = "http://192.168.188.126:8123"
DEFAULT_HA_TOKEN = ""  # normally provided via env var
DEFAULT_LANGUAGE = None  # None = auto, "en" = English, "de" = German
DEFAULT_API_PROVIDER = "ollama"
DEFAULT_API_KEY = ""

# UI Colors
COLOR_BACKGROUND = "#05070b"
COLOR_ACCENT_CYAN = "#37e6ff"
COLOR_ACCENT_TEAL = "#4fffff"
COLOR_BUBBLE_USER = "#0b1018"
COLOR_BUBBLE_ASSISTANT = "#0f1520"
COLOR_TEXT_PRIMARY = "#ffffff"
COLOR_TEXT_SECONDARY = "#888888"

SETTINGS_FILE = "settings.json"

class Config:
    def __init__(self):
        self._settings = self._load_settings()
    
    def _load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    @property
    def whisper_model(self):
        return self._settings.get('whisper_model', DEFAULT_WHISPER_MODEL)
    
    @whisper_model.setter
    def whisper_model(self, value):
        self._settings['whisper_model'] = value
    
    @property
    def ollama_model(self):
        return self._settings.get('ollama_model', DEFAULT_OLLAMA_MODEL)
    
    @ollama_model.setter
    def ollama_model(self, value):
        self._settings['ollama_model'] = value
    
    @property
    def ollama_api_url(self):
        return self._settings.get('ollama_api_url', DEFAULT_OLLAMA_API_URL)
    
    @property
    def tts_rate(self):
        return self._settings.get('tts_rate', DEFAULT_TTS_RATE)
    
    @tts_rate.setter
    def tts_rate(self, value):
        self._settings['tts_rate'] = value
    
    @property
    def tts_volume(self):
        return self._settings.get('tts_volume', DEFAULT_TTS_VOLUME)
    
    @tts_volume.setter
    def tts_volume(self, value):
        self._settings['tts_volume'] = value

    @property
    def tts_voice_id(self):
        return self._settings.get('tts_voice_id', DEFAULT_TTS_VOICE_ID)

    @tts_voice_id.setter
    def tts_voice_id(self, value):
        self._settings['tts_voice_id'] = value
    
    @property
    def wake_word_enabled(self):
        return self._settings.get('wake_word_enabled', DEFAULT_WAKE_WORD_ENABLED)
    
    @wake_word_enabled.setter
    def wake_word_enabled(self, value):
        self._settings['wake_word_enabled'] = value
    
    @property
    def wake_word(self):
        return self._settings.get('wake_word', DEFAULT_WAKE_WORD)
    
    @wake_word.setter
    def wake_word(self, value):
        self._settings['wake_word'] = value.lower().strip()

    @property
    def ha_url(self) -> str:
        # Prefer value from settings.json, otherwise env var, otherwise default
        return self._settings.get("ha_url", os.environ.get("HA_URL", DEFAULT_HA_URL))

    @ha_url.setter
    def ha_url(self, value: str) -> None:
        self._settings["ha_url"] = value

    @property
    def ha_token(self) -> str:
        # Prefer env var for security, but allow override via settings.json if explicitly set
        return self._settings.get("ha_token", os.environ.get("HA_TOKEN", DEFAULT_HA_TOKEN))

    @ha_token.setter
    def ha_token(self, value: str) -> None:
        self._settings["ha_token"] = value

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
        return self._settings.get("api_key", DEFAULT_API_KEY)

    @api_key.setter
    def api_key(self, value: str) -> None:
        self._settings["api_key"] = value
    
    def save(self):
        try:
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(self._settings, f, indent=2)
        except Exception as e:
            print(f"Failed to save settings: {e}")

# Global instance
cfg = Config()
