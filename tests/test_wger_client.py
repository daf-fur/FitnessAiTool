import json
from unittest.mock import patch

import pytest

import wger_client


@pytest.fixture(autouse=True)
def reset_caches():
    wger_client._muscle_cache = None
    wger_client._equipment_cache = None
    yield
    wger_client._muscle_cache = None
    wger_client._equipment_cache = None


def _response(json_data, status_ok=True):
    class FakeResponse:
        def raise_for_status(self):
            if not status_ok:
                raise wger_client.requests.RequestException("boom")

        def json(self):
            return json_data

    return FakeResponse()


MUSCLES = {
    "results": [
        {"id": 4, "name": "Biceps brachii", "name_en": "Biceps"},
        {"id": 10, "name": "Pectoralis major", "name_en": "Chest"},
    ]
}

EQUIPMENT = {
    "results": [
        {"id": 1, "name": "Dumbbell"},
        {"id": 7, "name": "none (bodyweight exercise)"},
    ]
}


def _exerciseinfo(names):
    return {
        "results": [
            {
                "translations": [{"language": wger_client.ENGLISH_LANGUAGE_ID, "name": name}],
                "category": {"name": "Arms"},
            }
            for name in names
        ]
    }


class TestGet:
    def test_retries_and_recovers_after_transient_failure(self):
        calls = [wger_client.requests.RequestException("blip"), _response(MUSCLES)]

        def fake_get(*args, **kwargs):
            result = calls.pop(0)
            if isinstance(result, Exception):
                raise result
            return result

        with patch.object(wger_client.requests, "get", side_effect=fake_get) as mock_get:
            response = wger_client._get("http://example.com")

        assert response.json() == MUSCLES
        assert mock_get.call_count == 2

    def test_gives_up_after_exhausting_retries(self):
        with patch.object(
            wger_client.requests, "get", side_effect=wger_client.requests.RequestException("down")
        ) as mock_get:
            with pytest.raises(wger_client.requests.RequestException):
                wger_client._get("http://example.com")

        assert mock_get.call_count == wger_client.RETRY_ATTEMPTS + 1


class TestFindMuscleId:
    def test_matches_by_english_name(self):
        with patch.object(wger_client.requests, "get", return_value=_response(MUSCLES)):
            assert wger_client.find_muscle_id("chest") == 10

    def test_matches_case_insensitively_and_by_native_name(self):
        with patch.object(wger_client.requests, "get", return_value=_response(MUSCLES)):
            assert wger_client.find_muscle_id("Biceps") == 4

    def test_returns_none_when_not_found(self):
        with patch.object(wger_client.requests, "get", return_value=_response(MUSCLES)):
            assert wger_client.find_muscle_id("quads") is None

    def test_caches_across_calls(self):
        with patch.object(wger_client.requests, "get", return_value=_response(MUSCLES)) as mock_get:
            wger_client.find_muscle_id("chest")
            wger_client.find_muscle_id("biceps")
            assert mock_get.call_count == 1

    def test_returns_error_dict_on_request_failure(self):
        with patch.object(
            wger_client.requests, "get", side_effect=wger_client.requests.RequestException("down")
        ):
            result = wger_client.find_muscle_id("chest")
            assert isinstance(result, dict)
            assert "error" in result


class TestFindEquipmentId:
    def test_matches_by_substring(self):
        with patch.object(wger_client.requests, "get", return_value=_response(EQUIPMENT)):
            assert wger_client.find_equipment_id("bodyweight") == 7

    def test_returns_none_when_not_found(self):
        with patch.object(wger_client.requests, "get", return_value=_response(EQUIPMENT)):
            assert wger_client.find_equipment_id("kettlebell") is None

    def test_returns_error_dict_on_request_failure(self):
        with patch.object(
            wger_client.requests, "get", side_effect=wger_client.requests.RequestException("down")
        ):
            result = wger_client.find_equipment_id("dumbbell")
            assert isinstance(result, dict)
            assert "error" in result


