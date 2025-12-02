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

    def _run_generate(self, messages: list[dict], format: str):
        url = f"{cfg.ha_url.replace('8123', '11434').replace('/api', '')}/api/chat"
        # Fallback if HA URL isn't localhost (Ollama usually on localhost:11434)
        if "192.168" in cfg.ha_url:
             url = "http://127.0.0.1:11434/api/chat"

        payload = {
            "model": cfg.ollama_model,
            "messages": messages,
            "stream": False,
        }
        
        if format == "json":
            payload["format"] = "json"

        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()
            content = result.get("message", {}).get("content", "")
            self.finished.emit(content)
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP Error: {e}"
            if e.response is not None:
                try:
                    error_details = e.response.text
                    print(f"Ollama Error Details: {error_details}", flush=True)
                    error_msg += f"\nDetails: {error_details}"
                except:
                    pass
            self.error.emit(error_msg)
        except requests.exceptions.ConnectionError:
            self.error.emit(
                f"Could not connect to Ollama at {cfg.ollama_api_url}.\n"
                "Please make sure Ollama is running."
            )
        except Exception as e:
            self.error.emit(f"LLM Error: {e}")
