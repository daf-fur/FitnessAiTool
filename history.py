import json
from datetime import datetime, timezone
from pathlib import Path

import wger_client

DEFAULT_HISTORY_FILE = Path("workout_history.json")


def _read_history(history_file):
    if not history_file.exists():
        return []
    try:
        return json.loads(history_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def log_last_workout(notes=None, history_file=DEFAULT_HISTORY_FILE):
    if wger_client._last_plan is None:
        return {"error": "No workout plan has been built yet."}

    entry = {
        "logged_at": datetime.now(timezone.utc).isoformat(),
        "plan": wger_client._last_plan,
        "notes": notes,
    }

    history = _read_history(history_file)
    history.append(entry)
    try:
        history_file.parent.mkdir(parents=True, exist_ok=True)
        history_file.write_text(json.dumps(history, indent=2), encoding="utf-8")
    except OSError as error:
        return {"error": f"Failed to save workout history: {error}"}

    return entry


def get_workout_history(limit=5, history_file=DEFAULT_HISTORY_FILE):
    history = _read_history(history_file)
    if limit:
        history = history[-limit:]
    return history


def get_exercise_progress(exercise_name, history_file=DEFAULT_HISTORY_FILE):
    """Return how many times an exercise has been logged before."""
    history = _read_history(history_file)
    times_logged = 0
    for entry in history:
        for muscle_entry in entry.get("plan", []):
            for exercise in muscle_entry.get("exercises", []):
                if exercise.get("name") == exercise_name:
                    times_logged += 1
    return times_logged