class TestLookupExercise:
    def test_returns_exercises_for_known_muscle(self):
        responses = [_response(MUSCLES), _response(_exerciseinfo(["Curl", "Chin-up"]))]
        with patch.object(wger_client.requests, "get", side_effect=responses):
            result = wger_client.lookup_exercise("biceps")
            assert result == [
                {"name": "Curl", "category": "Arms"},
                {"name": "Chin-up", "category": "Arms"},
            ]

    def test_returns_empty_list_for_unknown_muscle(self):
        with patch.object(wger_client.requests, "get", return_value=_response(MUSCLES)):
            assert wger_client.lookup_exercise("quads") == []

    def test_unknown_equipment_returns_error(self):
        with patch.object(wger_client.requests, "get", return_value=_response(MUSCLES)):
            result = wger_client.lookup_exercise("chest", equipment="jetpack")
            assert result == {"error": "Unknown equipment: jetpack"}

    def test_falls_back_to_first_translation_when_no_english(self):
        exerciseinfo = {
            "results": [
                {
                    "translations": [{"language": 99, "name": "Curl de bíceps"}],
                    "category": {"name": "Arms"},
                }
            ]
        }
        responses = [_response(MUSCLES), _response(exerciseinfo)]
        with patch.object(wger_client.requests, "get", side_effect=responses):
            result = wger_client.lookup_exercise("biceps")
            assert result == [{"name": "Curl de bíceps", "category": "Arms"}]

    def test_returns_error_dict_when_equipment_lookup_fails(self):
        responses = [_response(MUSCLES)]

        def fake_get(*args, **kwargs):
            if responses:
                return responses.pop(0)
            raise wger_client.requests.RequestException("down")

        with patch.object(wger_client.requests, "get", side_effect=fake_get):
            result = wger_client.lookup_exercise("chest", equipment="dumbbell")
            assert isinstance(result, dict)
            assert "error" in result

    def test_filters_by_equipment_when_resolved(self):
        exercises = _exerciseinfo(["Push-up"])
        responses = [_response(MUSCLES), _response(EQUIPMENT), _response(exercises)]
        with patch.object(wger_client.requests, "get", side_effect=responses) as mock_get:
            result = wger_client.lookup_exercise("chest", equipment="dumbbell")
            assert result == [{"name": "Push-up", "category": "Arms"}]
            assert "equipment=1" in mock_get.call_args_list[-1].args[0]

    def test_returns_error_dict_on_exerciseinfo_request_failure(self):
        responses = [_response(MUSCLES)]

        def fake_get(*args, **kwargs):
            if responses:
                return responses.pop(0)
            raise wger_client.requests.RequestException("down")

        with patch.object(wger_client.requests, "get", side_effect=fake_get):
            result = wger_client.lookup_exercise("chest")
            assert result == {"error": "Failed to look up exercises: down"}


LEG_MUSCLES = {
    "results": [
        {"id": 10, "name": "Quadriceps femoris", "name_en": "Quads"},
        {"id": 11, "name": "Biceps femoris", "name_en": "Hamstrings"},
        {"id": 7, "name": "Gastrocnemius", "name_en": "Calves"},
        {"id": 8, "name": "Gluteus maximus", "name_en": "Glutes"},
    ]
}


