import pyttsx3
import sys

try:
    print("Start")
    engine = pyttsx3.init()
    print("Engine init")
    v = engine.getProperty('voices')
    print(f"Voices count: {len(v)}")
except Exception as e:
    print(f"Error: {e}")
