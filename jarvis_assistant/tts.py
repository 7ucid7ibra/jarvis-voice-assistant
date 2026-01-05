import os
import requests
import pyttsx3
import threading
import wave
import tempfile
import subprocess
import platform
from PyQt6.QtCore import QObject, pyqtSignal
from .config import cfg
from .utils import logger

# Constants for Piper
PIPER_MODEL_NAME = "en_US-amy-medium"
PIPER_BASE_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/"
PIPER_ONNX = f"{PIPER_MODEL_NAME}.onnx"
PIPER_JSON = f"{PIPER_MODEL_NAME}.onnx.json"

class TTSWorker(QObject):
    """
    Worker for Text-to-Speech using Piper (primary) or system fallback (say/pyttsx3).
    """
    finished = pyqtSignal()
    started = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.engine = None
        self.piper_model_path = os.path.join(os.getcwd(), "models", "tts", PIPER_ONNX)
        self.piper_config_path = os.path.join(os.getcwd(), "models", "tts", PIPER_JSON)
        self.use_piper = False
        self._ensure_piper_models()

    def _ensure_piper_models(self):
        """Check if Piper models exist, download if not."""
        model_dir = os.path.dirname(self.piper_model_path)
        if not os.path.exists(model_dir):
            os.makedirs(model_dir, exist_ok=True)

        if not os.path.exists(self.piper_model_path) or not os.path.exists(self.piper_config_path):
            logger.info("Piper models missing. Starting background download...")
            threading.Thread(target=self._download_piper_models, daemon=True).start()
        else:
            self.use_piper = True
            logger.info("Piper TTS ready.")

    def _download_piper_models(self):
        try:
            for filename in [PIPER_ONNX, PIPER_JSON]:
                path = os.path.join(os.getcwd(), "models", "tts", filename)
                if not os.path.exists(path):
                    url = PIPER_BASE_URL + filename
                    logger.info(f"Downloading {filename} from {url}...")
                    r = requests.get(url, stream=True)
                    r.raise_for_status()
                    with open(path, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
            self.use_piper = True
            logger.info("Piper models downloaded and ready.")
        except Exception as e:
            logger.error(f"Failed to download Piper models: {e}")
            self.use_piper = False

    def init_engine(self):
        if self.use_piper:
            try:
                from piper.voice import PiperVoice
                self.engine = PiperVoice.load(self.piper_model_path, config_path=self.piper_config_path)
                logger.info("Piper engine initialized.")
                return
            except Exception as e:
                logger.error(f"Failed to init Piper: {e}. Falling back to system TTS.")
                self.use_piper = False

        # Fallback to system say or pyttsx3
        try:
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', cfg.tts_rate)
            self.engine.setProperty('volume', cfg.tts_volume)
        except Exception as e:
            logger.error(f"Fallback TTS init failed: {e}")

    def speak(self, text: str):
        if not text:
            return
        
        self.started.emit()

        if cfg.tts_volume == 0.0:
            self.finished.emit()
            return

        if self.engine is None:
            self.init_engine()
        
        if self.use_piper and self.engine:
            try:
                # Piper synthesize to wav file
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
                    temp_path = temp_wav.name
                
                with wave.open(temp_path, "wb") as wav_file:
                    self.engine.synthesize(text, wav_file)
                
                # Play wav using afplay (built-in macOS player)
                subprocess.run(["afplay", temp_path])
                try:
                    os.unlink(temp_path)
                except:
                    pass
            except Exception as e:
                logger.error(f"Piper speak failed: {e}. Fallback to system say.")
                self._speak_fallback(text)
        else:
            self._speak_fallback(text)

        self.finished.emit()

    def _speak_fallback(self, text):
        try:
            if platform.system() == "Darwin":
                cmd = ["say"]
                if cfg.tts_voice_id:
                    voice_name = cfg.tts_voice_id.split('.')[-1]
                    cmd.extend(["-v", voice_name])
                cmd.append(text)
                subprocess.run(cmd)
            else:
                if self.engine:
                    self.engine.setProperty('rate', cfg.tts_rate)
                    self.engine.setProperty('volume', cfg.tts_volume)
                    self.engine.say(text)
                    self.engine.runAndWait()
        except Exception as e:
            logger.error(f"Fallback speak failed: {e}")

    def stop(self):
        """Stop current speech playback"""
        if self.use_piper:
            # afplay doesn't easily stop without PID tracking, but we can pkill it
            subprocess.run(["pkill", "afplay"])
        elif self.engine is not None and hasattr(self.engine, 'stop'):
            self.engine.stop()
        self.finished.emit()
