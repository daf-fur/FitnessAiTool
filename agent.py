import argparse
import json
from importlib.metadata import PackageNotFoundError, version

from dotenv import load_dotenv
from openai import OpenAI

import paths
import tools
from tools import TOOLS

load_dotenv()

client = OpenAI()

MODEL = "gpt-4o-mini"
MAX_TOOL_ITERATIONS = 5

SYSTEM_PROMPT = (
    "You are a fitness assistant. Use lookup_exercise for a single muscle group, "
    "or build_workout_plan when the user wants a full workout covering multiple "
    "muscle groups. Both tools accept an optional equipment filter if the user "
    "mentions available equipment or wants a bodyweight-only workout. "
    "build_workout_plan also accepts a goal (strength, hypertrophy, or endurance) "
    "to set the sets/reps/rest scheme; ask the user's goal if it isn't clear, "
    "otherwise it defaults to hypertrophy. If the user asks to save or export a "
    "plan, call build_workout_plan again with a save_to file path. If the user says "
    "they completed a workout, call log_last_workout. If they ask about past "
    "workouts, call get_workout_history. Always ground recommendations in real "
    "tool results. The user's saved profile (default equipment, goal, and "
    "exercise/injury exclusions) is applied automatically by lookup_exercise and "
    "build_workout_plan whenever those aren't specified in the current request. "
    "Call update_profile whenever the user states a lasting preference — equipment "
    "they own, a training goal, or an exercise/muscle to avoid — so it's remembered "
    "next time. Use get_profile if the user asks what's saved."
)

AVAILABLE_FUNCTIONS = tools.build_dispatch(
    paths.profile_path(paths.resolve_user()), paths.history_path(paths.resolve_user())
)


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


def run_agent(user_message, user=None):
    global AVAILABLE_FUNCTIONS
    if user is not None:
        AVAILABLE_FUNCTIONS = tools.build_dispatch(paths.profile_path(user), paths.history_path(user))

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]
    return run_turn(messages)


def chat(user=None):
    global AVAILABLE_FUNCTIONS
    resolved_user = paths.resolve_user(user)
    AVAILABLE_FUNCTIONS = tools.build_dispatch(
        paths.profile_path(resolved_user), paths.history_path(resolved_user)
    )

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    print(f"Fitness agent ready for {resolved_user}. Type 'exit' or 'quit' to stop.")

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


def _version():
    try:
        return version("wger-fitness-agent")
    except PackageNotFoundError:
        return "unknown"


def main():
    parser = argparse.ArgumentParser(description="Fitness chat agent")
    parser.add_argument(
        "--user", help="Profile/history identity to use (defaults to $FITNESS_AGENT_USER or your OS username)"
    )
    parser.add_argument("--version", action="version", version=f"fitness-agent {_version()}")
    args = parser.parse_args()
    chat(user=args.user)


if __name__ == "__main__":
    main()
