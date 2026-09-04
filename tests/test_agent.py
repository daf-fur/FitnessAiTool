from unittest.mock import patch

import pytest

import agent
import paths


@pytest.fixture(autouse=True)
def restore_available_functions():
    original_functions = agent.AVAILABLE_FUNCTIONS
    original_model = agent.MODEL
    yield
    agent.AVAILABLE_FUNCTIONS = original_functions
    agent.MODEL = original_model


class FakeFunction:
    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments


class FakeToolCall:
    def __init__(self, call_id, name, arguments):
        self.id = call_id
        self.function = FakeFunction(name, arguments)


class FakeMessage:
    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls


class FakeChoice:
    def __init__(self, message):
        self.message = message


class FakeResponse:
    def __init__(self, message):
        self.choices = [FakeChoice(message)]


def _create_side_effect(messages):
    responses = [FakeResponse(m) for m in messages]

    def create(*args, **kwargs):
        return responses.pop(0)

    return create


class TestRunTurn:
    def test_returns_content_when_no_tool_calls(self):
        messages = [{"role": "user", "content": "hi"}]
        reply = FakeMessage(content="Hello there.")
        with patch.object(agent.client.chat.completions, "create", side_effect=_create_side_effect([reply])):
            result = agent.run_turn(messages)
            assert result == "Hello there."
            assert messages[-1] is reply

    def test_calls_tool_and_returns_final_content(self):
        tool_call = FakeToolCall("call_1", "lookup_exercise", '{"muscle_group": "chest"}')
        first = FakeMessage(tool_calls=[tool_call])
        second = FakeMessage(content="Here are chest exercises.")
        messages = [{"role": "user", "content": "chest exercises"}]

        stub = lambda muscle_group: [{"name": "Bench Press", "category": "Chest"}]  # noqa: E731
        with (
            patch.dict(agent.AVAILABLE_FUNCTIONS, {"lookup_exercise": stub}),
            patch.object(
                agent.client.chat.completions, "create", side_effect=_create_side_effect([first, second])
            ),
        ):
            result = agent.run_turn(messages)

        assert result == "Here are chest exercises."
        tool_messages = [m for m in messages if isinstance(m, dict) and m.get("role") == "tool"]
        assert len(tool_messages) == 1
        assert tool_messages[0]["tool_call_id"] == "call_1"
        assert "Bench Press" in tool_messages[0]["content"]

    def test_stops_after_max_iterations(self):
        tool_call = FakeToolCall("call_1", "lookup_exercise", '{"muscle_group": "chest"}')
        always_tool_calls = FakeMessage(tool_calls=[tool_call])
        responses = [always_tool_calls] * (agent.MAX_TOOL_ITERATIONS + 1)
        messages = [{"role": "user", "content": "chest exercises"}]

        stub_calls = []
        stub = lambda muscle_group: stub_calls.append(muscle_group) or []  # noqa: E731
        with (
            patch.dict(agent.AVAILABLE_FUNCTIONS, {"lookup_exercise": stub}),
            patch.object(
                agent.client.chat.completions, "create", side_effect=_create_side_effect(responses)
            ) as mock_create,
        ):
            agent.run_turn(messages)

        assert mock_create.call_count == agent.MAX_TOOL_ITERATIONS + 1
        assert len(stub_calls) == agent.MAX_TOOL_ITERATIONS


class TestRunAgent:
    def test_builds_system_and_user_messages(self):
        captured = {}

        def fake_run_turn(messages):
            captured["messages"] = messages
            return "reply"

        with patch.object(agent, "run_turn", side_effect=fake_run_turn):
            result = agent.run_agent("give me a leg day")

        assert result == "reply"
        assert captured["messages"][0] == {"role": "system", "content": agent.SYSTEM_PROMPT}
        assert captured["messages"][1] == {"role": "user", "content": "give me a leg day"}


