import requests
import json
import threading # Added for the new generate method
import subprocess
import time
from pathlib import Path
from typing import List, Dict, Any
from urllib.parse import urlparse
from requests.exceptions import ConnectionError, HTTPError, Timeout, RequestException
from PyQt6.QtCore import QObject, pyqtSignal, QRunnable, pyqtSlot
from .config import cfg

class LLMWorker(QObject):
    REMOTE_UNREACHABLE_PREFIX = "__OLLAMA_REMOTE_UNREACHABLE__"
    """
    Worker for calling Ollama API.
    """
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    progress = pyqtSignal(str, str, int) # model, status, percentage

    def __init__(self):
        super().__init__()
        self.tried_start_ollama = False
        self._cancel_event = threading.Event()
        self.download_active = False
        self.download_model = ""
        self.download_status = ""
        self.download_pct = -1
        self._download_cancel_events: dict[str, threading.Event] = {}
        self._download_states: dict[str, dict] = {}

    def _ollama_base_url(self):
        return cfg.ollama_api_url

    def _ollama_url(self, path: str) -> str:
        return f"{self._ollama_base_url()}/api/{path.lstrip('/')}"

    def _is_local_ollama_host(self) -> bool:
        try:
            host = (urlparse(self._ollama_base_url()).hostname or "").lower()
        except Exception:
            host = ""
        return host in {"127.0.0.1", "localhost", "::1"}

    def test_ollama_connection(self, base_url: str | None = None) -> dict:
        target = (base_url or self._ollama_base_url() or "").strip().rstrip('/')
        if not target:
            return {"ok": False, "error": "Empty Ollama base URL"}
        try:
            resp = requests.get(f"{target}/api/tags", timeout=5)
            resp.raise_for_status()
            models = resp.json().get("models", [])
            return {"ok": True, "model_count": len(models), "base_url": target}
        except Exception as e:
            return {"ok": False, "error": str(e), "base_url": target}

    def cancel_download(self, name: str | None = None):
        """Request cancellation of current download(s)."""
        if name:
            ev = self._download_cancel_events.get(name)
            if ev:
                ev.set()
            state = self._download_states.get(name)
            if state:
                state["status"] = "Cancelling download..."
        else:
            self._cancel_event.set()
            for ev in self._download_cancel_events.values():
                ev.set()
            for state in self._download_states.values():
                state["status"] = "Cancelling download..."

    def get_download_state(self) -> dict:
        # Backward-compatible single-download snapshot (most recent active, else last known)
        states = self.get_download_states()
        if states:
            active = [v for v in states.values() if v.get("active")]
            pick = (active[0] if active else list(states.values())[0]).copy()
            return pick
        return {
            "active": self.download_active,
            "model": self.download_model,
            "status": self.download_status,
            "pct": self.download_pct,
        }

    def get_download_states(self) -> dict[str, dict]:
        return {k: v.copy() for k, v in self._download_states.items()}

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
            url = self._ollama_url("tags")
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
                self._ollama_url("show"),
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
        url = self._ollama_url("pull")
        payload = {"name": name, "stream": True}
        cancel_event = threading.Event()
        self._download_cancel_events[name] = cancel_event
        self._download_states[name] = {
            "active": True,
            "model": name,
            "status": f"Starting download: {name}...",
            "pct": 0,
        }
        self.download_active = True
        self.download_model = name
        self.download_status = self._download_states[name]["status"]
        self.download_pct = 0

        if not self._ensure_ollama_running():
            self._download_states[name] = {
                "active": False,
                "model": name,
                "status": "Error: Ollama not running",
                "pct": -1,
            }
            self.download_active = any(v.get("active") for v in self._download_states.values())
            self.download_model = name
            self.download_status = self._download_states[name]["status"]
            self.download_pct = -1
            self.progress.emit(name, self.download_status, -1)
            return {"status": "error", "error": "Ollama not running"}

        try:
            response = requests.post(url, json=payload, stream=True, timeout=300)
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

                        self._download_states[name] = {
                            "active": True,
                            "model": name,
                            "status": status,
                            "pct": pct,
                        }
                        self.download_active = True
                        self.download_model = name
                        self.download_status = status
                        self.download_pct = pct
                        self.progress.emit(name, status, pct)
                    except json.JSONDecodeError:
                        continue

                if self._cancel_event.is_set() or cancel_event.is_set():
                    self._download_states[name] = {
                        "active": False,
                        "model": name,
                        "status": "Download Cancelled.",
                        "pct": -1,
                    }
                    self.download_active = any(v.get("active") for v in self._download_states.values())
                    self.download_model = name
                    self.download_status = "Download Cancelled."
                    self.download_pct = -1
                    self.progress.emit(name, "Download Cancelled.", -1)
                    return {"status": "cancelled"}

            self._download_states[name] = {
                "active": False,
                "model": name,
                "status": "Download Finished.",
                "pct": -1,
            }
            self.download_active = any(v.get("active") for v in self._download_states.values())
            self.download_model = name
            self.download_status = "Download Finished."
            self.download_pct = -1
            self.progress.emit(name, "Download Finished.", -1)
            return {"status": "success"}
        except Exception as e:
            msg = f"Error: {e}"
            self._download_states[name] = {
                "active": False,
                "model": name,
                "status": msg,
                "pct": -1,
            }
            self.download_active = any(v.get("active") for v in self._download_states.values())
            self.download_model = name
            self.download_status = msg
            self.download_pct = -1
            self.progress.emit(name, msg, -1)
            return {"status": "error", "error": str(e)}
        finally:
            self._download_cancel_events.pop(name, None)

    def remove_model(self, name: str) -> Dict[str, str]:
        """
        Remove a model via Ollama API.
        """
        url = self._ollama_url("delete")
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
        url = self._ollama_url("chat")

        payload = {
            "model": cfg.ollama_model,
            "messages": messages,
            "stream": False,
        }

        if format == "json":
            payload["format"] = "json"

        if not self._ensure_ollama_running():
            base = self._ollama_base_url()
            if self._is_local_ollama_host():
                self.error.emit("Ollama is not reachable. Start it with 'ollama serve' and ensure port 11434 is open.")
            else:
                self.error.emit(f"{self.REMOTE_UNREACHABLE_PREFIX}:{base}")
            return

        try:
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
            base = self._ollama_base_url()
            if self._is_local_ollama_host():
                self.error.emit("Ollama is not reachable. Start it with 'ollama serve' and ensure port 11434 is open.")
            else:
                self.error.emit(f"{self.REMOTE_UNREACHABLE_PREFIX}:{base}")
        except HTTPError as e:
            self.error.emit(f"Ollama returned an HTTP error: {e}")
        except Timeout:
            self.error.emit("Ollama request timed out. Try again in a moment.")
        except RequestException as e:
            self.error.emit(f"Ollama Error: {e}")

    def _ensure_ollama_running(self, force_start: bool = False) -> bool:
        """
        Ping Ollama; optionally try to start it if not reachable.
        Auto-start is local-host only.
        """
        try:
            resp = requests.get(self._ollama_url("tags"), timeout=2)
            if resp.status_code == 200:
                return True
        except Exception:
            pass

        if not self._is_local_ollama_host():
            return False

        if force_start and not self.tried_start_ollama:
            self.tried_start_ollama = True
            try:
                subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                time.sleep(2)
                try:
                    resp = requests.get(self._ollama_url("tags"), timeout=3)
                    if resp.status_code == 200:
                        return True
                except Exception:
                    pass

                subprocess.Popen(["open", "-a", "Ollama"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                time.sleep(3)
                try:
                    resp = requests.get(self._ollama_url("tags"), timeout=3)
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
        OpenCode models share endpoints with different providers.
        Use model-specific routing so non-OpenAI-compatible models (e.g. minimax) work.
        """
        model = cfg.ollama_model or "grok-code"
        headers = {"Content-Type": "application/json"}
        if cfg.api_key:
            headers["Authorization"] = f"Bearer {cfg.api_key}"

        # Decide endpoint + payload shape based on model family
        anthropic_models = {"minimax-m2.1-free", "claude-sonnet-4", "claude-3-5-haiku", "claude-haiku-4-5"}
        if model in anthropic_models:
            url = "https://opencode.ai/zen/v1/messages"
            sys_msgs = [m["content"] for m in messages if m.get("role") == "system"]
            conv = []
            for m in messages:
                role = m.get("role")
                if role == "system":
                    continue
                if role not in ("user", "assistant"):
                    continue
                conv.append({"role": role, "content": [{"type": "text", "text": m.get("content", "")}]})
            payload: Dict[str, Any] = {
                "model": model,
                "messages": conv,
                "max_tokens": 512,  # required by anthropic-compatible API
            }
            if sys_msgs:
                payload["system"] = "\n\n".join(sys_msgs)
        else:
            url = "https://opencode.ai/zen/v1/chat/completions"
            payload = {
                "model": model,
                "messages": messages,
            }
            if format == "json":
                payload["response_format"] = {"type": "json_object"}

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=120)  # GLM and others can be slow
            resp.raise_for_status()
            data = resp.json()
            if model in anthropic_models:
                parts = data.get("content", [])
                content = "".join([p.get("text", "") for p in parts if isinstance(p, dict)])
            else:
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
