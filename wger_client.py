import json
from pathlib import Path

import requests

WGER_BASE_URL = "https://wger.de/api/v2"
ENGLISH_LANGUAGE_ID = 2

REP_SCHEMES = {
    "strength": {"sets": 5, "reps": "5", "rest_seconds": 180},
    "hypertrophy": {"sets": 3, "reps": "8-12", "rest_seconds": 90},
    "endurance": {"sets": 3, "reps": "15-20", "rest_seconds": 45},
}
DEFAULT_GOAL = "hypertrophy"

_muscle_cache = None
_equipment_cache = None


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


def lookup_exercise(muscle_group, equipment=None, limit=5):
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

    return results


def _plan_to_markdown(plan):
    lines = ["# Workout Plan", ""]
    for entry in plan:
        lines.append(f"## {entry['muscle_group'].title()}")
        if "error" in entry:
            lines.append(f"- Error: {entry['error']}")
        else:
            for i, exercise in enumerate(entry["exercises"], 1):
                lines.append(
                    f"{i}. **{exercise['name']}** ({exercise['category']}) — "
                    f"{exercise['sets']} sets x {exercise['reps']} reps, "
                    f"rest {exercise['rest_seconds']}s"
                )
        lines.append("")

    return "\n".join(lines)


def build_workout_plan(muscle_groups, exercises_per_muscle=3, equipment=None, goal=None, save_to=None):
    scheme = REP_SCHEMES.get(goal, REP_SCHEMES[DEFAULT_GOAL])

    plan = []
    used_names = set()

    for muscle_group in muscle_groups:
        exercises = lookup_exercise(muscle_group, equipment=equipment, limit=exercises_per_muscle + 5)
        if isinstance(exercises, dict):
            plan.append({"muscle_group": muscle_group, "error": exercises["error"]})
            continue

        unique_exercises = [e for e in exercises if e["name"] not in used_names]
        selected = unique_exercises[:exercises_per_muscle]
        used_names.update(e["name"] for e in selected)
        for exercise in selected:
            exercise.update(scheme)

        plan.append({"muscle_group": muscle_group, "exercises": selected})

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
