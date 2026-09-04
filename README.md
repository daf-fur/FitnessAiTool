# aiTool

![CI](https://github.com/daf-fur/aiTool/actions/workflows/ci.yml/badge.svg)

A small chat agent for fitness questions. Instead of letting the model make up exercise names from memory, it calls the [wger](https://wger.de) exercise API and answers from real data.

I built this to get hands-on with tool-calling: giving an LLM a few functions, letting it decide when to call them, and grounding its answers in something real instead of trusting whatever it remembers.

## Setup

```
pip install -r requirements.txt
```

Or install it as a CLI tool:

```
pip install -e .
```

Add your OpenAI key to a `.env` file:

```
OPENAI_API_KEY=sk-...
```

## Usage

```
python agent.py
```

or, if installed via `pip install -e .`:

```
fitness-agent
```

Starts an interactive chat. Type `exit` or `quit` to stop.

Your profile and workout history are scoped per user, so multiple people can share the same install without mixing data. Identity comes from `--user <name>`, then the `FITNESS_AGENT_USER` env var, then your OS username:

```
fitness-agent --user alice
fitness-agent --list-users        # see who has saved data on this install
fitness-agent --model gpt-4o      # override the model (defaults to $FITNESS_AGENT_MODEL or gpt-4o-mini)
```

Example prompts:
- "give me some chest exercises"
- "bodyweight leg exercises"
- "build me a push day for chest, shoulders, and triceps"
- "make that a strength-focused plan and save it to plan.md"
- "I did that workout, log it — I did bench at 135 for 8"
- "what have I done recently?"
- "I only have dumbbells at home, remember that"
- "my knee's bothering me, avoid squats"
- "give me a 4-day push/pull/legs/upper split"
- "swap out the dips, my shoulder's bothering me"
- "actually that bench weight was wrong, it was 145 not 135"
- "delete that last log, I logged it by mistake"
- "forget everything you've saved about me"

Sample session:

```
> give me two bodyweight chest exercises
Here are two bodyweight exercises for the chest:

1. Dips
2. Diamond Push-Ups

These exercises effectively target the chest muscles using just your body weight! Let me know if you need more information or additional exercises.
```

## Web frontend

A small FastAPI server (`server.py`) wraps the same agent logic behind a browser chat UI in `public/` (`index.html`, `style.css`, `app.js`) — no build step, no framework.

```
uvicorn server:app --reload      # dev
fitness-agent-server             # after pip install -e ., runs via uvicorn on $PORT (default 8000)
```

Open `http://localhost:8000`. Enter a name (same role as the CLI's `--user` — it's what scopes your profile/history) and start chatting; a "Reset chat" button clears the conversation.

Notes:
- The OpenAI key never leaves the server — the browser only ever talks to `/api/chat` and `/api/reset`.
- Conversation state is kept in memory, keyed by a `session_id` the browser generates and stores in `localStorage`. This is single-process and doesn't survive a server restart — a deliberate tradeoff for shipping quickly, not a bug, but not something to point multiple server instances (e.g. behind a load balancer) at.
- `PORT` is read from the environment so it runs as-is on typical PaaS targets (Render/Railway/Fly) without extra config.

## How it works

- `agent.py` — the chat loop, sends messages to the configured model with tool-calling enabled; resolves the current user and binds the tool dispatch table to their profile/history files
- `tools.py` — the tool schemas the model sees, and `build_dispatch(profile_file, history_file)`, a factory that binds tool names to real functions scoped to one user's data
- `wger_client.py` — the actual wger API calls (with a couple of retries on transient failures): muscle/equipment lookup, exercise search, and workout plan building
- `history.py` — logs workouts to a per-user `workout_history.json`, supports editing/deleting entries, and archives old entries once the active file gets large
- `user_profile.py` — saves default equipment, default goal, and exercise/injury exclusions to a per-user `user_profile.json`
- `paths.py` — resolves which user is running the session and maps them to `data/<user>/user_profile.json` and `data/<user>/workout_history.json`
- `server.py` — FastAPI app for the web frontend; keeps per-session conversation state in memory and calls `agent.run_turn` explicitly per request (not via the CLI's global state) so concurrent users don't interfere with each other

Tools available to the model:
- `lookup_exercise(muscle_group, equipment=None)`
- `find_muscle_id(muscle_group)`
- `find_equipment_id(equipment)`
- `build_workout_plan(muscle_groups, exercises_per_muscle=3, equipment=None, goal=None, save_to=None)`
- `build_program(days, exercises_per_muscle=3, equipment=None, goal=None, save_to=None)` — a multi-day split in one call; `days` is `[{"day": "Push", "muscle_groups": [...]}, ...]`
- `substitute_exercise(exercise_name, equipment=None)` — swaps one exercise in the current plan for an alternative targeting the same muscle group
- `log_last_workout(sets=None, notes=None)` — logs the most recently built plan; `sets` is optional actual performance (`[{"exercise": ..., "weight": ..., "reps": ..., "unit": "lb"|"kg"}]`)
- `get_workout_history(limit=5)`
- `update_workout(logged_at=None, notes=None, sets=None)` — edits a logged workout (defaults to the most recent)
- `delete_workout(logged_at=None)` — deletes a logged workout (defaults to the most recent)
- `get_profile()` — returns saved default equipment, goal, and exclusions
- `update_profile(equipment=None, goal=None, add_exclusions=None, remove_exclusions=None)` — saves a lasting preference
- `reset_profile()` — clears the whole saved profile back to unset

`get_workout_history` isn't a required tool call before every plan — `build_workout_plan`/`build_program` check it automatically. Any exercise you've logged before comes back with a `progression` tip suggesting a rep or weight bump — a specific one (e.g. "last time: 135 x 8 reps") if you logged actual `sets`, otherwise a generic nudge.

Goals — `strength`, `hypertrophy` (default), `endurance` — each set a different sets/reps/rest scheme.

## A few design notes

- **Caching**: wger's muscle and equipment lists barely ever change, so they're fetched once and reused instead of hitting the API on every lookup.
- **Deduping**: wger tags exercises with secondary muscles too, so building a plan across several muscle groups kept pulling the same exercise more than once. The plan builder now tracks what's already been picked and skips repeats.
- **Synonyms**: wger's muscle names are literal ("Quadriceps femoris"), so asking for "legs" wouldn't match anything. Common terms like `legs`, `back`, `arms`, and `core` get expanded to their component muscles before searching.
- **Progressive overload**: `build_workout_plan` checks workout history for each exercise it picks. If you logged actual weight/reps last time (via `log_last_workout`'s `sets`), the tip is specific ("last time: 135 x 8 reps"); otherwise it falls back to a generic "logged N times before" nudge.
- **Profile**: `lookup_exercise` and `build_workout_plan` fall back to your saved equipment/goal whenever a request doesn't specify one, and automatically skip anything on your exclusions list — so "no barbell" or "my knee hurts, no squats" only needs to be said once. An explicit equipment/goal in a request still overrides the saved default for that request.
- **Per-user data**: profile and history live under `data/<user>/`, keyed by whatever identity `agent.py` resolves (`--user`, then `$FITNESS_AGENT_USER`, then your OS username) — so a shared install doesn't mix people's data. Anything saved before this existed (a root-level `workout_history.json`) isn't auto-migrated.
- **Retries**: wger API calls retry a couple of times with a short backoff before giving up, so a one-off network blip doesn't surface straight to the user as an error.
- **Atomic writes**: profile and history files are written to a temp file and swapped into place, so a crash or write failure mid-save can't corrupt or truncate existing data — you either get the old version or the new one, never a half-written one.
- **Archiving**: once `workout_history.json` passes 500 entries, the oldest ones move to a `.archive.json` file alongside it, keeping the active file bounded without ever discarding history.

## Dev

```
pip install -r requirements-dev.txt
pytest --cov=. --cov-report=term-missing
ruff check .
```

CI runs both on every push and pull request to `main`.
