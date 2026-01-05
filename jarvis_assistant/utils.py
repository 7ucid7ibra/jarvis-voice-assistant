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
