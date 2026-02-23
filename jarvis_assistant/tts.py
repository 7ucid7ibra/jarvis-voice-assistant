import os
import requests
import pyttsx3
import threading
import wave
import tempfile
import subprocess
import platform
import importlib.util
import shutil
import sys
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal
from .config import cfg
from .app_paths import models_dir
from .utils import logger

# Constants for Piper
DEFAULT_PIPER_VOICE_ID = "piper:en_US-amy-medium"
PIPER_VOICES = {
    "piper:en_US-amy-medium": {
        "label": "Piper (Amy) US Female",
        "model": "en_US-amy-medium",
        "base_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/",
    },
    "piper:en_US-lessac-medium": {
        "label": "Piper (Lessac) US Female",
        "model": "en_US-lessac-medium",
        "base_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/",
    },
    "piper:en_US-ryan-medium": {
        "label": "Piper (Ryan) US Male",
        "model": "en_US-ryan-medium",
        "base_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/ryan/medium/",
    },
    "piper:en_US-ljspeech-medium": {
        "label": "Piper (LJ) US Female",
        "model": "en_US-ljspeech-medium",
        "base_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/ljspeech/medium/",
    },
    "piper:de_DE-thorsten-medium": {
        "label": "Piper (Thorsten) DE Male",
        "model": "de_DE-thorsten-medium",
        "base_url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/de/de_DE/thorsten/medium/",
    },
}

