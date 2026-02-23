from __future__ import annotations

import logging
import os
import shutil
import sys
import tempfile
from pathlib import Path

APP_NAME = "Jarvis Assistant"
MIGRATION_MARKER = ".data_migration_v1_done"


def _path_logger() -> logging.Logger:
    return logging.getLogger("JarvisPaths")


def _default_data_root() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME
    return Path.home() / ".jarvis_assistant"


def _safe_ensure_dir(path: Path) -> Path:
    try:
        path.mkdir(parents=True, exist_ok=True)
        return path
    except Exception as exc:
        fallback = Path(tempfile.gettempdir()) / "jarvis_assistant_data"
        try:
            fallback.mkdir(parents=True, exist_ok=True)
            _path_logger().warning(
                f"Falling back to writable temp dir because '{path}' was unavailable: {exc}"
            )
            return fallback
        except Exception:
            _path_logger().warning(
                f"Could not create '{path}' or fallback '{fallback}'. Continuing without guaranteed writable storage."
            )
            return path


def data_root() -> str:
    override = os.environ.get("JARVIS_DATA_DIR", "").strip()
    root = Path(override).expanduser() if override else _default_data_root()
    return str(_safe_ensure_dir(root))


def settings_file() -> str:
    override = os.environ.get("JARVIS_SETTINGS_FILE", "").strip()
    if override:
        target = Path(override).expanduser()
        if target.parent:
            _safe_ensure_dir(target.parent)
        return str(target)
    target = Path(data_root()) / "settings.json"
    _safe_ensure_dir(target.parent)
    return str(target)


def history_dir() -> str:
    return str(_safe_ensure_dir(Path(data_root()) / "history"))


def memory_dir() -> str:
    return str(_safe_ensure_dir(Path(data_root()) / "memory"))


def models_dir() -> str:
    return str(_safe_ensure_dir(Path(data_root()) / "models"))


def logs_dir() -> str:
    return str(_safe_ensure_dir(Path(data_root()) / "logs"))


def profiles_history_file(profile: str) -> str:
    safe_profile = (profile or "default").strip() or "default"
    return str(Path(history_dir()) / f"history_{safe_profile}.json")


def profiles_memory_file(profile: str) -> str:
    safe_profile = (profile or "default").strip() or "default"
    return str(Path(memory_dir()) / f"memory_{safe_profile}.json")


def _copy_file_if_missing(source: Path, destination: Path) -> tuple[bool, bool]:
    if not source.exists() or not source.is_file():
        return False, False
    if destination.exists():
        return False, True
    try:
        _safe_ensure_dir(destination.parent)
        shutil.copy2(source, destination)
        return True, False
    except Exception as exc:
        _path_logger().warning(f"Failed to migrate file '{source}' -> '{destination}': {exc}")
        return False, False


def _copy_tree_no_overwrite(source_root: Path, destination_root: Path) -> tuple[int, int]:
    if not source_root.exists() or not source_root.is_dir():
        return 0, 0

    copied = 0
    skipped = 0
    for source in source_root.rglob("*"):
        if not source.is_file():
            continue
        relative = source.relative_to(source_root)
        destination = destination_root / relative
        if destination.exists():
            skipped += 1
            continue
        try:
            _safe_ensure_dir(destination.parent)
            shutil.copy2(source, destination)
            copied += 1
        except Exception as exc:
            _path_logger().warning(
                f"Failed to migrate path '{source}' -> '{destination}': {exc}"
            )
    return copied, skipped


def _legacy_candidate_roots() -> list[Path]:
    roots: list[Path] = []
    candidates = [
        Path.cwd(),
        Path(__file__).resolve().parents[1],
        Path(sys.argv[0]).resolve().parent if sys.argv and sys.argv[0] else None,
    ]
    for candidate in candidates:
        if candidate is None:
            continue
        try:
            resolved = candidate.resolve()
        except Exception:
            continue
        if resolved.exists() and resolved.is_dir() and resolved not in roots:
            roots.append(resolved)
    return roots


def migrate_legacy_data_once() -> None:
    root = Path(data_root())
    marker = root / MIGRATION_MARKER
    if marker.exists():
        return

    logger = _path_logger()
    copied_count = 0
    skipped_count = 0

    target_settings = Path(settings_file())
    target_history = Path(history_dir())
    target_memory = Path(memory_dir())
    target_tts_models = Path(models_dir()) / "tts"

    for source_root in _legacy_candidate_roots():
        try:
            if source_root.resolve() == root.resolve():
                continue
        except Exception:
            pass

        copied, skipped = _copy_file_if_missing(source_root / "settings.json", target_settings)
        copied_count += int(copied)
        skipped_count += int(skipped)

        c, s = _copy_tree_no_overwrite(source_root / "history", target_history)
        copied_count += c
        skipped_count += s

        c, s = _copy_tree_no_overwrite(source_root / "memory", target_memory)
        copied_count += c
        skipped_count += s

        c, s = _copy_tree_no_overwrite(source_root / "models" / "tts", target_tts_models)
        copied_count += c
        skipped_count += s

    try:
        marker.write_text("done\n", encoding="utf-8")
    except Exception as exc:
        logger.warning(f"Failed to write migration marker '{marker}': {exc}")

    if copied_count or skipped_count:
        logger.info(
            f"Legacy data migration finished: copied={copied_count}, skipped_existing={skipped_count}"
        )
