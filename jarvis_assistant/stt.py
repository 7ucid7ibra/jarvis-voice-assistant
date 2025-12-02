import whisper
import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal, QRunnable, pyqtSlot
from .config import cfg

class STTWorker(QObject):
    """
    Worker for running Whisper transcription.
    """
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.model = None

    def load_model(self):
        if self.model is None:
            print(f"Loading Whisper model: {cfg.whisper_model}...")
            try:
                self.model = whisper.load_model(cfg.whisper_model)
                print("Whisper model loaded.")
            except Exception as e:
                self.error.emit(f"Failed to load Whisper model: {e}")

    def transcribe(self, audio_data: np.ndarray):
        if self.model is None:
            self.load_model()
        
        if self.model is None:
            return

        try:
            # Whisper expects float32 array.
            # Flatten if needed (sounddevice returns [N, 1])
            if len(audio_data.shape) > 1:
                audio_data = audio_data.flatten()
            
            result = self.model.transcribe(audio_data, fp16=False, language=cfg.language) # fp16=False for CPU
            text = result['text'].strip()
            self.finished.emit(text)
        except Exception as e:
            self.error.emit(f"Transcription failed: {e}")
