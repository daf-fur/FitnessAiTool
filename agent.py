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
    response = requests.get(f"{WGER_BASE_URL}/muscle/?format=json&limit=50")
    response.raise_for_status()
    data = response.json()

    muscle_group = muscle_group.lower()
    for muscle in data["results"]:
        if muscle_group in muscle["name"].lower() or muscle_group in muscle["name_en"].lower():
            return muscle["id"]

    return None


def lookup_exercise(muscle_group):
    muscle_id = find_muscle_id(muscle_group)
    if muscle_id is None:
        return []

    url = f"{WGER_BASE_URL}/exerciseinfo/?format=json&muscles={muscle_id}&limit=5"
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()

    results = []
    for exercise in data["results"]:
        translations = exercise["translations"]
        english = next((t for t in translations if t["language"] == ENGLISH_LANGUAGE_ID), None)
        name = english["name"] if english else translations[0]["name"] if translations else None
        results.append({"name": name, "category": exercise["category"]["name"]})

    return results


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
]

AVAILABLE_FUNCTIONS = {
    "lookup_exercise": lookup_exercise,
    "find_muscle_id": find_muscle_id,
}


def run_agent(user_message):
    messages = [
        {
            "role": "system",
            "content": (
                "You are a fitness assistant. Use the lookup_exercise tool to find "
                "real exercises before recommending a workout."
            ),
        },
        {"role": "user", "content": user_message},
    ]

    response = client.chat.completions.create(model=MODEL, messages=messages, tools=TOOLS)
    message = response.choices[0].message

    while message.tool_calls:
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

    return message.content


if __name__ == "__main__":
    print(run_agent("Give me three exercises for biceps."))
