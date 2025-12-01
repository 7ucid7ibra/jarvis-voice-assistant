import pyttsx3
from PyQt6.QtCore import QObject, pyqtSignal
from .config import cfg

class TTSWorker(QObject):
    """
    Worker for Text-to-Speech.
    """
    finished = pyqtSignal()
    started = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.engine = None

    def init_engine(self):
        if self.engine is None:
            self.engine = pyttsx3.init()
            # Configure voice/rate/volume
            self.engine.setProperty('rate', cfg.tts_rate)
            self.engine.setProperty('volume', cfg.tts_volume)
            
            # Connect events
            self.engine.connect('started-utterance', self._on_start)
            self.engine.connect('finished-utterance', self._on_end)

    def _on_start(self, name):
        self.started.emit()

    def _on_end(self, name, completed):
        self.finished.emit()

    def speak(self, text: str):
        if not text:
            return
        
        if self.engine is None:
            self.init_engine()
        
        # Update properties in case config changed
        self.engine.setProperty('rate', cfg.tts_rate)
        self.engine.setProperty('volume', cfg.tts_volume)

        self.engine.say(text)
        self.engine.runAndWait()
