import pyttsx3
import sys

try:
    print("Initializing engine...")
    engine = pyttsx3.init()
    print("Getting voices property...")
    # This might hang if there's a driver issue
    voices = engine.getProperty('voices')
    print(f"Voices type: {type(voices)}")
    if voices:
        print(f"First voice: {voices[0]}")
except Exception as e:
    print(f"Error: {e}")