class TestChat:
    def test_processes_message_then_exits(self, capsys):
        with (
            patch("builtins.input", side_effect=["give me a leg day", "exit"]),
            patch.object(agent, "run_turn", return_value="Here's a leg day.") as mock_run_turn,
        ):
            agent.chat()

        out = capsys.readouterr().out
        assert "Here's a leg day." in out
        assert mock_run_turn.call_count == 1
        sent_messages = mock_run_turn.call_args.args[0]
        assert sent_messages[-1] == {"role": "user", "content": "give me a leg day"}

    def test_skips_blank_input(self):
        with (
            patch("builtins.input", side_effect=["", "exit"]),
            patch.object(agent, "run_turn") as mock_run_turn,
        ):
            agent.chat()

        mock_run_turn.assert_not_called()

    def test_handles_run_turn_error_and_continues(self, capsys):
        with (
            patch("builtins.input", side_effect=["bad request", "exit"]),
            patch.object(agent, "run_turn", side_effect=RuntimeError("boom")),
        ):
            agent.chat()

        out = capsys.readouterr().out
        assert "Error: boom" in out

    def test_exits_on_keyboard_interrupt(self):
        with patch("builtins.input", side_effect=KeyboardInterrupt):
            agent.chat()


class TestMain:
    def test_parses_user_flag_and_calls_chat(self):
        with (
            patch("sys.argv", ["fitness-agent", "--user", "alice"]),
            patch.object(agent, "chat") as mock_chat,
        ):
            agent.main()

        mock_chat.assert_called_once_with(user="alice", model=None)

    def test_defaults_user_to_none(self):
        with (
            patch("sys.argv", ["fitness-agent"]),
            patch.object(agent, "chat") as mock_chat,
        ):
            agent.main()

        mock_chat.assert_called_once_with(user=None, model=None)

    def test_parses_model_flag_and_calls_chat(self):
        with (
            patch("sys.argv", ["fitness-agent", "--model", "gpt-4o"]),
            patch.object(agent, "chat") as mock_chat,
        ):
            agent.main()

        mock_chat.assert_called_once_with(user=None, model="gpt-4o")

    def test_list_users_prints_and_skips_chat(self, capsys):
        with (
            patch("sys.argv", ["fitness-agent", "--list-users"]),
            patch.object(agent.paths, "list_users", return_value=["alice", "bob"]),
            patch.object(agent, "chat") as mock_chat,
        ):
            agent.main()

        out = capsys.readouterr().out
        assert "alice" in out
        assert "bob" in out
        mock_chat.assert_not_called()

    def test_list_users_reports_when_empty(self, capsys):
        with (
            patch("sys.argv", ["fitness-agent", "--list-users"]),
            patch.object(agent.paths, "list_users", return_value=[]),
            patch.object(agent, "chat"),
        ):
            agent.main()

        out = capsys.readouterr().out
        assert "No saved users yet." in out


class TestUserScoping:
    def test_run_agent_rebuilds_dispatch_for_explicit_user(self):
        sentinel = object()
        with (
            patch.object(agent.tools, "build_dispatch", return_value=sentinel) as mock_build,
            patch.object(agent, "run_turn", return_value="reply"),
        ):
            agent.run_agent("hi", user="alice")

        mock_build.assert_called_once_with(paths.profile_path("alice"), paths.history_path("alice"))
        assert agent.AVAILABLE_FUNCTIONS is sentinel

    def test_run_agent_leaves_dispatch_unchanged_when_no_user(self):
        original = agent.AVAILABLE_FUNCTIONS
        with (
            patch.object(agent.tools, "build_dispatch") as mock_build,
            patch.object(agent, "run_turn", return_value="reply"),
        ):
            agent.run_agent("hi")

        mock_build.assert_not_called()
        assert agent.AVAILABLE_FUNCTIONS is original

    def test_chat_rebuilds_dispatch_for_resolved_user(self):
        sentinel = object()
        with (
            patch.object(agent.paths, "resolve_user", return_value="alice"),
            patch.object(agent.tools, "build_dispatch", return_value=sentinel) as mock_build,
            patch("builtins.input", side_effect=["exit"]),
        ):
            agent.chat(user="alice")

        mock_build.assert_called_once_with(paths.profile_path("alice"), paths.history_path("alice"))
        assert agent.AVAILABLE_FUNCTIONS is sentinel

    def test_run_agent_overrides_model_when_given(self):
        with patch.object(agent, "run_turn", return_value="reply"):
            agent.run_agent("hi", model="gpt-4o")

        assert agent.MODEL == "gpt-4o"

    def test_run_agent_leaves_model_unchanged_when_not_given(self):
        original = agent.MODEL
        with patch.object(agent, "run_turn", return_value="reply"):
            agent.run_agent("hi")

        assert agent.MODEL == original

    def test_chat_overrides_model_when_given(self):
        with patch("builtins.input", side_effect=["exit"]):
            agent.chat(model="gpt-4o")

        assert agent.MODEL == "gpt-4o"
