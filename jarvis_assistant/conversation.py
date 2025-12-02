from dataclasses import dataclass, asdict
from typing import List, Literal
import time
import json
import os

Role = Literal["user", "assistant", "system"]

@dataclass
class Message:
    role: Role
    content: str
    timestamp: float = 0.0

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()

class Conversation:
    def __init__(self, history_file: str = "conversation_history.json"):
        self.messages: List[Message] = []
        self.history_file = history_file
        self.system_prompt = (
            "You are a helpful, concise Jarvis-style assistant for a single user. "
            "You speak in short conversational paragraphs, in English or German, matching the user.\n\n"
            "You can also control a Home Assistant smart home. For now there is only one device:\n"
            "- A virtual switch with entity_id \"input_boolean.test_schalter\" "
            "called \"Test Schalter\".\n\n"
            "When the user says something that should change this switch "
            "(for example: 'turn on the test switch', 'schalte den Testschalter an', "
            "'it is really cold in here' if it clearly implies turning something on), "
            "you MUST return a pure JSON object of the form:\n"
            "{\n"
            "  \"reply\": \"What you will say back to the user\",\n"
            "  \"ha_actions\": [\n"
            "    {\n"
            "      \"domain\": \"input_boolean\",\n"
            "      \"service\": \"turn_on\" or \"turn_off\",\n"
            "      \"entity_id\": \"input_boolean.test_schalter\"\n"
            "    }\n"
            "  ]\n"
            "}\n\n"
            "If no Home Assistant action is needed, return:\n"
            "{ \"reply\": \"...normal answer...\", \"ha_actions\": [] }\n\n"
            "Always respond with VALID JSON using double quotes, no trailing commas, "
            "and absolutely no extra text before or after the JSON (no Markdown)."
        )

    def add_message(self, role: Role, content: str):
        self.messages.append(Message(role, content))
        self.save()

    def get_ollama_messages(self) -> List[dict]:
        """Convert to format expected by Ollama API"""
        payload = [{"role": "system", "content": self.system_prompt}]
        for msg in self.messages:
            payload.append({"role": msg.role, "content": msg.content})
        return payload

    def save(self):
        try:
            data = [asdict(m) for m in self.messages[-50:]] # Keep last 50
            with open(self.history_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Failed to save history: {e}")

    def load(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r') as f:
                    data = json.load(f)
                    self.messages = [Message(**m) for m in data]
            except Exception as e:
                print(f"Failed to load history: {e}")

    def clear(self):
        self.messages = []
        self.save()
