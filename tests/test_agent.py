from unittest.mock import patch

import agent


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
