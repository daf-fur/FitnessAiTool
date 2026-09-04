import json
from pathlib import Path

import requests

import user_profile

WGER_BASE_URL = "https://wger.de/api/v2"
ENGLISH_LANGUAGE_ID = 2

REP_SCHEMES = {
    "strength": {"sets": 5, "reps": "5", "rest_seconds": 180},
    "hypertrophy": {"sets": 3, "reps": "8-12", "rest_seconds": 90},
    "endurance": {"sets": 3, "reps": "15-20", "rest_seconds": 45},
}
DEFAULT_GOAL = "hypertrophy"

MUSCLE_SYNONYMS = {
    "legs": ["quads", "hamstrings", "calves", "glutes"],
    "back": ["lats", "traps"],
    "arms": ["biceps", "triceps"],
    "core": ["abs", "obliques"],
    "traps": ["trapezius"],
    "obliques": ["obliquus externus abdominis"],
}

_muscle_cache = None
_equipment_cache = None
_last_plan = None


def _get_muscles():
    global _muscle_cache
    if _muscle_cache is None:
        try:
            response = requests.get(f"{WGER_BASE_URL}/muscle/?format=json&limit=50", timeout=10)
            response.raise_for_status()
        except requests.RequestException as error:
            return {"error": f"Failed to look up muscle groups: {error}"}
        _muscle_cache = response.json()["results"]

    return _muscle_cache


def _get_equipment():
    global _equipment_cache
    if _equipment_cache is None:
        try:
            response = requests.get(f"{WGER_BASE_URL}/equipment/?format=json&limit=20", timeout=10)
            response.raise_for_status()
        except requests.RequestException as error:
            return {"error": f"Failed to look up equipment: {error}"}
        _equipment_cache = response.json()["results"]

    return _equipment_cache


def find_muscle_id(muscle_group):
    muscles = _get_muscles()
    if isinstance(muscles, dict):
        return muscles

    muscle_group = muscle_group.lower()
    for muscle in muscles:
        if muscle_group in muscle["name"].lower() or muscle_group in muscle["name_en"].lower():
            return muscle["id"]

    return None


def find_equipment_id(equipment):
    equipment_list = _get_equipment()
    if isinstance(equipment_list, dict):
        return equipment_list

    equipment = equipment.lower()
    for item in equipment_list:
        if equipment in item["name"].lower():
            return item["id"]

    return None


def _excludes(name, exclusions):
    name_lower = name.lower()
    return any(term.lower() in name_lower for term in exclusions)


def lookup_exercise(muscle_group, equipment=None, limit=5, profile_file=None):
    profile_kwargs = {"profile_file": profile_file} if profile_file is not None else {}
    profile = user_profile.get_profile(**profile_kwargs)
    if equipment is None:
        equipment = profile["equipment"]
    exclusions = profile["exclusions"]

    synonyms = MUSCLE_SYNONYMS.get(muscle_group.lower())
    if synonyms:
        merged = []
        seen_names = set()
        errors = []
        for term in synonyms:
            sub_results = lookup_exercise(term, equipment=equipment, limit=limit, profile_file=profile_file)
            if isinstance(sub_results, dict):
                errors.append(sub_results["error"])
                continue
            for exercise in sub_results:
                if exercise["name"] not in seen_names:
                    seen_names.add(exercise["name"])
                    merged.append(exercise)

        if not merged and errors:
            return {"error": "; ".join(errors)}
        return merged[:limit]

    muscle_id = find_muscle_id(muscle_group)
    if not isinstance(muscle_id, int):
        return muscle_id if isinstance(muscle_id, dict) else []

    url = f"{WGER_BASE_URL}/exerciseinfo/?format=json&muscles={muscle_id}&limit={limit}"

    if equipment:
        equipment_id = find_equipment_id(equipment)
        if isinstance(equipment_id, dict):
            return equipment_id
        if equipment_id is None:
            return {"error": f"Unknown equipment: {equipment}"}
        url += f"&equipment={equipment_id}"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.RequestException as error:
        return {"error": f"Failed to look up exercises: {error}"}
    data = response.json()

    results = []
    for exercise in data["results"]:
        translations = exercise["translations"]
        english = next((t for t in translations if t["language"] == ENGLISH_LANGUAGE_ID), None)
        name = english["name"] if english else translations[0]["name"] if translations else None
        results.append({"name": name, "category": exercise["category"]["name"]})

    if exclusions:
        results = [exercise for exercise in results if not _excludes(exercise["name"], exclusions)]

    return results


def _progression_note(times_logged, last_performance=None):
    if times_logged == 0:
        return None
    if last_performance:
        weight = last_performance.get("weight")
        reps = last_performance.get("reps")
        if weight is not None and reps is not None:
            return f"Last time: {weight} x {reps} reps — try adding weight or a rep this time."
        if weight is not None:
            return f"Last time: {weight} — try adding a bit more weight this time."
        if reps is not None:
            return f"Last time: {reps} reps — try adding a rep this time."
    if times_logged == 1:
        return "Logged once before — try adding a rep or a bit more weight this time."
    return f"Logged {times_logged} times before — keep pushing weight or reps if it's felt easy."


