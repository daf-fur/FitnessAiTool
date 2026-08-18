import requests
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI()

WGER_BASE_URL = "https://wger.de/api/v2"
ENGLISH_LANGUAGE_ID = 2


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


if __name__ == "__main__":
    results = lookup_exercise("biceps")
    print(results)
