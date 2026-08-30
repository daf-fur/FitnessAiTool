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
        responses = [
            _response(MUSCLES),
            wger_client.requests.RequestException("down"),
        ]

        def fake_get(*args, **kwargs):
            result = responses.pop(0)
            if isinstance(result, Exception):
                raise result
            return result

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
        responses = [_response(MUSCLES), wger_client.requests.RequestException("down")]

        def fake_get(*args, **kwargs):
            result = responses.pop(0)
            if isinstance(result, Exception):
                raise result
            return result

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


class TestBuildWorkoutPlan:
    def test_dedupes_exercises_across_muscle_groups(self):
        exercises = _exerciseinfo(["Bench Press"])
        responses = [_response(MUSCLES), _response(exercises), _response(exercises)]
        with patch.object(wger_client.requests, "get", side_effect=responses):
            plan = wger_client.build_workout_plan(["chest", "biceps"], exercises_per_muscle=1)
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

    def test_applies_goal_specific_scheme(self):
        exercises = _exerciseinfo(["Squat"])
        responses = [_response(MUSCLES), _response(exercises)]
        with patch.object(wger_client.requests, "get", side_effect=responses):
            plan = wger_client.build_workout_plan(["chest"], exercises_per_muscle=1, goal="strength")
            exercise = plan[0]["exercises"][0]
            assert exercise["sets"] == 5
            assert exercise["reps"] == "5"
            assert exercise["rest_seconds"] == 180

    def test_unknown_goal_falls_back_to_default(self):
        exercises = _exerciseinfo(["Squat"])
        responses = [_response(MUSCLES), _response(exercises)]
        with patch.object(wger_client.requests, "get", side_effect=responses):
            plan = wger_client.build_workout_plan(["chest"], exercises_per_muscle=1, goal="yoga")
            exercise = plan[0]["exercises"][0]
            assert exercise["sets"] == wger_client.REP_SCHEMES[wger_client.DEFAULT_GOAL]["sets"]

    def test_records_error_for_failed_muscle_group(self):
        with patch.object(
            wger_client.requests, "get", side_effect=wger_client.requests.RequestException("down")
        ):
            plan = wger_client.build_workout_plan(["chest"])
            assert "error" in plan[0]

    def test_save_to_json(self, tmp_path):
        exercises = _exerciseinfo(["Bench Press"])
        responses = [_response(MUSCLES), _response(exercises)]
        out_file = tmp_path / "plan.json"
        with patch.object(wger_client.requests, "get", side_effect=responses):
            result = wger_client.build_workout_plan(
                ["chest"], exercises_per_muscle=1, save_to=str(out_file)
            )
            assert result["saved_to"] == str(out_file)
            assert out_file.exists()
            assert "Bench Press" in out_file.read_text()

    def test_save_to_markdown(self, tmp_path):
        exercises = _exerciseinfo(["Bench Press"])
        responses = [_response(MUSCLES), _response(exercises)]
        out_file = tmp_path / "plan.md"
        with patch.object(wger_client.requests, "get", side_effect=responses):
            wger_client.build_workout_plan(["chest"], exercises_per_muscle=1, save_to=str(out_file))
            content = out_file.read_text()
            assert "# Workout Plan" in content
            assert "3 sets x 8-12 reps, rest 90s" in content

    def test_save_to_markdown_with_error_entry(self, tmp_path):
        out_file = tmp_path / "plan.md"
        with patch.object(
            wger_client.requests, "get", side_effect=wger_client.requests.RequestException("down")
        ):
            wger_client.build_workout_plan(["chest"], save_to=str(out_file))
            content = out_file.read_text()
            assert "- Error:" in content

    def test_save_error_is_reported(self, tmp_path):
        exercises = _exerciseinfo(["Bench Press"])
        responses = [_response(MUSCLES), _response(exercises)]
        out_file = tmp_path / "plan.json"
        with patch.object(wger_client.requests, "get", side_effect=responses):
            with patch.object(wger_client.Path, "write_text", side_effect=OSError("disk full")):
                result = wger_client.build_workout_plan(
                    ["chest"], exercises_per_muscle=1, save_to=str(out_file)
                )
                assert "save_error" in result
                assert "disk full" in result["save_error"]
