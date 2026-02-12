"""Tests for CLI."""

import os
import pytest

from miniclaw.cli import CLI
from miniclaw.agent import StopReason


@pytest.fixture
def cli() -> CLI:
    return CLI()


@pytest.fixture
def cli_with_env(monkeypatch) -> CLI:
    """CLI with mock GROQ_API_KEY set."""
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    return CLI()


def test_new_chat_id(cli: CLI) -> None:
    """Test chat ID generation."""
    assert cli.chat_id.startswith("cli-")
    assert len(cli.chat_id) == 12  # "cli-" + 8 hex chars


def test_reset_changes_chat_id(cli_with_env: CLI) -> None:
    """Test that reset generates a new chat_id."""
    old_id = cli_with_env.chat_id
    cli_with_env._reset()
    assert cli_with_env.chat_id != old_id
    assert cli_with_env.chat_id.startswith("cli-")


def test_handle_command_exit(cli: CLI) -> None:
    """Test exit commands return False."""
    assert cli._handle_command("/exit") is False
    assert cli._handle_command("/quit") is False
    assert cli._handle_command("exit") is False
    assert cli._handle_command("quit") is False


def test_handle_command_help(cli: CLI) -> None:
    """Test help command returns True."""
    assert cli._handle_command("/help") is True


def test_handle_command_reset(cli_with_env: CLI) -> None:
    """Test reset command returns True."""
    old_id = cli_with_env.chat_id
    assert cli_with_env._handle_command("/reset") is True
    assert cli_with_env.chat_id != old_id


def test_format_response_complete(cli: CLI) -> None:
    """Test response formatting for complete runs."""
    output = cli._format_response("Hello!", StopReason.COMPLETE, 1)
    assert "Hello!" in output
    assert "Stopped" not in output


def test_format_response_stopped(cli: CLI) -> None:
    """Test response formatting when stopped early."""
    output = cli._format_response("Partial", StopReason.MAX_TURNS, 5)
    assert "Partial" in output
    assert "Stopped: max_turns" in output
    assert "turns: 5" in output
