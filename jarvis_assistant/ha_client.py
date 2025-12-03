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
            {"entity_id": "input_boolean.switch"},
        )

    def get_states(self) -> list:
        url = f"{self.base_url}/api/states"
        resp = requests.get(url, headers=self._headers(), timeout=5)
        resp.raise_for_status()
        return resp.json()

    def get_relevant_entities(self) -> str:
        """
        Fetches all states and returns a formatted string of relevant entities
        (lights, switches, sensors) for the LLM prompt.
        """
        try:
            states = self.get_states()
        except Exception as e:
            return f"Error fetching entities: {e}"

        relevant_domains = [
            "light", "switch", "sensor", "binary_sensor", 
            "cover", "climate", "input_boolean"
        ]
        
        lines = []
        for state in states:
            entity_id = state.get("entity_id", "")
            domain = entity_id.split(".")[0]
            
            if domain in relevant_domains:
                friendly_name = state.get("attributes", {}).get("friendly_name", entity_id)
                state_val = state.get("state", "unknown")
                lines.append(f"- Name: '{friendly_name}', Entity: '{entity_id}', State: '{state_val}'")
                
        if not lines:
            return "No relevant devices found."
            
        return "\n".join(lines)