def _plan_to_markdown(plan):
    lines = ["# Workout Plan", ""]
    for entry in plan:
        header = f"## {entry['muscle_group'].title()}"
        if entry.get("day"):
            header = f"## {entry['day']}: {entry['muscle_group'].title()}"
        lines.append(header)
        if "error" in entry:
            lines.append(f"- Error: {entry['error']}")
        else:
            for i, exercise in enumerate(entry["exercises"], 1):
                lines.append(
                    f"{i}. **{exercise['name']}** ({exercise['category']}) — "
                    f"{exercise['sets']} sets x {exercise['reps']} reps, "
                    f"rest {exercise['rest_seconds']}s"
                )
                if exercise.get("progression"):
                    lines.append(f"   - {exercise['progression']}")
        lines.append("")

    return "\n".join(lines)


def build_workout_plan(
    muscle_groups,
    exercises_per_muscle=3,
    equipment=None,
    goal=None,
    save_to=None,
    history_file=None,
    profile_file=None,
):
    import history as history_module

    profile_kwargs = {"profile_file": profile_file} if profile_file is not None else {}
    profile = user_profile.get_profile(**profile_kwargs)
    if equipment is None:
        equipment = profile["equipment"]
    if goal is None:
        goal = profile["goal"]

    scheme = REP_SCHEMES.get(goal, REP_SCHEMES[DEFAULT_GOAL])
    history_kwargs = {"history_file": history_file} if history_file is not None else {}

    plan = []
    used_names = set()

    for muscle_group in muscle_groups:
        exercises = lookup_exercise(
            muscle_group, equipment=equipment, limit=exercises_per_muscle + 5, profile_file=profile_file
        )
        if isinstance(exercises, dict):
            plan.append({"muscle_group": muscle_group, "error": exercises["error"]})
            continue

        unique_exercises = [e for e in exercises if e["name"] not in used_names]
        selected = unique_exercises[:exercises_per_muscle]
        used_names.update(e["name"] for e in selected)
        for exercise in selected:
            exercise.update(scheme)
            times_logged = history_module.get_exercise_progress(exercise["name"], **history_kwargs)
            last_performance = history_module.get_last_performance(exercise["name"], **history_kwargs)
            note = _progression_note(times_logged, last_performance)
            if note:
                exercise["progression"] = note

        plan.append({"muscle_group": muscle_group, "exercises": selected})

    global _last_plan
    _last_plan = plan

    if not save_to:
        return plan

    path = Path(save_to)
    content = _plan_to_markdown(plan) if path.suffix.lower() == ".md" else json.dumps(plan, indent=2)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    except OSError as error:
        return {"plan": plan, "save_error": f"Failed to save plan to {save_to}: {error}"}

    return {"plan": plan, "saved_to": str(path)}


def substitute_exercise(exercise_name, equipment=None, profile_file=None):
    if _last_plan is None:
        return {"error": "No workout plan has been built yet."}

    used_names = {
        exercise["name"] for entry in _last_plan for exercise in entry.get("exercises", [])
    }

    for entry in _last_plan:
        exercises = entry.get("exercises", [])
        for index, exercise in enumerate(exercises):
            if exercise["name"].lower() != exercise_name.lower():
                continue

            muscle_group = entry["muscle_group"]
            candidates = lookup_exercise(
                muscle_group, equipment=equipment, limit=10, profile_file=profile_file
            )
            if isinstance(candidates, dict):
                return candidates

            replacement = next((c for c in candidates if c["name"] not in used_names), None)
            if replacement is None:
                return {"error": f"No alternative found for {exercise_name}."}

            for key in ("sets", "reps", "rest_seconds"):
                if key in exercise:
                    replacement[key] = exercise[key]

            exercises[index] = replacement
            return {"replaced": exercise["name"], "with": replacement, "muscle_group": muscle_group}

    return {"error": f"{exercise_name} isn't in your current plan."}


def build_program(
    days,
    exercises_per_muscle=3,
    equipment=None,
    goal=None,
    save_to=None,
    history_file=None,
    profile_file=None,
):
    """Build a multi-day program. `days` is a list of {"day": str, "muscle_groups": [str, ...]}."""
    flat_plan = []

    for day in days:
        day_name = day.get("day", "Day")
        day_plan = build_workout_plan(
            day.get("muscle_groups", []),
            exercises_per_muscle=exercises_per_muscle,
            equipment=equipment,
            goal=goal,
            history_file=history_file,
            profile_file=profile_file,
        )
        for entry in day_plan:
            entry["day"] = day_name
            flat_plan.append(entry)

    global _last_plan
    _last_plan = flat_plan

    if not save_to:
        return flat_plan

    path = Path(save_to)
    if path.suffix.lower() == ".md":
        content = _plan_to_markdown(flat_plan)
    else:
        content = json.dumps(flat_plan, indent=2)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    except OSError as error:
        return {"plan": flat_plan, "save_error": f"Failed to save program to {save_to}: {error}"}

    return {"plan": flat_plan, "saved_to": str(path)}
