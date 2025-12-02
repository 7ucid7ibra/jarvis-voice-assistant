import requests
from .config import cfg

class HomeAssistantClient:
    def __init__(self, base_url: str | None = None, token: str | None = None) -> None:
        self.base_url = base_url or cfg.ha_url
        self.token = token or cfg.ha_token

    def _headers(self) -> dict:
        if not self.token:
            raise RuntimeError(
                "Home Assistant token is not set. "
                "Set HA_TOKEN env var or ha_token in settings."
            )
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def call_service(self, domain: str, service: str, data: dict) -> list:
        url = f"{self.base_url}/api/services/{domain}/{service}"
        resp = requests.post(url, headers=self._headers(), json=data, timeout=5)
        resp.raise_for_status()
        return resp.json()

    # Convenience helper for the current test switch
    def set_test_switch(self, on: bool) -> list:
        domain = "input_boolean"
        service = "turn_on" if on else "turn_off"
        return self.call_service(
            domain,
            service,
            {"entity_id": "input_boolean.test_schalter"},
        )
