# aiTool

A chat agent that answers fitness questions by calling the [wger](https://wger.de) exercise API. Ask it for exercises by muscle group or equipment, or have it build a full workout plan.

## Setup

```
pip install -r requirements.txt
```

Add your OpenAI key to a `.env` file:

```
OPENAI_API_KEY=sk-...
```

## Usage

```
python agent.py
```

Starts an interactive chat. Type `exit` or `quit` to stop.

Example prompts:
- "give me some chest exercises"
- "bodyweight leg exercises"
- "build me a push day for chest, shoulders, and triceps"
- "make that a strength-focused plan and save it to plan.md"
- "I did that workout, log it"
- "what have I done recently?"

## How it works

- `agent.py` — chat loop, sends messages to `gpt-4o-mini` with tool-calling enabled
- `tools.py` — tool schemas and the function dispatch table
- `wger_client.py` — the wger API calls: muscle/equipment lookup (cached), exercise search, and workout plan building (dedupes exercises, applies sets/reps/rest by goal, can save to `.md` or `.json`)
- `history.py` — logs the last built plan to `workout_history.json` and reads it back

Tools available to the model:
- `lookup_exercise(muscle_group, equipment=None)`
- `find_muscle_id(muscle_group)`
- `find_equipment_id(equipment)`
- `build_workout_plan(muscle_groups, exercises_per_muscle=3, equipment=None, goal=None, save_to=None)`
- `log_last_workout(notes=None)` — logs the most recently built plan
- `get_workout_history(limit=5)`

Goals: `strength`, `hypertrophy` (default), `endurance` — each sets a different sets/reps/rest scheme.

## Dev

```
pip install -r requirements-dev.txt
pytest --cov=. --cov-report=term-missing
ruff check .
```
