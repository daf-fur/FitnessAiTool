# aiTool

![CI](https://github.com/daf-fur/aiTool/actions/workflows/ci.yml/badge.svg)

A small chat agent for fitness questions. Instead of letting the model make up exercise names from memory, it calls the [wger](https://wger.de) exercise API and answers from real data.

I built this to get hands-on with tool-calling: giving an LLM a few functions, letting it decide when to call them, and grounding its answers in something real instead of trusting whatever it remembers.

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

- `agent.py` — the chat loop, sends messages to `gpt-4o-mini` with tool-calling enabled
- `tools.py` — the tool schemas the model sees, and a dispatch table mapping tool names to real functions
- `wger_client.py` — the actual wger API calls: muscle/equipment lookup, exercise search, and workout plan building
- `history.py` — logs the last built plan to `workout_history.json` and reads it back

Tools available to the model:
- `lookup_exercise(muscle_group, equipment=None)`
- `find_muscle_id(muscle_group)`
- `find_equipment_id(equipment)`
- `build_workout_plan(muscle_groups, exercises_per_muscle=3, equipment=None, goal=None, save_to=None)`
- `log_last_workout(notes=None)` — logs the most recently built plan
- `get_workout_history(limit=5)`

Goals — `strength`, `hypertrophy` (default), `endurance` — each set a different sets/reps/rest scheme.

## A few design notes

- **Caching**: wger's muscle and equipment lists barely ever change, so they're fetched once and reused instead of hitting the API on every lookup.
- **Deduping**: wger tags exercises with secondary muscles too, so building a plan across several muscle groups kept pulling the same exercise more than once. The plan builder now tracks what's already been picked and skips repeats.
- **Synonyms**: wger's muscle names are literal ("Quadriceps femoris"), so asking for "legs" wouldn't match anything. Common terms like `legs`, `back`, `arms`, and `core` get expanded to their component muscles before searching.

## Dev

```
pip install -r requirements-dev.txt
pytest --cov=. --cov-report=term-missing
ruff check .
```

CI runs both on every push and pull request to `main`.
