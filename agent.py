import json

from dotenv import load_dotenv
from openai import OpenAI

from tools import AVAILABLE_FUNCTIONS, TOOLS

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
    "tool results."
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
