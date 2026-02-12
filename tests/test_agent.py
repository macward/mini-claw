"""Tests for agent loop."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from miniclaw.agent import AgentConfig, AgentLoop, StopReason
from miniclaw.tools import Tool, ToolResult, ToolRegistry


class MockTool(Tool):
    """Mock tool for testing."""

    def __init__(self, name: str = "mock", fail: bool = False):
        self._name = name
        self._fail = fail
        self.call_count = 0

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return "A mock tool"

    @property
    def parameters(self) -> dict:
        return {"type": "object", "properties": {}, "required": []}

    async def execute(self, **kwargs) -> ToolResult:
        self.call_count += 1
        if self._fail:
            return ToolResult(success=False, output="", error="Mock error")
        return ToolResult(success=True, output="Mock output")


def make_mock_response(content: str = None, tool_calls: list = None):
    """Create a mock Groq response."""
    message = MagicMock()
    message.content = content
    message.tool_calls = tool_calls
    message.model_dump = lambda: {
        "role": "assistant",
        "content": content,
        "tool_calls": [
            {"id": tc.id, "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
            for tc in (tool_calls or [])
        ] if tool_calls else None,
    }

    choice = MagicMock()
    choice.message = message

    response = MagicMock()
    response.choices = [choice]
    return response


def make_tool_call(tool_id: str, name: str, arguments: str = "{}"):
    """Create a mock tool call."""
    tc = MagicMock()
    tc.id = tool_id
    tc.function = MagicMock()
    tc.function.name = name
    tc.function.arguments = arguments
    return tc


@pytest.fixture
def registry() -> ToolRegistry:
    reg = ToolRegistry()
    reg.register(MockTool())
    return reg


@pytest.fixture
def mock_client() -> AsyncMock:
    return AsyncMock()


@pytest.mark.asyncio
async def test_simple_response(registry: ToolRegistry, mock_client: AsyncMock) -> None:
    """Test agent returns LLM response when no tools called."""
    mock_client.chat.completions.create.return_value = make_mock_response(
        content="Hello, I'm MiniClaw!"
    )

    agent = AgentLoop(registry, groq_client=mock_client)
    result = await agent.run("Hi")

    assert result.response == "Hello, I'm MiniClaw!"
    assert result.stop_reason == StopReason.COMPLETE
    assert result.turns == 1


@pytest.mark.asyncio
async def test_tool_execution(registry: ToolRegistry, mock_client: AsyncMock) -> None:
    """Test agent executes tool and continues."""
    mock_client.chat.completions.create.side_effect = [
        make_mock_response(tool_calls=[make_tool_call("1", "mock")]),
        make_mock_response(content="Done!"),
    ]

    agent = AgentLoop(registry, groq_client=mock_client)
    result = await agent.run("Do something")

    assert result.response == "Done!"
    assert result.stop_reason == StopReason.COMPLETE
    assert len(result.tool_calls) == 1


@pytest.mark.asyncio
async def test_max_turns(registry: ToolRegistry, mock_client: AsyncMock) -> None:
    """Test agent stops at max_turns."""
    call_count = 0

    def make_unique_response(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return make_mock_response(
            tool_calls=[make_tool_call(str(call_count), "mock", f'{{"n": {call_count}}}')]
        )

    mock_client.chat.completions.create.side_effect = make_unique_response

    config = AgentConfig(max_turns=3, max_repeated_calls=10)
    agent = AgentLoop(registry, config=config, groq_client=mock_client)
    result = await agent.run("Loop forever")

    assert result.stop_reason == StopReason.MAX_TURNS
    assert result.turns == 3


@pytest.mark.asyncio
async def test_consecutive_errors(mock_client: AsyncMock) -> None:
    """Test agent stops after consecutive errors."""
    registry = ToolRegistry()
    registry.register(MockTool(fail=True))

    call_count = 0

    def make_unique_response(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return make_mock_response(
            tool_calls=[make_tool_call(str(call_count), "mock", f'{{"n": {call_count}}}')]
        )

    mock_client.chat.completions.create.side_effect = make_unique_response

    config = AgentConfig(max_consecutive_errors=2, max_repeated_calls=10)
    agent = AgentLoop(registry, config=config, groq_client=mock_client)
    result = await agent.run("Fail")

    assert result.stop_reason == StopReason.CONSECUTIVE_ERRORS


@pytest.mark.asyncio
async def test_repeated_calls(registry: ToolRegistry, mock_client: AsyncMock) -> None:
    """Test agent stops on repeated identical calls."""
    mock_client.chat.completions.create.return_value = make_mock_response(
        tool_calls=[make_tool_call("1", "mock", '{"x": 1}')]
    )

    config = AgentConfig(max_repeated_calls=2)
    agent = AgentLoop(registry, config=config, groq_client=mock_client)
    result = await agent.run("Repeat")

    assert result.stop_reason == StopReason.REPEATED_CALL
