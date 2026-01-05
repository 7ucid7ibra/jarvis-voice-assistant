import pyttsx3
import sys
try:
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')
    if not voices:
        print("No voices found")
    for v in voices:
        print(f"Name: {v.name}, ID: {v.id}")
except Exception as e:
    print(f"Error: {e}")