class TestMuscleSynonyms:
    def test_expands_compound_term_and_dedupes(self):
        responses = [
            _response(LEG_MUSCLES),
            _response(_exerciseinfo(["Squat", "Shared Exercise"])),
            _response(_exerciseinfo(["Deadlift"])),
            _response(_exerciseinfo(["Calf Raise"])),
            _response(_exerciseinfo(["Shared Exercise", "Hip Thrust"])),
        ]
        with patch.object(wger_client.requests, "get", side_effect=responses):
            result = wger_client.lookup_exercise("legs", limit=10)

        names = [exercise["name"] for exercise in result]
        assert names.count("Shared Exercise") == 1
        assert set(names) == {"Squat", "Shared Exercise", "Deadlift", "Calf Raise", "Hip Thrust"}

    def test_respects_limit_across_component_muscles(self):
        responses = [
            _response(LEG_MUSCLES),
            _response(_exerciseinfo(["Squat", "Lunge"])),
            _response(_exerciseinfo(["Deadlift"])),
            _response(_exerciseinfo(["Calf Raise"])),
            _response(_exerciseinfo(["Hip Thrust"])),
        ]
        with patch.object(wger_client.requests, "get", side_effect=responses):
            result = wger_client.lookup_exercise("legs", limit=2)

        assert len(result) == 2

    def test_returns_error_when_all_component_lookups_fail(self):
        error = wger_client.requests.RequestException("down")
        with patch.object(wger_client.requests, "get", side_effect=error):
            result = wger_client.lookup_exercise("legs")

        assert isinstance(result, dict)
        assert "error" in result


class TestLookupExerciseProfile:
    def test_uses_profile_equipment_when_none_given(self, tmp_path):
        profile_file = tmp_path / "profile.json"
        profile_file.write_text(json.dumps({"equipment": "dumbbell"}))
        exercises = _exerciseinfo(["Push-up"])
        responses = [_response(MUSCLES), _response(EQUIPMENT), _response(exercises)]
        with patch.object(wger_client.requests, "get", side_effect=responses) as mock_get:
            result = wger_client.lookup_exercise("chest", profile_file=profile_file)
            assert result == [{"name": "Push-up", "category": "Arms"}]
            assert "equipment=1" in mock_get.call_args_list[-1].args[0]

    def test_explicit_equipment_overrides_profile(self, tmp_path):
        profile_file = tmp_path / "profile.json"
        profile_file.write_text(json.dumps({"equipment": "bodyweight"}))
        exercises = _exerciseinfo(["Push-up"])
        responses = [_response(MUSCLES), _response(EQUIPMENT), _response(exercises)]
        with patch.object(wger_client.requests, "get", side_effect=responses) as mock_get:
            wger_client.lookup_exercise("chest", equipment="dumbbell", profile_file=profile_file)
            assert "equipment=1" in mock_get.call_args_list[-1].args[0]

    def test_filters_out_excluded_exercise(self, tmp_path):
        profile_file = tmp_path / "profile.json"
        profile_file.write_text(json.dumps({"exclusions": ["Push-up"]}))
        exercises = _exerciseinfo(["Push-up", "Bench Press"])
        responses = [_response(MUSCLES), _response(exercises)]
        with patch.object(wger_client.requests, "get", side_effect=responses):
            result = wger_client.lookup_exercise("chest", profile_file=profile_file)
            assert result == [{"name": "Bench Press", "category": "Arms"}]


