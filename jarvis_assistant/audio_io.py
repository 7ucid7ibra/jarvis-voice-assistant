import glob
import os
import threading
import time

import numpy as np
import sounddevice as sd
from PyQt6.QtCore import QObject, pyqtSignal

from . import app_paths
from .config import cfg
from .utils import logger


class AudioRecorder(QObject):
    """Records audio from the default microphone."""

    finished = pyqtSignal(object)  # Emits numpy array
    recording_stopped = pyqtSignal(str)  # stop reason
    _auto_stop_requested = pyqtSignal(str)

    wake_word_detected = pyqtSignal(str)
    wake_word_error = pyqtSignal(str)
    wake_word_status = pyqtSignal(str)

    MODE_MANUAL = "manual"
    MODE_WAKE_COMMAND = "wake_command"

    def __init__(self, sample_rate=16000):
        super().__init__()
        self.sample_rate = sample_rate
        self.recording = False
        self.wake_word_listening = False
        self.frames = []
        self._frames_lock = threading.Lock()
        self.stream = None
        self.wake_word_stream = None

        self._record_mode = self.MODE_MANUAL
        self._record_start_ts = 0.0
        self._last_voice_ts = 0.0
        self._silence_timeout_sec = 0.8
        self._max_duration_sec = 8.0
        self._vad_energy_threshold = 0.01
        self._auto_stop_emitted = False

        self._wake_model = None
        self._wake_model_label = ""
        self._wake_score_key = ""
        self._wake_consecutive_hits = 0
        self._wake_threshold = 0.45
        self._wake_debug_threshold = 0.30
        self._wake_required_hits = 1

        self._auto_stop_requested.connect(self._on_auto_stop_requested)

    def _classify_input_error(self, exc: Exception) -> str:
        msg = str(exc).lower()
        if "permission" in msg or "not permitted" in msg or "not authorized" in msg:
            return "Microphone permission denied or not granted in macOS settings"
        if "no default input" in msg or "invalid number of channels" in msg or "device unavailable" in msg:
            return "No usable microphone input device detected"
        return "Microphone input stream failed"

    def _normalize_wake_label(self, value: str) -> str:
        raw = (value or "").strip().lower()
        aliases = {
            "jarvis": "hey_jarvis",
            "hey jarvis": "hey_jarvis",
            "ok jarvis": "hey_jarvis",
            "jarvis assistant": "hey_jarvis",
            "mycroft": "hey_mycroft",
            "hey mycroft": "hey_mycroft",
            "rhasspy": "hey_rhasspy",
            "hey rhasspy": "hey_rhasspy",
            "alexa": "alexa",
            "weather": "weather",
            "timer": "timer",
        }
        return aliases.get(raw, raw or "hey_jarvis")

    def _resolve_openwakeword_model(self, label: str) -> tuple[object, str, str]:
        try:
            from openwakeword.model import Model as OpenWakeWordModel
            from openwakeword.utils import download_models
        except Exception as exc:
            raise RuntimeError(
                "openwakeword is not available; install dependencies in the project virtualenv"
            ) from exc

        preferred = self._normalize_wake_label(label)
        fallbacks = [preferred, "hey_jarvis", "alexa", "hey_mycroft", "hey_rhasspy"]
        candidates = []
        for name in fallbacks:
            if name not in candidates:
                candidates.append(name)

        model_dir = os.path.join(app_paths.models_dir(), "openwakeword")
        os.makedirs(model_dir, exist_ok=True)

        download_models(model_names=candidates, target_directory=model_dir)

        melspec_model_path = os.path.join(model_dir, "melspectrogram.onnx")
        embedding_model_path = os.path.join(model_dir, "embedding_model.onnx")

        last_error = None
        for candidate in candidates:
            matches = sorted(glob.glob(os.path.join(model_dir, f"{candidate}_v*.onnx")))
            if not matches:
                continue
            model_path = matches[-1]
            try:
                model = OpenWakeWordModel(
                    wakeword_models=[model_path],
                    inference_framework="onnx",
                    melspec_model_path=melspec_model_path,
                    embedding_model_path=embedding_model_path,
                )
                score_key = next(iter(model.models.keys()), candidate)
                return model, candidate, score_key
            except Exception as exc:
                last_error = exc
                continue

        if last_error:
            raise last_error
        raise RuntimeError("No usable openWakeWord model found")

    def _teardown_wake_engine(self):
        if self._wake_model is not None:
            try:
                self._wake_model.reset()
            except Exception:
                pass
        self._wake_model = None
        self._wake_model_label = ""
        self._wake_score_key = ""
        self._wake_consecutive_hits = 0

    def _on_auto_stop_requested(self, reason: str):
        self.stop_recording(reason=reason)

    def _request_auto_stop(self, reason: str):
        if self._auto_stop_emitted:
            return
        self._auto_stop_emitted = True
        logger.info(f"Auto-stop recording requested: {reason}")
        self._auto_stop_requested.emit(reason)

    def start_recording(
        self,
        mode: str = MODE_MANUAL,
        silence_timeout_sec: float | None = None,
        max_duration_sec: float | None = None,
        vad_energy_threshold: float | None = None,
    ):
        """Start recording for user input."""
        if self.recording:
            return

        self.recording = True
        self._record_mode = mode
        self._record_start_ts = time.monotonic()
        self._last_voice_ts = self._record_start_ts
        self._auto_stop_emitted = False

        self._silence_timeout_sec = float(
            silence_timeout_sec if silence_timeout_sec is not None else cfg.wake_record_silence_sec
        )
        self._max_duration_sec = float(
            max_duration_sec if max_duration_sec is not None else cfg.wake_record_max_sec
        )
        self._vad_energy_threshold = float(
            vad_energy_threshold if vad_energy_threshold is not None else cfg.wake_vad_energy_threshold
        )

        with self._frames_lock:
            self.frames = []

        logger.info(
            "Recording started mode=%s silence_timeout=%.2fs max_duration=%.2fs vad_threshold=%.4f",
            self._record_mode,
            self._silence_timeout_sec,
            self._max_duration_sec,
            self._vad_energy_threshold,
        )

        def callback(indata, frames, _time, status):
            if status:
                logger.warning(f"Audio status: {status}")
            if not self.recording:
                return

            chunk = indata.copy()
            with self._frames_lock:
                self.frames.append(chunk)

            if self._record_mode != self.MODE_WAKE_COMMAND:
                return

            now = time.monotonic()
            rms = float(np.sqrt(np.mean(np.square(chunk[:, 0]))))
            if rms >= self._vad_energy_threshold:
                self._last_voice_ts = now

            if (now - self._record_start_ts) >= self._max_duration_sec:
                self._request_auto_stop("max_duration")
                return

            if (now - self._last_voice_ts) >= self._silence_timeout_sec:
                self._request_auto_stop("silence_timeout")

        try:
            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="float32",
                callback=callback,
            )
            self.stream.start()
        except Exception as exc:
            self.recording = False
            detail = self._classify_input_error(exc)
            logger.error(f"{detail}: {type(exc).__name__}: {exc}")
            self.stream = None

    def stop_recording(self, reason: str = "manual_stop"):
        """Stop recording and emit audio data."""
        if not self.recording and self.stream is None:
            return

        self.recording = False
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            finally:
                self.stream = None

        with self._frames_lock:
            frames_copy = list(self.frames)
            self.frames = []

        duration = max(0.0, time.monotonic() - self._record_start_ts) if self._record_start_ts else 0.0
        logger.info(
            "Recording stopped mode=%s reason=%s duration=%.2fs frames=%d",
            self._record_mode,
            reason,
            duration,
            len(frames_copy),
        )

        if frames_copy:
            audio_data = np.concatenate(frames_copy, axis=0)
            self.finished.emit(audio_data)
        else:
            self.finished.emit(np.array([]))

        self.recording_stopped.emit(reason)

    def start_wake_word_listening(self, keyword: str | None = None) -> bool:
        """Start continuous listening for openWakeWord detection."""
        if self.wake_word_listening:
            return True

        try:
            self._wake_model, self._wake_model_label, self._wake_score_key = self._resolve_openwakeword_model(
                keyword or cfg.wake_word
            )
        except Exception as exc:
            message = f"Wake word unavailable: {type(exc).__name__}: {exc}"
            logger.error(message)
            self.wake_word_error.emit(message)
            return False

        self.sample_rate = 16000
        self.wake_word_listening = True
        self._wake_consecutive_hits = 0
        logger.info(
            "Wake word listening started (openWakeWord model='%s', score_key='%s').",
            self._wake_model_label,
            self._wake_score_key,
        )
        self.wake_word_status.emit(f"Wake word listening: {self._wake_model_label}")

        def wake_word_callback(indata, _frames, _time, status):
            if not self.wake_word_listening or self._wake_model is None:
                return
            if status:
                logger.warning(f"Wake word audio status: {status}")
            try:
                mono = indata[:, 0]
                pcm = np.clip(mono, -1.0, 1.0)
                pcm_i16 = (pcm * 32767).astype(np.int16)
                scores = self._wake_model.predict(pcm_i16)
                score = float(scores.get(self._wake_score_key, 0.0))

                if score >= self._wake_debug_threshold:
                    logger.info(
                        "Wake score (%s -> %s): %.3f",
                        self._wake_model_label,
                        self._wake_score_key,
                        score,
                    )

                if score >= self._wake_threshold:
                    self._wake_consecutive_hits += 1
                else:
                    self._wake_consecutive_hits = 0

                if self._wake_consecutive_hits >= self._wake_required_hits:
                    self.wake_word_listening = False
                    self.wake_word_detected.emit(self._wake_model_label)
            except Exception as exc:
                detail = f"Wake word processing failed: {type(exc).__name__}: {exc}"
                logger.error(detail)
                self.wake_word_listening = False
                self.wake_word_error.emit(detail)

        try:
            self.wake_word_stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="float32",
                callback=wake_word_callback,
            )
            self.wake_word_stream.start()
            return True
        except Exception as exc:
            self.wake_word_listening = False
            detail = self._classify_input_error(exc)
            logger.error(f"Wake word listener failed ({detail}): {type(exc).__name__}: {exc}")
            self.wake_word_error.emit(f"Wake word unavailable: {detail}")
            if self.wake_word_stream:
                try:
                    self.wake_word_stream.close()
                except Exception:
                    pass
                self.wake_word_stream = None
            self._teardown_wake_engine()
            return False

    def stop_wake_word_listening(self):
        """Stop continuous wake word listening."""
        self.wake_word_listening = False
        if self.wake_word_stream:
            try:
                self.wake_word_stream.stop()
                self.wake_word_stream.close()
            finally:
                self.wake_word_stream = None
        self._teardown_wake_engine()
        logger.info("Wake word listening stopped.")
