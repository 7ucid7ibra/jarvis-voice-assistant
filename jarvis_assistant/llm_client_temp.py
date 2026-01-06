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