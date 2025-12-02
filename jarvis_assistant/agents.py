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
    def get_system_prompt(self) -> str:
        return (
            "You are an Intent Classifier. Your job is to analyze the user's latest message "
            "in the context of the conversation history and determine their intent.\n\n"
            "Available Intents:\n"
            "- 'home_control': User wants to control a device (turn on, turn off, toggle).\n"
            "- 'conversation': User is just chatting, asking questions, or greeting.\n\n"
            "Context Resolution:\n"
            "- You MUST resolve pronouns like 'it', 'that', 'the switch' to specific targets based on history.\n"
            "- The only available device is 'test_switch' (input_boolean.test_schalter).\n\n"
            "Output Format:\n"
            "You must return a single JSON object:\n"
            "{\n"
            "  \"intent\": \"home_control\" or \"conversation\",\n"
            "  \"target\": \"test_switch\" or null,\n"
            "  \"action\": \"turn_on\", \"turn_off\", \"toggle\" or null,\n"
            "  \"confidence\": 0.0 to 1.0\n"
            "}\n\n"
            "Examples:\n"
            "User: 'Turn on the test switch' -> {\"intent\": \"home_control\", \"target\": \"test_switch\", \"action\": \"turn_on\"}\n"
            "User: 'Turn it off' (after switch context) -> {\"intent\": \"home_control\", \"target\": \"test_switch\", \"action\": \"turn_off\"}\n"
            "User: 'Hello' -> {\"intent\": \"conversation\", \"target\": null, \"action\": null}"
        )

class ActionAgent(BaseAgent):
    """
    Generates the specific Home Assistant service call.
    """
    def get_system_prompt(self) -> str:
        return (
            "You are a Home Assistant Action Generator. Your job is to convert a resolved intent "
            "into a specific Home Assistant service call JSON.\n\n"
            "Available Devices:\n"
            "- Name: 'Test Schalter', Entity: 'input_boolean.test_schalter', Domain: 'input_boolean'\n\n"
            "Output Format:\n"
            "Return a JSON object representing the service call:\n"
            "{\n"
            "  \"domain\": \"input_boolean\",\n"
            "  \"service\": \"turn_on\" or \"turn_off\",\n"
            "  \"entity_id\": \"input_boolean.test_schalter\"\n"
            "}\n\n"
            "If the action is unclear or impossible, return empty JSON: {}"
        )

class ResponseAgent(BaseAgent):
    """
    Generates a natural language response.
    """
    def get_system_prompt(self) -> str:
        lang_instruction = "You speak in short conversational paragraphs, in English or German, matching the user."
        if cfg.language == "en":
            lang_instruction = "You MUST speak in English, regardless of the user's language."
        elif cfg.language == "de":
            lang_instruction = "You MUST speak in German (Deutsch), regardless of the user's language."

        return (
            "You are a helpful Voice Assistant. Your job is to respond to the user.\n"
            f"{lang_instruction}\n\n"
            "Context:\n"
            "- You will be provided with the User's message and the Action that was just taken (if any).\n"
            "- If an action was taken (e.g., switch turned on), confirm it naturally.\n"
            "- If no action was taken, answer the user's question or chat naturally.\n"
            "- Be concise. Do not output JSON. Output only the text response."
        )
