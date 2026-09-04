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

    def test_logs_sets_when_given(self, tmp_path):
        wger_client._last_plan = [{"muscle_group": "chest", "exercises": []}]
        history_file = tmp_path / "history.json"
        sets = [{"exercise": "Bench Press", "weight": 135, "reps": 8}]

        entry = history.log_last_workout(sets=sets, history_file=history_file)

        assert entry["sets"] == sets

    def test_defaults_sets_to_empty_list(self, tmp_path):
        wger_client._last_plan = [{"muscle_group": "chest", "exercises": []}]
        history_file = tmp_path / "history.json"

        entry = history.log_last_workout(history_file=history_file)

        assert entry["sets"] == []

    def test_creates_parent_directory(self, tmp_path):
        wger_client._last_plan = [{"muscle_group": "chest", "exercises": []}]
        history_file = tmp_path / "nested" / "dir" / "history.json"

        history.log_last_workout(history_file=history_file)

        assert history_file.exists()

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

    def test_original_file_untouched_when_write_fails(self, tmp_path, monkeypatch):
        history_file = tmp_path / "history.json"
        history_file.write_text(json.dumps([{"plan": "old"}]))
        wger_client._last_plan = [{"muscle_group": "chest", "exercises": []}]

        def broken_write_text(self, *args, **kwargs):
            raise OSError("disk full")

        monkeypatch.setattr(type(history_file), "write_text", broken_write_text)

        history.log_last_workout(history_file=history_file)

        assert json.loads(history_file.read_text()) == [{"plan": "old"}]
        assert not (tmp_path / "history.json.tmp").exists()


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


class TestGetLastPerformance:
    def test_returns_none_when_no_history(self, tmp_path):
        history_file = tmp_path / "missing.json"
        assert history.get_last_performance("Bench Press", history_file=history_file) is None

    def test_returns_none_when_exercise_never_logged_with_sets(self, tmp_path):
        history_file = tmp_path / "history.json"
        history_file.write_text(json.dumps([{"plan": [], "sets": []}]))
        assert history.get_last_performance("Bench Press", history_file=history_file) is None

    def test_returns_most_recent_logged_performance(self, tmp_path):
        history_file = tmp_path / "history.json"
        history_file.write_text(
            json.dumps(
                [
                    {"plan": [], "sets": [{"exercise": "Bench Press", "weight": 125, "reps": 8}]},
                    {"plan": [], "sets": [{"exercise": "Bench Press", "weight": 135, "reps": 6}]},
                ]
            )
        )

        result = history.get_last_performance("Bench Press", history_file=history_file)

        assert result == {"weight": 135, "reps": 6, "unit": None}

    def test_includes_unit_when_logged(self, tmp_path):
        history_file = tmp_path / "history.json"
        history_file.write_text(
            json.dumps(
                [{"plan": [], "sets": [{"exercise": "Bench Press", "weight": 135, "reps": 8, "unit": "lb"}]}]
            )
        )

        result = history.get_last_performance("Bench Press", history_file=history_file)

        assert result == {"weight": 135, "reps": 8, "unit": "lb"}

    def test_ignores_other_exercises(self, tmp_path):
        history_file = tmp_path / "history.json"
        history_file.write_text(
            json.dumps([{"plan": [], "sets": [{"exercise": "Squat", "weight": 185, "reps": 5}]}])
        )

        assert history.get_last_performance("Bench Press", history_file=history_file) is None


class TestUpdateWorkout:
    def test_returns_error_when_no_history(self, tmp_path):
        result = history.update_workout(notes="oops", history_file=tmp_path / "missing.json")
        assert result == {"error": "No workout history to update."}

    def test_updates_most_recent_when_no_timestamp_given(self, tmp_path):
        history_file = tmp_path / "history.json"
        history_file.write_text(
            json.dumps(
                [
                    {"logged_at": "2026-01-01T00:00:00", "notes": "first", "sets": []},
                    {"logged_at": "2026-01-02T00:00:00", "notes": "second", "sets": []},
                ]
            )
        )

        result = history.update_workout(notes="fixed", history_file=history_file)

        assert result["notes"] == "fixed"
        assert result["logged_at"] == "2026-01-02T00:00:00"
        saved = json.loads(history_file.read_text())
        assert saved[0]["notes"] == "first"
        assert saved[1]["notes"] == "fixed"

    def test_updates_entry_by_timestamp(self, tmp_path):
        history_file = tmp_path / "history.json"
        history_file.write_text(
            json.dumps(
                [
                    {"logged_at": "2026-01-01T00:00:00", "notes": "first", "sets": []},
                    {"logged_at": "2026-01-02T00:00:00", "notes": "second", "sets": []},
                ]
            )
        )

        result = history.update_workout(
            logged_at="2026-01-01T00:00:00", notes="fixed", history_file=history_file
        )

        assert result["notes"] == "fixed"
        saved = json.loads(history_file.read_text())
        assert saved[0]["notes"] == "fixed"
        assert saved[1]["notes"] == "second"

    def test_returns_error_for_unknown_timestamp(self, tmp_path):
        history_file = tmp_path / "history.json"
        history_file.write_text(json.dumps([{"logged_at": "2026-01-01T00:00:00", "notes": "first"}]))

        result = history.update_workout(logged_at="nope", notes="fixed", history_file=history_file)

        assert result == {"error": "No workout found with logged_at='nope'."}

    def test_replaces_sets(self, tmp_path):
        history_file = tmp_path / "history.json"
        history_file.write_text(
            json.dumps([{"logged_at": "2026-01-01T00:00:00", "sets": [{"exercise": "Squat"}]}])
        )
        new_sets = [{"exercise": "Bench Press", "weight": 135, "reps": 8}]

        result = history.update_workout(sets=new_sets, history_file=history_file)

        assert result["sets"] == new_sets

    def test_returns_error_when_write_fails(self, tmp_path, monkeypatch):
        history_file = tmp_path / "history.json"
        history_file.write_text(json.dumps([{"logged_at": "2026-01-01T00:00:00", "notes": "old"}]))

        def broken_write_text(self, *args, **kwargs):
            raise OSError("disk full")

        monkeypatch.setattr(type(history_file), "write_text", broken_write_text)

        result = history.update_workout(notes="new", history_file=history_file)
        assert "error" in result


