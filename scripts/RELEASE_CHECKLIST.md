# Release Checklist

1. Verify builder Python version is 3.11+:
   - `python --version`
2. Build Intel artifact on Intel host:
   - `./scripts/build_release_dmg.sh v1.0.6 x86_64`
3. Build Apple Silicon artifact on Apple Silicon host:
   - `./scripts/build_release_dmg.sh v1.0.6 arm64`
4. Sanity-test each app after install:
   - Drag app to `/Applications`
   - `xattr -dr com.apple.quarantine "/Applications/Jarvis Assistant.app"`
   - Launch once from Terminal and ensure no immediate traceback
5. Publish release `v1.0.6` with both assets:
   - `Jarvis-Assistant-v1.0.6-x86_64.dmg`
   - `Jarvis-Assistant-v1.0.6-arm64.dmg`
