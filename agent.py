import json
from pathlib import Path

import requests
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI()

WGER_BASE_URL = "https://wger.de/api/v2"
ENGLISH_LANGUAGE_ID = 2
MODEL = "gpt-4o-mini"

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
                lines.append(f"{i}. **{exercise['name']}** ({exercise['category']})")
        lines.append("")

    return "\n".join(lines)


def build_workout_plan(muscle_groups, exercises_per_muscle=3, equipment=None, save_to=None):
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


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "lookup_exercise",
            "description": "Look up exercises that target a given muscle group (e.g. biceps, chest, quads).",
            "parameters": {
                "type": "object",
                "properties": {
                    "muscle_group": {
                        "type": "string",
                        "description": "The muscle group to find exercises for.",
                    },
                    "equipment": {
                        "type": "string",
                        "description": (
                            "Optional equipment filter (e.g. dumbbell, barbell, "
                            "resistance band, or 'bodyweight' for no equipment)."
                        ),
                    },
                },
                "required": ["muscle_group"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_muscle_id",
            "description": "Resolve a muscle group name (e.g. biceps, chest, quads) to its wger muscle ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "muscle_group": {
                        "type": "string",
                        "description": "The muscle group to resolve.",
                    },
                },
                "required": ["muscle_group"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_equipment_id",
            "description": "Resolve an equipment name (e.g. dumbbell, barbell, bodyweight) to its wger equipment ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "equipment": {
                        "type": "string",
                        "description": "The equipment name to resolve.",
                    },
                },
                "required": ["equipment"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "build_workout_plan",
            "description": (
                "Build a full workout plan by looking up exercises for multiple "
                "muscle groups at once (e.g. a push day: chest, shoulders, triceps). "
                "Exercises are deduplicated across the whole plan so the same "
                "exercise isn't repeated under different muscle groups."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "muscle_groups": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "The muscle groups to include in the plan.",
                    },
                    "exercises_per_muscle": {
                        "type": "integer",
                        "description": "How many exercises to include per muscle group (default 3).",
                    },
                    "equipment": {
                        "type": "string",
                        "description": (
                            "Optional equipment filter applied to every muscle group "
                            "(e.g. dumbbell, barbell, or 'bodyweight' for no equipment)."
                        ),
                    },
                    "save_to": {
                        "type": "string",
                        "description": (
                            "Optional file path to save the plan to, if the user asks to "
                            "save or export it. Use a '.md' extension for a readable "
                            "markdown file, any other extension (e.g. '.json') for JSON."
                        ),
                    },
                },
                "required": ["muscle_groups"],
            },
        },
    },
]

AVAILABLE_FUNCTIONS = {
    "lookup_exercise": lookup_exercise,
    "find_muscle_id": find_muscle_id,
    "find_equipment_id": find_equipment_id,
    "build_workout_plan": build_workout_plan,
}

SYSTEM_PROMPT = (
    "You are a fitness assistant. Use lookup_exercise for a single muscle group, "
    "or build_workout_plan when the user wants a full workout covering multiple "
    "muscle groups. Both tools accept an optional equipment filter if the user "
    "mentions available equipment or wants a bodyweight-only workout. If the user "
    "asks to save or export a plan, call build_workout_plan again with a save_to "
    "file path. Always ground recommendations in real tool results."
)

MAX_TOOL_ITERATIONS = 5


def run_turn(messages):
    response = client.chat.completions.create(model=MODEL, messages=messages, tools=TOOLS)
    message = response.choices[0].message

    iterations = 0
    while message.tool_calls and iterations < MAX_TOOL_ITERATIONS:
        messages.append(message)
        for tool_call in message.tool_calls:
            function = AVAILABLE_FUNCTIONS[tool_call.function.name]
            arguments = json.loads(tool_call.function.arguments)
            result = function(**arguments)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result),
                }
            )

        response = client.chat.completions.create(model=MODEL, messages=messages, tools=TOOLS)
        message = response.choices[0].message
        iterations += 1

    messages.append(message)
    return message.content


def run_agent(user_message):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]
    return run_turn(messages)


def chat():
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    print("Fitness agent ready. Type 'exit' or 'quit' to stop.")

    while True:
        try:
            user_message = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user_message:
            continue
        if user_message.lower() in {"exit", "quit"}:
            break

        messages.append({"role": "user", "content": user_message})
        try:
            reply = run_turn(messages)
        except Exception as error:
            print(f"Error: {error}")
            messages.pop()
            continue

        print(reply)


if __name__ == "__main__":
    chat()
