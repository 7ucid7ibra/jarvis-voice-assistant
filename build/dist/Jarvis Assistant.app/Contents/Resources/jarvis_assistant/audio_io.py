import sounddevice as sd
import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal, QThread

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
        self.stream = None
        self.wake_word_stream = None
    
    def start_recording(self):
        """Start recording for user input"""
        self.recording = True
        self.frames = []
        
        def callback(indata, frames, time, status):
            if status:
                print(f"Audio status: {status}")
            if self.recording:
                self.frames.append(indata.copy())
        
        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype='float32',
            callback=callback
        )
        self.stream.start()
    
    def stop_recording(self):
        """Stop recording and emit the audio data"""
        self.recording = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        
        if self.frames:
            audio_data = np.concatenate(self.frames, axis=0)
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
            wake_word_buffer.append(indata.copy())
            
            # When we have enough frames, emit the chunk
            if len(wake_word_buffer) * len(indata) >= chunk_frames:
                audio_chunk = np.concatenate(wake_word_buffer, axis=0)
                self.wake_word_chunk.emit(audio_chunk)
                wake_word_buffer.clear()
        
        self.wake_word_stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype='float32',
            callback=wake_word_callback
        )
        self.wake_word_stream.start()
    
    def stop_wake_word_listening(self):
        """Stop continuous wake word listening"""
        self.wake_word_listening = False
        if self.wake_word_stream:
            self.wake_word_stream.stop()
            self.wake_word_stream.close()
            self.wake_word_stream = None
