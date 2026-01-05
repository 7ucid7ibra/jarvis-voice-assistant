import json
import os
from typing import Dict, List, Optional

class MemoryManager:
    def __init__(self, memory_file: str = "memory.json"):
        self.memory_file = memory_file
        self.facts: Dict[str, str] = {}
        self.load()

    def add_fact(self, key: str, value: str):
        """Adds or updates a fact."""
        self.facts[key] = value
        self.save()

    def get_fact(self, key: str) -> Optional[str]:
        """Retrieves a specific fact."""
        return self.facts.get(key)

    def delete_fact(self, key: str):
        """Removes a fact."""
        if key in self.facts:
            del self.facts[key]
            self.save()

    def get_all_context(self) -> str:
        """Returns all facts formatted for the LLM system prompt."""
        if not self.facts:
            return "No specific user facts known yet."
        
        lines = ["User Facts:"]
        for k, v in self.facts.items():
            lines.append(f"- {k}: {v}")
        return "\n".join(lines)

    def save(self):
        try:
            with open(self.memory_file, 'w') as f:
                json.dump(self.facts, f, indent=2)
        except Exception as e:
            print(f"Failed to save memory: {e}")

    def load(self):
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, 'r') as f:
                    self.facts = json.load(f)
            except Exception as e:
                print(f"Failed to load memory: {e}")
                self.facts = {}
