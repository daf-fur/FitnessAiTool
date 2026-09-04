import argparse
import json
import os
from importlib.metadata import PackageNotFoundError, version

from dotenv import load_dotenv
from openai import OpenAI

import paths
import tools
from tools import TOOLS

load_dotenv()

client = OpenAI()

MODEL = os.environ.get("FITNESS_AGENT_MODEL", "gpt-4o-mini")
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
    "next time. Use get_profile if the user asks what's saved. Use build_program "
    "instead of build_workout_plan when the user wants a multi-day split (e.g. push/"
    "pull/legs). If the user wants to swap out one exercise in the current plan "
    "(injury, dislike, no equipment), call substitute_exercise rather than rebuilding "
    "the whole plan. When logging a completed workout, if the user mentions actual "
    "weights or reps, pass them to log_last_workout as sets — always include a unit "
    "(lb or kg) with any weight, so progression comparisons don't mix units — so "
    "future progression tips are based on real numbers instead of a generic nudge. "
    "If the user wants to fix or remove a past log entry, use update_workout or "
    "delete_workout (both default to the most recent entry if no timestamp is given). "
    "Use reset_profile only if the user explicitly asks to clear/forget everything "
    "saved; for removing one preference, use update_profile's remove_exclusions instead."
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


def run_agent(user_message, user=None, model=None):
    global AVAILABLE_FUNCTIONS, MODEL
    if user is not None:
        AVAILABLE_FUNCTIONS = tools.build_dispatch(paths.profile_path(user), paths.history_path(user))
    if model is not None:
        MODEL = model

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]
    return run_turn(messages)


def chat(user=None, model=None):
    global AVAILABLE_FUNCTIONS, MODEL
    resolved_user = paths.resolve_user(user)
    AVAILABLE_FUNCTIONS = tools.build_dispatch(
        paths.profile_path(resolved_user), paths.history_path(resolved_user)
    )
    if model is not None:
        MODEL = model

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    print(f"Fitness agent ready for {resolved_user} (model: {MODEL}). Type 'exit' or 'quit' to stop.")

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
    parser.add_argument(
        "--model", help="OpenAI model to use (defaults to $FITNESS_AGENT_MODEL or gpt-4o-mini)"
    )
    parser.add_argument(
        "--list-users", action="store_true", help="List users with saved data on this install and exit"
    )
    parser.add_argument("--version", action="version", version=f"fitness-agent {_version()}")
    args = parser.parse_args()

    if args.list_users:
        users = paths.list_users()
        print("\n".join(users) if users else "No saved users yet.")
        return

    chat(user=args.user, model=args.model)


if __name__ == "__main__":
    main()
