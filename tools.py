from history import get_workout_history, log_last_workout
from wger_client import build_workout_plan, find_equipment_id, find_muscle_id, lookup_exercise

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
            "description": (
                "Resolve an equipment name (e.g. dumbbell, barbell, bodyweight) to its wger equipment ID."
            ),
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
                    "goal": {
                        "type": "string",
                        "enum": ["strength", "hypertrophy", "endurance"],
                        "description": (
                            "Training goal, which sets the sets/reps/rest scheme for every "
                            "exercise in the plan. Defaults to hypertrophy if not specified."
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
    {
        "type": "function",
        "function": {
            "name": "log_last_workout",
            "description": (
                "Log the most recently built workout plan to history, e.g. when the user "
                "says they completed it. Fails if no plan has been built yet this session."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "notes": {
                        "type": "string",
                        "description": "Optional notes about how the workout went.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_workout_history",
            "description": "Get past logged workouts, most recent last.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "How many recent workouts to return (default 5).",
                    },
                },
                "required": [],
            },
        },
    },
]

AVAILABLE_FUNCTIONS = {
    "lookup_exercise": lookup_exercise,
    "find_muscle_id": find_muscle_id,
    "find_equipment_id": find_equipment_id,
    "build_workout_plan": build_workout_plan,
    "log_last_workout": log_last_workout,
    "get_workout_history": get_workout_history,
}
