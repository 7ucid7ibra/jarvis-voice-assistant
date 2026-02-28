# Jarvis Voice Assistant

A fully local, "Jarvis-style" voice assistant for macOS with a modern PyQt6 GUI. All processing happens on your machine - no cloud services required.

**🌐 Website:** [https://jarvis-home-ai.netlify.app/](https://jarvis-home-ai.netlify.app/)

## Features

- 🎤 **Push-to-talk voice input** with visual feedback
- 🧠 **Local LLM** powered by Ollama (qwen2.5:0.5b)
- 🗣️ **Speech-to-Text** using Faster-Whisper (base model by default)
- **Text-to-Speech** using Piper (preferred) with macOS system voice fallback
- 💬 **Conversation history** with persistent storage
- 🎨 **Modern dark UI** with animated mic button and chat bubbles
- **Configurable settings** for model selection and TTS rate

## Requirements

- macOS Sequoia 15.x (tested on 2019 Intel MacBook Pro)
- Python 3.11 (recommended)
- 8GB+ RAM
- Homebrew (for dependencies)

## Installation

### Install from DMG (Recommended for users)

1. Download the latest `.dmg` from Releases.
2. Open the DMG.
3. Drag `Jarvis Assistant.app` to `Applications`.
4. Launch from `Applications`.

If macOS blocks launch because the app is unsigned, run:

```bash
xattr -dr com.apple.quarantine "/Applications/Jarvis Assistant.app"
```

### Prerequisites

Homebrew is required for system dependencies. Ollama is installed automatically if missing.

#### Install Homebrew (if not already installed):
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### Quick Start (From source)

1. Clone or download the repository.
2. Run the setup and launcher script:

```bash
./scripts/start.sh
```

The script will automatically:
1. Install system dependencies (portaudio, ffmpeg, Ollama if needed)
2. Set up Python virtual environment
3. Install Python dependencies
4. Start Ollama (if not already running)
5. Pull the required Ollama model
6. Launch the application

That's it! The app will open with a GUI.

### Release Prerequisites (Maintainers)

When packaging a release DMG:
1. Use Python 3.11+.
2. Verify before building:

```bash
python --version
```

3. Build with:

```bash
./scripts/build_release_dmg.sh v1.0.6 x86_64   # Intel host
./scripts/build_release_dmg.sh v1.0.6 arm64    # Apple Silicon host
```

## Usage

1. **Start the app**: Run `./scripts/start.sh`
2. **Talk**: Click the circular mic button to start recording
3. **Stop**: Click again to stop and process your speech
4. **Listen**: The assistant will respond with voice and text
5. **Settings**: Click the settings button to change models or TTS settings
6. **Close**: Click the close button to exit

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

Settings can be changed via the GUI settings dialog and are persisted to:
- `~/Library/Application Support/Jarvis Assistant/settings.json`

Sensitive values (`ha_token`, `api_key`, `telegram_bot_token`, `telegram_chat_id`) are stored in macOS Keychain and are removed from `settings.json`.
Environment variables still override stored secrets.

### Intelligence Provider Notes

- **Ollama endpoint is configurable** in Settings -> Intelligence as a base URL (example: `http://100.74.176.49:11434`).
- You can click **Test Connection** to verify reachability and refresh model discovery from that endpoint.
- Ollama-specific endpoint controls are shown **only when provider is set to `ollama`**.
- For `opencode`, the model list is intentionally restricted to **`big-pickle`**.

### Recent Runtime Updates

- Progress acknowledgements (e.g., "let me think" / "working on it") are now anchored to voice recording stop, so the 2.5s timer includes transcription time.
- Wake-word settings now apply immediately after pressing **Save Changes** (no extra mic-button press required).
- Model downloads support concurrent progress rows in Settings -> Intelligence (one progress bar per active model download).
- Quick Commands authoring is available in Settings -> Speech and uses manual phrase input (comma-separated) without hidden phrase expansion.

## Project Structure

```
Jarvis/
├── scripts/
│   ├── start.sh                # Source launcher script
│   └── build_release_dmg.sh    # DMG build helper
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
- **faster-whisper**: Speech recognition
- **piper-tts**: High-quality local text-to-speech
- **pyttsx3**: Non-macOS fallback text-to-speech
- **requests**: HTTP client for Ollama API
- **keyring**: Secure secret storage via macOS Keychain

## Verification

Run from project root:

```bash
python -m py_compile jarvis_assistant/*.py
```

Manual secret-storage check:
1. Enter HA/API/Telegram credentials in the Settings dialog and save.
2. Restart the app and confirm credentials are still available.
3. Open `~/Library/Application Support/Jarvis Assistant/settings.json` and confirm secret keys are absent.

## Performance

On a 2019 Intel MacBook Pro (8-core i9, 16GB RAM):
- **STT (Whisper base)**: ~2-3 seconds for 5-second audio
- **LLM (qwen2.5:0.5b)**: ~1-2 seconds for short responses
- **TTS**: Real-time playback

## Privacy

All processing happens locally on your machine. No data is sent to external servers. Conversation history, memory, logs, and TTS models are stored under:

- `~/Library/Application Support/Jarvis Assistant/`

## License

See `LICENSE`.
