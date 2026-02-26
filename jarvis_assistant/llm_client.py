import requests
import json
import threading # Added for the new generate method
import subprocess
import time
from pathlib import Path
from typing import List, Dict, Any
from urllib.parse import quote, urlparse
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
        self._lmstudio_supports_response_format: bool | None = None

    def _ollama_base_url(self):
        return cfg.ollama_api_url

    def _ollama_url(self, path: str) -> str:
        return f"{self._ollama_base_url()}/api/{path.lstrip('/')}"

    def _lmstudio_base_url(self):
        return cfg.lmstudio_api_url

    def _lmstudio_url(self, path: str) -> str:
        return f"{self._lmstudio_base_url()}/api/v0/{path.lstrip('/')}"

    def _lmstudio_v1_url(self, path: str) -> str:
        return f"{self._lmstudio_base_url()}/v1/{path.lstrip('/')}"

    def _provider_key(self, model_name: str, provider: str | None = None) -> str:
        p = (provider or cfg.api_provider or "ollama").strip().lower()
        return f"{p}::{model_name}"

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

    def _parse_lmstudio_error_text(self, response: requests.Response) -> str:
        try:
            payload = response.json()
            if isinstance(payload, dict):
                err = payload.get("error")
                if isinstance(err, dict):
                    msg = err.get("message") or err.get("error") or str(err)
                    return str(msg)
                if isinstance(err, str) and err.strip():
                    return err.strip()
                msg = payload.get("message")
                if isinstance(msg, str) and msg.strip():
                    return msg.strip()
                return json.dumps(payload, ensure_ascii=False)
            if isinstance(payload, list):
                return json.dumps(payload, ensure_ascii=False)
        except Exception:
            pass
        text = (response.text or "").strip()
        return text or response.reason or "Unknown LM Studio error"

    def _fetch_lmstudio_v1_model_ids(self, base_url: str | None = None) -> tuple[list[str], str | None]:
        target = (base_url or self._lmstudio_base_url() or "").strip().rstrip('/')
        if not target:
            return [], "Empty LM Studio base URL"
        try:
            resp = requests.get(f"{target}/v1/models", timeout=8)
            resp.raise_for_status()
            data = resp.json()
            rows = data.get("data") if isinstance(data, dict) else data
            if not isinstance(rows, list):
                return [], "Invalid /v1/models response shape"
            ids: list[str] = []
            for row in rows:
                if isinstance(row, dict):
                    mid = row.get("id") or row.get("model") or row.get("name")
                    if isinstance(mid, str) and mid.strip():
                        ids.append(mid.strip())
            return ids, None
        except Exception as exc:
            return [], str(exc)

    def test_lmstudio_connection(self, base_url: str | None = None) -> dict:
        target = (base_url or self._lmstudio_base_url() or "").strip().rstrip('/')
        if not target:
            return {"ok": False, "error": "Empty LM Studio base URL", "base_url": target}

        v0_models: list[Any] = []
        try:
            resp_v0 = requests.get(f"{target}/api/v0/models", timeout=6)
            resp_v0.raise_for_status()
            data_v0 = resp_v0.json()
            rows_v0 = data_v0.get("data") if isinstance(data_v0, dict) else data_v0
            if isinstance(rows_v0, list):
                v0_models = rows_v0
        except Exception as exc:
            return {
                "ok": False,
                "error": f"/api/v0/models failed: {exc}",
                "base_url": target,
            }

        v1_ids, v1_err = self._fetch_lmstudio_v1_model_ids(base_url=target)
        if v1_err:
            return {
                "ok": False,
                "error": f"/v1/models failed: {v1_err}",
                "base_url": target,
                "v0_model_count": len(v0_models),
                "v1_model_count": 0,
                "selected_model_visible_in_v1": False,
            }

        selected_model = (cfg.lmstudio_model or "").strip()
        selected_visible = (selected_model in v1_ids) if selected_model else True
        diag = None
        if selected_model and not selected_visible:
            diag = (
                f"Selected model '{selected_model}' is not visible in /v1/models. "
                "Choose a /v1 model id or press USE to load/select one."
            )

        return {
            "ok": True,
            "base_url": target,
            "v0_model_count": len(v0_models),
            "v1_model_count": len(v1_ids),
            "model_count": len(v0_models),
            "selected_model_visible_in_v1": selected_visible,
            "diagnostic_message": diag,
            "v1_model_ids": v1_ids,
        }

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

    def list_models_detailed(self, provider: str | None = None) -> List[Dict[str, Any]]:
        """
        Returns installed models with metadata for the selected local provider.
        """
        provider_name = (provider or cfg.api_provider or "ollama").strip().lower()
        if provider_name == "lmstudio":
            return self.list_models_detailed_lmstudio()

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

    def list_models_detailed_lmstudio(self) -> List[Dict[str, Any]]:
        try:
            resp = requests.get(self._lmstudio_url("models"), timeout=8)
            resp.raise_for_status()
            data = resp.json()
            raw_models = data.get("data") if isinstance(data, dict) else data
            if not isinstance(raw_models, list):
                raw_models = []
            models: List[Dict[str, Any]] = []
            for m in raw_models:
                if not isinstance(m, dict):
                    continue
                name = (
                    m.get("modelKey")
                    or m.get("id")
                    or m.get("name")
                    or m.get("path")
                    or ""
                )
                size_bytes = int(m.get("sizeBytes") or m.get("size") or 0)
                arch = m.get("architecture") or m.get("arch") or ""
                quant = m.get("quantization") or m.get("quant") or ""
                params = m.get("parameterSize") or m.get("params") or None
                models.append(
                    {
                        "name": name,
                        "size": self._format_size(size_bytes),
                        "raw_size": size_bytes,
                        "parameter_size": params,
                        "quantization": quant,
                        "hardware": self._hardware_hint(str(params) if params else None, str(quant) if quant else None),
                        "architecture": arch,
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

    def pull_model(self, name: str, provider: str | None = None) -> Dict[str, str]:
        """
        Pull a model via selected local provider API with progress signals.
        """
        provider_name = (provider or cfg.api_provider or "ollama").strip().lower()
        if provider_name == "lmstudio":
            return self.download_model_lmstudio(name)

        url = self._ollama_url("pull")
        payload = {"name": name, "stream": True}
        cancel_event = threading.Event()
        download_key = self._provider_key(name, provider_name)
        self._download_cancel_events[download_key] = cancel_event
        self._download_states[download_key] = {
            "active": True,
            "model": name,
            "status": f"Starting download: {name}...",
            "pct": 0,
        }
        self.download_active = True
        self.download_model = name
        self.download_status = self._download_states[download_key]["status"]
        self.download_pct = 0

        if not self._ensure_ollama_running():
            self._download_states[download_key] = {
                "active": False,
                "model": name,
                "status": "Error: Ollama not running",
                "pct": -1,
            }
            self.download_active = any(v.get("active") for v in self._download_states.values())
            self.download_model = name
            self.download_status = self._download_states[download_key]["status"]
            self.download_pct = -1
            self.progress.emit(download_key, self.download_status, -1)
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

                        self._download_states[download_key] = {
                            "active": True,
                            "model": name,
                            "status": status,
                            "pct": pct,
                        }
                        self.download_active = True
                        self.download_model = name
                        self.download_status = status
                        self.download_pct = pct
                        self.progress.emit(download_key, status, pct)
                    except json.JSONDecodeError:
                        continue

                if self._cancel_event.is_set() or cancel_event.is_set():
                    self._download_states[download_key] = {
                        "active": False,
                        "model": name,
                        "status": "Download Cancelled.",
                        "pct": -1,
                    }
                    self.download_active = any(v.get("active") for v in self._download_states.values())
                    self.download_model = name
                    self.download_status = "Download Cancelled."
                    self.download_pct = -1
                    self.progress.emit(download_key, "Download Cancelled.", -1)
                    return {"status": "cancelled"}

            self._download_states[download_key] = {
                "active": False,
                "model": name,
                "status": "Download Finished.",
                "pct": -1,
            }
            self.download_active = any(v.get("active") for v in self._download_states.values())
            self.download_model = name
            self.download_status = "Download Finished."
            self.download_pct = -1
            self.progress.emit(download_key, "Download Finished.", -1)
            return {"status": "success"}
        except Exception as e:
            msg = f"Error: {e}"
            self._download_states[download_key] = {
                "active": False,
                "model": name,
                "status": msg,
                "pct": -1,
            }
            self.download_active = any(v.get("active") for v in self._download_states.values())
            self.download_model = name
            self.download_status = msg
            self.download_pct = -1
            self.progress.emit(download_key, msg, -1)
            return {"status": "error", "error": str(e)}
        finally:
            self._download_cancel_events.pop(download_key, None)

    def download_model_lmstudio(self, model_key: str) -> Dict[str, str]:
        download_key = self._provider_key(model_key, "lmstudio")
        cancel_event = threading.Event()
        self._download_cancel_events[download_key] = cancel_event
        self._download_states[download_key] = {
            "active": True,
            "model": download_key,
            "status": f"Starting download: {model_key}...",
            "pct": 0,
        }
        self.download_active = True
        self.download_model = download_key
        self.download_status = self._download_states[download_key]["status"]
        self.download_pct = 0
        self._cancel_event.clear()

        download_id = None
        try:
            resp = requests.post(
                self._lmstudio_url("models/download"),
                json={"modelKey": model_key},
                timeout=20,
            )
            resp.raise_for_status()
            data = resp.json() if resp.content else {}
            if isinstance(data, dict):
                download_id = data.get("downloadId") or data.get("id")
        except Exception as e:
            msg = f"Error: {e}"
            self._download_states[download_key] = {
                "active": False,
                "model": download_key,
                "status": msg,
                "pct": -1,
            }
            self.progress.emit(download_key, msg, -1)
            self.download_active = any(v.get("active") for v in self._download_states.values())
            return {"status": "error", "error": str(e)}

        try:
            deadline = time.time() + 1800
            while time.time() < deadline:
                if self._cancel_event.is_set() or cancel_event.is_set():
                    try:
                        if download_id:
                            requests.delete(self._lmstudio_url(f"models/downloads/{download_id}"), timeout=5)
                    except Exception:
                        pass
                    self._download_states[download_key] = {
                        "active": False,
                        "model": download_key,
                        "status": "Download Cancelled.",
                        "pct": -1,
                    }
                    self.progress.emit(download_key, "Download Cancelled.", -1)
                    self.download_active = any(v.get("active") for v in self._download_states.values())
                    return {"status": "cancelled"}

                status = "Downloading"
                pct = -1
                done = False

                if download_id:
                    try:
                        st = requests.get(self._lmstudio_url(f"models/downloads/{download_id}"), timeout=8)
                        st.raise_for_status()
                        payload = st.json() if st.content else {}
                        if isinstance(payload, dict):
                            raw_status = str(payload.get("status") or payload.get("state") or "downloading")
                            progress = payload.get("progress")
                            if isinstance(progress, (int, float)):
                                pct = int(progress * 100) if progress <= 1 else int(progress)
                                pct = max(0, min(100, pct))
                            if pct >= 0:
                                status = f"{raw_status} ({pct}%)"
                            else:
                                status = raw_status
                            done = raw_status.lower() in {"completed", "finished", "done", "success"}
                            if raw_status.lower() in {"failed", "error"}:
                                raise RuntimeError(payload.get("error") or "Download failed")
                    except Exception:
                        # fall back to existence check below
                        pass

                # fallback completion check: model appears in installed list
                installed = self.list_models_detailed_lmstudio()
                if any((m.get("name") or "") == model_key for m in installed):
                    done = True

                if done:
                    self._download_states[download_key] = {
                        "active": False,
                        "model": download_key,
                        "status": "Download Finished.",
                        "pct": -1,
                    }
                    self.progress.emit(download_key, "Download Finished.", -1)
                    self.download_active = any(v.get("active") for v in self._download_states.values())
                    return {"status": "success"}

                self._download_states[download_key] = {
                    "active": True,
                    "model": download_key,
                    "status": status,
                    "pct": pct,
                }
                self.progress.emit(download_key, status, pct)
                time.sleep(1.0)

            raise Timeout("LM Studio download timed out")
        except Exception as e:
            msg = f"Error: {e}"
            self._download_states[download_key] = {
                "active": False,
                "model": download_key,
                "status": msg,
                "pct": -1,
            }
            self.progress.emit(download_key, msg, -1)
            self.download_active = any(v.get("active") for v in self._download_states.values())
            return {"status": "error", "error": str(e)}
        finally:
            self._download_cancel_events.pop(download_key, None)

    def remove_model_lmstudio(self, model_key: str) -> Dict[str, str]:
        try:
            safe_key = quote(model_key, safe="")
            resp = requests.delete(self._lmstudio_url(f"models/{safe_key}"), timeout=10)
            resp.raise_for_status()
            return {"status": "success"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def load_model_lmstudio(self, model_key: str) -> Dict[str, str]:
        try:
            resp = requests.post(self._lmstudio_url("models/load"), json={"modelKey": model_key}, timeout=20)
            resp.raise_for_status()
            return {"status": "success"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def remove_model(self, name: str, provider: str | None = None) -> Dict[str, str]:
        """Remove a model via selected local provider API."""
        provider_name = (provider or cfg.api_provider or "ollama").strip().lower()
        if provider_name == "lmstudio":
            return self.remove_model_lmstudio(name)

        url = self._ollama_url("delete")
        try:
            resp = requests.delete(url, json={"name": name}, timeout=10)
            resp.raise_for_status()
            return {"status": "success"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def load_catalog(self, provider: str | None = None) -> List[Dict[str, Any]]:
        """Load provider-specific curated model catalog."""
        provider_name = (provider or cfg.api_provider or "ollama").strip().lower()
        if provider_name == "lmstudio":
            return self.load_lmstudio_catalog()

        catalog_path = Path(__file__).parent / "model_catalog.json"
        if not catalog_path.exists():
            return []
        try:
            with open(catalog_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("models", [])
        except Exception:
            return []

    def load_lmstudio_catalog(self) -> List[Dict[str, Any]]:
        catalog_path = Path(__file__).parent / "lmstudio_model_catalog.json"
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
        elif provider == "lmstudio":
            self._generate_lmstudio(messages, format)
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

    def _generate_lmstudio(self, messages: list[dict], format: str):
        model = (cfg.lmstudio_model or "").strip()
        if not model:
            self.error.emit("LM Studio model not selected. Choose a model in Settings -> Intelligence.")
            return

        v1_ids, v1_err = self._fetch_lmstudio_v1_model_ids()
        if v1_err:
            self.error.emit(f"LM Studio /v1/models check failed: {v1_err}")
            return
        if v1_ids and model not in v1_ids:
            preview = ", ".join(v1_ids[:5])
            suffix = " ..." if len(v1_ids) > 5 else ""
            self.error.emit(
                f"LM Studio model id mismatch: '{model}' is not in /v1/models. "
                f"Available ids: {preview}{suffix}."
            )
            return

        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
        }
        # LM Studio compatibility: do not send OpenAI response_format=json_object.
        # JSON behavior is enforced by prompt + parser on the app side.
        include_response_format = False

        endpoint = self._lmstudio_v1_url("chat/completions")
        try:
            response = requests.post(endpoint, json=payload, timeout=180)
            if response.status_code >= 400:
                err_text = self._parse_lmstudio_error_text(response)
                self.error.emit(f"LM Studio {response.status_code}: {err_text} | endpoint={endpoint} model={model}")
                return

            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            self.finished.emit(content)
        except Exception as e:
            self.error.emit(f"LM Studio request failed: {e} | endpoint={endpoint} model={model}")

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
