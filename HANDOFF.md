# Jarvis Voice Assistant - Handoff Documentation

## Current Status: STABLE - Multi-Agent Working (v0.1.26)

**Version**: v0.1.26
**Architecture**: Multi-Agent (Intent -> Action -> Response)
**Status**: Fully functional. The previous refactor issues have been resolved.

**Key Achievements**:
- ✅ Multi-agent state machine working correctly in `main.py`.
- ✅ Signal flow fixed (no more infinite loading).
- ✅ Wake word functionality removed (was causing instability).
- ✅ "Broken pipe" Ollama error documented and solvable.

---

## Next Steps for Next AI

1.  **Refine Response Latency**: The multi-agent chain adds latency. Consider optimizing prompts or parallelizing where possible.
2.  **Re-implement Wake Word**: If desired, re-introduce wake word detection using a dedicated, isolated thread that doesn't interfere with the main loop.
3.  **Error Handling**: Improve UI feedback for network errors or Ollama crashes.

---

## Project Overview

A voice-controlled assistant for macOS that integrates with Home Assistant to control smart home devices.

### Tech Stack
- **STT**: OpenAI Whisper (local)
- **LLM**: Ollama (qwen2.5:0.5b)
- **TTS**: pyttsx3
- **GUI**: PyQt6
- **Home Assistant**: REST API integration

### Key Files
- `main.py`: Main controller (currently broken)
- `agents.py`: Multi-agent system (newly created, not integrated)
- `llm_client.py`: Ollama API client (refactored)
- `conversation.py`: Chat history management
- `gui.py`: PyQt6 UI
- `stt.py`: Whisper STT worker
- `tts.py`: Text-to-speech worker
- `ha_client.py`: Home Assistant API client
- `config.py`: Configuration management

---

## What Worked (Before Multi-Agent Refactor)

### ✅ Successful Features (v0.1.19)
1. **Voice Input/Output**: Whisper STT + pyttsx3 TTS working
2. **Home Assistant Integration**: Can control `input_boolean.test_schalter`
3. **Settings UI**: Language, HA URL, HA Token configurable
4. **Language Detection**: Auto/English/German selection
5. **JSON Output**: LLM generates structured JSON for actions

### ✅ Git Workflow
- All commits tagged (v0.1.14 → v0.1.24)
- Branch: `v0.1`

---

## What Didn't Work

### ❌ Multi-Agent Architecture (v0.1.20 → v0.1.24)
**Goal**: Split LLM responsibilities into 3 agents:
1. **Intent Agent**: Classify intent, resolve context ("it" → "switch")
2. **Action Agent**: Generate HA JSON commands
3. **Response Agent**: Generate natural language replies

**What Went Wrong**:
1. **Incomplete Refactor**: I removed old methods (`generate_reply`, `handle_llm_finished`) but didn't properly replace them.
2. **Invalid References**: Left references to non-existent `wake_word_stt`, `wake_word_worker`, etc.
3. **Missing Methods**: `toggle_listening` method exists in `main.py` but the connection is broken.
4. **Signal Mismatches**: Changed `llm_worker.finished` to connect to `handle_llm_response` but didn't verify all connections.

### Current Errors (v0.1.24)
```
AttributeError: 'JarvisController' object has no attribute 'toggle_listening'
```

---

## Root Cause Analysis

### The Problem
The 0.5B model (`qwen2.5:0.5b`) is too small and unreliable:
- **Context Loss**: Can't resolve "it" → "test_switch"
- **Invalid JSON**: Sometimes omits `entity_id` or `ha_actions`
- **Incoherent Replies**: Copies placeholder text from prompts
- **Language Mixing**: Ignores language settings

### User's Request
Implement a multi-agent system to help the small model by:
- Splitting responsibilities across 3 sequential agents
- Each agent has a focused, simple task
- Reducing conversation history to 5-10 messages

---

## Recommended Next Steps

### Option 1: Rollback and Fix (RECOMMENDED)
1. **Rollback to v0.1.19**:
   ```bash
   git checkout v0.1.19
   ```
2. **Fix the Core Issues**:
   - Reduce conversation history to 5-10 messages in `conversation.py`
   - Improve prompt examples (already done in v0.1.19)
   - Add simple keyword detection for "it", "that" → last mentioned device
3. **Test Thoroughly** before attempting multi-agent again

### Option 2: Fix Current Broken State
1. **View `main.py` lines 240-280** to see the `toggle_listening` method
2. **Fix Signal Connections**:
   - Ensure `self.window.mic_btn.clicked` connects to existing method
   - Ensure `self.llm_worker.finished` connects to existing handler
   - Remove all references to `wake_word_stt`, `wake_word_worker`
3. **Fix Missing Connections**:
   - `self.audio_recorder.audio_ready` → `self.stt_worker.transcribe`
   - `self.stt_worker.finished` → `self.handle_stt_finished`
   - `self.tts_worker.started/finished` → handlers
4. **Test** after each fix

### Option 3: Upgrade Model (Simplest)
- Switch to `qwen2.5:3b` or `llama3.2:3b`
- Larger models handle context better
- No code changes needed
- Trade-off: Slower, more RAM

---

## Key Configuration

### Home Assistant
- **URL**: `http://192.168.188.126:8123`
- **Token**: (stored in `settings.json`)
- **Test Device**: `input_boolean.test_schalter`

### Settings Location
- `settings.json` (in project root)
- Environment variables: `HA_URL`, `HA_TOKEN`

### Language Settings
- Auto / English / German
- Configured in Settings UI (⚙ icon)

---

## Known Issues

1. **LLM Refusals**: Fixed in v0.1.18 by strengthening prompt
2. **Missing `entity_id`**: Small model sometimes omits it
3. **Context Loss**: "Turn it off" doesn't work reliably
4. **Incoherent Replies**: Model copies placeholder text

---

## Testing Checklist

After any fix, test these scenarios:
1. ✅ App starts without errors
2. ✅ "Turn on the test switch" → Switch turns on
3. ✅ "Turn it off again" → Switch turns off (context test)
4. ✅ Language enforcement (set German, speak English → reply in German)
5. ✅ General chat: "Who are you?" → Natural reply

---

## Troubleshooting

### Ollama "Broken Pipe" / 500 Error
If you see `HTTP Error: 500 ... signal: broken pipe`, it means Ollama has crashed.
Fix it by restarting Ollama:
```bash
pkill ollama
ollama serve > ollama.log 2>&1 &
```

## Git Tags Reference

- `v0.1.14`: Initial HA integration
- `v0.1.15`: Added language settings
- `v0.1.16`: Settings UI
- `v0.1.17`: Bug fixes
- `v0.1.18`: Strengthened prompt
- `v0.1.19`: **LAST WORKING VERSION**
- `v0.1.20`: Added `agents.py`
- `v0.1.21`: Refactored `llm_client.py`
- `v0.1.22`: Implemented multi-agent orchestration (broken)
- `v0.1.23`: Indentation fix
- `v0.1.24`: Current (broken)

---

## Apologies and Lessons Learned

I made critical mistakes:
1. **Didn't test incrementally** - should have run the app after each change
2. **Incomplete refactor** - removed old code without fully replacing it
3. **Assumed methods existed** - hallucinated `WakeWordWorker` from previous context
4. **Didn't verify connections** - changed signal names without checking handlers

**For Next AI**: Please test after EVERY change. Run `bash scripts/start.sh` to verify the app starts before making the next edit.
