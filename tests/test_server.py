from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

import agent
import paths
import server

client = TestClient(server.app)


@pytest.fixture(autouse=True)
def clear_sessions():
    server.SESSIONS.clear()
    yield
    server.SESSIONS.clear()


class TestIndex:
    def test_serves_static_page(self):
        response = client.get("/")
        assert response.status_code == 200
        assert "Fitness Agent" in response.text


class TestChat:
    def test_creates_session_on_first_message(self):
        with patch.object(agent, "run_turn", return_value="hello there") as mock_run_turn:
            response = client.post(
                "/api/chat", json={"session_id": "s1", "user": "alice", "message": "hi"}
            )

        assert response.status_code == 200
        assert response.json() == {"reply": "hello there"}
        assert "s1" in server.SESSIONS
        messages = server.SESSIONS["s1"]
        assert messages[0] == {"role": "system", "content": agent.SYSTEM_PROMPT}
        assert messages[1] == {"role": "user", "content": "hi"}
        mock_run_turn.assert_called_once()

    def test_reuses_session_across_calls(self):
        with patch.object(agent, "run_turn", return_value="ok"):
            client.post("/api/chat", json={"session_id": "s1", "user": "alice", "message": "first"})
            client.post("/api/chat", json={"session_id": "s1", "user": "alice", "message": "second"})

        messages = server.SESSIONS["s1"]
        user_messages = [m["content"] for m in messages if m.get("role") == "user"]
        assert user_messages == ["first", "second"]

    def test_builds_dispatch_from_user(self):
        with (
            patch.object(server.tools, "build_dispatch", return_value={}) as mock_build,
            patch.object(agent, "run_turn", return_value="ok"),
        ):
            client.post("/api/chat", json={"session_id": "s1", "user": "alice", "message": "hi"})

        mock_build.assert_called_once_with(paths.profile_path("alice"), paths.history_path("alice"))

    def test_returns_error_and_pops_user_message_on_failure(self):
        with patch.object(agent, "run_turn", side_effect=RuntimeError("boom")):
            response = client.post(
                "/api/chat", json={"session_id": "s1", "user": "alice", "message": "hi"}
            )

        assert response.json() == {"error": "boom"}
        messages = server.SESSIONS["s1"]
        assert all(m.get("role") != "user" for m in messages)


class TestReset:
    def test_clears_session(self):
        with patch.object(agent, "run_turn", return_value="ok"):
            client.post("/api/chat", json={"session_id": "s1", "user": "alice", "message": "hi"})
        assert "s1" in server.SESSIONS

        response = client.post("/api/reset", json={"session_id": "s1"})

        assert response.json() == {"ok": True}
        assert "s1" not in server.SESSIONS

    def test_no_error_when_session_missing(self):
        response = client.post("/api/reset", json={"session_id": "missing"})
        assert response.json() == {"ok": True}
