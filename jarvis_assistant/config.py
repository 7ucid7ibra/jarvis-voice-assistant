import os
import json

# Default Settings
DEFAULT_WHISPER_MODEL = "base"
DEFAULT_OLLAMA_MODEL = "qwen2.5:0.5b"
DEFAULT_OLLAMA_API_URL = "http://localhost:11434/api/chat"
DEFAULT_TTS_RATE = 190
DEFAULT_TTS_VOLUME = 1.0

# UI Colors
COLOR_BACKGROUND = "#05070b"
COLOR_ACCENT_CYAN = "#37e6ff"
COLOR_ACCENT_TEAL = "#4fffff"
COLOR_BUBBLE_USER = "#0b1018"
COLOR_BUBBLE_ASSISTANT = "#0f1520"
COLOR_TEXT_PRIMARY = "#ffffff"
COLOR_TEXT_SECONDARY = "#888888"

CONFIG_FILE = "settings.json"

class Config:
    def __init__(self):
        self.whisper_model = DEFAULT_WHISPER_MODEL
        self.ollama_model = DEFAULT_OLLAMA_MODEL
        self.ollama_api_url = DEFAULT_OLLAMA_API_URL
        self.tts_rate = DEFAULT_TTS_RATE
        self.tts_volume = DEFAULT_TTS_VOLUME
        self.load()

    def load(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    self.whisper_model = data.get("whisper_model", DEFAULT_WHISPER_MODEL)
                    self.ollama_model = data.get("ollama_model", DEFAULT_OLLAMA_MODEL)
                    self.tts_rate = data.get("tts_rate", DEFAULT_TTS_RATE)
                    self.tts_volume = data.get("tts_volume", DEFAULT_TTS_VOLUME)
            except Exception as e:
                print(f"Failed to load settings: {e}")

    def save(self):
        data = {
            "whisper_model": self.whisper_model,
            "ollama_model": self.ollama_model,
            "tts_rate": self.tts_rate,
            "tts_volume": self.tts_volume
        }
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Failed to save settings: {e}")

# Global instance
cfg = Config()