class TTSWorker(QObject):
    """
    Worker for Text-to-Speech using Piper (primary) or system fallback (say/pyttsx3).
    """
    finished = pyqtSignal()
    started = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.engine = None
        self.use_piper = False
        self.piper_voice_id = None
        self.piper_model_path = None
        self.piper_config_path = None
        self._afplay_proc = None
        self._afplay_lock = threading.Lock()
        self._ensure_piper_models(self._get_piper_voice_id(), background=True)

    def _piper_env(self) -> dict[str, str]:
        """
        Build environment for Piper execution.
        On some macOS setups, piper/espeak fails when ESPEAK_DATA_PATH has spaces.
        We create a stable no-space symlink in /tmp and point ESPEAK_DATA_PATH there.
        """
        env = os.environ.copy()
        spec = importlib.util.find_spec("piper")
        if not spec or not spec.origin:
            return env

        data_dir = Path(spec.origin).resolve().parent / "espeak-ng-data"
        if not data_dir.exists():
            return env

        espeak_path = str(data_dir)
        if " " in espeak_path:
            link_path = Path(tempfile.gettempdir()) / "jarvis_piper_espeak_data"
            try:
                if link_path.is_symlink():
                    if os.path.realpath(link_path) != str(data_dir):
                        link_path.unlink()
                elif link_path.exists():
                    link_path.unlink()

                if not link_path.exists():
                    link_path.symlink_to(data_dir, target_is_directory=True)
                espeak_path = str(link_path)
            except Exception as e:
                logger.warning(f"Could not create Piper espeak symlink: {e}")

        env["ESPEAK_DATA_PATH"] = espeak_path
        os.environ["ESPEAK_DATA_PATH"] = espeak_path
        return env

    def _play_wav_file(self, path: str) -> None:
        with self._afplay_lock:
            self._afplay_proc = subprocess.Popen(["afplay", path])
            proc = self._afplay_proc
        try:
            proc.wait()
        finally:
            with self._afplay_lock:
                if self._afplay_proc is proc:
                    self._afplay_proc = None

    def _get_piper_voice_id(self) -> str | None:
        voice_id = cfg.tts_voice_id
        if voice_id and isinstance(voice_id, str) and voice_id.startswith("piper:"):
            return voice_id
        if voice_id == "piper" or not voice_id:
            return DEFAULT_PIPER_VOICE_ID
        return None

    def _get_piper_voice_info(self, voice_id: str) -> dict:
        return PIPER_VOICES.get(voice_id, PIPER_VOICES[DEFAULT_PIPER_VOICE_ID])

    def _set_piper_paths(self, voice_id: str) -> None:
        info = self._get_piper_voice_info(voice_id)
        model_name = info["model"]
        tts_model_dir = os.path.join(models_dir(), "tts")
        self.piper_model_path = os.path.join(tts_model_dir, f"{model_name}.onnx")
        self.piper_config_path = os.path.join(tts_model_dir, f"{model_name}.onnx.json")

    def _ensure_piper_models(self, voice_id: str | None, background: bool = True):
        """Check if Piper models exist for the requested voice, download if not."""
        if not voice_id:
            return
        if importlib.util.find_spec("piper.voice") is None:
            self.use_piper = False
            logger.error("Piper module not installed; falling back to system TTS.")
            return
        self._piper_env()
        self._set_piper_paths(voice_id)
        model_dir = os.path.dirname(self.piper_model_path)
        if not os.path.exists(model_dir):
            os.makedirs(model_dir, exist_ok=True)

        if os.path.exists(self.piper_model_path) and os.path.exists(self.piper_config_path):
            self.use_piper = True
            logger.info("Piper TTS ready.")
            return

        if background:
            logger.info("Piper models missing. Starting background download...")
            threading.Thread(target=self._download_piper_models, args=(voice_id,), daemon=True).start()
        else:
            self._download_piper_models(voice_id)

    def _download_piper_models(self, voice_id: str):
        try:
            info = self._get_piper_voice_info(voice_id)
            model_name = info["model"]
            base_url = info["base_url"]
            files = [f"{model_name}.onnx", f"{model_name}.onnx.json"]
            tts_model_dir = os.path.join(models_dir(), "tts")
            for filename in files:
                path = os.path.join(tts_model_dir, filename)
                if not os.path.exists(path):
                    url = base_url + filename
                    logger.info(f"Downloading {filename} from {url}...")
                    r = requests.get(url, stream=True)
                    r.raise_for_status()
                    with open(path, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
            self.use_piper = True
            self._set_piper_paths(voice_id)
            logger.info("Piper models downloaded and ready.")
        except Exception as e:
            logger.error(f"Failed to download Piper models: {e}")
            self.use_piper = False

    def prepare_piper_voice(self, voice_id: str) -> bool:
        """Ensure a Piper voice is ready (download synchronously)."""
        if not voice_id:
            return False
        if importlib.util.find_spec("piper.voice") is None:
            logger.error("Piper module not installed; cannot preview Piper voice.")
            return False
        self._ensure_piper_models(voice_id, background=False)
        return bool(self.use_piper and self.piper_model_path and os.path.exists(self.piper_model_path))

    def init_engine(self):
        if self.use_piper:
            try:
                self._piper_env()
                from piper.voice import PiperVoice
                self.engine = PiperVoice.load(self.piper_model_path, config_path=self.piper_config_path)
                logger.info("Piper engine initialized.")
                return
            except Exception as e:
                logger.error(f"Failed to init Piper: {e}. Falling back to system TTS.")
                self.use_piper = False

        # Fallback to system say or pyttsx3
        try:
            if platform.system() == "Darwin":
                # Use 'say' on macOS; avoid pyttsx3 objc dependency.
                self.engine = None
                return
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', cfg.tts_rate)
            self.engine.setProperty('volume', cfg.tts_volume)
        except Exception as e:
            logger.error(f"Fallback TTS init failed: {e}")

    def _synthesize_piper(self, text: str, temp_path: str) -> None:
        """Synthesize Piper audio to temp_path."""
        # Piper length-scale: higher = slower, lower = faster
        length_scale = 1.0
        if cfg.tts_rate:
            try:
                length_scale = max(0.6, min(1.6, 190.0 / float(cfg.tts_rate)))
            except Exception:
                length_scale = 1.0

        piper_env = self._piper_env()

        # Prefer in-process Piper engine first (avoids external CLI dependency issues).
        if self.engine is None:
            self.init_engine()
        if self.engine is not None and hasattr(self.engine, "synthesize"):
            try:
                logger.info("Using Piper in-process engine.")
                with wave.open(temp_path, "wb") as wav_file:
                    # Newer Piper exposes synthesize_wav(..., wav_file), older versions use synthesize(text, wav_file).
                    if hasattr(self.engine, "synthesize_wav"):
                        self.engine.synthesize_wav(text, wav_file)
                    else:
                        sample_rate = 22050
                        try:
                            if hasattr(self.engine, "config"):
                                sample_rate = int(getattr(self.engine.config, "sample_rate", sample_rate) or sample_rate)
                        except Exception:
                            sample_rate = 22050
                        wav_file.setnchannels(1)
                        wav_file.setsampwidth(2)
                        wav_file.setframerate(sample_rate)
                        self.engine.synthesize(text, wav_file)

                if os.path.getsize(temp_path) > 44:
                    return
                logger.warning("Piper in-process synthesis returned empty WAV; trying CLI fallback.")
            except Exception as e:
                logger.warning(f"Piper in-process synthesis failed; trying CLI fallback: {e}")

        # Fallback to CLI execution paths if engine mode is unavailable.
        piper_bin = shutil.which("piper")
        if piper_bin:
            logger.info("Using Piper CLI.")
            proc = subprocess.run(
                [
                    piper_bin,
                    "--model",
                    self.piper_model_path,
                    "--config",
                    self.piper_config_path,
                    "--output_file",
                    temp_path,
                    "--length-scale",
                    str(length_scale),
                ],
                input=text,
                text=True,
                env=piper_env,
                check=True,
            )
            if proc.returncode != 0:
                raise RuntimeError("Piper CLI failed.")
            return

        if importlib.util.find_spec("piper") is not None:
            logger.info("Using Piper module via python -m piper.")
            proc = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "piper",
                    "--model",
                    self.piper_model_path,
                    "--config",
                    self.piper_config_path,
                    "--output_file",
                    temp_path,
                    "--length-scale",
                    str(length_scale),
                ],
                input=text,
                text=True,
                env=piper_env,
                check=True,
            )
            if proc.returncode != 0:
                raise RuntimeError("Piper module CLI failed.")
            return

        if not self.engine:
            raise RuntimeError("Piper engine not initialized.")

        with wave.open(temp_path, "wb") as wav_file:
            sample_rate = None
            if hasattr(self.engine, "config"):
                sample_rate = getattr(self.engine.config, "sample_rate", None)
            if sample_rate:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
            self.engine.synthesize(text, wav_file)

    def speak(self, text: str):
        logger.info(f"TTS Request: '{text}' | Vol: {cfg.tts_volume} | Voice: {cfg.tts_voice_id}")
        if not text:
            # logger.warning("TTS: Empty text")
            return
        
        self.started.emit()

        if cfg.tts_volume == 0.0:
            logger.info("TTS: Muted (volume 0.0)")
            self.finished.emit()
            return

        if self.engine is None:
            self.init_engine()
        
        # STRICT CHECK: Only use Piper if selected OR if no voice is selected and Piper is available
        # If user selected a system voice (e.g. "com.apple..."), DO NOT use Piper.
        use_piper_for_this_request = False
        requested_piper_voice = self._get_piper_voice_id()
        if requested_piper_voice:
            self._ensure_piper_models(requested_piper_voice, background=True)
            if self.use_piper and os.path.exists(self.piper_model_path or ""):
                use_piper_for_this_request = True
        
        if use_piper_for_this_request:
            try:
                if requested_piper_voice != self.piper_voice_id:
                    self.piper_voice_id = requested_piper_voice
                    self._set_piper_paths(requested_piper_voice)
                    self.engine = None
                    self.init_engine()

                # Piper synthesize to wav file
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
                    temp_path = temp_wav.name
                self._synthesize_piper(text, temp_path)

                if os.path.getsize(temp_path) <= 44:
                    raise RuntimeError("Piper output was empty or invalid.")
                
                # Play wav using afplay (built-in macOS player)
                self._play_wav_file(temp_path)
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

    def speak_ack(self, text: str):
        """Lightweight TTS for acknowledgements (no UI state signals)."""
        logger.info(f"TTS Ack: '{text}' | Vol: {cfg.tts_volume} | Voice: {cfg.tts_voice_id}")
        if not text or cfg.tts_volume == 0.0:
            return
        requested_piper_voice = self._get_piper_voice_id()
        use_piper = False
        if requested_piper_voice:
            self._ensure_piper_models(requested_piper_voice, background=True)
            if self.use_piper and os.path.exists(self.piper_model_path or ""):
                use_piper = True

        if use_piper:
            try:
                if requested_piper_voice != self.piper_voice_id:
                    self.piper_voice_id = requested_piper_voice
                    self._set_piper_paths(requested_piper_voice)
                    self.engine = None
                    self.init_engine()
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
                    temp_path = temp_wav.name
                self._synthesize_piper(text, temp_path)
                self._play_wav_file(temp_path)
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass
                return
            except Exception as e:
                logger.error(f"Piper ack failed: {e}. Falling back to system say.")

        self._speak_fallback(text)

    def _speak_fallback(self, text):
        try:
            if platform.system() == "Darwin":
                cmd = ["say"]
                if cfg.tts_rate:
                    cmd.extend(["-r", str(cfg.tts_rate)])
                if cfg.tts_voice_id and not cfg.tts_voice_id.startswith("piper"):
                    # Extract voice name if it's a full ID like "com.apple.speech.synthesis.voice.Alex"
                    # But 'say -v' expects the name (e.g. "Alex") or ID. ID often works better for specific ones.
                    # cfg.tts_voice_id comes from QComboBox data.
                    # System voices usually: "com.apple.speech.synthesis.voice.Daniel"
                    # say -v ? shows names.
                    # But subprocess calls to 'say -v ID' might not work, usually 'say -v Name'
                    # Let's try to extract the Name from the ID if possible, or just pass it if it's a simple name.
                    # Fallback: Many IDs end in .Name (e.g. .Daniel).
                    voice_arg = cfg.tts_voice_id
                    if "." in voice_arg:
                        voice_arg = voice_arg.split('.')[-1]
                    
                    cmd.extend(["-v", voice_arg])
                
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
            with self._afplay_lock:
                proc = self._afplay_proc
            if proc and proc.poll() is None:
                try:
                    proc.terminate()
                except Exception as e:
                    logger.debug(f"Failed to terminate afplay process: {e}")
        elif self.engine is not None and hasattr(self.engine, 'stop'):
            self.engine.stop()
        self.finished.emit()