class TestBuildWorkoutPlan:
    def test_dedupes_exercises_across_muscle_groups(self, tmp_path):
        exercises = _exerciseinfo(["Bench Press"])
        responses = [_response(MUSCLES), _response(exercises), _response(exercises)]
        with patch.object(wger_client.requests, "get", side_effect=responses):
            plan = wger_client.build_workout_plan(
                ["chest", "biceps"], exercises_per_muscle=1, history_file=tmp_path / "history.json"
            )
            assert plan[0]["exercises"] == [
                {
                    "name": "Bench Press",
                    "category": "Arms",
                    "sets": 3,
                    "reps": "8-12",
                    "rest_seconds": 90,
                }
            ]
            assert plan[1]["exercises"] == []

    def test_applies_goal_specific_scheme(self, tmp_path):
        exercises = _exerciseinfo(["Squat"])
        responses = [_response(MUSCLES), _response(exercises)]
        with patch.object(wger_client.requests, "get", side_effect=responses):
            plan = wger_client.build_workout_plan(
                ["chest"], exercises_per_muscle=1, goal="strength", history_file=tmp_path / "history.json"
            )
            exercise = plan[0]["exercises"][0]
            assert exercise["sets"] == 5
            assert exercise["reps"] == "5"
            assert exercise["rest_seconds"] == 180

    def test_unknown_goal_falls_back_to_default(self, tmp_path):
        exercises = _exerciseinfo(["Squat"])
        responses = [_response(MUSCLES), _response(exercises)]
        with patch.object(wger_client.requests, "get", side_effect=responses):
            plan = wger_client.build_workout_plan(
                ["chest"], exercises_per_muscle=1, goal="yoga", history_file=tmp_path / "history.json"
            )
            exercise = plan[0]["exercises"][0]
            assert exercise["sets"] == wger_client.REP_SCHEMES[wger_client.DEFAULT_GOAL]["sets"]

    def test_records_error_for_failed_muscle_group(self, tmp_path):
        with patch.object(
            wger_client.requests, "get", side_effect=wger_client.requests.RequestException("down")
        ):
            plan = wger_client.build_workout_plan(["chest"], history_file=tmp_path / "history.json")
            assert "error" in plan[0]

    def test_save_to_json(self, tmp_path):
        exercises = _exerciseinfo(["Bench Press"])
        responses = [_response(MUSCLES), _response(exercises)]
        out_file = tmp_path / "plan.json"
        with patch.object(wger_client.requests, "get", side_effect=responses):
            result = wger_client.build_workout_plan(
                ["chest"],
                exercises_per_muscle=1,
                save_to=str(out_file),
                history_file=tmp_path / "history.json",
            )
            assert result["saved_to"] == str(out_file)
            assert out_file.exists()
            assert "Bench Press" in out_file.read_text()

    def test_save_to_markdown(self, tmp_path):
        exercises = _exerciseinfo(["Bench Press"])
        responses = [_response(MUSCLES), _response(exercises)]
        out_file = tmp_path / "plan.md"
        with patch.object(wger_client.requests, "get", side_effect=responses):
            wger_client.build_workout_plan(
                ["chest"],
                exercises_per_muscle=1,
                save_to=str(out_file),
                history_file=tmp_path / "history.json",
            )
            content = out_file.read_text()
            assert "# Workout Plan" in content
            assert "3 sets x 8-12 reps, rest 90s" in content

    def test_save_to_markdown_with_error_entry(self, tmp_path):
        out_file = tmp_path / "plan.md"
        with patch.object(
            wger_client.requests, "get", side_effect=wger_client.requests.RequestException("down")
        ):
            wger_client.build_workout_plan(
                ["chest"], save_to=str(out_file), history_file=tmp_path / "history.json"
            )
            content = out_file.read_text()
            assert "- Error:" in content

    def test_save_error_is_reported(self, tmp_path):
        exercises = _exerciseinfo(["Bench Press"])
        responses = [_response(MUSCLES), _response(exercises)]
        out_file = tmp_path / "plan.json"
        with patch.object(wger_client.requests, "get", side_effect=responses):
            with patch.object(wger_client.Path, "write_text", side_effect=OSError("disk full")):
                result = wger_client.build_workout_plan(
                    ["chest"],
                    exercises_per_muscle=1,
                    save_to=str(out_file),
                    history_file=tmp_path / "history.json",
                )
                assert "save_error" in result
                assert "disk full" in result["save_error"]


class TestBuildWorkoutPlanProfile:
    def test_uses_profile_goal_when_none_given(self, tmp_path):
        profile_file = tmp_path / "profile.json"
        profile_file.write_text(json.dumps({"goal": "strength"}))
        exercises = _exerciseinfo(["Squat"])
        responses = [_response(MUSCLES), _response(exercises)]
        with patch.object(wger_client.requests, "get", side_effect=responses):
            plan = wger_client.build_workout_plan(
                ["chest"],
                exercises_per_muscle=1,
                history_file=tmp_path / "history.json",
                profile_file=profile_file,
            )
            exercise = plan[0]["exercises"][0]
            assert exercise["sets"] == 5
            assert exercise["reps"] == "5"

    def test_explicit_goal_overrides_profile(self, tmp_path):
        profile_file = tmp_path / "profile.json"
        profile_file.write_text(json.dumps({"goal": "strength"}))
        exercises = _exerciseinfo(["Squat"])
        responses = [_response(MUSCLES), _response(exercises)]
        with patch.object(wger_client.requests, "get", side_effect=responses):
            plan = wger_client.build_workout_plan(
                ["chest"],
                exercises_per_muscle=1,
                goal="endurance",
                history_file=tmp_path / "history.json",
                profile_file=profile_file,
            )
            exercise = plan[0]["exercises"][0]
            assert exercise["sets"] == 3
            assert exercise["reps"] == "15-20"


