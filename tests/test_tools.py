import json
from unittest.mock import patch

import pytest

import tools
import wger_client


def _response(json_data):
    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return json_data

    return FakeResponse()


MUSCLES = {"results": [{"id": 10, "name": "Pectoralis major", "name_en": "Chest"}]}


def _exerciseinfo(names):
    return {
        "results": [
            {
                "translations": [{"language": wger_client.ENGLISH_LANGUAGE_ID, "name": name}],
                "category": {"name": "Chest"},
            }
            for name in names
        ]
    }


@pytest.fixture(autouse=True)
def reset_last_plan():
    wger_client._last_plan = None
    wger_client._muscle_cache = None
    wger_client._equipment_cache = None
    yield
    wger_client._last_plan = None
    wger_client._muscle_cache = None
    wger_client._equipment_cache = None


class TestBuildDispatch:
    def test_get_profile_reads_from_bound_path(self, tmp_path):
        profile_file = tmp_path / "profile.json"
        profile_file.write_text(json.dumps({"equipment": "dumbbell"}))
        history_file = tmp_path / "history.json"

        dispatch = tools.build_dispatch(profile_file, history_file)

        assert dispatch["get_profile"]()["equipment"] == "dumbbell"

    def test_update_profile_writes_to_bound_path(self, tmp_path):
        profile_file = tmp_path / "profile.json"
        history_file = tmp_path / "history.json"

        dispatch = tools.build_dispatch(profile_file, history_file)
        dispatch["update_profile"](equipment="barbell")

        assert json.loads(profile_file.read_text())["equipment"] == "barbell"

    def test_log_last_workout_writes_to_bound_path(self, tmp_path):
        profile_file = tmp_path / "profile.json"
        history_file = tmp_path / "history.json"
        wger_client._last_plan = [{"muscle_group": "chest", "exercises": []}]

        dispatch = tools.build_dispatch(profile_file, history_file)
        dispatch["log_last_workout"]()

        assert history_file.exists()

    def test_get_workout_history_reads_from_bound_path(self, tmp_path):
        profile_file = tmp_path / "profile.json"
        history_file = tmp_path / "history.json"
        history_file.write_text(json.dumps([{"plan": "old"}]))

        dispatch = tools.build_dispatch(profile_file, history_file)

        assert dispatch["get_workout_history"]() == [{"plan": "old"}]

    def test_find_muscle_id_and_find_equipment_id_are_unbound(self, tmp_path):
        dispatch = tools.build_dispatch(tmp_path / "profile.json", tmp_path / "history.json")
        assert dispatch["find_muscle_id"] is wger_client.find_muscle_id
        assert dispatch["find_equipment_id"] is wger_client.find_equipment_id

    def test_substitute_exercise_uses_bound_profile(self, tmp_path):
        profile_file = tmp_path / "profile.json"
        profile_file.write_text(json.dumps({"exclusions": ["Dips"]}))
        history_file = tmp_path / "history.json"
        wger_client._last_plan = [
            {"muscle_group": "chest", "exercises": [{"name": "Bench Press", "sets": 3}]}
        ]

        responses = [_response(MUSCLES), _response(_exerciseinfo(["Dips", "Push-up"]))]
        dispatch = tools.build_dispatch(profile_file, history_file)
        with patch.object(wger_client.requests, "get", side_effect=responses):
            result = dispatch["substitute_exercise"](exercise_name="Bench Press")

        assert result["with"]["name"] == "Push-up"

    def test_build_program_writes_to_bound_history(self, tmp_path):
        profile_file = tmp_path / "profile.json"
        history_file = tmp_path / "history.json"

        responses = [_response(MUSCLES), _response(_exerciseinfo(["Bench Press"]))]
        dispatch = tools.build_dispatch(profile_file, history_file)
        with patch.object(wger_client.requests, "get", side_effect=responses):
            dispatch["build_program"](days=[{"day": "Push", "muscle_groups": ["chest"]}])
        dispatch["log_last_workout"]()

        assert history_file.exists()
        saved = json.loads(history_file.read_text())
        assert saved[0]["plan"][0]["day"] == "Push"

    def test_reset_profile_writes_to_bound_path(self, tmp_path):
        profile_file = tmp_path / "profile.json"
        history_file = tmp_path / "history.json"
        profile_file.write_text(json.dumps({"equipment": "dumbbell", "goal": None, "exclusions": []}))

        dispatch = tools.build_dispatch(profile_file, history_file)
        result = dispatch["reset_profile"]()

        assert result == {"equipment": None, "goal": None, "exclusions": []}

    def test_update_workout_writes_to_bound_path(self, tmp_path):
        profile_file = tmp_path / "profile.json"
        history_file = tmp_path / "history.json"
        history_file.write_text(json.dumps([{"logged_at": "t1", "notes": "old", "sets": []}]))

        dispatch = tools.build_dispatch(profile_file, history_file)
        dispatch["update_workout"](notes="new")

        assert json.loads(history_file.read_text())[0]["notes"] == "new"

    def test_delete_workout_writes_to_bound_path(self, tmp_path):
        profile_file = tmp_path / "profile.json"
        history_file = tmp_path / "history.json"
        history_file.write_text(json.dumps([{"logged_at": "t1"}]))

        dispatch = tools.build_dispatch(profile_file, history_file)
        dispatch["delete_workout"]()

        assert json.loads(history_file.read_text()) == []
