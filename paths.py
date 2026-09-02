import getpass
import os
import re
from pathlib import Path

DATA_DIR = Path("data")
DEFAULT_USER = "default"
_UNSAFE_CHARS = re.compile(r"[^A-Za-z0-9_-]+")


def resolve_user(explicit_user=None):
    if explicit_user:
        return explicit_user
    return os.environ.get("FITNESS_AGENT_USER") or getpass.getuser()


def sanitize_user(user):
    safe = _UNSAFE_CHARS.sub("_", user or "").strip("_")
    return safe or DEFAULT_USER


def profile_path(user):
    return DATA_DIR / sanitize_user(user) / "user_profile.json"


def history_path(user):
    return DATA_DIR / sanitize_user(user) / "workout_history.json"
