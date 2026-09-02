import json

import pytest

import tools
import wger_client


@pytest.fixture(autouse=True)
def reset_last_plan():
    wger_client._last_plan = None
    yield
    wger_client._last_plan = None


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
