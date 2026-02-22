import os
from typing import Dict, Tuple


def profile_file_paths(profile: str, base_dir: str = ".") -> Tuple[str, str]:
    """
    Return memory/history file paths for a profile.
    """
    memory_path = os.path.join(base_dir, "memory", f"memory_{profile}.json")
    history_path = os.path.join(base_dir, "history", f"history_{profile}.json")
    return memory_path, history_path


def remove_profile_files(profile: str, base_dir: str = ".") -> Dict[str, bool]:
    """
    Delete profile memory/history files if they exist.
    """
    memory_path, history_path = profile_file_paths(profile, base_dir=base_dir)
    removed_memory = False
    removed_history = False
    if os.path.exists(memory_path):
        os.remove(memory_path)
        removed_memory = True
    if os.path.exists(history_path):
        os.remove(history_path)
        removed_history = True
    return {"removed_memory": removed_memory, "removed_history": removed_history}
