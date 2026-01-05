import pyttsx3
import sys
import os

# Try to find where pyttsx3 is
try:
    import pyttsx3
    print(f"pyttsx3 location: {pyttsx3.__file__}")
except Exception as e:
    print(f"Import error: {e}")

try:
    print("Initializing engine...")
    # Add a timeout or just try simple init
    engine = pyttsx3.init()
    print("Getting voices...")
    # Only get 1 property to check
    rate = engine.getProperty('rate')
    print(f"Current rate: {rate}")
    voices = engine.getProperty('voices')
    print(f"Found {len(voices)} voices")
    for v in voices:
        print(f"Name: {v.name}, ID: {v.id}")
except Exception as e:
    print(f"Error: {e}")
