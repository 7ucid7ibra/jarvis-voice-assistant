# Project Handoff: Jarvis Voice Assistant

**Date**: 2025-12-01  
**Current Version**: v0.1.6  
**Branch**: v0.1  
**Status**: ✅ Fully Functional

---

## Project Overview

A fully local, "Jarvis-style" voice assistant for macOS with PyQt6 GUI. All processing happens locally - no cloud services.

**Tech Stack**:
- **GUI**: PyQt6 (frameless dark theme with animations)
- **STT**: OpenAI Whisper (CPU-based, configurable model)
- **LLM**: Ollama (local inference, default: qwen2.5:0.5b)
- **TTS**: pyttsx3 (macOS system voices)
- **Audio**: sounddevice + numpy

**Target Platform**: macOS Sequoia 15.x (tested on 2019 Intel MacBook Pro, 8-core i9, 16GB RAM)

---

## Current Features (v0.1.6)

### Core Functionality
- ✅ Push-to-talk voice input (click or 'M' key)
- ✅ Speech-to-Text via Whisper
- ✅ LLM conversation via Ollama
- ✅ Text-to-Speech playback
- ✅ Persistent conversation history
- ✅ Settings dialog (models, TTS rate, wake word)

### UI Features
- ✅ Frameless window with drag support
- ✅ Animated mic button (4 states: idle, listening, thinking, speaking)
- ✅ Chat bubbles for conversation display
- ✅ Status line showing current state
- ✅ Close button
- ✅ Settings button

### Advanced Features
- ✅ **Wake word detection** (continuous background listening)
- ✅ **Keyboard shortcut** ('M' key)
- ✅ **Stop TTS** by clicking mic button during playback
- ✅ **Configurable settings** with persistence

---

## Project Structure

```
VoiceAssistantMac/
├── start.sh                    # macOS launcher (bash)
├── requirements.txt            # Python dependencies
├── README.md                   # User documentation
├── git_workflow.md            # Git workflow rules
├── HANDOFF.md                 # This file
└── jarvis_assistant/
    ├── __init__.py
    ├── main.py                # Entry point, JarvisController
    ├── config.py              # Settings management
    ├── gui.py                 # PyQt6 UI components
    ├── audio_io.py            # Microphone recording
    ├── stt.py                 # Whisper STT worker
    ├── llm_client.py          # Ollama API client
    ├── tts.py                 # pyttsx3 TTS worker
    ├── conversation.py        # Message history
    └── utils.py               # Logging utilities
```

---

## Git Workflow

**Branch Structure**:
- `master`: v0.0 baseline (initial commit)
- `v0.1`: Current development branch

**Tagging**:
- v0.0: Initial working application
- v0.1.1: Git workflow documentation
- v0.1.2: TTS stop functionality
- v0.1.3: Fix mic button state handling
- v0.1.4: Keyboard shortcut ('M')
- v0.1.5: Wake word settings UI
- v0.1.6: Wake word detection implementation

**Workflow Rules** (see `git_workflow.md`):
1. All changes on `v0.1` branch
2. Commit after each logical change
3. Tag each commit incrementally (v0.1.x)
4. Comprehensive commit messages

---

## Recent Changes (v0.1.6)

### Wake Word Detection
- Added continuous background listening (3-second audio chunks)
- Separate STT worker for wake word detection (no interference)
- Configurable wake word (default: "jarvis")
- Auto-starts recording when wake word detected
- Restarts background listening after each interaction

### Implementation Details
- `AudioRecorder.start_wake_word_listening()`: Continuous capture
- `AudioRecorder.wake_word_chunk` signal: Emits audio chunks
- `JarvisController.wake_word_stt`: Dedicated STT worker
- `JarvisController.handle_wake_word_detected()`: Text matching logic

---

## Known Issues & Limitations

### Current Issues
1. **Windows Compatibility**: `start.sh` is macOS-only (uses bash, brew, macOS commands)
2. **Ollama Model Crashes**: `phi3.5` crashes on Intel Macs → using `qwen2.5:0.5b` instead
3. **Font Warning**: "Segoe UI" missing warning (harmless, uses system default)
4. **Large Model Performance**: Whisper "large" model (2.9GB) is very slow on CPU

### Design Limitations
- **macOS Only**: Uses `pyttsx3` with macOS voices, `pyobjc` frameworks
- **CPU-bound**: Whisper runs on CPU (no GPU acceleration)
- **Single User**: No multi-user support
- **Local Only**: No cloud sync or remote access

---

## Configuration

### Default Settings (`config.py`)
```python
DEFAULT_WHISPER_MODEL = "base"           # Recommended for Intel Macs
DEFAULT_OLLAMA_MODEL = "qwen2.5:0.5b"   # Fast, stable model
DEFAULT_TTS_RATE = 190                   # Words per minute
DEFAULT_WAKE_WORD_ENABLED = False
DEFAULT_WAKE_WORD = "jarvis"
```

### User Settings (`settings.json`)
Persisted settings:
- `whisper_model`: STT model size
- `ollama_model`: LLM model name
- `tts_rate`: Speech speed
- `wake_word_enabled`: Boolean
- `wake_word`: Custom wake word text

---

## Architecture

### Threading Model
- **Main Thread**: PyQt6 GUI event loop
- **STT Thread**: Whisper transcription (user input)
- **Wake Word STT Thread**: Whisper transcription (background chunks)
- **LLM Thread**: Ollama API requests
- **TTS Thread**: pyttsx3 speech synthesis

