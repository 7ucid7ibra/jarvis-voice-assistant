import pyttsx3
import sys

def onStart(name):
    print('starting', name)

def onWord(name, location, length):
    print('word', name, location, length)

def onEnd(name, completed):
    print('finishing', name, completed)

try:
    print("Pre-init")
    engine = pyttsx3.init()
    print("Post-init")
    engine.connect('started-utterance', onStart)
    engine.connect('started-word', onWord)
    engine.connect('finished-utterance', onEnd)
    
    voices = engine.getProperty('voices')
    print(f"Voices found: {len(voices)}")
    for voice in voices:
        print(f" - {voice.name} ({voice.id})")
    
    print("Setting voice...")
    if voices:
        engine.setProperty('voice', voices[0].id)
    
    print("Testing speak...")
    engine.say('The quick brown fox jumped over the lazy dog.')
    engine.runAndWait()
    print("Done")
except Exception as e:
    print(f"Exception: {e}")
