import requests
import json
from PyQt6.QtCore import QObject, pyqtSignal, QRunnable, pyqtSlot
from .config import cfg

class LLMWorker(QObject):
    """
    Worker for calling Ollama API.
    """
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def generate_reply(self, messages: list):
        try:
            payload = {
                "model": cfg.ollama_model,
                "messages": messages,
                "stream": False
            }
            response = requests.post(cfg.ollama_api_url, json=payload)
            response.raise_for_status()
            
            data = response.json()
            reply = data.get("message", {}).get("content", "")
            self.finished.emit(reply)

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