### Signal/Slot Connections
```
User Input Flow:
Mic Click → start_recording() → finished signal → 
handle_recording_finished() → request_stt signal → 
STTWorker.transcribe() → finished signal → 
handle_stt_finished() → request_llm signal → 
LLMWorker.generate_reply() → finished signal → 
handle_llm_finished() → request_tts signal → 
TTSWorker.speak() → finished signal → 
handle_tts_finished() → IDLE state

Wake Word Flow:
wake_word_chunk signal (every 3s) → 
wake_word_stt.transcribe() → finished signal → 
handle_wake_word_detected() → check for wake word → 
if detected: start_recording()
```

### State Machine (Mic Button)
- **IDLE**: Ready to listen (cyan, slow pulse)
- **LISTENING**: Recording user input (bright cyan, fast pulse)
- **THINKING**: Processing (spinning animation)
- **SPEAKING**: Playing TTS (pulsing)

---

## Testing & Verification

### What Works
✅ Voice input recording  
✅ Whisper transcription (base model)  
✅ Ollama LLM responses (qwen2.5:0.5b)  
✅ TTS playback  
✅ Conversation history persistence  
✅ Settings persistence  
✅ Wake word detection  
✅ Keyboard shortcut ('M')  
✅ Stop TTS mid-playback  
✅ Window dragging  
✅ Close button  

### Not Tested
❌ Windows compatibility  
❌ Linux compatibility  
❌ Other Whisper models (tiny, small, medium, large)  
❌ Other Ollama models  
❌ Long conversation history (>50 messages)  
❌ Multiple wake words  
❌ Non-English languages  

---

## Dependencies

### System Requirements
- macOS Sequoia 15.x (or compatible)
- Python 3.11+ (3.13 has torch issues)
- Homebrew (for portaudio, ffmpeg, ollama)
- 8GB+ RAM
- ~5GB disk space (models + dependencies)

### Python Packages (requirements.txt)
```
PyQt6
sounddevice
numpy<2                    # Pinned for torch compatibility
git+https://github.com/openai/whisper.git
pyttsx3
requests
```

### System Packages (via brew)
- portaudio (audio I/O)
- ffmpeg (audio processing)
- ollama (LLM runtime)

---

## Next Steps / TODO

### High Priority
1. **Windows Support**: Create `start.bat` or `start.ps1` launcher
2. **Cross-platform README**: Add Windows/Linux installation instructions
3. **Model Selection**: Add UI to download/switch Whisper models
4. **Error Handling**: Better error messages for common issues

### Medium Priority
5. **Wake Word Accuracy**: Improve detection (currently simple substring match)
6. **Performance Optimization**: Profile and optimize wake word STT
7. **Settings Validation**: Validate user input in settings dialog
8. **Conversation Export**: Add ability to export chat history

### Low Priority
9. **Themes**: Add light theme option
10. **Hotkey Customization**: Let user change keyboard shortcut
11. **Multiple Wake Words**: Support multiple wake word options
12. **Voice Selection**: Let user choose TTS voice

### Nice to Have
13. **System Tray**: Minimize to system tray
14. **Auto-start**: Launch on system startup
15. **Plugins**: Plugin system for custom commands
16. **Multi-language**: Support for non-English languages

---

## Common Issues & Solutions

### Issue: Ollama model crashes with "broken pipe"
**Solution**: Switch to `qwen2.5:0.5b` model (already default)

### Issue: NumPy compatibility error
**Solution**: Already pinned to `numpy<2` in requirements.txt

### Issue: PyQt6 type errors (QPoint vs QPointF)
**Solution**: Already fixed in gui.py (using QPointF for gradients)

### Issue: Wake word not detecting
**Checklist**:
1. Is wake word enabled in settings?
2. Is Whisper model loaded? (check terminal output)
3. Is microphone working? (check system permissions)
4. Is wake word spelled correctly? (case-insensitive match)

### Issue: App won't start
**Checklist**:
1. Is Ollama running? (`ollama serve`)
2. Is model pulled? (`ollama pull qwen2.5:0.5b`)
3. Is Python 3.11? (`python3.11 --version`)
4. Are dependencies installed? (check .venv)

---

## Development Notes

### Code Style
- Type hints used where helpful
- Docstrings for public methods
- Signal/slot pattern for async operations
- QThread for long-running tasks

### Git Commit Messages
Format: `<type>: <description>`
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation
- `refactor:` Code restructuring

### Testing Approach
- Manual testing via GUI
- Terminal output for debugging
- No automated tests yet

---

## Resources

### Documentation
- [PyQt6 Docs](https://www.riverbankcomputing.com/static/Docs/PyQt6/)
- [Whisper GitHub](https://github.com/openai/whisper)
- [Ollama Docs](https://ollama.ai/docs)
- [pyttsx3 Docs](https://pyttsx3.readthedocs.io/)

### Model Info
- [Whisper Models](https://github.com/openai/whisper#available-models-and-languages)
- [Ollama Models](https://ollama.ai/library)

---

## Contact & Context

**User's Machine**: 2019 Intel MacBook Pro, 8-core i9, 16GB RAM, macOS Sequoia 15.x  
**User's Preferences**: Follows git workflow strictly, wants comprehensive commits  
**Project Goal**: Fully local voice assistant, no cloud dependencies

---

## Quick Start for Next AI

1. **Read git_workflow.md** - Understand branching/tagging rules
2. **Check current branch**: Should be on `v0.1`
3. **Review last few commits**: `git log --oneline -5`
4. **Test the app**: `./start.sh` (should work immediately)
5. **Check settings**: Open settings dialog, verify wake word config
6. **Continue from v0.1.7**: Next tag should be v0.1.7

**Current State**: App is fully functional. Wake word detection works. User may want to revert Whisper model from "large" back to "base" for better performance.

---

*End of Handoff Document*
