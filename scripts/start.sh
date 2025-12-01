#!/usr/bin/env bash
set -e

# Configuration
OLLAMA_MODEL="qwen2.5:0.5b"

echo "=== Jarvis Assistant Launcher ==="

# 1. Check for Homebrew
if ! command -v brew &> /dev/null; then
    echo "Error: Homebrew is required. Install it from https://brew.sh and rerun ./start.sh"
    exit 1
fi

# 2. Install system dependencies
echo "Checking system dependencies..."
brew install portaudio ffmpeg || true

# 3. Check for Ollama
if ! command -v ollama &> /dev/null; then
    echo "Ollama not found. Installing..."
    curl -fsSL https://ollama.com/install.sh | sh
else
    echo "Ollama is installed."
fi

# Ensure Ollama is running (naive check, just try to start it or assume it's a service)
# On macOS, Ollama is usually an app. We can try to start the serve mode in background if not running.
if ! pgrep -x "ollama" > /dev/null; then
    echo "Starting Ollama..."
    ollama serve &
    sleep 5
fi

# 4. Python Environment
echo "Setting up Python environment..."

# Find a compatible Python version (prefer 3.11, then 3.10, 3.12)
if command -v python3.11 &> /dev/null; then
    PYTHON_CMD="python3.11"
elif command -v python3.10 &> /dev/null; then
    PYTHON_CMD="python3.10"
elif command -v python3.12 &> /dev/null; then
    PYTHON_CMD="python3.12"
else
    PYTHON_CMD="python3"
fi

echo "Using Python: $PYTHON_CMD"
$PYTHON_CMD --version

# Check if we need to recreate venv (simple check: if .venv exists but python version differs)
# For robustness, we'll just remove it if it exists and we are running this script, 
# or we can trust the user. But since we had a 3.13 failure, let's be safe.
if [ -d ".venv" ]; then
    # Check if the existing venv is the same version
    VENV_VER=$(.venv/bin/python --version 2>&1 | awk '{print $2}')
    TARGET_VER=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
    
    # If major.minor differs, recreate
    # (Simplified logic: just recreate if 3.13 is detected or if we want to enforce 3.11)
    if [[ "$VENV_VER" != "$TARGET_VER" ]]; then
        echo "Recreating virtual environment (Found $VENV_VER, switching to $TARGET_VER)..."
        rm -rf .venv
    fi
fi

if [ ! -d ".venv" ]; then
    $PYTHON_CMD -m venv .venv
fi
source .venv/bin/activate

# 5. Install Python dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# 6. Ensure Ollama model exists
echo "Checking Ollama model: $OLLAMA_MODEL"
if ! ollama list | grep -q "$OLLAMA_MODEL"; then
    echo "Pulling model $OLLAMA_MODEL..."
    ollama pull "$OLLAMA_MODEL"
fi

# 7. Run the GUI
echo "Starting Jarvis..."
python -m jarvis_assistant.main
