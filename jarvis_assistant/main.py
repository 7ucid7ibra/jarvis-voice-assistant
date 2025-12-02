import sys
import threading
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QThread, pyqtSlot, QObject, pyqtSignal

from .gui import MainWindow, MicButton
from .conversation import Conversation
from .audio_io import AudioRecorder
from .stt import STTWorker
from .llm_client import LLMWorker
from .tts import TTSWorker
from .ha_client import HomeAssistantClient
from .utils import logger
import json
from typing import Any

class JarvisApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.window = MainWindow()
        self.conversation = Conversation()
        
        # Components
        self.recorder = AudioRecorder()
        self.stt = STTWorker()
        self.llm = LLMWorker()
        self.tts = TTSWorker()
        
        # Threads
        self.stt_thread = QThread()
        self.llm_thread = QThread()
        self.tts_thread = QThread()
        
        # Move workers to threads
        self.stt.moveToThread(self.stt_thread)
        self.llm.moveToThread(self.llm_thread)
        self.tts.moveToThread(self.tts_thread)
        
        # Start threads
        self.stt_thread.start()
        self.llm_thread.start()
        self.tts_thread.start()
        
        # Wire signals
        self._connect_signals()
        
        # Load history
        self.conversation.load()
        for msg in self.conversation.messages:
            self.window.add_message(msg.content, msg.role == "user")
            
        self.window.show()

    def _connect_signals(self):
        # Mic Button
        self.window.mic_btn.clicked.connect(self.handle_mic_click)
        
        # Recorder
        self.recorder.finished.connect(self.handle_recording_finished)
        
        # STT
        self.stt.finished.connect(self.handle_stt_finished)
        self.stt.error.connect(self.handle_error)
        
        # LLM
        self.llm.finished.connect(self.handle_llm_finished)
        self.llm.error.connect(self.handle_error)
        
        # TTS
        self.tts.started.connect(self.handle_tts_started)
        self.tts.finished.connect(self.handle_tts_finished)

    def handle_mic_click(self):
        if self.window.mic_btn.state == MicButton.STATE_IDLE:
            self.start_listening()
        elif self.window.mic_btn.state == MicButton.STATE_LISTENING:
            self.stop_listening()
        elif self.window.mic_btn.state == MicButton.STATE_SPEAKING:
            # Stop speaking if clicked
            # TODO: Implement stop logic in TTS
            pass

    def start_listening(self):
        self.window.mic_btn.set_state(MicButton.STATE_LISTENING)
        self.window.set_status("Listening...")
        self.recorder.start_recording()

    def stop_listening(self):
        self.window.set_status("Processing...")
        self.recorder.stop_recording()

    def handle_recording_finished(self, audio_data):
        if len(audio_data) == 0:
            self.window.mic_btn.set_state(MicButton.STATE_IDLE)
            self.window.set_status("Idle")
            return
            
        self.window.mic_btn.set_state(MicButton.STATE_THINKING)
        self.window.set_status("Transcribing...")
        # Invoke STT in its thread
        # We use QMetaObject.invokeMethod or simply emit a signal connected to the slot.
        # But here we can just call a wrapper that emits a signal, or better yet,
        # define a signal in this class to trigger STT.
        # For simplicity, let's add a signal to JarvisApp to trigger STT.
        self.trigger_stt(audio_data)

    def trigger_stt(self, audio_data):
        # We need to pass this to the worker thread.
        # Since we can't easily emit numpy array via signal across threads without registration sometimes,
        # but PyQt6 handles it well.
        # Let's define a signal on the App class.
        pass

    def handle_stt_finished(self, text):
        if not text:
            self.window.mic_btn.set_state(MicButton.STATE_IDLE)
            self.window.set_status("Idle")
            return
            
        logger.info(f"User: {text}")
        self.conversation.add_message("user", text)
        self.window.add_message(text, is_user=True)
        
        self.window.set_status("Thinking...")
        # Trigger LLM
        messages = self.conversation.get_ollama_messages()
        # Again, need to trigger worker.
        self.trigger_llm(messages)

    def handle_llm_finished(self, text):
        logger.info(f"Assistant: {text}")
        self.conversation.add_message("assistant", text)
        self.window.add_message(text, is_user=False)
        
        self.window.set_status("Speaking...")
        # Trigger TTS
        self.trigger_tts(text)

    def handle_tts_started(self):
        self.window.mic_btn.set_state(MicButton.STATE_SPEAKING)

    def handle_tts_finished(self):
        self.window.mic_btn.set_state(MicButton.STATE_IDLE)
        self.window.set_status("Idle")

    def handle_error(self, msg):
        logger.error(msg)
        self.window.set_status("Error")
        self.window.add_message(f"Error: {msg}", is_user=False)
        self.window.mic_btn.set_state(MicButton.STATE_IDLE)

    # Signal definitions need to be at class level, but we are inside methods.
    # So we need to restructure slightly to use signals for cross-thread communication.

