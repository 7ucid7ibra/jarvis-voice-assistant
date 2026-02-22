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
    if "all lights" in text or "all light" in text or "alle lichter" in text:
        return False

    matched_domains = set()
    for ent in entities:
        name = (ent.get("name") or "").lower()
        entity_id = (ent.get("entity_id") or "").lower()
        suffix = entity_id.split(".")[-1] if entity_id else ""
        if name and name in text:
            matched_domains.add(ent.get("domain"))
        elif suffix and re.search(rf"\b{re.escape(suffix)}\b", text):
            matched_domains.add(ent.get("domain"))

    if ("heater" in text or "heizung" in text) and any(ch.isdigit() for ch in text):
        matched_domains.add("input_number")

    return len(matched_domains) > 1
