import json

import pytest

import history
import wger_client


@pytest.fixture(autouse=True)
def reset_last_plan():
    wger_client._last_plan = None
    yield
    wger_client._last_plan = None


class TestLogLastWorkout:
    def test_returns_error_when_no_plan_built(self, tmp_path):
        result = history.log_last_workout(history_file=tmp_path / "history.json")
        assert result == {"error": "No workout plan has been built yet."}

    def test_logs_the_last_built_plan(self, tmp_path):
        wger_client._last_plan = [{"muscle_group": "chest", "exercises": []}]
        history_file = tmp_path / "history.json"

        entry = history.log_last_workout(notes="felt good", history_file=history_file)

        assert entry["plan"] == wger_client._last_plan
        assert entry["notes"] == "felt good"
        assert "logged_at" in entry
        saved = json.loads(history_file.read_text())
        assert saved == [entry]

    def test_appends_to_existing_history(self, tmp_path):
        history_file = tmp_path / "history.json"
        history_file.write_text(json.dumps([{"plan": "old"}]))
        wger_client._last_plan = [{"muscle_group": "legs", "exercises": []}]

        history.log_last_workout(history_file=history_file)

        saved = json.loads(history_file.read_text())
        assert len(saved) == 2
        assert saved[0] == {"plan": "old"}

    def test_returns_error_when_write_fails(self, tmp_path, monkeypatch):
        wger_client._last_plan = [{"muscle_group": "chest", "exercises": []}]
        history_file = tmp_path / "history.json"

        def broken_write_text(self, *args, **kwargs):
            raise OSError("disk full")

        monkeypatch.setattr(type(history_file), "write_text", broken_write_text)

        result = history.log_last_workout(history_file=history_file)
        assert "error" in result


class TestGetWorkoutHistory:
    def test_returns_empty_list_when_no_file(self, tmp_path):
        assert history.get_workout_history(history_file=tmp_path / "missing.json") == []

    def test_returns_empty_list_on_corrupted_file(self, tmp_path):
        history_file = tmp_path / "history.json"
        history_file.write_text("not json")
        assert history.get_workout_history(history_file=history_file) == []

    def test_respects_limit(self, tmp_path):
        history_file = tmp_path / "history.json"
        history_file.write_text(json.dumps([{"n": i} for i in range(10)]))

        result = history.get_workout_history(limit=3, history_file=history_file)

        assert result == [{"n": 7}, {"n": 8}, {"n": 9}]

    def test_returns_all_when_limit_is_zero_or_none(self, tmp_path):
        history_file = tmp_path / "history.json"
        history_file.write_text(json.dumps([{"n": i} for i in range(3)]))

        assert len(history.get_workout_history(limit=None, history_file=history_file)) == 3


class TestGetExerciseProgress:
    def test_returns_zero_when_no_history(self, tmp_path):
        history_file = tmp_path / "missing.json"
        assert history.get_exercise_progress("Bench Press", history_file=history_file) == 0

    def test_counts_matching_exercise_across_entries(self, tmp_path):
        history_file = tmp_path / "history.json"
        history_file.write_text(
            json.dumps(
                [
                    {"plan": [{"muscle_group": "chest", "exercises": [{"name": "Bench Press"}]}]},
                    {"plan": [{"muscle_group": "chest", "exercises": [{"name": "Push-up"}]}]},
                    {
                        "plan": [
                            {
                                "muscle_group": "chest",
                                "exercises": [{"name": "Bench Press"}, {"name": "Dip"}],
                            }
                        ]
                    },
                ]
            )
        )

        assert history.get_exercise_progress("Bench Press", history_file=history_file) == 2
        assert history.get_exercise_progress("Dip", history_file=history_file) == 1
        assert history.get_exercise_progress("Overhead Press", history_file=history_file) == 0

    def test_handles_entries_with_error_muscle_groups(self, tmp_path):
        history_file = tmp_path / "history.json"
        history_file.write_text(
            json.dumps([{"plan": [{"muscle_group": "legs", "error": "boom"}]}])
        )

        assert history.get_exercise_progress("Squat", history_file=history_file) == 0
