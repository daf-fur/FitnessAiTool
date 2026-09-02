from pathlib import Path

import paths


class TestResolveUser:
    def test_explicit_user_wins(self, monkeypatch):
        monkeypatch.setenv("FITNESS_AGENT_USER", "env-user")
        monkeypatch.setattr(paths.getpass, "getuser", lambda: "os-user")
        assert paths.resolve_user("explicit-user") == "explicit-user"

    def test_falls_back_to_env_var(self, monkeypatch):
        monkeypatch.setenv("FITNESS_AGENT_USER", "env-user")
        monkeypatch.setattr(paths.getpass, "getuser", lambda: "os-user")
        assert paths.resolve_user() == "env-user"

    def test_falls_back_to_os_user(self, monkeypatch):
        monkeypatch.delenv("FITNESS_AGENT_USER", raising=False)
        monkeypatch.setattr(paths.getpass, "getuser", lambda: "os-user")
        assert paths.resolve_user() == "os-user"


class TestSanitizeUser:
    def test_leaves_safe_names_alone(self):
        assert paths.sanitize_user("alice-2") == "alice-2"

    def test_replaces_unsafe_characters(self):
        assert paths.sanitize_user("alice smith!") == "alice_smith"

    def test_neutralizes_path_traversal_attempts(self):
        safe = paths.sanitize_user("../../etc/passwd")
        assert "/" not in safe
        assert ".." not in safe

    def test_empty_input_falls_back_to_default(self):
        assert paths.sanitize_user("") == paths.DEFAULT_USER
        assert paths.sanitize_user(None) == paths.DEFAULT_USER


class TestUserPaths:
    def test_profile_path_is_scoped_under_data_dir(self):
        assert paths.profile_path("alice") == Path("data") / "alice" / "user_profile.json"

    def test_history_path_is_scoped_under_data_dir(self):
        assert paths.history_path("alice") == Path("data") / "alice" / "workout_history.json"

    def test_different_users_get_different_paths(self):
        assert paths.profile_path("alice") != paths.profile_path("bob")
