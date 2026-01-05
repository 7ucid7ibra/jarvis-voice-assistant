try:
    from faster_whisper import WhisperModel
    whisper_available = True
except ImportError:
    print("WARNING: 'faster-whisper' not found. STT will be disabled.")
    whisper_available = False

import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal, QRunnable, pyqtSlot
from .config import cfg

class STTWorker(QObject):
    """
    Worker for running Faster-Whisper transcription.
    """
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.model = None

    def is_available(self):
        return whisper_available

    def load_model(self):
        if not whisper_available:
            self.error.emit("STT Disabled: 'faster-whisper' not found.")
            return

        if self.model is None:
            print(f"Loading Faster-Whisper model: {cfg.whisper_model}...")
            try:
                # device="cpu" is safer, compute_type="int8" is fast on CPU
                self.model = WhisperModel(cfg.whisper_model, device="cpu", compute_type="int8")
                print("Faster-Whisper model loaded.")
            except Exception as e:
                self.error.emit(f"Failed to load Faster-Whisper model: {e}")

    def transcribe(self, audio_data: np.ndarray):
        if not whisper_available:
            return

        if self.model is None:
            self.load_model()
        
        if self.model is None:
            return

        try:
            # Ensure float32
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32)
                
            # Flatten if needed
            if len(audio_data.shape) > 1:
                audio_data = audio_data.flatten()
            
            segments, info = self.model.transcribe(audio_data, beam_size=5, language=cfg.language)
            text = " ".join([segment.text for segment in segments]).strip()
            self.finished.emit(text)
        except Exception as e:
            self.error.emit(f"Transcription failed: {e}")
