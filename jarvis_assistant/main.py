import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QThread, QObject, pyqtSignal, QTimer

from .gui import MainWindow, MicButton
from .conversation import Conversation
from .audio_io import AudioRecorder
from .stt import STTWorker
from .llm_client import LLMWorker
from .tts import TTSWorker
from .ha_client import HomeAssistantClient
from .memory import MemoryManager
from .intent_utils import (
    parse_delay_seconds,
    is_multi_domain_request,
    looks_like_home_control_request,
    state_matches_action,
)
from .config import cfg
from .utils import logger, extract_json, extract_tool_call_query
import json
import time
from datetime import datetime
import requests
from typing import Any
import re
import unicodedata
from urllib.parse import urlparse, parse_qs, unquote
from html import unescape

from .agents import IntentAgent, ActionAgent, ResponseAgent


class JarvisController(QObject):
    # Signals to drive workers
    request_stt = pyqtSignal(object)
    request_llm = pyqtSignal(list, str)
    request_tts = pyqtSignal(str)
    request_tts_ack = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.app = QApplication(sys.argv)
        self.window = MainWindow()
        self.window.controller = self # Inject ref for settings
        self.conversation = Conversation()
        self.ha_client = HomeAssistantClient()
        self.ha_entities = ""
        QTimer.singleShot(500, self._async_load_ha_entities)
        

        
        # Components
        self.audio_recorder = AudioRecorder()
        self.stt_worker = STTWorker()
        self.wake_word_stt = STTWorker()
        self.llm_worker = LLMWorker()
        self.tts_worker = TTSWorker()
        
        # Profile-aware initialization
        self.init_profile_data()

        # Threads
        self.stt_thread = QThread()
        self.wake_word_thread = QThread()
        self.llm_thread = QThread()
        self.tts_thread = QThread()

        # Move workers
        self.stt_worker.moveToThread(self.stt_thread)
        self.wake_word_stt.moveToThread(self.wake_word_thread)
        self.llm_worker.moveToThread(self.llm_thread)
        self.tts_worker.moveToThread(self.tts_thread)

        # Connect Driver Signals to Worker Slots
        self.request_stt.connect(self.stt_worker.transcribe)
        self.audio_recorder.wake_word_chunk.connect(self.wake_word_stt.transcribe)
        self.request_llm.connect(self.llm_worker.generate)
        self.request_tts.connect(self.tts_worker.speak)
        self.request_tts_ack.connect(self.tts_worker.speak_ack)

        # Connect Worker Signals to Controller Slots
        self.audio_recorder.finished.connect(self.stt_worker.transcribe)
        self.wake_word_stt.finished.connect(self.handle_wake_word_detected)
        self.wake_word_stt.error.connect(self.handle_error)
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
        self.wake_word_thread.start()
        self.llm_thread.start()
        self.tts_thread.start()

        # Load conversation into UI
        # Load conversation into UI
        self.window.clear_chat()
        for msg in self.conversation.messages:
            self.window.add_message(msg.content, msg.role == "user")

        self.window.set_status("Idle")
        
        self.pending_action = None
        self.current_state = "idle"
        self._wake_word_active = False
        self._ack_spoken = False
        self._action_pending = False
        self._ack_stage = None
        self._ack_start_time = 0.0
        self._ack_index = 0
        self._ack_schedule = [3000]
        self._ack_timer = QTimer(self)
        self._ack_timer.setSingleShot(True)
        self._ack_timer.timeout.connect(self._on_ack_timeout)
        self._ignore_llm = False
        self._scheduled_tasks = []
        self.current_time_context = ""
        self._llm_timeout = QTimer(self)
        self._llm_timeout.setSingleShot(True)
        self._llm_timeout.timeout.connect(self._on_llm_timeout)
        self._start_wake_word_if_enabled()

    def _async_load_ha_entities(self):
        self.ha_entities = self.ha_client.get_relevant_entities()
        logger.info(f"Loaded HA Entities:\n{self.ha_entities}")

    def _start_wake_word_if_enabled(self):
        if cfg.wake_word_enabled and not self._wake_word_active:
            if not self.stt_worker.is_available():
                logger.warning("Wake word enabled but STT unavailable.")
                return
            self.audio_recorder.start_wake_word_listening()
            self._wake_word_active = True

    def _stop_wake_word_listening(self):
        if self._wake_word_active:
            self.audio_recorder.stop_wake_word_listening()
            self._wake_word_active = False

    def init_profile_data(self):
        profile = cfg.current_profile
        logger.info(f"Initializing profile: {profile}")
        
        # Ensure directories exist
        os.makedirs("memory", exist_ok=True)
        os.makedirs("history", exist_ok=True)
        
        mem_file = os.path.join("memory", f"memory_{profile}.json")
        hist_file = os.path.join("history", f"history_{profile}.json")
        
        self.memory_manager = MemoryManager(memory_file=mem_file)
        self.conversation = Conversation(history_file=hist_file)
        self.conversation.load()
        
    def switch_profile(self, new_profile):
        if new_profile == cfg.current_profile:
            return
            
        logger.info(f"Switching profile to: {new_profile}")
        cfg.current_profile = new_profile
        cfg.save()
        
        # Reload subsystems
        self.init_profile_data()
        
        # Refresh UI
        # Refresh UI
        self.window.clear_chat()
        for msg in self.conversation.messages:
            self.window.add_message(msg.content, msg.role == "user")
        
        self.window.set_status(f"Profile: {new_profile}")
        self.pending_action = None
        self.window.show()

    def run(self):
        self.window.show()
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

    def _parse_entities(self) -> list[dict[str, str]]:
        entities = []
        for line in (self.ha_entities or "").splitlines():
            line = line.strip()
            match = re.match(r"- Name: '(.+?)', Entity: '(.+?)', State: '(.+?)'$", line)
            if not match:
                continue
            name, entity_id, state = match.groups()
            domain = entity_id.split(".")[0] if "." in entity_id else ""
            entities.append(
                {
                    "name": name,
                    "entity_id": entity_id,
                    "state": state,
                    "domain": domain,
                }
            )
        return entities

    def _build_input_number_action(self) -> dict | None:
        text = (self.current_user_text or "").lower()
        value = None
        match = re.search(r"(-?\d+(?:\.\d+)?)", text)
        if match:
            raw = match.group(1)
            value = float(raw)
            if value.is_integer():
                value = int(value)
        else:
            if any(tok in text for tok in ["off", "aus", "zero", "null"]):
                value = 0
        relative_delta = None
        if value is None:
            if any(tok in text for tok in ["down", "lower", "less", "decrease", "runter", "weniger"]):
                relative_delta = -1
            if any(tok in text for tok in ["up", "higher", "more", "increase", "rauf", "hoeher", "mehr"]):
                relative_delta = 1
            if any(tok in text for tok in ["a little", "slightly", "a bit", "bit", "etwas", "ein wenig"]):
                if relative_delta is None:
                    relative_delta = -1
            if any(tok in text for tok in ["a lot", "much", "way down", "way up", "viel"]):
                if relative_delta is None:
                    relative_delta = -2

        target_hint = ""
        if isinstance(self.current_intent, dict):
            target_hint = (self.current_intent.get("target") or "").lower()

        entities = [e for e in self._parse_entities() if e["domain"] == "input_number"]
        candidates = []
        if target_hint:
            for ent in entities:
                if target_hint in ent["name"].lower() or target_hint in ent["entity_id"].lower():
                    candidates.append(ent)
        if not candidates and ("heater" in text or "heizung" in text):
            for ent in entities:
                name_lower = ent["name"].lower()
                entity_lower = ent["entity_id"].lower()
                if "heater" in name_lower or "heater" in entity_lower or "heizung" in name_lower or "heizung" in entity_lower:
                    candidates.append(ent)
        if not candidates and len(entities) == 1:
            candidates = entities
        if not candidates:
            return None

        if value is None and relative_delta is not None:
            current_raw = candidates[0].get("state")
            try:
                current_val = float(current_raw)
                value = current_val + relative_delta
                if value.is_integer():
                    value = int(value)
            except Exception:
                return None

        if value is None:
            return None

        return {
            "domain": "input_number",
            "service": "set_value",
            "entity_id": candidates[0]["entity_id"],
            "value": value,
        }

    def _execute_action(self, action: dict) -> dict:
        valid_services = ["turn_on", "turn_off", "toggle", "set_value"]
        if action.get("service") not in valid_services:
            return {"error": f"Service '{action.get('service')}' is not supported. I can only turn on, turn off, toggle, or set a value.", "action": action}
        if action.get("service") == "set_value":
            if action.get("domain") != "input_number":
                return {"error": "set_value is only supported for input_number.", "action": action}
            if action.get("value") is None:
                return {"error": "No value provided for input_number.", "action": action}

        try:
            target_ids = action.get("entity_id")
            if isinstance(target_ids, str):
                target_ids = [target_ids]
            if not target_ids:
                return {"error": "No target entity provided.", "action": action}

            initial_states = {}
            for eid in target_ids:
                initial_states[eid] = self.ha_client.get_entity_state(eid).get("state")

            payload = {"entity_id": action.get("entity_id")}
            if action.get("service") == "set_value":
                value = action.get("value")
                if isinstance(value, str):
                    try:
                        value = float(value)
                        if value.is_integer():
                            value = int(value)
                    except Exception:
                        return {"error": "Value must be numeric for input_number.", "action": action}
                # Clamp to min/max if available to avoid 400 errors
                try:
                    entity_info = self.ha_client.get_entity_state(target_ids[0])
                    attrs = entity_info.get("attributes", {}) if isinstance(entity_info, dict) else {}
                    min_val = attrs.get("min")
                    max_val = attrs.get("max")
                    step = attrs.get("step")
                    if isinstance(min_val, (int, float)) and value < min_val:
                        value = min_val
                    if isinstance(max_val, (int, float)) and value > max_val:
                        value = max_val
                    if isinstance(step, (int, float)) and isinstance(value, (int, float)):
                        if isinstance(min_val, (int, float)):
                            value = min_val + round((value - min_val) / step) * step
                        else:
                            value = round(value / step) * step
                        if isinstance(value, float) and value.is_integer():
                            value = int(value)
                except Exception:
                    pass
                payload["value"] = value
            self.ha_client.call_service(action.get("domain"), action.get("service"), payload)

            # Some integrations (e.g. WiZ) can take a few seconds to propagate state.
            verify_deadline = time.time() + 5.0
            poll_interval = 0.5
            final_states = {}
            verified = False
            while True:
                all_match = True
                for eid in target_ids:
                    try:
                        new_state = self.ha_client.get_entity_state(eid).get("state", "unknown")
                    except Exception:
                        new_state = "unknown"
                    final_states[eid] = new_state
                    if not state_matches_action(
                        action.get("service"),
                        initial_states.get(eid),
                        new_state,
                        action.get("value"),
                    ):
                        all_match = False

                if all_match:
                    verified = True
                    break
                if time.time() >= verify_deadline:
                    break
                time.sleep(poll_interval)

            result = action.copy()
            result["verified"] = verified
            result["final_states"] = final_states
            return result
        except Exception as e:
            logger.error(f"HA Call failed: {e}")
            return {"error": str(e), "action": action}

    def _schedule_action(self, action: dict, delay_seconds: int) -> dict:
        clean_action = {k: v for k, v in action.items() if k != "delay_seconds"}
        delay_ms = max(0, int(delay_seconds * 1000))

        def run_action():
            result = self._execute_action(clean_action)
            summary = self._summarize_scheduled_result(clean_action, result)
            self.conversation.add_message("assistant", summary)
            self.window.add_message(summary, is_user=False)
            if cfg.tts_volume > 0.0:
                QTimer.singleShot(0, lambda: self.request_tts.emit(summary))

        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(run_action)
        timer.start(delay_ms)
        self._scheduled_tasks.append(timer)
        return {"scheduled": True, "delay_seconds": delay_seconds, "action": clean_action}

    def _summarize_scheduled_result(self, action: dict, result: dict) -> str:
        if result.get("error"):
            return "Scheduled task failed."
        if result.get("verified") is False:
            final_states = result.get("final_states", {}) or {}
            entity_id = action.get("entity_id")
            if isinstance(entity_id, list):
                state_bits = [f"{eid}: {final_states.get(eid, 'unknown')}" for eid in entity_id]
                return f"Scheduled task ran, but state did not update in time ({', '.join(state_bits)})."
            return f"Scheduled task ran, but {entity_id} is still '{final_states.get(entity_id, 'unknown')}'."
        domain = action.get("domain")
        service = action.get("service")
        entity_id = action.get("entity_id")
        if service == "set_value":
            return f"Scheduled task completed: set {entity_id} to {action.get('value')}."
        if service == "turn_on":
            return f"Scheduled task completed: turned on {entity_id}."
        if service == "turn_off":
            return f"Scheduled task completed: turned off {entity_id}."
        return f"Scheduled task completed for {domain}:{service} on {entity_id}."

    def _summarize_action_result(self, action: dict) -> str:
        if action.get("service") == "set_value":
            return f"Set {action.get('entity_id')} to {action.get('value')}."
        if action.get("service") == "turn_on":
            return f"Turned on {action.get('entity_id')}."
        if action.get("service") == "turn_off":
            return f"Turned off {action.get('entity_id')}."
        if action.get("service") == "toggle":
            return f"Toggled {action.get('entity_id')}."
        return "Action completed."

    def _summarize_action_failure(self, action: dict) -> str:
        if action.get("error"):
            return f"Action failed. {action.get('error')}"
        if action.get("verified") is False:
            final_states = action.get("final_states", {}) or {}
            entity_id = action.get("entity_id") or "the device"
            if isinstance(entity_id, list):
                state_bits = [f"{eid}: {final_states.get(eid, 'unknown')}" for eid in entity_id]
                return f"I sent the command, but state did not update in time ({', '.join(state_bits)})."
            return f"I sent the command, but {entity_id} is still '{final_states.get(entity_id, 'unknown')}'."
        return "Action failed."

    def _send_telegram_message(self, message: str) -> dict:
        token = cfg.telegram_bot_token
        chat_id = cfg.telegram_chat_id
        if not token or not chat_id:
            return {"status": "error", "error": "Telegram token or chat ID is not set."}
        if not message:
            return {"status": "error", "error": "Message is empty."}
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        try:
            resp = requests.post(url, json={"chat_id": chat_id, "text": message}, timeout=10)
            resp.raise_for_status()
            return {"status": "success"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _telegram_reply(self, status: dict) -> str:
        is_de = cfg.language == "de"
        if status.get("scheduled"):
            delay = status.get("delay_seconds")
            if delay:
                return f"Telegram-Nachricht in {int(delay)} Sekunden eingeplant." if is_de else f"Scheduled the Telegram message in {int(delay)} seconds."
            return "Telegram-Nachricht eingeplant." if is_de else "Scheduled the Telegram message."
        if status.get("status") == "success":
            return "Telegram-Nachricht gesendet." if is_de else "Sent the Telegram message."
        error = status.get("error") or ("Telegram-Nachricht fehlgeschlagen." if is_de else "Telegram message failed.")
        return f"Telegram-Nachricht fehlgeschlagen. {error}" if is_de else f"Telegram message failed. {error}"

    def _web_search(self, query: str, max_results: int = 3) -> dict:
        if not cfg.web_search_enabled:
            return {"status": "error", "error": "Web search is disabled in settings."}
        if not query:
            return {"status": "error", "error": "Empty search query."}
        logger.info(f"Web search query: {query}")
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
        }
        try:
            resp = requests.get(
                "https://duckduckgo.com/html/",
                params={"q": query},
                headers=headers,
                timeout=10,
            )
            resp.raise_for_status()
            html = resp.text
        except Exception as e:
            return {"status": "error", "error": str(e)}

        results = []
        pattern = re.compile(
            r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>.*?'
            r'(?:<a[^>]+class="result__snippet"[^>]*>|<div[^>]+class="result__snippet"[^>]*>)(.*?)</',
            re.DOTALL,
        )
        for match in pattern.finditer(html):
            href = match.group(1)
            title = unescape(re.sub(r"<.*?>", "", match.group(2))).strip()
            snippet = unescape(re.sub(r"<.*?>", "", match.group(3))).strip()
            url = href
            parsed = urlparse(href)
            if parsed.path == "/l/" and "uddg" in parse_qs(parsed.query):
                url = unquote(parse_qs(parsed.query)["uddg"][0])
            if title and url:
                results.append({"title": title, "url": url, "snippet": snippet})
            if len(results) >= max_results:
                break

        if results:
            return {"status": "success", "query": query, "results": results}

        # Fallback: Wikipedia OpenSearch (free, limited scope)
        try:
            wiki_resp = requests.get(
                "https://en.wikipedia.org/w/api.php",
                params={
                    "action": "opensearch",
                    "search": query,
                    "limit": max_results,
                    "namespace": 0,
                    "format": "json",
                },
                headers=headers,
                timeout=10,
            )
            wiki_resp.raise_for_status()
            data = wiki_resp.json()
            titles = data[1] if len(data) > 1 else []
            snippets = data[2] if len(data) > 2 else []
            urls = data[3] if len(data) > 3 else []
            for title, snippet, url in zip(titles, snippets, urls):
                if title and url:
                    results.append({"title": title, "url": url, "snippet": snippet})
        except Exception as e:
            return {"status": "error", "error": f"No results found. {e}"}

        if not results:
            return {"status": "error", "error": "No results found."}
        return {"status": "success", "query": query, "results": results}

    def _parse_time_context(self) -> datetime:
        raw = (self.current_time_context or "").strip()
        if raw:
            try:
                return datetime.fromisoformat(raw)
            except Exception:
                pass
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%H:%M:%S", "%H:%M"):
                try:
                    parsed = datetime.strptime(raw, fmt)
                    if fmt.startswith("%H"):
                        return datetime.now().replace(hour=parsed.hour, minute=parsed.minute, second=getattr(parsed, "second", 0), microsecond=0)
                    return parsed
                except Exception:
                    continue
        return datetime.now()

    def _parse_delay_seconds(self, user_text: str) -> int:
        return parse_delay_seconds(user_text, self._parse_time_context())

    def _schedule_telegram_message(self, message: str, delay_seconds: int) -> dict:
        delay_ms = max(0, int(delay_seconds * 1000))

        def run_send():
            result = self._send_telegram_message(message)
            is_de = cfg.language == "de"
            summary = "Geplante Telegram-Nachricht gesendet." if is_de else "Scheduled Telegram message sent."
            if result.get("status") != "success":
                summary = "Geplante Telegram-Nachricht fehlgeschlagen." if is_de else "Scheduled Telegram message failed."
            self.conversation.add_message("assistant", summary)
            self.window.add_message(summary, is_user=False)
            if cfg.tts_volume > 0.0:
                QTimer.singleShot(0, lambda: self.request_tts.emit(summary))

        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(run_send)
        timer.start(delay_ms)
        self._scheduled_tasks.append(timer)
        return {"scheduled": True, "delay_seconds": delay_seconds, "type": "telegram_send"}

    def _reply_direct(self, text: str):
        self._cancel_ack_timer()
        self._cancel_llm_timeout()
        self.current_state = "idle"
        logger.info(f"Assistant: {text}")
        self.conversation.add_message("assistant", text)
        self.window.add_message(text, is_user=False)
        self.window.set_status("Speaking...")
        QTimer.singleShot(0, lambda: self.request_tts.emit(text))

    def _is_multi_domain_request(self, user_text: str) -> bool:
        return is_multi_domain_request(user_text, self._parse_entities())

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
            "Scheduling: I can run actions later if you say things like 'in 30 minutes'. "
            "Time: I can read the current time from Home Assistant. "
            "Messaging: I can send Telegram messages if you add a bot token and chat ID in settings. "
            "Web search: I can look things up online when you ask me to search the web. "
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
        # Cancel in-flight processing if user clicks while thinking
        if self.window.mic_btn.state == MicButton.STATE_THINKING:
            self._cancel_inflight("Cancelled")
            return
            
        if self.window.mic_btn.state == MicButton.STATE_IDLE:
            if not self.stt_worker.is_available():
                self.window.set_status("STT Disabled (Whisper missing)")
                return
            self._stop_wake_word_listening()
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
            self._start_wake_word_if_enabled()
            return
        
        self.window.mic_btn.set_state(MicButton.STATE_THINKING)
        self.window.set_status("Transcribing...")
        self.request_stt.emit(audio_data)

    def handle_text_input(self):
        if self.current_state in ("intent", "action", "response"):
            self.window.set_status("Please wait...")
            return
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
            self._start_wake_word_if_enabled()
            
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
        QTimer.singleShot(0, lambda: self.window.scroll_area.verticalScrollBar().setValue(self.window.scroll_area.verticalScrollBar().maximum()))
        
        self.window.set_status("Thinking...")
        # Start Multi-Agent Process
        self.start_processing(text)

    def handle_wake_word_detected(self, text: str):
        if not text or not cfg.wake_word_enabled:
            return
        if self.window.mic_btn.state != MicButton.STATE_IDLE:
            return
        wake_word = (cfg.wake_word or "").strip().lower()
        if not wake_word:
            return
        if wake_word in text.lower():
            logger.info(f"Wake word detected: {text}")
            self._stop_wake_word_listening()
            self.window.mic_btn.set_state(MicButton.STATE_LISTENING)
            self.window.set_status("Listening...")
            self.audio_recorder.start_recording()



    def start_processing(self, user_text: str):
        self._ignore_llm = False
        self.window.chat_input.setEnabled(False)
        self.current_time_context = self.ha_client.get_time_context()
        self.window.set_status("Thinking (Intent)...")
        self._ack_spoken = False
        self._action_pending = False
        self._ack_start_time = time.time()
        self._ack_stage = None
        self._ack_index = 0
        self._start_ack_timer()
        self._start_llm_timeout("intent")
        
        # Get history
        history = self.conversation.get_ollama_messages()[-5:] # Last 5 messages
        
        # 1. Intent Agent
        intent_agent = IntentAgent()
        memory_context = self.memory_manager.get_all_context()
        messages = [{"role": "system", "content": intent_agent.get_system_prompt(
            entities_context=self.ha_entities,
            memory_context=memory_context,
            capabilities=self.describe_capabilities(),
            time_context=self.current_time_context
        )}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_text})
        
        # We need a way to handle the callback for THIS specific request
        # Since LLMWorker uses a single signal, we might need a request ID or 
        # instantiate a worker per request, or use a state machine.
        # For simplicity, let's use a state machine in the controller.
        
        self.current_state = "intent"
        self.current_user_text = user_text
        self.request_llm.emit(messages, "json")

    def handle_llm_response(self, response: str):
        if self._ignore_llm:
            logger.info("Ignoring LLM response due to cancellation.")
            return
        logger.debug(f"handle_llm_response state={self.current_state} preview={response[:50]!r}")
        logger.info(f"LLM Response ({self.current_state}): {response}")
        
        if self.current_state == "intent":
            # Try structured parsing first (supports fenced JSON like ```json {...}```).
            data = None
            try:
                parsed = extract_json(response)
                if isinstance(parsed, dict) and any(k in parsed for k in ("intent", "action", "target")):
                    data = parsed
            except Exception:
                data = None

            if data is None:
                tool_query = extract_tool_call_query(response, "web_search")
                if tool_query:
                    self._action_pending = True
                    self.current_intent = {"intent": "web_search", "query": tool_query}
                    result = self._web_search(tool_query)
                    if result.get("status") == "success":
                        self.current_action_taken = {
                            "action": "web_search",
                            "web_search_results": result.get("results", []),
                            "query": result.get("query"),
                        }
                    else:
                        self.current_action_taken = {
                            "action": "web_search",
                            "error": result.get("error") or "Search failed.",
                        }
                    self._maybe_schedule_short_ack()
                    self.start_response_agent()
                    return

                # If the user asked for device control but intent output is plain text,
                # do not allow a fake "done" confirmation with no executed action.
                if looks_like_home_control_request(self.current_user_text, self._parse_entities()):
                    is_de = cfg.language == "de"
                    reply = (
                        "Ich konnte den Steuerbefehl nicht sicher ausfuehren. "
                        "Bitte wiederhole ihn kurz, zum Beispiel: 'Schalte die Tischlampe aus.'"
                    ) if is_de else (
                        "I could not safely execute that control command. "
                        "Please repeat it clearly, for example: 'Turn off the table lamp.'"
                    )
                    logger.warning(
                        "Rejected direct intent reply for control-like request without JSON intent."
                    )
                    self._reply_direct(reply)
                    return

                # Direct conversation reply from IntentAgent
                self._cancel_ack_timer()
                self._cancel_llm_timeout()
                reply = self._sanitize_reply(response)
                logger.info(f"Assistant (direct): {reply}")
                self.conversation.add_message("assistant", reply)
                self.window.add_message(reply, is_user=False)

                self.window.set_status("Speaking...")
                QTimer.singleShot(0, lambda: self.request_tts.emit(reply))
                self.current_state = "idle"
                return

            # JSON response - proceed with normal intent processing
            try:
                self.current_intent = data
                logger.info(f"Parsed intent: {data.get('intent')}")

                # Voice help intent
                if data.get("intent") == "help":
                    self._action_pending = False
                    self.current_action_taken = {
                        "action": "help",
                        "capabilities": self.describe_capabilities(),
                    }
                    self._maybe_schedule_short_ack()
                    self.start_response_agent()
                    return

                # Voice-triggered entity refresh
                if data.get("intent") == "refresh_entities" or data.get("action") == "refresh":
                    self._action_pending = True
                    refresh_result = self.refresh_entities()
                    self.current_action_taken = {"action": "refresh_entities", **refresh_result}
                    self._maybe_schedule_short_ack()
                    self.start_response_agent()
                    return
                
                # Handle Memory Write Intent
                if data.get("intent") == "memory_write" or (data.get("action") == "remember"):
                    self._action_pending = False
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
                        self._maybe_schedule_short_ack()
                        self.start_response_agent()
                        return
                    else:
                        logger.warning(f"Ignored invalid memory fact: '{fact}'")
                        self.current_intent = {"intent": "conversation"}
                        self.current_action_taken = None
                        self._maybe_schedule_short_ack()
                        self.start_response_agent()
                        return

                # Handle Memory Read Intent
                if data.get("intent") == "memory_read":
                    self._action_pending = False
                    # Just pass through to ResponseAgent, but mark action as 'recall' so it knows to look in memory
                    self.current_action_taken = {"action": "recall", "status": "success"}
                    self._maybe_schedule_short_ack()
                    self.start_response_agent()
                    return

                if data.get("intent") == "home_control":
                    self._action_pending = True
                    # 2. Action Agent
                    self.window.set_status("Thinking (Action)...")
                    self.current_state = "action"
                    self._start_llm_timeout("action")
                    
                    action_agent = ActionAgent()
                    messages = [{"role": "system", "content": action_agent.get_system_prompt(self.ha_entities, self.current_time_context)}]
                    messages.append({"role": "user", "content": f"Intent: {json.dumps(data)}. User: {self.current_user_text}"})
                    self._maybe_schedule_short_ack()
                    self.request_llm.emit(messages, "json")
                elif data.get("intent") == "telegram_send" or data.get("action") == "send_message":
                    self._action_pending = True
                    message = data.get("message") or self.current_user_text
                    delay = self._parse_delay_seconds(self.current_user_text)
                    if delay > 0:
                        result = self._schedule_telegram_message(message, delay)
                    else:
                        result = self._send_telegram_message(message)
                    self.current_action_taken = {"action": "telegram_send", **result}
                    self._maybe_schedule_short_ack()
                    self.start_response_agent()
                elif data.get("intent") == "web_search":
                    self._action_pending = True
                    query = data.get("query") or self.current_user_text
                    result = self._web_search(query)
                    if result.get("status") == "success":
                        self.current_action_taken = {"action": "web_search", "web_search_results": result.get("results", []), "query": result.get("query")}
                    else:
                        self.current_action_taken = {"action": "web_search", "error": result.get("error") or "Search failed."}
                    self._maybe_schedule_short_ack()
                    self.start_response_agent()
                elif data.get("intent") == "helper_create":
                    self._action_pending = True
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
                    self._maybe_schedule_short_ack()
                    self.start_response_agent()
                elif data.get("intent") == "helper_delete":
                    self._action_pending = True
                    # Stage deletion confirmation
                    target = data.get("target") or data.get("helper_name") or self.current_user_text.strip()
                    self.pending_action = {
                        "pending": True,
                        "action": "delete_helper",
                        "entity_id": target,
                        "message": f"Delete helper/entity '{target}'?"
                    }
                    self.current_action_taken = self.pending_action
                    self._maybe_schedule_short_ack()
                    self.start_response_agent()
                elif data.get("intent") == "todo_add":
                    self._action_pending = True
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
                    self._maybe_schedule_short_ack()
                    self.start_response_agent()
                elif data.get("intent") == "todo_remove":
                    self._action_pending = True
                    title = data.get("todo_title") or self.current_user_text
                    self.pending_action = {
                        "pending": True,
                        "action": "remove_todo",
                        "todo_title": title,
                        "message": f"Remove reminder '{title}'?"
                    }
                    self.current_action_taken = self.pending_action
                    self._maybe_schedule_short_ack()
                    self.start_response_agent()
                else:
                    logger.info(f"Unhandled intent falling through to conversation: {data}")
                    self._action_pending = False
                    # Skip to Response Agent
                    self.current_action_taken = None
                    self._maybe_schedule_short_ack()
                    self.start_response_agent()
                    
            except Exception as e:
                logger.error(f"Intent parsing failed: {e}")
                self.current_intent = {"intent": "conversation"}
                # Provide feedback instead of silent failure
                self.current_action_taken = {"error": "I couldn't understand that command. Please rephrasing."}
                self._maybe_schedule_short_ack()
                self.start_response_agent()

        elif self.current_state == "action":
            try:
                action_payload = extract_json(response) or {}
                actions = []
                if isinstance(action_payload, dict) and isinstance(action_payload.get("actions"), list):
                    actions = [a for a in action_payload.get("actions") if isinstance(a, dict)]
                elif isinstance(action_payload, dict) and action_payload:
                    actions = [action_payload]

                if not actions:
                    fallback = self._build_input_number_action()
                    if fallback:
                        actions = [fallback]

                normalized_actions = []
                for action in actions:
                    if not action or not action.get("service"):
                        continue
                    if action.get("domain") == "input_number" and action.get("service") in ["turn_on", "turn_off", "toggle"]:
                        fallback = self._build_input_number_action()
                        if fallback:
                            action = fallback
                    normalized_actions.append(action)

                if normalized_actions:
                    self.window.set_status("Executing...")
                    results = []
                    fallback_delay = self._parse_delay_seconds(self.current_user_text)
                    for action in normalized_actions:
                        delay = action.get("delay_seconds") or 0
                        try:
                            delay = int(float(delay))
                        except Exception:
                            delay = 0
                        if delay == 0 and fallback_delay > 0:
                            delay = fallback_delay

                        if delay > 0:
                            results.append(self._schedule_action(action, delay))
                        else:
                            results.append(self._execute_action(action))
                    self.current_action_taken = {"actions": results}
                else:
                    self.current_action_taken = None
            except Exception as e:
                logger.error(f"Action parsing failed: {e}")
                self.current_action_taken = None
            
            self.start_response_agent()

        elif self.current_state == "response":
            self._cancel_ack_timer()
            self._cancel_llm_timeout()
            # Final response
            reply = self._sanitize_reply(response)
            logger.info(f"Assistant: {reply}")
            self.conversation.add_message("assistant", reply)
            self.window.add_message(reply, is_user=False)
            
            self.window.set_status("Speaking...")
            QTimer.singleShot(0, lambda: self.request_tts.emit(reply))
            self.current_state = "idle"

    def start_response_agent(self):
        self.window.set_status("Thinking (Reply)...")
        self.current_state = "response"
        self._start_llm_timeout("response")

        if isinstance(self.current_action_taken, dict) and self.current_action_taken.get("action") == "telegram_send":
            self._reply_direct(self._telegram_reply(self.current_action_taken))
            return

        if isinstance(self.current_action_taken, dict):
            if isinstance(self.current_action_taken.get("actions"), list):
                failures = []
                successes = []
                for action in self.current_action_taken.get("actions", []):
                    if action.get("error") or action.get("verified") is False:
                        failures.append(action)
                    elif action.get("verified") is True:
                        successes.append(action)
                if failures:
                    parts = []
                    for act in successes:
                        parts.append(self._summarize_action_result(act))
                    for act in failures:
                        parts.append(self._summarize_action_failure(act))
                    self._reply_direct(" ".join(parts))
                    return
            elif self.current_action_taken.get("error") or self.current_action_taken.get("verified") is False:
                reply = self._summarize_action_failure(self.current_action_taken)
                self._reply_direct(reply)
                return
        
        # Get memory context
        memory_context = self.memory_manager.get_all_context()
        
        response_agent = ResponseAgent()
        messages = [{"role": "system", "content": response_agent.get_system_prompt(
            memory_context=memory_context,
            entities_context=self.ha_entities,
            capabilities=self.describe_capabilities(),
            time_context=self.current_time_context
        )}]
        
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
        
        self.request_llm.emit(messages, "text")

    def _start_ack_timer(self):
        if self._ack_timer.isActive():
            self._ack_timer.stop()
        if self._ack_index >= len(self._ack_schedule):
            return
        elapsed_ms = int((time.time() - self._ack_start_time) * 1000)
        target_ms = self._ack_schedule[self._ack_index]
        remaining = max(0, target_ms - elapsed_ms)
        self._ack_timer.start(remaining)

    def _cancel_ack_timer(self):
        if self._ack_timer.isActive():
            self._ack_timer.stop()

    def _on_ack_timeout(self):
        if self.current_state not in ("intent", "action", "response"):
            return
        stage = self._stage_for_index(self._ack_index)
        ack = self._pick_ack_phrase(stage=stage)
        if not ack:
            return
        self._ack_spoken = True
        self._ack_stage = stage
        QTimer.singleShot(0, lambda: self.window.add_message(ack, is_user=False, animate=False))
        try:
            QTimer.singleShot(60, lambda: self.request_tts_ack.emit(ack))
        except Exception as e:
            logger.error(f"Ack TTS failed: {e}")
        self._ack_index += 1
        self._start_ack_timer()

    def _stage_for_index(self, idx: int) -> str:
        if idx == 0:
            return "short"
        if idx == 1:
            return "long"
        return "very_long"

    def _maybe_schedule_short_ack(self):
        if self._ack_index == 0:
            self._start_ack_timer()

    def _pick_ack_phrase(self, stage: str) -> str:
        is_de = cfg.language == "de"
        if self._action_pending:
            if stage == "very_long":
                options = [
                    "Sorry for the wait. Still working on it.",
                    "Apologies, this is taking longer than usual.",
                    "Sorry, still handling that.",
                    "Thanks for waiting. Still on it.",
                    "I am still on it. Thank you for your patience.",
                    "Still working on it. I will be with you shortly.",
                ] if not is_de else [
                    "Entschuldigung, das dauert laenger. Ich arbeite noch daran.",
                    "Danke fuer deine Geduld. Ich bin noch dran.",
                    "Es dauert etwas. Ich kuemmere mich noch darum.",
                    "Sorry, ich arbeite noch daran.",
                    "Ich bin weiterhin dran. Gleich fertig.",
                ]
            elif stage == "long":
                options = [
                    "Still on it.",
                    "Just a moment longer.",
                    "Working through that now.",
                    "Almost there.",
                    "Hang tight, nearly done.",
                    "Still working on that.",
                    "One more moment, I am on it.",
                    "Still in progress, almost done.",
                    "Holding steady, finishing up now.",
                ] if not is_de else [
                    "Ich bin dran.",
                    "Einen Moment noch.",
                    "Ich arbeite daran.",
                    "Fast fertig.",
                    "Ich bin noch dran.",
                    "Ich bin gleich fertig.",
                    "Noch einen kurzen Moment.",
                ]
            else:
                options = [
                    "Working on it.",
                    "On it.",
                    "Alright, handling that now.",
                    "Got it, doing it now.",
                    "Okay, one moment.",
                    "Taking care of it.",
                    "Starting that now.",
                    "Doing that now.",
                    "Understood, I am on it.",
                    "Okay, I will handle that.",
                ] if not is_de else [
                    "Ich kuemmere mich darum.",
                    "Alles klar, ich mache das.",
                    "Verstanden, ich bin dran.",
                    "In Ordnung, ich mache das jetzt.",
                    "Okay, einen Moment.",
                    "Ich erledige das.",
                    "Ich starte das jetzt.",
                ]
        else:
            if stage == "very_long":
                options = [
                    "Sorry for the wait. Still thinking.",
                    "Apologies, this is taking a bit.",
                    "Sorry, still working it out.",
                    "Thanks for waiting. Still thinking.",
                    "Sorry for the wait. Still working it out.",
                    "Thanks for your patience. I am still thinking.",
                ] if not is_de else [
                    "Entschuldigung, das dauert laenger. Ich denke noch nach.",
                    "Danke fuers Warten. Ich denke noch nach.",
                    "Es dauert etwas. Ich denke noch.",
                    "Sorry, ich ueberlege noch.",
                    "Ich denke noch nach. Gleich soweit.",
                ]
            elif stage == "long":
                options = [
                    "Still thinking.",
                    "Taking a little longer, hang on.",
                    "One more moment.",
                    "Give me a second longer.",
                    "Thinking it through.",
                    "Almost done, hang on.",
                    "Just a bit longer.",
                    "Let me think a moment longer.",
                    "Still working it out, one moment.",
                ] if not is_de else [
                    "Ich denke noch nach.",
                    "Einen Moment noch.",
                    "Noch einen Moment.",
                    "Ich ueberlege kurz.",
                    "Ich denke das kurz durch.",
                    "Gleich fertig.",
                    "Nur einen Moment.",
                ]
            else:
                options = [
                    "Hmm, let me think.",
                    "One moment.",
                    "Let me check.",
                    "Let me think for a second.",
                    "Just a moment.",
                    "Checking that now.",
                    "Let me take a quick look.",
                    "Let me have a quick look.",
                    "Thinking for a moment.",
                    "Give me a second to think.",
                    "Let me think this through.",
                    "I am thinking on that.",
                    "Give me a moment.",
                ] if not is_de else [
                    "Hmm, einen Moment.",
                    "Einen Moment.",
                    "Lass mich kurz nachsehen.",
                    "Ich denke kurz nach.",
                    "Einen kurzen Moment.",
                    "Ich schaue kurz nach.",
                    "Ich ueberlege kurz.",
                    "Ich denke kurz drueber nach.",
                    "Gib mir einen Moment.",
                ]
        idx = int(time.time() * 1000) % len(options)
        return options[idx]

    def _sanitize_reply(self, text: str) -> str:
        if not text:
            return ""
        cleaned = text.strip()
        cleaned = unicodedata.normalize("NFKC", cleaned)
        # Remove XML-like tool call blocks (e.g., minimax tool invocation markup).
        cleaned = re.sub(
            r"<minimax:tool_call>[\s\S]*?</minimax:tool_call>",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(
            r"<invoke[\s\S]*?</invoke>",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(
            r"<parameter[\s\S]*?</parameter>",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )
        # Remove fenced JSON command blocks that should never be spoken to the user.
        cleaned = re.sub(
            r"```(?:json)?\s*(\{[\s\S]*?\})\s*```",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )
        # Remove standalone "json" marker lines.
        cleaned = re.sub(r"(?im)^\s*json\s*$", "", cleaned)
        # Remove leaked inline command objects from model output.
        cleaned = re.sub(
            r"\{[^{}]*\"(?:intent|action|target|domain|service|entity_id)\"[^{}]*\}",
            "",
            cleaned,
        )
        # Remove common markdown markers without stripping content.
        cleaned = cleaned.replace("**", "").replace("__", "").replace("`", "")
        cleaned = re.sub(r"^#{1,6}\s*", "", cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r"^[-•]\s+", "", cleaned, flags=re.MULTILINE)
        # Remove URLs to keep TTS conversational.
        cleaned = re.sub(r"https?://\S+", "", cleaned)
        cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned.strip()

    def handle_tts_started(self):
        self.window.mic_btn.set_state(MicButton.STATE_SPEAKING)

    def handle_tts_finished(self):
        self.window.mic_btn.set_state(MicButton.STATE_IDLE)
        self.window.set_status("Idle")
        self.window.chat_input.setEnabled(True)
        self._start_wake_word_if_enabled()

    def handle_error(self, msg):
        self._cancel_ack_timer()
        self._cancel_llm_timeout()
        self.window.set_status("Error")
        self.window.add_message(f"Error: {msg}", is_user=False)
        self.window.mic_btn.set_state(MicButton.STATE_IDLE)
        self.window.chat_input.setEnabled(True)

    def _cancel_inflight(self, reason: str):
        self._ignore_llm = True
        self._cancel_ack_timer()
        self._cancel_llm_timeout()
        self.current_state = "idle"
        self.window.mic_btn.set_state(MicButton.STATE_IDLE)
        self.window.set_status("Idle")
        self.window.chat_input.setEnabled(True)

    def _start_llm_timeout(self, stage: str):
        if self._llm_timeout.isActive():
            self._llm_timeout.stop()
        # Shorter timeout for intent/action, longer for response.
        if stage in ("intent", "action"):
            self._llm_timeout.start(180000)
        else:
            self._llm_timeout.start(240000)

    def _cancel_llm_timeout(self):
        if self._llm_timeout.isActive():
            self._llm_timeout.stop()

    def _on_llm_timeout(self):
        self.window.set_status("Error")
        self.window.add_message("Error: Response timed out. Please try again.", is_user=False)
        self.window.mic_btn.set_state(MicButton.STATE_IDLE)
        self.current_state = "idle"
        self._start_wake_word_if_enabled()
    
def main():
    controller = JarvisController()
    controller.run()


if __name__ == "__main__":
    main()