class TestDeleteWorkout:
    def test_returns_error_when_no_history(self, tmp_path):
        result = history.delete_workout(history_file=tmp_path / "missing.json")
        assert result == {"error": "No workout history to delete from."}

    def test_deletes_most_recent_when_no_timestamp_given(self, tmp_path):
        history_file = tmp_path / "history.json"
        history_file.write_text(
            json.dumps(
                [
                    {"logged_at": "2026-01-01T00:00:00"},
                    {"logged_at": "2026-01-02T00:00:00"},
                ]
            )
        )

        result = history.delete_workout(history_file=history_file)

        assert result["deleted"]["logged_at"] == "2026-01-02T00:00:00"
        saved = json.loads(history_file.read_text())
        assert len(saved) == 1
        assert saved[0]["logged_at"] == "2026-01-01T00:00:00"

    def test_deletes_entry_by_timestamp(self, tmp_path):
        history_file = tmp_path / "history.json"
        history_file.write_text(
            json.dumps(
                [
                    {"logged_at": "2026-01-01T00:00:00"},
                    {"logged_at": "2026-01-02T00:00:00"},
                ]
            )
        )

        history.delete_workout(logged_at="2026-01-01T00:00:00", history_file=history_file)

        saved = json.loads(history_file.read_text())
        assert len(saved) == 1
        assert saved[0]["logged_at"] == "2026-01-02T00:00:00"

    def test_returns_error_for_unknown_timestamp(self, tmp_path):
        history_file = tmp_path / "history.json"
        history_file.write_text(json.dumps([{"logged_at": "2026-01-01T00:00:00"}]))

        result = history.delete_workout(logged_at="nope", history_file=history_file)

        assert result == {"error": "No workout found with logged_at='nope'."}

    def test_returns_error_when_write_fails(self, tmp_path, monkeypatch):
        history_file = tmp_path / "history.json"
        history_file.write_text(json.dumps([{"logged_at": "2026-01-01T00:00:00"}]))

        def broken_write_text(self, *args, **kwargs):
            raise OSError("disk full")

        monkeypatch.setattr(type(history_file), "write_text", broken_write_text)

        result = history.delete_workout(history_file=history_file)
        assert "error" in result


class TestArchiveOverflow:
    def test_no_archiving_below_threshold(self, tmp_path, monkeypatch):
        monkeypatch.setattr(history, "MAX_ACTIVE_ENTRIES", 3)
        history_file = tmp_path / "history.json"
        history_file.write_text(json.dumps([{"logged_at": str(i)} for i in range(2)]))
        wger_client._last_plan = [{"muscle_group": "chest", "exercises": []}]

        history.log_last_workout(history_file=history_file)

        assert len(json.loads(history_file.read_text())) == 3
        assert not history._archive_path(history_file).exists()

    def test_archives_oldest_entries_once_over_threshold(self, tmp_path, monkeypatch):
        monkeypatch.setattr(history, "MAX_ACTIVE_ENTRIES", 2)
        history_file = tmp_path / "history.json"
        history_file.write_text(json.dumps([{"logged_at": str(i)} for i in range(3)]))
        wger_client._last_plan = [{"muscle_group": "chest", "exercises": []}]

        history.log_last_workout(history_file=history_file)

        active = json.loads(history_file.read_text())
        assert len(active) == 2

        archive = json.loads(history._archive_path(history_file).read_text())
        assert [e["logged_at"] for e in archive] == ["0", "1"]

    def test_archived_entries_stay_out_of_active_file_across_calls(self, tmp_path, monkeypatch):
        monkeypatch.setattr(history, "MAX_ACTIVE_ENTRIES", 2)
        history_file = tmp_path / "history.json"
        wger_client._last_plan = [{"muscle_group": "chest", "exercises": []}]

        history.log_last_workout(history_file=history_file)
        history.log_last_workout(history_file=history_file)
        history.log_last_workout(history_file=history_file)

        assert len(json.loads(history_file.read_text())) == 2
        assert len(json.loads(history._archive_path(history_file).read_text())) == 1

    def test_keeps_everything_active_when_archive_write_fails(self, tmp_path, monkeypatch):
        monkeypatch.setattr(history, "MAX_ACTIVE_ENTRIES", 2)
        history_file = tmp_path / "history.json"
        history_file.write_text(json.dumps([{"logged_at": str(i)} for i in range(3)]))
        wger_client._last_plan = [{"muscle_group": "chest", "exercises": []}]

        def broken_write_text(self, *args, **kwargs):
            raise OSError("disk full")

        monkeypatch.setattr(type(history_file), "write_text", broken_write_text)

        history.log_last_workout(history_file=history_file)

        assert not history._archive_path(history_file).exists()
