import requests
import json
import threading # Added for the new generate method
import subprocess
import time
from pathlib import Path
from typing import List, Dict, Any
from requests.exceptions import ConnectionError, HTTPError, Timeout, RequestException
from PyQt6.QtCore import QObject, pyqtSignal, QRunnable, pyqtSlot
from .config import cfg

class LLMWorker(QObject):
    """
    Worker for calling Ollama API.
    """
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    progress = pyqtSignal(str, int) # status, percentage

    def __init__(self):
        super().__init__()
        self.tried_start_ollama = False

    def generate(self, messages: list[dict], format: str = "json"):
        """
        Generic generation method.
        """
        threading.Thread(target=self._run_generate, args=(messages, format)).start()

    def list_models(self):
        """
        Lists installed models.
        """
        return [m["name"] for m in self.list_models_detailed()]

    def list_models_detailed(self) -> List[Dict[str, Any]]:
        """
        Returns installed models with metadata (name, size, params, quantization).
        """
        self._ensure_ollama_running(force_start=True)
        try:
            url = "http://127.0.0.1:11434/api/tags"
            resp = requests.get(url, timeout=5)
            resp.raise_for_status()
            models = []
            for m in resp.json().get("models", []):
                name = m.get("name", "")
                details = m.get("details", {}) or {}
                size_bytes = m.get("size", 0) or 0
                models.append(
                    {
                        "name": name,
                        "size": self._format_size(size_bytes),
                        "raw_size": size_bytes,
                        "parameter_size": details.get("parameter_size"),
                        "quantization": details.get("quantization"),
                        "hardware": self._hardware_hint(details.get("parameter_size"), details.get("quantization")),
                    }
                )
            return models
        except Exception:
            return []

    def get_model_info(self, name: str) -> Dict[str, Any]:
        """
        Fetch detailed info for a model (even if not installed) via /api/show.
        """
        try:
            resp = requests.post(
                "http://127.0.0.1:11434/api/show",
                json={"name": name},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            details = data.get("details", {}) or {}
            size_bytes = details.get("size", 0) or data.get("size", 0) or 0
            return {
                "name": name,
                "size": self._format_size(size_bytes),
                "raw_size": size_bytes,
                "parameter_size": details.get("parameter_size"),
                "quantization": details.get("quantization"),
                "hardware": self._hardware_hint(details.get("parameter_size"), details.get("quantization")),
            }
        except Exception:
            return {}

    def pull_model(self, name: str) -> Dict[str, str]:
        """
        Pull a model via Ollama API with streaming progress signals.
        """
        url = "http://127.0.0.1:11434/api/pull"
        payload = {"name": name, "stream": True}
        
        if not self._ensure_ollama_running():
            return {"status": "error", "error": "Ollama not running"}
            
        try:
            response = requests.post(url, json=payload, stream=True, timeout=300) # Increased timeout for large models
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        status = data.get("status", "")
                        total = data.get("total", 0)
                        completed = data.get("completed", 0)
                        
                        pct = -1
                        if total > 0:
                            pct = int((completed / total) * 100)
                            status = f"{status} ({pct}%)"
                            
                        self.progress.emit(status, pct)
                    except json.JSONDecodeError:
                        continue
            
            self.progress.emit("Download Finished.", -1)
            return {"status": "success"}
        except Exception as e:
            self.progress.emit(f"Error: {e}", -1)
            return {"status": "error", "error": str(e)}

    def remove_model(self, name: str) -> Dict[str, str]:
        """
        Remove a model via Ollama API.
        """
        url = "http://127.0.0.1:11434/api/delete"
        try:
            resp = requests.delete(url, json={"name": name}, timeout=10)
            resp.raise_for_status()
            return {"status": "success"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def load_catalog(self) -> List[Dict[str, Any]]:
        """
        Load a curated list of common models with size/hardware notes.
        """
        catalog_path = Path(__file__).parent / "model_catalog.json"
        if not catalog_path.exists():
            return []
        try:
            with open(catalog_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("models", [])
        except Exception:
            return []

    def _format_size(self, size_bytes: int) -> str:
        if not size_bytes:
            return "unknown"
        units = ["B", "KB", "MB", "GB", "TB"]
        size = float(size_bytes)
        for unit in units:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"

    def _hardware_hint(self, param_size: str | None, quant: str | None) -> str:
        """
        Very rough guidance based on parameter size and quantization.
        """
        if not param_size:
            return "CPU-friendly (small) or unknown requirements"
        try:
            val = param_size.lower().replace("b", "").strip()
            num = float(val)
        except Exception:
            return "Check hardware; size unknown"

        if num <= 1.5:
            return "CPU-friendly; 8GB RAM OK"
        if num <= 4:
            return "Better with fast CPU or modest GPU"
        if num <= 8:
            return "Prefer discrete GPU; 16GB+ RAM"
        return "Heavy model; strong GPU and RAM recommended"

    def _run_generate(self, messages: list[dict], format: str):
        provider = cfg.api_provider
        
        if provider == "openai":
            self._generate_openai(messages, format)
        elif provider == "gemini":
            self._generate_gemini(messages, format)
        elif provider and provider.startswith("opencode"):
            self._generate_opencode(messages, format)
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

        if not self._ensure_ollama_running():
            self.error.emit("Ollama is not reachable. Start it with 'ollama serve' and ensure port 11434 is open.")
            return

        try:
            # Increased timeout for CPU users / slow models
            response = requests.post(url, json=payload, timeout=300)
            response.raise_for_status()
            result = response.json()
            content = result.get("message", {}).get("content", "")
            self.finished.emit(content)
            return
        except ConnectionError:
            if self._ensure_ollama_running(force_start=True):
                try:
                    response = requests.post(url, json=payload, timeout=60)
                    response.raise_for_status()
                    result = response.json()
                    content = result.get("message", {}).get("content", "")
                    self.finished.emit(content)
                    return
                except Exception as e:
                    self.error.emit(f"Ollama Error after retry: {e}")
            self.error.emit("Ollama is not reachable. Start it with 'ollama serve' and ensure port 11434 is open.")
        except HTTPError as e:
            self.error.emit(f"Ollama returned an HTTP error: {e}")
        except Timeout:
            self.error.emit("Ollama request timed out. Try again in a moment.")
        except RequestException as e:
            self.error.emit(f"Ollama Error: {e}")

    def _ensure_ollama_running(self, force_start: bool = False) -> bool:
        """
        Ping Ollama; optionally try to start it if not reachable.
        """
        try:
            resp = requests.get("http://127.0.0.1:11434/api/tags", timeout=2)
            if resp.status_code == 200:
                return True
        except Exception:
            pass

        if force_start and not self.tried_start_ollama:
            self.tried_start_ollama = True
            try:
                # First try CLI
                subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                time.sleep(2)
                try:
                    resp = requests.get("http://127.0.0.1:11434/api/tags", timeout=3)
                    if resp.status_code == 200:
                        return True
                except Exception:
                    pass
                # Fallback: launch the macOS app if present
                subprocess.Popen(["open", "-a", "Ollama"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                time.sleep(3)
                try:
                    resp = requests.get("http://127.0.0.1:11434/api/tags", timeout=3)
                    return resp.status_code == 200
                except Exception:
                    return False
            except Exception:
                return False
        return False

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

    def _generate_opencode(self, messages: list[dict], format: str):
        """
        OpenCode Grok (openai-compatible) without requiring API key.
        """
        url = "https://opencode.ai/zen/v1/chat/completions"
        headers = {
            "Content-Type": "application/json"
        }
        # If user provides a key anyway, respect it
        if cfg.api_key:
            headers["Authorization"] = f"Bearer {cfg.api_key}"

        payload = {
            "model": cfg.ollama_model or "grok-code",
            "messages": messages
        }
        
        if format == "json":
            payload["response_format"] = {"type": "json_object"}

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            self.finished.emit(content)
        except Exception as e:
            self.error.emit(f"OpenCode Error: {e}")

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

        payload: Dict[str, Any] = {
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
