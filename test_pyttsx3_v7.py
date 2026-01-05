import pyttsx3
import sys

try:
    print("Start")
    engine = pyttsx3.init()
    print("Engine init")
    # Instead of voices, try rate
    rate = engine.getProperty('rate')
    print(f"Rate: {rate}")
    print("End")
except Exception as e:
    print(f"Error: {e}")
