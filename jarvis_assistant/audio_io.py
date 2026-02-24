import threading

import numpy as np
import sounddevice as sd
from PyQt6.QtCore import QObject, pyqtSignal

from .utils import logger


class AudioRecorder(QObject):
    """
    Records audio from the default microphone.
    """
    finished = pyqtSignal(object)  # Emits numpy array
    wake_word_chunk = pyqtSignal(object)  # Emits short audio chunks for wake word detection

    def __init__(self, sample_rate=16000):
        super().__init__()
        self.sample_rate = sample_rate
        self.recording = False
        self.wake_word_listening = False
        self.frames = []
        self._frames_lock = threading.Lock()
        self.stream = None
        self.wake_word_stream = None

    def _classify_input_error(self, exc: Exception) -> str:
        msg = str(exc).lower()
        if "permission" in msg or "not permitted" in msg or "not authorized" in msg:
            return "Microphone permission denied or not granted in macOS settings"
        if "no default input" in msg or "invalid number of channels" in msg or "device unavailable" in msg:
            return "No usable microphone input device detected"
        return "Microphone input stream failed"

    def start_recording(self):
        """Start recording for user input"""
        self.recording = True
        with self._frames_lock:
            self.frames = []

        def callback(indata, frames, time, status):
            if status:
                logger.warning(f"Audio status: {status}")
            if self.recording:
                with self._frames_lock:
                    self.frames.append(indata.copy())

        try:
            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype='float32',
                callback=callback,
            )
            self.stream.start()
        except Exception as exc:
            self.recording = False
            detail = self._classify_input_error(exc)
            logger.error(f"{detail}: {type(exc).__name__}: {exc}")
            self.stream = None

    def stop_recording(self):
        """Stop recording and emit the audio data"""
        self.recording = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None

        with self._frames_lock:
            frames_copy = list(self.frames)
            self.frames = []

        if frames_copy:
            audio_data = np.concatenate(frames_copy, axis=0)
            self.finished.emit(audio_data)
        else:
            self.finished.emit(np.array([]))

    def start_wake_word_listening(self):
        """Start continuous listening for wake word detection"""
        self.wake_word_listening = True
        chunk_duration = 3  # seconds per chunk
        chunk_frames = int(self.sample_rate * chunk_duration)
        wake_word_buffer = []

        def wake_word_callback(indata, frames, time, status):
            if not self.wake_word_listening:
                return
            if status:
                logger.warning(f"Wake word audio status: {status}")
            wake_word_buffer.append(indata.copy())

            # When we have enough frames, emit the chunk
            if len(wake_word_buffer) * len(indata) >= chunk_frames:
                audio_chunk = np.concatenate(wake_word_buffer, axis=0)
                self.wake_word_chunk.emit(audio_chunk)
                wake_word_buffer.clear()

        try:
            self.wake_word_stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype='float32',
                callback=wake_word_callback,
            )
            self.wake_word_stream.start()
        except Exception as exc:
            self.wake_word_listening = False
            detail = self._classify_input_error(exc)
            logger.error(f"Wake word listener failed ({detail}): {type(exc).__name__}: {exc}")
            self.wake_word_stream = None

    def stop_wake_word_listening(self):
        """Stop continuous wake word listening"""
        self.wake_word_listening = False
        if self.wake_word_stream:
            self.wake_word_stream.stop()
            self.wake_word_stream.close()
            self.wake_word_stream = None