class TestBuildWorkoutPlanProgression:
    def test_adds_progression_note_for_previously_logged_exercise(self, tmp_path):
        history_file = tmp_path / "history.json"
        history_file.write_text(
            json.dumps(
                [{"plan": [{"muscle_group": "chest", "exercises": [{"name": "Bench Press"}]}]}]
            )
        )
        exercises = _exerciseinfo(["Bench Press"])
        responses = [_response(MUSCLES), _response(exercises)]
        with patch.object(wger_client.requests, "get", side_effect=responses):
            plan = wger_client.build_workout_plan(
                ["chest"], exercises_per_muscle=1, history_file=history_file
            )
            assert "Logged once before" in plan[0]["exercises"][0]["progression"]

    def test_progression_note_pluralizes_for_repeat_logs(self, tmp_path):
        history_file = tmp_path / "history.json"
        history_file.write_text(
            json.dumps(
                [
                    {"plan": [{"muscle_group": "chest", "exercises": [{"name": "Bench Press"}]}]},
                    {"plan": [{"muscle_group": "chest", "exercises": [{"name": "Bench Press"}]}]},
                ]
            )
        )
        exercises = _exerciseinfo(["Bench Press"])
        responses = [_response(MUSCLES), _response(exercises)]
        with patch.object(wger_client.requests, "get", side_effect=responses):
            plan = wger_client.build_workout_plan(
                ["chest"], exercises_per_muscle=1, history_file=history_file
            )
            assert "Logged 2 times before" in plan[0]["exercises"][0]["progression"]

    def test_no_progression_note_for_new_exercise(self, tmp_path):
        exercises = _exerciseinfo(["Bench Press"])
        responses = [_response(MUSCLES), _response(exercises)]
        with patch.object(wger_client.requests, "get", side_effect=responses):
            plan = wger_client.build_workout_plan(
                ["chest"], exercises_per_muscle=1, history_file=tmp_path / "history.json"
            )
            assert "progression" not in plan[0]["exercises"][0]

    def test_progression_note_appears_in_markdown(self, tmp_path):
        history_file = tmp_path / "history.json"
        history_file.write_text(
            json.dumps(
                [{"plan": [{"muscle_group": "chest", "exercises": [{"name": "Bench Press"}]}]}]
            )
        )
        exercises = _exerciseinfo(["Bench Press"])
        responses = [_response(MUSCLES), _response(exercises)]
        out_file = tmp_path / "plan.md"
        with patch.object(wger_client.requests, "get", side_effect=responses):
            wger_client.build_workout_plan(
                ["chest"], exercises_per_muscle=1, save_to=str(out_file), history_file=history_file
            )
            content = out_file.read_text()
            assert "Logged once before" in content

    def test_real_progression_note_from_logged_sets(self, tmp_path):
        history_file = tmp_path / "history.json"
        history_file.write_text(
            json.dumps(
                [
                    {
                        "plan": [{"muscle_group": "chest", "exercises": [{"name": "Bench Press"}]}],
                        "sets": [{"exercise": "Bench Press", "weight": 135, "reps": 8}],
                    }
                ]
            )
        )
        exercises = _exerciseinfo(["Bench Press"])
        responses = [_response(MUSCLES), _response(exercises)]
        with patch.object(wger_client.requests, "get", side_effect=responses):
            plan = wger_client.build_workout_plan(
                ["chest"], exercises_per_muscle=1, history_file=history_file
            )
            assert "Last time: 135 x 8 reps" in plan[0]["exercises"][0]["progression"]

    def test_real_progression_note_includes_unit(self, tmp_path):
        history_file = tmp_path / "history.json"
        history_file.write_text(
            json.dumps(
                [
                    {
                        "plan": [{"muscle_group": "chest", "exercises": [{"name": "Bench Press"}]}],
                        "sets": [{"exercise": "Bench Press", "weight": 135, "reps": 8, "unit": "lb"}],
                    }
                ]
            )
        )
        exercises = _exerciseinfo(["Bench Press"])
        responses = [_response(MUSCLES), _response(exercises)]
        with patch.object(wger_client.requests, "get", side_effect=responses):
            plan = wger_client.build_workout_plan(
                ["chest"], exercises_per_muscle=1, history_file=history_file
            )
            assert "Last time: 135 lb x 8 reps" in plan[0]["exercises"][0]["progression"]

    def test_real_progression_note_weight_only(self, tmp_path):
        history_file = tmp_path / "history.json"
        history_file.write_text(
            json.dumps(
                [
                    {
                        "plan": [{"muscle_group": "chest", "exercises": [{"name": "Bench Press"}]}],
                        "sets": [{"exercise": "Bench Press", "weight": 135}],
                    }
                ]
            )
        )
        exercises = _exerciseinfo(["Bench Press"])
        responses = [_response(MUSCLES), _response(exercises)]
        with patch.object(wger_client.requests, "get", side_effect=responses):
            plan = wger_client.build_workout_plan(
                ["chest"], exercises_per_muscle=1, history_file=history_file
            )
            assert "Last time: 135" in plan[0]["exercises"][0]["progression"]

    def test_real_progression_note_reps_only(self, tmp_path):
        history_file = tmp_path / "history.json"
        history_file.write_text(
            json.dumps(
                [
                    {
                        "plan": [{"muscle_group": "chest", "exercises": [{"name": "Bench Press"}]}],
                        "sets": [{"exercise": "Bench Press", "reps": 8}],
                    }
                ]
            )
        )
        exercises = _exerciseinfo(["Bench Press"])
        responses = [_response(MUSCLES), _response(exercises)]
        with patch.object(wger_client.requests, "get", side_effect=responses):
            plan = wger_client.build_workout_plan(
                ["chest"], exercises_per_muscle=1, history_file=history_file
            )
            assert "Last time: 8 reps" in plan[0]["exercises"][0]["progression"]


