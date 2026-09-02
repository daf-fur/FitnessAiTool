import json
from pathlib import Path

DEFAULT_PROFILE_FILE = Path("user_profile.json")


def _read_profile(profile_file):
    if not profile_file.exists():
        return {}
    try:
        return json.loads(profile_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def get_profile(profile_file=DEFAULT_PROFILE_FILE):
    profile = _read_profile(profile_file)
    profile.setdefault("equipment", None)
    profile.setdefault("goal", None)
    profile.setdefault("exclusions", [])
    return profile


def update_profile(
    equipment=None, goal=None, add_exclusions=None, remove_exclusions=None, profile_file=DEFAULT_PROFILE_FILE
):
    profile = get_profile(profile_file=profile_file)

    if equipment is not None:
        profile["equipment"] = equipment
    if goal is not None:
        profile["goal"] = goal

    exclusions = set(profile["exclusions"])
    if add_exclusions:
        exclusions.update(term.strip() for term in add_exclusions if term.strip())
    if remove_exclusions:
        removal = {term.strip().lower() for term in remove_exclusions}
        exclusions = {term for term in exclusions if term.lower() not in removal}
    profile["exclusions"] = sorted(exclusions)

    try:
        profile_file.parent.mkdir(parents=True, exist_ok=True)
        profile_file.write_text(json.dumps(profile, indent=2), encoding="utf-8")
    except OSError as error:
        return {"error": f"Failed to save profile: {error}"}

    return profile