class JarvisController(QObject):
    # Signals to drive workers
    request_stt = pyqtSignal(object)
    request_llm = pyqtSignal(list)
    request_tts = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.app = QApplication(sys.argv)
        self.window = MainWindow()
        self.conversation = Conversation()
        self.ha_client = HomeAssistantClient()
        
        # Components
        self.recorder = AudioRecorder()
        self.stt = STTWorker()
        self.wake_word_stt = STTWorker()  # Separate STT for wake word detection
        self.llm = LLMWorker()
        self.tts = TTSWorker()
        
        # Threads
        self.stt_thread = QThread()
        self.wake_word_stt_thread = QThread()
        self.llm_thread = QThread()
        self.tts_thread = QThread()
        
        # Move workers
        self.stt.moveToThread(self.stt_thread)
        self.wake_word_stt.moveToThread(self.wake_word_stt_thread)
        self.llm.moveToThread(self.llm_thread)
        self.tts.moveToThread(self.tts_thread)
        
        # Connect Driver Signals to Worker Slots
        self.request_stt.connect(self.stt.transcribe)
        self.request_llm.connect(self.llm.generate_reply)
        self.request_tts.connect(self.tts.speak)
        
        # Connect Worker Signals to Controller Slots
        self.recorder.finished.connect(self.handle_recording_finished)
        self.recorder.wake_word_chunk.connect(self.wake_word_stt.transcribe)
        
        self.stt.finished.connect(self.handle_stt_finished)
        self.stt.error.connect(self.handle_error)
        
        self.wake_word_stt.finished.connect(self.handle_wake_word_detected)
        
        self.llm.finished.connect(self.handle_llm_finished)
        self.llm.error.connect(self.handle_error)
        
        self.tts.started.connect(self.handle_tts_started)
        self.tts.finished.connect(self.handle_tts_finished)
        
        # UI Signals
        self.window.mic_btn.clicked.connect(self.handle_mic_click)
        
        # Start Threads
        self.stt_thread.start()
        self.wake_word_stt_thread.start()
        self.llm_thread.start()
        self.tts_thread.start()
        
        # Init
        self.conversation.load()
        for msg in self.conversation.messages:
            self.window.add_message(msg.content, msg.role == "user")
        
        # Start wake word listening if enabled
        from .config import cfg
        if cfg.wake_word_enabled:
            self.recorder.start_wake_word_listening()
            self.window.set_status(f"Listening for '{cfg.wake_word}'...")
            
        self.window.show()

    def run(self):
        sys.exit(self.app.exec())

    def handle_mic_click(self):
        # Ignore clicks during THINKING state
        if self.window.mic_btn.state == MicButton.STATE_THINKING:
            return
            
        if self.window.mic_btn.state == MicButton.STATE_IDLE:
            # Stop wake word listening when user manually activates
            from .config import cfg
            if cfg.wake_word_enabled:
                self.recorder.stop_wake_word_listening()
            
            self.window.mic_btn.set_state(MicButton.STATE_LISTENING)
            self.window.set_status("Listening...")
            self.recorder.start_recording()
        elif self.window.mic_btn.state == MicButton.STATE_LISTENING:
            self.window.set_status("Processing...")
            self.recorder.stop_recording()
        elif self.window.mic_btn.state == MicButton.STATE_SPEAKING:
            # Stop TTS playback without starting recording
            self.tts.stop()
            # Note: tts.stop() will emit finished signal which calls handle_tts_finished
            # which will set state to IDLE, so we don't need to do it here

    def handle_recording_finished(self, audio_data):
        if len(audio_data) == 0:
            self.window.mic_btn.set_state(MicButton.STATE_IDLE)
            self.window.set_status("Idle")
            # Restart wake word listening if enabled
            from .config import cfg
            if cfg.wake_word_enabled:
                self.recorder.start_wake_word_listening()
                self.window.set_status(f"Listening for '{cfg.wake_word}'...")
            return
        
        self.window.mic_btn.set_state(MicButton.STATE_THINKING)
        self.window.set_status("Transcribing...")
        self.request_stt.emit(audio_data)

    def handle_stt_finished(self, text):
        if not text:
            self.window.mic_btn.set_state(MicButton.STATE_IDLE)
            self.window.set_status("Idle")
            # Restart wake word listening if enabled
            from .config import cfg
            if cfg.wake_word_enabled:
                self.recorder.start_wake_word_listening()
                self.window.set_status(f"Listening for '{cfg.wake_word}'...")
            return
            
        self.conversation.add_message("user", text)
        self.window.add_message(text, is_user=True)
        
        self.window.set_status("Thinking...")
        self.request_llm.emit(self.conversation.get_ollama_messages())

    def handle_llm_finished(self, text: str):
        logger.info(f"LLM raw output: {text}")

        reply_text = text
        actions: list[dict[str, Any]] = []

        # Try to parse JSON according to the protocol in Conversation.system_prompt
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                reply_text = str(data.get("reply", "")).strip() or text
                actions = data.get("ha_actions") or []
        except Exception as e:
            logger.warning(f"Failed to parse LLM JSON, using raw reply. Error: {e}")

        # Save + display assistant reply
        logger.info(f"Assistant: {reply_text}")
        self.conversation.add_message("assistant", reply_text)
        self.window.add_message(reply_text, is_user=False)

        # Execute Home Assistant actions (if any)
        for action in actions:
            try:
                domain = action.get("domain")
                service = action.get("service")
                entity_id = action.get("entity_id")

                if domain and service and entity_id:
                    logger.info(f"Calling HA service {domain}.{service} on {entity_id}")
                    self.ha_client.call_service(domain, service, {"entity_id": entity_id})
                else:
                    # Optional: support a simpler custom format e.g. {"name": "test_switch", "on": true}
                    name = action.get("name")
                    if name == "test_switch":
                        self.ha_client.set_test_switch(bool(action.get("on", True)))
            except Exception as e:
                logger.error(f"Error calling Home Assistant: {e}")
                self.window.add_message(f"Home Assistant error: {e}", is_user=False)
        
        self.window.set_status("Speaking...")
        self.request_tts.emit(reply_text)

    def handle_tts_started(self):
        self.window.mic_btn.set_state(MicButton.STATE_SPEAKING)

    def handle_tts_finished(self):
        self.window.mic_btn.set_state(MicButton.STATE_IDLE)
        self.window.set_status("Idle")
        # Restart wake word listening if enabled
        from .config import cfg
        if cfg.wake_word_enabled:
            self.recorder.start_wake_word_listening()
            self.window.set_status(f"Listening for '{cfg.wake_word}'...")

    def handle_error(self, msg):
        self.window.set_status("Error")
        self.window.add_message(f"Error: {msg}", is_user=False)
        self.window.mic_btn.set_state(MicButton.STATE_IDLE)
        # Restart wake word listening if enabled
        from .config import cfg
        if cfg.wake_word_enabled:
            self.recorder.start_wake_word_listening()
            self.window.set_status(f"Listening for '{cfg.wake_word}'...")
    
    def handle_wake_word_detected(self, text):
        """Check if wake word was detected in transcribed audio chunk"""
        from .config import cfg
        if not cfg.wake_word_enabled or not text:
            return
        
        # Check if wake word is in the transcribed text
        if cfg.wake_word.lower() in text.lower():
            print(f"Wake word '{cfg.wake_word}' detected!", flush=True)
            # Stop wake word listening and start normal recording
            self.recorder.stop_wake_word_listening()
            self.window.mic_btn.set_state(MicButton.STATE_LISTENING)
            self.window.set_status("Listening...")
            self.recorder.start_recording()

if __name__ == "__main__":
    controller = JarvisController()
    controller.run()
