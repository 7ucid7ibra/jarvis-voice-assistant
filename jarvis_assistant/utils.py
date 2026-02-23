import logging
import sys
import os

def setup_logging():
    log_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "jarvis.log")
    handlers = [
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_path, mode="a", encoding="utf-8")
    ]
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=handlers
    )
    return logging.getLogger("Jarvis")

logger = setup_logging()

import json
import re

def extract_json(text: str) -> dict:
    """
    Robustly extract JSON from a string, handling markdown code blocks and raw text.
    """
    if not text:
        raise ValueError("Empty response")

    text = text.strip()
    # Common prefix produced by some models: "json\n{...}"
    text = re.sub(r"^\s*json\s*\n", "", text, flags=re.IGNORECASE)
    
    # 1. Try direct parsing
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
        
    # 2. Extract from markdown code blocks (```json ... ```)
    # This regex handles ```json { ... } ``` and ``` { ... } ```
    match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(1))
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass
            
    # 3. Decode the first valid JSON object from any "{" position.
    decoder = json.JSONDecoder()
    for match in re.finditer(r"\{", text):
        start = match.start()
        try:
            data, _ = decoder.raw_decode(text[start:])
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            continue
            
    raise ValueError("No valid JSON found in response")


def extract_tool_call_query(text: str, tool_name: str = "web_search") -> str | None:
    """
    Extract a query parameter from XML-like tool call blocks, e.g.:
    <invoke name="web_search"><parameter name="query">...</parameter></invoke>
    """
    if not text:
        return None

    pattern = (
        rf"<invoke\s+name=[\"']{re.escape(tool_name)}[\"'][^>]*>"
        rf"[\s\S]*?<parameter\s+name=[\"']query[\"'][^>]*>([\s\S]*?)</parameter>"
        rf"[\s\S]*?</invoke>"
    )
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return None
    query = (match.group(1) or "").strip()
    return query or None
