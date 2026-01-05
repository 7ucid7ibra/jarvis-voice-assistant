import pyttsx3
import sys
import logging
logging.basicConfig(level=logging.DEBUG)
try:
    print("Initializing engine...")
    engine = pyttsx3.init()
    print("Getting voices...")
    voices = engine.getProperty('voices')
    print(f"Found {len(voices)} voices")
    for v in voices:
        print(f"Name: {v.name}, ID: {v.id}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
