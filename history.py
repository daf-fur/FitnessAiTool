import json
from datetime import datetime, timezone
from pathlib import Path

import wger_client

DEFAULT_HISTORY_FILE = Path("workout_history.json")
MAX_ACTIVE_ENTRIES = 500


def _read_history(history_file):
    if not history_file.exists():
        return []
    try:
        return json.loads(history_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _write_history(history, history_file):
    try:
        history_file.parent.mkdir(parents=True, exist_ok=True)
        tmp_file = history_file.with_name(history_file.name + ".tmp")
        tmp_file.write_text(json.dumps(history, indent=2), encoding="utf-8")
        tmp_file.replace(history_file)
    except OSError as error:
        return f"Failed to save workout history: {error}"
    return None


def _archive_path(history_file):
    return history_file.with_name(history_file.stem + ".archive.json")


def _archive_overflow(history, history_file):
    """Move the oldest entries out to an archive file once the active file grows too large."""
    if len(history) <= MAX_ACTIVE_ENTRIES:
        return history

    overflow_count = len(history) - MAX_ACTIVE_ENTRIES
    overflow, active = history[:overflow_count], history[overflow_count:]

    archive_file = _archive_path(history_file)
    archive = _read_history(archive_file)
    archive.extend(overflow)

    if _write_history(archive, archive_file) is not None:
        return history

    return active


def log_last_workout(sets=None, notes=None, history_file=DEFAULT_HISTORY_FILE):
    if wger_client._last_plan is None:
        return {"error": "No workout plan has been built yet."}

    entry = {
        "logged_at": datetime.now(timezone.utc).isoformat(),
        "plan": wger_client._last_plan,
        "notes": notes,
        "sets": sets or [],
    }

    history = _read_history(history_file)
    history.append(entry)
    history = _archive_overflow(history, history_file)

    error = _write_history(history, history_file)
    if error:
        return {"error": error}

    return entry


def get_workout_history(limit=5, history_file=DEFAULT_HISTORY_FILE):
    history = _read_history(history_file)
    if limit:
        history = history[-limit:]
    return history


def _find_index(history, logged_at):
    if logged_at is None:
        return len(history) - 1 if history else None
    return next((i for i, entry in enumerate(history) if entry.get("logged_at") == logged_at), None)


def update_workout(logged_at=None, notes=None, sets=None, history_file=DEFAULT_HISTORY_FILE):
    """Edit a logged workout's notes/sets. Defaults to the most recently logged one."""
    history = _read_history(history_file)
    index = _find_index(history, logged_at)
    if index is None:
        if logged_at is None:
            return {"error": "No workout history to update."}
        return {"error": f"No workout found with logged_at={logged_at!r}."}

    if notes is not None:
        history[index]["notes"] = notes
    if sets is not None:
        history[index]["sets"] = sets

    error = _write_history(history, history_file)
    if error:
        return {"error": error}

    return history[index]


def delete_workout(logged_at=None, history_file=DEFAULT_HISTORY_FILE):
    """Delete a logged workout. Defaults to the most recently logged one."""
    history = _read_history(history_file)
    index = _find_index(history, logged_at)
    if index is None:
        if logged_at is None:
            return {"error": "No workout history to delete from."}
        return {"error": f"No workout found with logged_at={logged_at!r}."}

    removed = history.pop(index)

    error = _write_history(history, history_file)
    if error:
        return {"error": error}

    return {"deleted": removed}


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


def get_last_performance(exercise_name, history_file=DEFAULT_HISTORY_FILE):
    """Return the most recently logged {weight, reps, unit} for an exercise, or None."""
    history = _read_history(history_file)
    for entry in reversed(history):
        for set_entry in entry.get("sets", []):
            if set_entry.get("exercise") == exercise_name:
                return {
                    "weight": set_entry.get("weight"),
                    "reps": set_entry.get("reps"),
                    "unit": set_entry.get("unit"),
                }
    return None
