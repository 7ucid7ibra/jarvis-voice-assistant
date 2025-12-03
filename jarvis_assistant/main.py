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
from .memory import MemoryManager
from .utils import logger
import json
import time
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

from .agents import IntentAgent, ActionAgent, ResponseAgent
# from .wake_word import WakeWordWorker # This module doesn't exist yet or was named differently in previous context.
# Checking previous context, WakeWordWorker was likely part of recorder or stt, or I hallucinated the file.
# Let's check where WakeWordWorker is defined.


class JarvisController(QObject):
    # Signals to drive workers
    request_stt = pyqtSignal(object)
    request_llm = pyqtSignal(list)
    request_tts = pyqtSignal(str)
    
    def open_settings(self):
        dlg = SettingsDialog(self)
        dlg.exec()
    
    def __init__(self):
        super().__init__()
        self.app = QApplication(sys.argv)
        self.window = MainWindow()
        self.conversation = Conversation()
        self.ha_client = HomeAssistantClient()
        self.ha_entities = self.ha_client.get_relevant_entities()
        logger.info(f"Loaded HA Entities:\n{self.ha_entities}")
        

        
        # Components
        self.audio_recorder = AudioRecorder()
        self.stt_worker = STTWorker()
        self.llm_worker = LLMWorker()
        self.tts_worker = TTSWorker()
        self.memory_manager = MemoryManager()
        # self.wake_word_worker = WakeWordWorker() # Removed
        
        # Threads
        self.stt_thread = QThread()
        self.llm_thread = QThread()
        self.tts_thread = QThread()
        # self.wake_word_thread = QThread() # Removed
        
        # Move workers
        self.stt_worker.moveToThread(self.stt_thread)
        self.llm_worker.moveToThread(self.llm_thread)
        self.tts_worker.moveToThread(self.tts_thread)
        # self.wake_word_worker.moveToThread(self.wake_word_thread) # Removed
        
        # Connect Driver Signals to Worker Slots
        self.request_stt.connect(self.stt_worker.transcribe)
        # self.request_llm.connect(self.llm_worker.generate_reply) # Removed: generate_reply no longer exists
        self.request_tts.connect(self.tts_worker.speak)
        
        # Connect Worker Signals to Controller Slots
        self.audio_recorder.finished.connect(self.stt_worker.transcribe)
        self.stt_worker.finished.connect(self.handle_stt_finished)
        self.stt_worker.error.connect(self.handle_error)
        
        self.llm_worker.finished.connect(self.handle_llm_response)
        self.llm_worker.error.connect(self.handle_error)
        
        self.tts_worker.started.connect(self.handle_tts_started)
        self.tts_worker.finished.connect(self.handle_tts_finished)
        
        # UI Signals
        self.window.mic_btn.clicked.connect(self.handle_mic_click)
        
        # Start Threads
        self.stt_thread.start()
        self.llm_thread.start()
        self.tts_thread.start()
        
        # Init
        self.conversation.load()
        for msg in self.conversation.messages:
            self.window.add_message(msg.content, msg.role == "user")
        
        self.window.set_status("Idle")
        self.window.show()

    def run(self):
        sys.exit(self.app.exec())

    def handle_mic_click(self):
        # Ignore clicks during THINKING state
        if self.window.mic_btn.state == MicButton.STATE_THINKING:
            return
            
        if self.window.mic_btn.state == MicButton.STATE_IDLE:
            self.window.mic_btn.set_state(MicButton.STATE_LISTENING)
            self.window.set_status("Listening...")
            self.audio_recorder.start_recording()
        elif self.window.mic_btn.state == MicButton.STATE_LISTENING:
            self.window.set_status("Processing...")
            self.audio_recorder.stop_recording()
        elif self.window.mic_btn.state == MicButton.STATE_SPEAKING:
            # Stop TTS playback without starting recording
            self.tts_worker.stop()
            # Note: tts.stop() will emit finished signal which calls handle_tts_finished
            # which will set state to IDLE, so we don't need to do it here

    def handle_recording_finished(self, audio_data):
        if len(audio_data) == 0:
            self.window.mic_btn.set_state(MicButton.STATE_IDLE)
            self.window.set_status("Idle")
            return
        
        self.window.mic_btn.set_state(MicButton.STATE_THINKING)
        self.window.set_status("Transcribing...")
        self.request_stt.emit(audio_data)

    def handle_stt_finished(self, text):
        if not text:
            self.window.mic_btn.set_state(MicButton.STATE_IDLE)
            self.window.set_status("Idle")
            
            return
            
        self.conversation.add_message("user", text)
        self.window.add_message(text, is_user=True)
        
        self.window.set_status("Thinking...")
        # Start Multi-Agent Process
        self.start_processing(text)



    def start_processing(self, user_text: str):
        self.window.set_status("Thinking (Intent)...")
        
        # Get history
        history = self.conversation.get_ollama_messages()[-5:] # Last 5 messages
        
        # 1. Intent Agent
        intent_agent = IntentAgent()
        messages = [{"role": "system", "content": intent_agent.get_system_prompt(self.ha_entities)}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_text})
        
        # We need a way to handle the callback for THIS specific request
        # Since LLMWorker uses a single signal, we might need a request ID or 
        # instantiate a worker per request, or use a state machine.
        # For simplicity, let's use a state machine in the controller.
        
        self.current_state = "intent"
        self.current_user_text = user_text
        self.llm_worker.generate(messages, format="json")

    def handle_llm_response(self, response: str):
        print(f"DEBUG: handle_llm_response called. State: {self.current_state}, Response: {response[:50]}...", flush=True)
        logger.info(f"LLM Response ({self.current_state}): {response}")
        
        if self.current_state == "intent":
            try:
                data = json.loads(response)
                self.current_intent = data
                
                # Handle Memory Write Intent
                if data.get("intent") == "memory_write" or (data.get("action") == "remember"):
                    # Extract fact logic (same as before but cleaner)
                    fact = self.current_user_text
                    lower_text = fact.lower()
                    if "remember that" in lower_text:
                         idx = lower_text.find("remember that") + len("remember that")
                         fact = fact[idx:].strip()
                    elif "remember" in lower_text:
                         idx = lower_text.find("remember") + len("remember")
                         fact = fact[idx:].strip()
                    elif "my name is" in lower_text:
                         # Special case for names if we want, or just rely on fallback
                         pass
                    else:
                        fact = self.current_user_text.strip()
                    
                    if fact and len(fact) > 2:
                        self.memory_manager.add_fact(f"fact_{int(time.time())}", fact)
                        self.current_action_taken = {"action": "remember", "status": "success", "fact": fact}
                        self.start_response_agent()
                        return
                    else:
                        logger.warning(f"Ignored invalid memory fact: '{fact}'")
                        self.current_intent = {"intent": "conversation"}
                        self.current_action_taken = None
                        self.start_response_agent()
                        return

                # Handle Memory Read Intent
                if data.get("intent") == "memory_read":
                    # Just pass through to ResponseAgent, but mark action as 'recall' so it knows to look in memory
                    self.current_action_taken = {"action": "recall", "status": "success"}
                    self.start_response_agent()
                    return

                if data.get("intent") == "home_control":
                    # 2. Action Agent
                    self.window.set_status("Thinking (Action)...")
                    self.current_state = "action"
                    
                    action_agent = ActionAgent()
                    messages = [{"role": "system", "content": action_agent.get_system_prompt(self.ha_entities)}]
                    messages.append({"role": "user", "content": f"Intent: {json.dumps(data)}. User: {self.current_user_text}"})
                    
                    self.llm_worker.generate(messages, format="json")
                else:
                    # Skip to Response Agent
                    self.current_action_taken = None
                    self.start_response_agent()
                    
            except Exception as e:
                logger.error(f"Intent parsing failed: {e}")
                # Fallback to conversation
                self.current_intent = {"intent": "conversation"}
                self.current_action_taken = None
                self.start_response_agent()

        elif self.current_state == "action":
            try:
                action = json.loads(response)
                # Execute Action
                if action and action.get("service"):
                    # Validate Service
                    valid_services = ["turn_on", "turn_off", "toggle"]
                    if action["service"] not in valid_services:
                        logger.error(f"Invalid service requested: {action['service']}")
                        self.current_action_taken = {"error": f"Service '{action['service']}' is not supported. I can only turn on, turn off, or toggle."}
                    else:
                        self.window.set_status("Executing...")
                        try:
                            self.ha_client.call_service(action["domain"], action["service"], {"entity_id": action["entity_id"]})
                            self.current_action_taken = action
                        except Exception as e:
                            logger.error(f"HA Call failed: {e}")
                            self.current_action_taken = {"error": str(e)}
                else:
                    self.current_action_taken = None
            except Exception as e:
                logger.error(f"Action parsing failed: {e}")
                self.current_action_taken = None
            
            self.start_response_agent()

        elif self.current_state == "response":
            # Final response
            reply = response.strip()
            logger.info(f"Assistant: {reply}")
            self.conversation.add_message("assistant", reply)
            self.window.add_message(reply, is_user=False)
            self.window.set_status("Speaking...")
            self.request_tts.emit(reply)
            self.current_state = "idle"

    def start_response_agent(self):
        self.window.set_status("Thinking (Reply)...")
        self.current_state = "response"
        
        # Get memory context
        memory_context = self.memory_manager.get_all_context()
        
        response_agent = ResponseAgent()
        messages = [{"role": "system", "content": response_agent.get_system_prompt(memory_context)}]
        
        # Add conversation history (last 10 messages)
        history = self.conversation.get_ollama_messages()[-10:]
        messages.extend(history)
        
        # Context for response
        system_context = ""
        if self.current_intent:
            system_context += f"Intent: {self.current_intent.get('intent')}\n"
        
        # Only add action if it was actually attempted and has a result
        if self.current_action_taken:
            system_context += f"Action Result: {json.dumps(self.current_action_taken)}\n"
        else:
            system_context += "Action Result: None (No action was taken)\n"
            
        # Construct the final prompt with clear delimiters
        final_prompt = (
            f"System Context:\n{system_context}\n"
            f"User Input:\n{self.current_user_text}"
        )
        
        messages.append({"role": "user", "content": final_prompt})
        
        self.llm_worker.generate(messages, format="text")

    def handle_tts_started(self):
        self.window.mic_btn.set_state(MicButton.STATE_SPEAKING)

    def handle_tts_finished(self):
        self.window.mic_btn.set_state(MicButton.STATE_IDLE)
        self.window.set_status("Idle")

    def handle_error(self, msg):
        self.window.set_status("Error")
        self.window.add_message(f"Error: {msg}", is_user=False)
        self.window.mic_btn.set_state(MicButton.STATE_IDLE)
    
if __name__ == "__main__":
    controller = JarvisController()
    controller.run()
