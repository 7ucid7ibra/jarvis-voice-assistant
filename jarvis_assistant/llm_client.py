import requests
import json
import threading # Added for the new generate method
from PyQt6.QtCore import QObject, pyqtSignal, QRunnable, pyqtSlot
from .config import cfg

class LLMWorker(QObject):
    """
    Worker for calling Ollama API.
    """
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def generate(self, messages: list[dict], format: str = "json"):
        """
        Generic generation method.
        """
        threading.Thread(target=self._run_generate, args=(messages, format)).start()

    def list_models(self):
        """
        Lists installed models.
        """
        try:
            url = "http://127.0.0.1:11434/api/tags"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                models = [m["name"] for m in resp.json().get("models", [])]
                return models
        except:
            pass
        return []

    def _run_generate(self, messages: list[dict], format: str):
        provider = cfg.api_provider
        
        if provider == "openai":
            self._generate_openai(messages, format)
        elif provider == "gemini":
            self._generate_gemini(messages, format)
        else:
            self._generate_ollama(messages, format)

    def _generate_ollama(self, messages: list[dict], format: str):
        url = "http://127.0.0.1:11434/api/chat"
        
        # We removed auto-pull here because we now have a manual button
        # But we could keep a check if we wanted. For now, let's assume user pulls it.

        payload = {
            "model": cfg.ollama_model,
            "messages": messages,
            "stream": False,
        }
        
        if format == "json":
            payload["format"] = "json"

        try:
            response = requests.post(url, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()
            content = result.get("message", {}).get("content", "")
            self.finished.emit(content)
        except Exception as e:
            self.error.emit(f"Ollama Error: {e}")

    def _ensure_model_pulled(self, model_name: str):
        # Deprecated in favor of manual pull
        pass

    def _generate_openai(self, messages: list[dict], format: str):
        if not cfg.api_key:
            self.error.emit("OpenAI API Key not set")
            return
            
        headers = {
            "Authorization": f"Bearer {cfg.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "gpt-4o-mini", # Default to mini for speed
            "messages": messages
        }
        
        if format == "json":
            payload["response_format"] = {"type": "json_object"}

        try:
            resp = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            self.finished.emit(content)
        except Exception as e:
            self.error.emit(f"OpenAI Error: {e}")

    def _generate_gemini(self, messages: list[dict], format: str):
        if not cfg.api_key:
            self.error.emit("Gemini API Key not set")
            return
            
        # Gemini API is a bit different, requires converting messages
        # For simplicity, we'll use a basic implementation or suggest using the official SDK
        # But requests is lighter.
        # URL: https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=YOUR_API_KEY
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={cfg.api_key}"
        
        # Convert messages to Gemini format
        contents = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            if msg["role"] == "system":
                # Gemini doesn't strictly support system role in the same way in the messages list for v1beta
                # It's better to prepend to first user message or use system_instruction
                # For now, let's prepend to first user message if possible
                continue 
            contents.append({"role": role, "parts": [{"text": msg["content"]}]})
            
        # Handle system prompt
        system_prompt = next((m["content"] for m in messages if m["role"] == "system"), None)
        
        payload = {
            "contents": contents
        }
        
        if system_prompt:
             payload["system_instruction"] = {"parts": [{"text": system_prompt}]}

        if format == "json":
            payload["generationConfig"] = {"response_mime_type": "application/json"}

        try:
            resp = requests.post(url, json=payload, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            content = data["candidates"][0]["content"]["parts"][0]["text"]
            self.finished.emit(content)
        except Exception as e:
            self.error.emit(f"Gemini Error: {e}")
