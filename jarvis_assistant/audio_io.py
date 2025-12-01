import sounddevice as sd
import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal, QThread

class AudioRecorder(QObject):
    """
    Records audio from the default microphone.
    """
    finished = pyqtSignal(object)  # Emits numpy array

    def __init__(self, sample_rate=16000):
        super().__init__()
        self.sample_rate = sample_rate
        self.recording = False
        self.frames = []

    def start_recording(self):
        self.frames = []
        self.recording = True
        # We'll use a blocking stream in a separate thread (handled by the worker approach in main)
        # or we can use a non-blocking stream.
        # Given the requirement for QThread, let's use a non-blocking stream but manage state here.
        try:
            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype='float32',
                callback=self._callback
            )
            self.stream.start()
        except Exception as e:
            print(f"Error starting recording: {e}")

    def stop_recording(self):
        if self.recording:
            self.recording = False
            self.stream.stop()
            self.stream.close()
            # Concatenate frames
            if self.frames:
                audio_data = np.concatenate(self.frames, axis=0)
                self.finished.emit(audio_data)
            else:
                self.finished.emit(np.array([]))

    def _callback(self, indata, frames, time, status):
        if status:
            print(status)
        if self.recording:
            self.frames.append(indata.copy())
