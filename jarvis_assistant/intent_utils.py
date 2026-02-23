import re
from datetime import datetime, timedelta


def parse_delay_seconds(user_text: str, now: datetime) -> int:
    text = (user_text or "").lower()
    rel = re.search(r"in\s+(\d+)\s*(seconds?|secs?|minutes?|mins?|hours?|hrs?)", text)
    if rel:
        amount = int(rel.group(1))
        unit = rel.group(2)
        if unit.startswith("sec"):
            return amount
        if unit.startswith("min"):
            return amount * 60
        if unit.startswith("hour") or unit.startswith("hr"):
            return amount * 3600
    if "half an hour" in text or "half hour" in text:
        return 1800

    at_match = re.search(r"(?:at|um)\s*(\d{1,2})[:.](\d{2})", text)
    if at_match:
        hour = int(at_match.group(1))
        minute = int(at_match.group(2))
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target <= now:
            target = target + timedelta(days=1)
        return int((target - now).total_seconds())

    return 0


def is_multi_domain_request(user_text: str, entities: list[dict[str, str]]) -> bool:
    text = (user_text or "").lower()
    text_compact = re.sub(r"[\s_\-]+", "", text)
    if "all lights" in text or "all light" in text or "alle lichter" in text:
        return False

    matched_domains = set()
    for ent in entities:
        name = (ent.get("name") or "").lower().strip()
        name_compact = re.sub(r"[\s_\-]+", "", name) if name else ""
        entity_id = (ent.get("entity_id") or "").lower()
        suffix = entity_id.split(".")[-1] if entity_id else ""
        if (name and name in text) or (name_compact and name_compact in text_compact):
            matched_domains.add(ent.get("domain"))
        elif suffix and re.search(rf"\b{re.escape(suffix)}\b", text):
            matched_domains.add(ent.get("domain"))

    if ("heater" in text or "heizung" in text) and any(ch.isdigit() for ch in text):
        matched_domains.add("input_number")

    return len(matched_domains) > 1


def looks_like_home_control_request(user_text: str, entities: list[dict[str, str]]) -> bool:
    text = (user_text or "").lower().strip()
    if not text:
        return False
    text_compact = re.sub(r"[\s_\-]+", "", text)

    has_action_keyword = any(
        re.search(pattern, text)
        for pattern in [
            r"\b(turn|switch)\s+(on|off)\b",
            r"\b(toggle|enable|disable|activate|deactivate)\b",
            r"\b(set|dim|brighten)\b",
            r"\b(ein|aus)schalt(?:e|en)?\b",
            r"\bschalt(?:e|en)?\b",
            r"\bmach(?:e|en)?\b.*\b(an|aus)\b",
            r"\ban\b",
            r"\baus\b",
        ]
    )
    if not has_action_keyword:
        return False

    device_keywords = {
        "light",
        "lights",
        "lamp",
        "lampe",
        "lichter",
        "switch",
        "steckdose",
        "plug",
        "tv",
        "fernseher",
        "heater",
        "heizung",
        "input_boolean",
        "wohnzimmer",
        "tischlampe",
    }
    if any(keyword in text for keyword in device_keywords):
        return True

    for ent in entities:
        name = (ent.get("name") or "").lower().strip()
        if name:
            name_compact = re.sub(r"[\s_\-]+", "", name)
            if name in text or (name_compact and name_compact in text_compact):
                return True
        entity_id = (ent.get("entity_id") or "").lower().strip()
        if entity_id and entity_id in text:
            return True
        suffix = entity_id.split(".")[-1] if entity_id else ""
        if suffix and re.search(rf"\b{re.escape(suffix)}\b", text):
            return True

    return False


def _is_unknown_state(value: str | None) -> bool:
    state = (value or "").strip().lower()
    return state in {"", "unknown", "unavailable", "none", "null"}


def state_matches_action(
    service: str,
    initial_state: str | None,
    new_state: str | None,
    value: int | float | str | None = None,
    tolerance: float = 0.001,
) -> bool:
    """
    Returns True if the observed state is consistent with the requested action.
    """
    service = (service or "").strip().lower()
    initial = (initial_state or "").strip().lower()
    current = (new_state or "").strip().lower()

    if service == "set_value":
        try:
            expected_val = float(value)
            actual_val = float(new_state)
            return abs(actual_val - expected_val) <= tolerance
        except Exception:
            return False

    if service == "turn_on":
        return current == "on"

    if service == "turn_off":
        return current == "off"

    if service == "toggle":
        if initial in {"on", "off"}:
            expected = "off" if initial == "on" else "on"
            return current == expected
        return not _is_unknown_state(new_state)

    return False
