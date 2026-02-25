from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from . import app_paths

SAFE_AUTO_DOMAINS = {"light", "switch", "input_boolean"}
SAFE_AUTO_SERVICES = {"turn_on", "turn_off", "toggle"}


@dataclass
class QuickCommand:
    id: str
    phrases: list[str]
    action: dict[str, Any]
    safety: str = "safe_auto"
    enabled: bool = True
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "phrases": list(self.phrases),
            "action": dict(self.action),
            "safety": self.safety,
            "enabled": self.enabled,
            "meta": dict(self.meta or {}),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "QuickCommand | None":
        if not isinstance(data, dict):
            return None
        cid = str(data.get("id") or "").strip()
        phrases = data.get("phrases")
        action = data.get("action")
        if not cid or not isinstance(phrases, list) or not isinstance(action, dict):
            return None
        clean_phrases = [str(p).strip() for p in phrases if str(p).strip()]
        if not clean_phrases:
            return None
        safety = str(data.get("safety") or "safe_auto").strip() or "safe_auto"
        enabled = bool(data.get("enabled", True))
        meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
        return cls(
            id=cid,
            phrases=clean_phrases,
            action=action,
            safety=safety,
            enabled=enabled,
            meta=meta,
        )


@dataclass
class FastIntentResult:
    kind: str
    response_text: str | None = None
    action: dict[str, Any] | None = None
    quick_command: QuickCommand | None = None
    requires_confirm: bool = False
    meta: dict[str, Any] = field(default_factory=dict)


def _slugify(value: str) -> str:
    base = _normalize_text(value)
    base = re.sub(r"[^a-z0-9]+", "_", base).strip("_")
    return base or "cmd"


def new_quick_command_id(seed: str = "quick") -> str:
    ts = int(datetime.now().timestamp() * 1000)
    return f"{_slugify(seed)}_{ts}"