class TestSubstituteExercise:
    def test_returns_error_when_no_plan_built(self):
        wger_client._last_plan = None
        assert wger_client.substitute_exercise("Bench Press") == {
            "error": "No workout plan has been built yet."
        }

    def test_returns_error_when_exercise_not_in_plan(self):
        wger_client._last_plan = [{"muscle_group": "chest", "exercises": [{"name": "Bench Press"}]}]
        result = wger_client.substitute_exercise("Squat")
        assert result == {"error": "Squat isn't in your current plan."}

    def test_replaces_exercise_with_alternative(self):
        wger_client._last_plan = [
            {
                "muscle_group": "chest",
                "exercises": [{"name": "Bench Press", "sets": 3, "reps": "8-12", "rest_seconds": 90}],
            }
        ]
        exercises = _exerciseinfo(["Bench Press", "Dips"])
        responses = [_response(MUSCLES), _response(exercises)]
        with patch.object(wger_client.requests, "get", side_effect=responses):
            result = wger_client.substitute_exercise("Bench Press")

        assert result["replaced"] == "Bench Press"
        assert result["with"]["name"] == "Dips"
        assert result["with"]["sets"] == 3
        assert wger_client._last_plan[0]["exercises"][0]["name"] == "Dips"

    def test_returns_error_when_no_alternative_available(self):
        wger_client._last_plan = [
            {"muscle_group": "chest", "exercises": [{"name": "Bench Press", "sets": 3}]}
        ]
        exercises = _exerciseinfo(["Bench Press"])
        responses = [_response(MUSCLES), _response(exercises)]
        with patch.object(wger_client.requests, "get", side_effect=responses):
            result = wger_client.substitute_exercise("Bench Press")

        assert result == {"error": "No alternative found for Bench Press."}

    def test_is_case_insensitive_on_exercise_name(self):
        wger_client._last_plan = [
            {"muscle_group": "chest", "exercises": [{"name": "Bench Press", "sets": 3}]}
        ]
        exercises = _exerciseinfo(["Bench Press", "Dips"])
        responses = [_response(MUSCLES), _response(exercises)]
        with patch.object(wger_client.requests, "get", side_effect=responses):
            result = wger_client.substitute_exercise("bench press")

        assert result["replaced"] == "Bench Press"

    def test_returns_error_dict_when_alternative_lookup_fails(self):
        wger_client._last_plan = [
            {"muscle_group": "chest", "exercises": [{"name": "Bench Press", "sets": 3}]}
        ]
        with patch.object(
            wger_client.requests, "get", side_effect=wger_client.requests.RequestException("down")
        ):
            result = wger_client.substitute_exercise("Bench Press")

        assert "error" in result


