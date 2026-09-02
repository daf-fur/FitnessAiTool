from functools import partial

import history
import user_profile
import wger_client

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
                        "description": (
                            "The muscle group to find exercises for. Compound terms "
                            "like 'legs', 'back', 'arms', and 'core' are also supported "
                            "and expand to their component muscles."
                        ),
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
                "exercise isn't repeated under different muscle groups. Exercises "
                "logged in workout history before come back with a 'progression' "
                "tip suggesting adding weight or reps — mention it if present."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "muscle_groups": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "The muscle groups to include in the plan. Compound terms "
                            "like 'legs', 'back', 'arms', and 'core' are also supported "
                            "and expand to their component muscles."
                        ),
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
    {
        "type": "function",
        "function": {
            "name": "get_profile",
            "description": (
                "Get the user's saved profile: default equipment, default training goal, and "
                "exercise/muscle exclusions (e.g. from injuries). Call this if the user asks what's "
                "saved, or to check before re-asking a preference that might already be on file."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_profile",
            "description": (
                "Save or update the user's profile so preferences persist across sessions. Call "
                "this whenever the user states a lasting preference: default equipment they train "
                "with, a training goal, or an exercise/injury to avoid (e.g. 'my knee hurts, no "
                "squats' or 'I only have dumbbells at home'). lookup_exercise and build_workout_plan "
                "automatically use these as defaults when equipment/goal aren't given explicitly in "
                "the request, and automatically skip excluded exercises."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "equipment": {
                        "type": "string",
                        "description": (
                            "Default equipment to assume when not stated (e.g. dumbbell, bodyweight)."
                        ),
                    },
                    "goal": {
                        "type": "string",
                        "enum": ["strength", "hypertrophy", "endurance"],
                        "description": "Default training goal to assume when not stated.",
                    },
                    "add_exclusions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Exercise names or muscle groups to avoid (e.g. due to injury or lack of "
                            "equipment), added to the saved list."
                        ),
                    },
                    "remove_exclusions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Previously saved exclusions to remove, e.g. once an injury has healed."
                        ),
                    },
                },
                "required": [],
            },
        },
    },
]


def build_dispatch(profile_file, history_file):
    """Build the tool dispatch table bound to a specific user's profile/history files."""
    return {
        "lookup_exercise": partial(wger_client.lookup_exercise, profile_file=profile_file),
        "find_muscle_id": wger_client.find_muscle_id,
        "find_equipment_id": wger_client.find_equipment_id,
        "build_workout_plan": partial(
            wger_client.build_workout_plan, profile_file=profile_file, history_file=history_file
        ),
        "log_last_workout": partial(history.log_last_workout, history_file=history_file),
        "get_workout_history": partial(history.get_workout_history, history_file=history_file),
        "get_profile": partial(user_profile.get_profile, profile_file=profile_file),
        "update_profile": partial(user_profile.update_profile, profile_file=profile_file),
    }
