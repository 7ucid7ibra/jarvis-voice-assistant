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
        self.pending_action = None
        
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
        self.window.chat_input.returnPressed.connect(self.handle_text_input)
        
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

    def _helper_payload(self, helper_type: str, value):
        """
        Build payload for helper creation; keep defaults minimal to avoid errors.
        """
        if helper_type == "input_number":
            payload = {"min": 0, "max": 100, "step": 1, "mode": "slider"}
            if isinstance(value, (int, float)):
                payload["initial"] = value
            return payload
        if helper_type == "input_text":
            payload = {"max": 100}
            if isinstance(value, str):
                payload["initial"] = value
            return payload
        # input_boolean default
        return {}

    def execute_pending_action(self):
        """Execute pending helper actions after explicit confirmation from user."""
        if not self.pending_action:
            return
        action = self.pending_action.get("action")
        try:
            if action == "create_helper":
                helper_type = self.pending_action.get("helper_type", "input_boolean")
                helper_name = self.pending_action.get("helper_name", "New Helper")
                helper_value = self.pending_action.get("helper_value")
                created = self.ha_client.create_helper(
                    helper_type,
                    helper_name,
                    self._helper_payload(helper_type, helper_value),
                )
                refreshed = self.ha_client.get_relevant_entities()
                self.ha_entities = refreshed
                self.current_action_taken = {"action": "create_helper", "result": created, "entities": refreshed}
            elif action == "delete_helper":
                entity_id = self.pending_action.get("entity_id")
                deleted = self.ha_client.delete_entity(entity_id)
                refreshed = self.ha_client.get_relevant_entities()
                self.ha_entities = refreshed
                self.current_action_taken = {"action": "delete_helper", "result": deleted, "entities": refreshed}
            elif action == "add_todo":
                title = self.pending_action.get("todo_title")
                due = self.pending_action.get("todo_due")
                added = self.ha_client.add_todo_item(cfg.todo_entity, title, due=due)
                items = self.ha_client.list_todo_items(cfg.todo_entity)
                self.current_action_taken = {"action": "add_todo", "result": added, "items": items}
            elif action == "remove_todo":
                title = self.pending_action.get("todo_title")
                removed = self.ha_client.remove_todo_item(cfg.todo_entity, title)
                items = self.ha_client.list_todo_items(cfg.todo_entity)
                self.current_action_taken = {"action": "remove_todo", "result": removed, "items": items}
        except Exception as e:
            self.current_action_taken = {"error": str(e)}
        finally:
            self.pending_action = None
            self.start_response_agent()

    def describe_capabilities(self) -> str:
        """
        Short, speech-friendly summary of what the assistant can do and how to use confirmations.
        """
        return (
            "I am voice-first. I listen on your mics, transcribe locally, and talk back with system voices. "
            "Home control: I can turn on, turn off, or toggle lights, switches, input_booleans, and other supported domains via Home Assistant. "
            "Discovery: say 'refresh devices' after adding hardware in Home Assistant and I'll pull the latest list. "
            "Memory: you can tell me facts to remember or ask me to recall them. "
            "Configuration changes like adding entities or starting config flows are guarded and require your confirmation; I'll summarize before anything risky."
        )

    def refresh_entities(self) -> dict[str, str]:
        """
        Re-fetch entities from Home Assistant for LLM context and return a brief status payload.
        """
        try:
            self.window.set_status("Refreshing devices...")
            entities = self.ha_client.get_relevant_entities()
            self.ha_entities = entities
            preview = entities.splitlines()[:5]
            return {
                "status": "success",
                "entities_preview": "\n".join(preview) if preview else "No relevant devices found.",
            }
        except Exception as e:
            logger.error(f"Failed to refresh HA entities: {e}")
            return {"status": "error", "error": str(e)}

    def handle_mic_click(self):
        # Ignore clicks during THINKING state
        if self.window.mic_btn.state == MicButton.STATE_THINKING:
            return
            
        if self.window.mic_btn.state == MicButton.STATE_IDLE:
            if not self.stt_worker.is_available():
                self.window.set_status("STT Disabled (Whisper missing)")
                return
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

    def handle_text_input(self):
        text = self.window.chat_input.text().strip()
        if not text:
            return
            
        self.window.chat_input.clear()
        
        # Similar logic to handle_stt_finished but for text
        self.conversation.add_message("user", text)
        self.window.add_message(text, is_user=True)
        
        self.window.set_status("Thinking...")
        self.start_processing(text)

    def handle_stt_finished(self, text):
        if not text:
            self.window.mic_btn.set_state(MicButton.STATE_IDLE)
            self.window.set_status("Idle")
            
            return

        # Handle pending confirmations (yes/no) before normal intent flow
        if self.pending_action:
            lowered = text.strip().lower()
            if any(k in lowered for k in ["yes", "sure", "do it", "confirm", "okay", "ok", "please do", "go ahead", "proceed"]):
                self.execute_pending_action()
                return
            if any(k in lowered for k in ["no", "cancel", "stop", "don't"]):
                self.pending_action = None
                self.current_action_taken = {"action": "cancelled"}
                self.start_response_agent()
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

                # Voice help intent
                if data.get("intent") == "help":
                    self.current_action_taken = {
                        "action": "help",
                        "capabilities": self.describe_capabilities(),
                    }
                    self.start_response_agent()
                    return

                # Voice-triggered entity refresh
                if data.get("intent") == "refresh_entities" or data.get("action") == "refresh":
                    refresh_result = self.refresh_entities()
                    self.current_action_taken = {"action": "refresh_entities", **refresh_result}
                    self.start_response_agent()
                    return
                
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
                elif data.get("intent") == "helper_create":
                    # Stage a confirmation; do not execute until user confirms
                    helper_type = (data.get("helper_type") or "input_boolean").strip()
                    helper_name = data.get("helper_name") or self.current_user_text.strip() or "New Helper"
                    helper_value = data.get("helper_value")
                    self.pending_action = {
                        "pending": True,
                        "action": "create_helper",
                        "helper_type": helper_type,
                        "helper_name": helper_name,
                        "helper_value": helper_value,
                        "message": f"Create {helper_type} named '{helper_name}'?"
                    }
                    self.current_action_taken = self.pending_action
                    self.start_response_agent()
                elif data.get("intent") == "helper_delete":
                    # Stage deletion confirmation
                    target = data.get("target") or data.get("helper_name") or self.current_user_text.strip()
                    self.pending_action = {
                        "pending": True,
                        "action": "delete_helper",
                        "entity_id": target,
                        "message": f"Delete helper/entity '{target}'?"
                    }
                    self.current_action_taken = self.pending_action
                    self.start_response_agent()
                elif data.get("intent") == "todo_add":
                    title = data.get("todo_title") or self.current_user_text
                    due = data.get("todo_due")
                    self.pending_action = {
                        "pending": True,
                        "action": "add_todo",
                        "todo_title": title,
                        "todo_due": due,
                        "message": f"Add reminder '{title}'" + (f" due {due}" if due else "") + "?"
                    }
                    self.current_action_taken = self.pending_action
                    self.start_response_agent()
                elif data.get("intent") == "todo_remove":
                    title = data.get("todo_title") or self.current_user_text
                    self.pending_action = {
                        "pending": True,
                        "action": "remove_todo",
                        "todo_title": title,
                        "message": f"Remove reminder '{title}'?"
                    }
                    self.current_action_taken = self.pending_action
                    self.start_response_agent()
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
