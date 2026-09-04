import json

import user_profile


class TestGetProfile:
    def test_returns_defaults_when_no_file(self, tmp_path):
        profile = user_profile.get_profile(profile_file=tmp_path / "missing.json")
        assert profile == {"equipment": None, "goal": None, "exclusions": []}

    def test_returns_defaults_on_corrupted_file(self, tmp_path):
        profile_file = tmp_path / "profile.json"
        profile_file.write_text("not json")
        profile = user_profile.get_profile(profile_file=profile_file)
        assert profile == {"equipment": None, "goal": None, "exclusions": []}

    def test_merges_saved_values_with_defaults(self, tmp_path):
        profile_file = tmp_path / "profile.json"
        profile_file.write_text(json.dumps({"equipment": "dumbbell"}))
        profile = user_profile.get_profile(profile_file=profile_file)
        assert profile == {"equipment": "dumbbell", "goal": None, "exclusions": []}


class TestUpdateProfile:
    def test_sets_equipment_and_goal(self, tmp_path):
        profile_file = tmp_path / "profile.json"
        profile = user_profile.update_profile(
            equipment="dumbbell", goal="strength", profile_file=profile_file
        )
        assert profile["equipment"] == "dumbbell"
        assert profile["goal"] == "strength"

    def test_persists_across_calls(self, tmp_path):
        profile_file = tmp_path / "profile.json"
        user_profile.update_profile(equipment="dumbbell", profile_file=profile_file)
        profile = user_profile.get_profile(profile_file=profile_file)
        assert profile["equipment"] == "dumbbell"

    def test_creates_parent_directory(self, tmp_path):
        profile_file = tmp_path / "nested" / "dir" / "profile.json"
        user_profile.update_profile(equipment="dumbbell", profile_file=profile_file)
        assert profile_file.exists()

    def test_adds_exclusions(self, tmp_path):
        profile_file = tmp_path / "profile.json"
        profile = user_profile.update_profile(
            add_exclusions=["Squat", "Overhead Press"], profile_file=profile_file
        )
        assert profile["exclusions"] == ["Overhead Press", "Squat"]

    def test_add_exclusions_merges_with_existing(self, tmp_path):
        profile_file = tmp_path / "profile.json"
        user_profile.update_profile(add_exclusions=["Squat"], profile_file=profile_file)
        profile = user_profile.update_profile(add_exclusions=["Deadlift"], profile_file=profile_file)
        assert profile["exclusions"] == ["Deadlift", "Squat"]

    def test_removes_exclusions_case_insensitively(self, tmp_path):
        profile_file = tmp_path / "profile.json"
        user_profile.update_profile(add_exclusions=["Squat", "Deadlift"], profile_file=profile_file)
        profile = user_profile.update_profile(remove_exclusions=["squat"], profile_file=profile_file)
        assert profile["exclusions"] == ["Deadlift"]

    def test_ignores_blank_exclusion_entries(self, tmp_path):
        profile_file = tmp_path / "profile.json"
        profile = user_profile.update_profile(add_exclusions=["  ", ""], profile_file=profile_file)
        assert profile["exclusions"] == []

    def test_returns_error_when_write_fails(self, tmp_path, monkeypatch):
        profile_file = tmp_path / "profile.json"

        def broken_write_text(self, *args, **kwargs):
            raise OSError("disk full")

        monkeypatch.setattr(type(profile_file), "write_text", broken_write_text)

        result = user_profile.update_profile(equipment="dumbbell", profile_file=profile_file)
        assert "error" in result

    def test_original_file_untouched_when_write_fails(self, tmp_path, monkeypatch):
        profile_file = tmp_path / "profile.json"
        profile_file.write_text(json.dumps({"equipment": "barbell", "goal": None, "exclusions": []}))

        def broken_write_text(self, *args, **kwargs):
            raise OSError("disk full")

        monkeypatch.setattr(type(profile_file), "write_text", broken_write_text)

        user_profile.update_profile(equipment="dumbbell", profile_file=profile_file)

        assert json.loads(profile_file.read_text())["equipment"] == "barbell"
        assert not (tmp_path / "profile.json.tmp").exists()


class TestResetProfile:
    def test_clears_saved_fields(self, tmp_path):
        profile_file = tmp_path / "profile.json"
        user_profile.update_profile(
            equipment="dumbbell", goal="strength", add_exclusions=["Squat"], profile_file=profile_file
        )

        result = user_profile.reset_profile(profile_file=profile_file)

        assert result == {"equipment": None, "goal": None, "exclusions": []}

    def test_persists_the_reset(self, tmp_path):
        profile_file = tmp_path / "profile.json"
        user_profile.update_profile(equipment="dumbbell", profile_file=profile_file)
        user_profile.reset_profile(profile_file=profile_file)

        assert user_profile.get_profile(profile_file=profile_file) == {
            "equipment": None,
            "goal": None,
            "exclusions": [],
        }

    def test_returns_error_when_write_fails(self, tmp_path, monkeypatch):
        profile_file = tmp_path / "profile.json"

        def broken_write_text(self, *args, **kwargs):
            raise OSError("disk full")

        monkeypatch.setattr(type(profile_file), "write_text", broken_write_text)

        result = user_profile.reset_profile(profile_file=profile_file)
        assert "error" in result
