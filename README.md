# Jarvis Voice Assistant

A fully local, "Jarvis-style" voice assistant for macOS with a modern PyQt6 GUI. All processing happens on your machine - no cloud services required.

**🌐 Website:** [https://jarvis-home-ai.netlify.app/](https://jarvis-home-ai.netlify.app/)

## Features

- 🎤 **Push-to-talk voice input** with visual feedback
- 🧠 **Local LLM** powered by Ollama (qwen2.5:0.5b)
- 🗣️ **Speech-to-Text** using OpenAI Whisper (base model)
- 🔊 **Text-to-Speech** using macOS system voices
- 💬 **Conversation history** with persistent storage
- 🎨 **Modern dark UI** with animated mic button and chat bubbles
- ⚙️ **Configurable settings** for model selection and TTS rate

## Requirements

- macOS Sequoia 15.x (tested on 2019 Intel MacBook Pro)
- Python 3.11 (recommended)
- 8GB+ RAM
- Homebrew (for dependencies)

## Installation

### Prerequisites

**Ollama** must be installed separately for the AI functionality:

#### Install Homebrew (if not already installed):
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

#### Install Ollama:
```bash
brew install ollama
```

### Install Jarvis

Simply run the launcher script:

```bash
./scripts/start.sh
```

The script will automatically:
1. Install system dependencies (portaudio, ffmpeg)
2. Set up Python virtual environment
3. Install Python dependencies
4. Start Ollama (if not already running)
5. Pull the required Ollama model
6. Launch the application

## Usage

1. **Start the app**: Run `./scripts/start.sh`
2. **Talk**: Click the circular mic button to start recording
3. **Stop**: Click again to stop and process your speech
4. **Listen**: The assistant will respond with voice and text
5. **Settings**: Click the ⚙ icon to change models or TTS settings
6. **Close**: Click the ✕ icon to exit

### Mic Button States

- **Idle** (cyan, slow pulse): Ready to listen
- **Listening** (bright cyan, fast pulse): Recording your voice
- **Thinking** (spinning): Processing your request
- **Speaking** (pulsing): Playing response

## Configuration

Default settings are stored in `jarvis_assistant/config.py`:

- **Whisper Model**: `base` (can be: tiny, base, small, medium, large)
- **Ollama Model**: `qwen2.5:0.5b` (fast, lightweight)
- **TTS Rate**: 190 words/minute
- **TTS Volume**: 1.0 (max)

Settings can be changed via the GUI settings dialog and are persisted to `settings.json`.

## Project Structure

```
VoiceAssistantMac/
├── scripts/
│   └── start.sh                # Launcher script
├── docs/
│   ├── git_workflow.md         # Git workflow rules
│   └── HANDOFF.md              # Project handoff document
├── requirements.txt            # Python dependencies
├── README.md                   # This file
└── jarvis_assistant/
    ├── __init__.py
    ├── main.py                 # Application entry point
    ├── config.py               # Configuration and settings
    ├── gui.py                  # PyQt6 GUI components
    ├── audio_io.py             # Microphone recording
    ├── stt.py                  # Speech-to-Text (Whisper)
    ├── llm_client.py           # LLM client (Ollama)
    ├── tts.py                  # Text-to-Speech (pyttsx3)
    ├── conversation.py         # Conversation history management
    └── utils.py                # Logging utilities
```

## Troubleshooting

### Model Crashes

If you encounter "llama runner process has terminated: signal: broken pipe", the Ollama model may be incompatible with your hardware. The app is configured to use `qwen2.5:0.5b` which works on Intel Macs. You can try other models via the settings dialog.

### Font Warning

The warning `Populating font family aliases took 219 ms. Replace uses of missing font family "Segoe UI"` is harmless. The app will use system default fonts.

### Ollama Not Starting

If Ollama fails to start automatically, you can start it manually:

```bash
ollama serve
```

Then run `./scripts/start.sh` again.

## Dependencies

### System
- **portaudio**: Audio I/O library
- **ffmpeg**: Audio processing
- **Ollama**: Local LLM runtime

### Python
- **PyQt6**: GUI framework
- **sounddevice**: Audio recording
- **numpy**: Numerical operations
- **openai-whisper**: Speech recognition
- **pyttsx3**: Text-to-speech
- **requests**: HTTP client for Ollama API

## Performance

On a 2019 Intel MacBook Pro (8-core i9, 16GB RAM):
- **STT (Whisper base)**: ~2-3 seconds for 5-second audio
- **LLM (qwen2.5:0.5b)**: ~1-2 seconds for short responses
- **TTS**: Real-time playback

## Privacy

All processing happens locally on your machine. No data is sent to external servers. Conversation history is stored in `conversation_history.json` in the project directory.

## License

This is a prototype project. Use at your own discretion.
