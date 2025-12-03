from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import json
from .config import cfg

@dataclass
class AgentResult:
    success: bool
    data: Any
    error: Optional[str] = None

class BaseAgent:
    def __init__(self):
        pass

    def get_system_prompt(self) -> str:
        raise NotImplementedError

class IntentAgent(BaseAgent):
    """
    Determines the user's intent and resolves context (e.g., "it" -> "switch").
    """
    def get_system_prompt(self, entities_context: str = "") -> str:
        return (
            "You are an Intent Classifier. Your job is to analyze the user's latest message "
            "in the context of the conversation history and determine their intent.\n\n"
            "Available Intents:\n"
            "- 'home_control': User wants to control a device (turn on, turn off, toggle).\n"
            "- 'conversation': User is just chatting, asking questions, or greeting.\n"
            "- 'memory': User explicitly asks you to remember a fact (e.g., 'Remember that...').\n\n"
            "Context Resolution:\n"
            "- You MUST resolve pronouns like 'it', 'that', 'the switch' to specific targets based on history.\n"
            f"- Available devices:\n{entities_context}\n\n"
            "Output Format:\n"
            "You must return a single JSON object:\n"
            "{\n"
            "  \"intent\": \"home_control\", \"conversation\", or \"memory\",\n"
            "  \"target\": \"test_switch\" or null,\n"
            "  \"action\": \"turn_on\", \"turn_off\", \"toggle\", \"remember\" or null,\n"
            "  \"confidence\": 0.0 to 1.0\n"
            "}\n\n"
            "Examples:\n"
            "User: 'Turn on the switch' -> {\"intent\": \"home_control\", \"target\": \"switch\", \"action\": \"turn_on\"}\n"
            "User: 'Turn it off' (after switch context) -> {\"intent\": \"home_control\", \"target\": \"switch\", \"action\": \"turn_off\"}\n"
            "User: 'Hello' -> {\"intent\": \"conversation\", \"target\": null, \"action\": null}\n"
            "User: 'Remember that I like blue' -> {\"intent\": \"memory\", \"target\": null, \"action\": \"remember\"}\n"
            "User: 'My name is Bobby' -> {\"intent\": \"memory\", \"target\": null, \"action\": \"remember\"}"
        )

class ActionAgent(BaseAgent):
    """
    Generates the specific Home Assistant service call.
    """
    def get_system_prompt(self, entities_context: str = "") -> str:
        return (
            "You are a Home Assistant Action Generator. Your job is to convert a resolved intent "
            "into a specific Home Assistant service call JSON.\n\n"
            "Available Devices:\n"
            f"{entities_context}\n\n"
            "Output Format:\n"
            "Return a JSON object representing the service call:\n"
            "{\n"
            "  \"domain\": \"input_boolean\",\n"
            "  \"service\": \"turn_on\" or \"turn_off\",\n"
            "  \"entity_id\": \"input_boolean.switch\"\n"
            "}\n\n"
            "If the action is unclear or impossible, return empty JSON: {}"
        )

class ResponseAgent(BaseAgent):
    """
    Generates a natural language response.
    """
    def get_system_prompt(self, memory_context: str = "") -> str:
        lang_instruction = "You speak in short conversational paragraphs, in English or German, matching the user."
        if cfg.language == "en":
            lang_instruction = "You MUST speak in English, regardless of the user's language."
        elif cfg.language == "de":
            lang_instruction = "You MUST speak in German (Deutsch), regardless of the user's language."

        return (
            "You are a helpful Voice Assistant. Your job is to respond to the user.\n"
            f"{lang_instruction}\n\n"
            "Memory & Context:\n"
            f"{memory_context}\n"
            "IMPORTANT: The 'User Facts' listed above describe the USER, not you. If a fact says 'my favorite color', it means the USER'S favorite color.\n\n"
            "Context:\n"
            "- You will be provided with 'System Context' (Intent, Action Result) and 'User Input'.\n"
            "- 'Action Result' tells you EXACTLY what happened. If it says 'None', NO action was taken.\n"
            "- CRITICAL: Do NOT claim to have performed an action unless 'Action Result' confirms it.\n"
            "- If 'Action Result' is None, just answer the user's question or chat naturally. Do NOT apologize unless there was an actual error.\n"
            "- If 'Action Result' shows an error, apologize and explain the error.\n"
            "- If 'Action Result' contains a successful action (e.g., 'turn_on'), you MUST confirm it (e.g., 'Okay, I turned it on'). Do NOT say you can't do it. The action has ALREADY happened.\n"
            "- Do NOT ask follow-up questions like 'Is there anything else?' or 'What brings you joy?'. Be professional and concise.\n"
            "- Do NOT output JSON. Output only the text response."
        )
