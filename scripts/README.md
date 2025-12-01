# Scripts

This directory contains utility scripts for the project:

- **[start.sh](start.sh)**: macOS launcher script
  - Installs system dependencies (brew)
  - Sets up Python virtual environment
  - Installs Python packages
  - Pulls Ollama model
  - Launches the application

## Usage

From the project root:
```bash
./scripts/start.sh
```

## Platform Support

Currently only macOS is supported. Windows and Linux launcher scripts are planned for future releases.