class TestBuildProgram:
    def test_builds_flat_plan_tagged_with_day(self, tmp_path):
        chest = _exerciseinfo(["Bench Press"])
        biceps = _exerciseinfo(["Row"])
        responses = [_response(MUSCLES), _response(chest), _response(biceps)]
        with patch.object(wger_client.requests, "get", side_effect=responses):
            program = wger_client.build_program(
                [
                    {"day": "Push", "muscle_groups": ["chest"]},
                    {"day": "Pull", "muscle_groups": ["biceps"]},
                ],
                exercises_per_muscle=1,
                history_file=tmp_path / "history.json",
            )

        assert program[0]["day"] == "Push"
        assert program[0]["exercises"][0]["name"] == "Bench Press"
        assert program[1]["day"] == "Pull"
        assert program[1]["exercises"][0]["name"] == "Row"

    def test_sets_last_plan_for_logging(self, tmp_path):
        exercises = _exerciseinfo(["Bench Press"])
        responses = [_response(MUSCLES), _response(exercises)]
        with patch.object(wger_client.requests, "get", side_effect=responses):
            program = wger_client.build_program(
                [{"day": "Push", "muscle_groups": ["chest"]}],
                exercises_per_muscle=1,
                history_file=tmp_path / "history.json",
            )

        assert wger_client._last_plan == program

    def test_save_to_markdown_groups_by_day(self, tmp_path):
        exercises = _exerciseinfo(["Bench Press"])
        responses = [_response(MUSCLES), _response(exercises)]
        out_file = tmp_path / "program.md"
        with patch.object(wger_client.requests, "get", side_effect=responses):
            wger_client.build_program(
                [{"day": "Push", "muscle_groups": ["chest"]}],
                exercises_per_muscle=1,
                save_to=str(out_file),
                history_file=tmp_path / "history.json",
            )

        content = out_file.read_text()
        assert "## Push: Chest" in content

    def test_save_error_is_reported(self, tmp_path):
        exercises = _exerciseinfo(["Bench Press"])
        responses = [_response(MUSCLES), _response(exercises)]
        out_file = tmp_path / "program.json"
        with patch.object(wger_client.requests, "get", side_effect=responses):
            with patch.object(wger_client.Path, "write_text", side_effect=OSError("disk full")):
                result = wger_client.build_program(
                    [{"day": "Push", "muscle_groups": ["chest"]}],
                    exercises_per_muscle=1,
                    save_to=str(out_file),
                    history_file=tmp_path / "history.json",
                )
                assert "save_error" in result
                assert "disk full" in result["save_error"]
