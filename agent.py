import json

import requests
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI()

WGER_BASE_URL = "https://wger.de/api/v2"
ENGLISH_LANGUAGE_ID = 2
MODEL = "gpt-4o-mini"


def find_muscle_id(muscle_group):
    try:
        response = requests.get(f"{WGER_BASE_URL}/muscle/?format=json&limit=50", timeout=10)
        response.raise_for_status()
    except requests.RequestException as error:
        return {"error": f"Failed to look up muscle groups: {error}"}
    data = response.json()

    muscle_group = muscle_group.lower()
    for muscle in data["results"]:
        if muscle_group in muscle["name"].lower() or muscle_group in muscle["name_en"].lower():
            return muscle["id"]

    return None


def find_equipment_id(equipment):
    try:
        response = requests.get(f"{WGER_BASE_URL}/equipment/?format=json&limit=20", timeout=10)
        response.raise_for_status()
    except requests.RequestException as error:
        return {"error": f"Failed to look up equipment: {error}"}
    data = response.json()

    equipment = equipment.lower()
    for item in data["results"]:
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


def build_workout_plan(muscle_groups, exercises_per_muscle=3, equipment=None):
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

    return plan


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
    "mentions available equipment or wants a bodyweight-only workout. Always "
    "ground recommendations in real tool results."
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
