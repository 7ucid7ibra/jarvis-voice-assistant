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
    
    # 1. Try direct parsing
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
        
    # 2. Extract from markdown code blocks (```json ... ```)
    # This regex handles ```json { ... } ``` and ``` { ... } ```
    match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
            
    # 3. Last resort: Find the first outermost curly braces
    # This assumes the JSON object is reasonably well-formed starting with {
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
            
    raise ValueError("No valid JSON found in response")
