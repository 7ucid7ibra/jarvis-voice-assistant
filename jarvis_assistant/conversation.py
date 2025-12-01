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
            "Respond conversationally, in short paragraphs."
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