def _normalize_text(text: str) -> str:
    txt = unicodedata.normalize("NFKD", (text or "").lower())
    txt = "".join(ch for ch in txt if not unicodedata.combining(ch))
    txt = re.sub(r"[^a-z0-9\s]", " ", txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt


def _tokenize(text: str) -> list[str]:
    norm = _normalize_text(text)
    return [t for t in norm.split(" ") if t]


def is_safe_auto_action(action: dict[str, Any]) -> bool:
    domain = str(action.get("domain") or "").strip().lower()
    service = str(action.get("service") or "").strip().lower()
    return domain in SAFE_AUTO_DOMAINS and service in SAFE_AUTO_SERVICES


def _quick_commands_root() -> Path:
    root = Path(app_paths.data_root()) / "quick_commands"
    root.mkdir(parents=True, exist_ok=True)
    return root


def quick_commands_file(profile: str) -> Path:
    safe = (profile or "default").strip() or "default"
    return _quick_commands_root() / f"{safe}.json"


class QuickCommandStore:
    SCHEMA_VERSION = 1

    def __init__(self, profile: str):
        self.profile = (profile or "default").strip() or "default"
        self.path = quick_commands_file(self.profile)

    def load_raw(self) -> dict[str, Any]:
        if not self.path.exists():
            return {
                "schema_version": self.SCHEMA_VERSION,
                "profile": self.profile,
                "commands": [],
                "last_generated_from_entities_at": None,
                "entity_snapshot_hash": None,
            }
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except Exception:
            pass
        return {
            "schema_version": self.SCHEMA_VERSION,
            "profile": self.profile,
            "commands": [],
            "last_generated_from_entities_at": None,
            "entity_snapshot_hash": None,
        }

    def load_commands(self) -> list[QuickCommand]:
        raw = self.load_raw()
        out: list[QuickCommand] = []
        for item in raw.get("commands", []):
            cmd = QuickCommand.from_dict(item)
            if cmd is not None:
                out.append(cmd)
        return out

    def save_commands(
        self,
        commands: list[QuickCommand],
        *,
        last_generated_from_entities_at: str | None = None,
        entity_snapshot_hash: str | None = None,
    ) -> None:
        payload = {
            "schema_version": self.SCHEMA_VERSION,
            "profile": self.profile,
            "commands": [c.to_dict() for c in commands],
            "last_generated_from_entities_at": last_generated_from_entities_at,
            "entity_snapshot_hash": entity_snapshot_hash,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


class QuickCommandMatcher:
    def __init__(self, commands: list[QuickCommand], fuzzy_enabled: bool = True):
        self.commands = commands
        self.fuzzy_enabled = fuzzy_enabled

    def match(self, text: str) -> QuickCommand | None:
        text_norm = _normalize_text(text)
        text_tokens = set(_tokenize(text))
        if not text_norm:
            return None

        # Step 1: deterministic
        for cmd in self.commands:
            if not cmd.enabled:
                continue
            for phrase in cmd.phrases:
                p_norm = _normalize_text(phrase)
                if not p_norm:
                    continue
                if text_norm == p_norm:
                    return cmd
                p_tokens = set(_tokenize(phrase))
                if p_tokens and p_tokens.issubset(text_tokens):
                    return cmd

        # Step 2: constrained fuzzy
        if self.fuzzy_enabled:
            best: tuple[float, QuickCommand | None] = (0.0, None)
            for cmd in self.commands:
                if not cmd.enabled:
                    continue
                for phrase in cmd.phrases:
                    p_norm = _normalize_text(phrase)
                    if not p_norm:
                        continue
                    score = SequenceMatcher(None, text_norm, p_norm).ratio()
                    if score > best[0]:
                        best = (score, cmd)
            if best[1] is not None and best[0] >= 0.92:
                return best[1]

        return None


class FastIntentRouter:
    _TIME_PATTERNS = [
        re.compile(r"\b(what\s+time\s+is\s+it|time\s+is\s+it|current\s+time|tell\s+me\s+the\s+time)\b"),
        re.compile(r"\b(wie\s+spat\s+ist\s+es|uhrzeit|wie\s+viel\s+uhr|sag\s+mir\s+die\s+uhrzeit)\b"),
    ]

    _CREATE_QC_PATTERNS = [
        re.compile(r"\bcreate\s+quick\s+command\s+for\s+(.+)$"),
        re.compile(r"\berstelle\s+schnell(?:en)?\s+befehl\s+fur\s+(.+)$"),
        re.compile(r"\berstelle\s+quick\s+command\s+fur\s+(.+)$"),
    ]

    _REMOVE_QC_PATTERNS = [
        re.compile(r"\b(remove|delete)\s+quick\s+command\s+(.+)$"),
        re.compile(r"\b(entferne|losche)\s+quick\s+command\s+(.+)$"),
    ]

    _GENERATE_QC_PATTERNS = [
        re.compile(r"\b(generate|create)\s+quick\s+commands\b"),
        re.compile(r"\b(erstelle|generiere)\s+quick\s+commands\b"),
    ]

    def __init__(self, commands: list[QuickCommand], fuzzy_enabled: bool = True):
        self.matcher = QuickCommandMatcher(commands, fuzzy_enabled=fuzzy_enabled)

    def match_fast_intent(self, text: str, locale: str | None = None, now_ctx: datetime | None = None) -> FastIntentResult | None:
        norm = _normalize_text(text)
        if not norm:
            return None

        for pattern in self._TIME_PATTERNS:
            if pattern.search(norm):
                now = now_ctx or datetime.now()
                if locale == "de":
                    reply = f"Es ist {now.strftime('%H:%M')} Uhr."
                else:
                    reply = f"It is {now.strftime('%H:%M')}."
                return FastIntentResult(kind="builtin_time", response_text=reply)

        for pattern in self._CREATE_QC_PATTERNS:
            m = pattern.search(norm)
            if m:
                target = (m.group(1) or "").strip()
                if target:
                    return FastIntentResult(kind="quick_command_create", meta={"target": target})

        for pattern in self._REMOVE_QC_PATTERNS:
            m = pattern.search(norm)
            if m:
                target = (m.group(2) or "").strip()
                if target:
                    return FastIntentResult(kind="quick_command_remove", meta={"target": target})

        for pattern in self._GENERATE_QC_PATTERNS:
            if pattern.search(norm):
                return FastIntentResult(kind="quick_command_generate")

        cmd = self.matcher.match(norm)
        if cmd is None:
            return None

        requires_confirm = cmd.safety == "requires_confirm" or not is_safe_auto_action(cmd.action)
        return FastIntentResult(
            kind="quick_action",
            action=dict(cmd.action),
            quick_command=cmd,
            requires_confirm=requires_confirm,
            meta={"command_id": cmd.id},
        )


def generate_commands_from_entities(entities: list[dict[str, Any]], *, locale: str | None = None) -> list[QuickCommand]:
    commands: list[QuickCommand] = []
    seen_entity_ids: set[str] = set()

    for entity in entities:
        entity_id = str(entity.get("entity_id") or "").strip()
        name = str(entity.get("name") or "").strip()
        domain = str(entity.get("domain") or "").strip().lower()
        if not entity_id or not name:
            continue
        if domain not in SAFE_AUTO_DOMAINS:
            continue
        if entity_id in seen_entity_ids:
            continue
        seen_entity_ids.add(entity_id)

        name_norm = _normalize_text(name)
        if not name_norm:
            continue

        de_on = [
            f"{name_norm} an",
            f"schalte {name_norm} an",
        ]
        de_off = [
            f"{name_norm} aus",
            f"schalte {name_norm} aus",
        ]
        en_on = [
            f"{name_norm} on",
            f"turn on {name_norm}",
        ]
        en_off = [
            f"{name_norm} off",
            f"turn off {name_norm}",
        ]

        is_de = locale == "de"
        on_phrases = de_on + en_on if is_de else en_on + de_on
        off_phrases = de_off + en_off if is_de else en_off + de_off

        commands.append(
            QuickCommand(
                id=new_quick_command_id(f"{name_norm}_on"),
                phrases=on_phrases,
                action={
                    "domain": domain,
                    "service": "turn_on",
                    "entity_id": entity_id,
                },
                safety="safe_auto",
                enabled=True,
                meta={"source": "entity_snapshot"},
            )
        )
        commands.append(
            QuickCommand(
                id=new_quick_command_id(f"{name_norm}_off"),
                phrases=off_phrases,
                action={
                    "domain": domain,
                    "service": "turn_off",
                    "entity_id": entity_id,
                },
                safety="safe_auto",
                enabled=True,
                meta={"source": "entity_snapshot"},
            )
        )

    return commands
